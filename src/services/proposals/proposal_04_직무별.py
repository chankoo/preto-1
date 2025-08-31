#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job, job_l1_order, job_l2_order
from services.helpers.utils import get_level1_ancestor, get_level2_ancestor

def create_figure_and_df():
    """
    제안 4-2: 직무별 경험 자산 현황 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    current_emps_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y'].copy()
    current_emps_df['TENURE_YEARS'] = current_emps_df['DURATION'] / 365.25

    current_job = job_info_df[job_info_df['JOB_APP_END_DATE'].isnull()][['EMP_ID', 'JOB_ID']]
    analysis_df = pd.merge(current_emps_df, current_job, on='EMP_ID', how='left')

    job_name_map = job_df.set_index('JOB_ID')['JOB_NAME'].to_dict()
    analysis_df['JOB_L1_NAME'] = analysis_df['JOB_ID'].apply(lambda x: job_name_map.get(get_level1_ancestor(x, job_df_indexed, parent_map_job)))
    analysis_df['JOB_L2_NAME'] = analysis_df['JOB_ID'].apply(lambda x: job_name_map.get(get_level2_ancestor(x, job_df_indexed, parent_map_job)))

    analysis_df = analysis_df.dropna(subset=['JOB_L1_NAME', 'JOB_L2_NAME', 'TENURE_YEARS'])

    # --- 3. Plotly 인터랙티브 그래프 생성 (그래프용 데이터 준비) ---
    analysis_df['TENURE_BIN'] = pd.cut(analysis_df['TENURE_YEARS'], bins=range(0, int(analysis_df['TENURE_YEARS'].max()) + 2), right=False, labels=range(0, int(analysis_df['TENURE_YEARS'].max()) + 1))
    job_l1_summary = analysis_df.groupby(['JOB_L1_NAME', 'TENURE_BIN'], observed=False).size().reset_index(name='COUNT')
    job_l2_summary = analysis_df.groupby(['JOB_L1_NAME', 'JOB_L2_NAME', 'TENURE_BIN'], observed=False).size().reset_index(name='COUNT')

    x_max = analysis_df['TENURE_YEARS'].max()
    fixed_x_range = [-0.5, x_max + 1.5]

    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, job_l1_name in enumerate(job_l1_order):
        df_filtered = job_l1_summary[job_l1_summary['JOB_L1_NAME'] == job_l1_name]
        fig.add_trace(go.Bar(x=df_filtered['TENURE_BIN'], y=df_filtered['COUNT'], name=job_l1_name, marker_color=colors[i]))
    job_l2_traces_map = {}
    trace_idx_counter = len(fig.data)
    for job_l1_name in job_l1_order:
        job_l1_df = job_l2_summary[job_l2_summary['JOB_L1_NAME'] == job_l1_name]
        jobs_in_l1 = [j for j in job_l2_order if j in job_l1_df['JOB_L2_NAME'].unique()]
        job_l2_traces_map[job_l1_name] = []
        for j, job_l2_name in enumerate(jobs_in_l1):
            df_filtered = job_l1_df[job_l1_df['JOB_L2_NAME'] == job_l2_name]
            fig.add_trace(go.Bar(x=df_filtered['TENURE_BIN'], y=df_filtered['COUNT'], name=job_l2_name, visible=False, marker_color=colors[j % len(colors)], showlegend=False))
            job_l2_traces_map[job_l1_name].append(trace_idx_counter)
            trace_idx_counter += 1
    buttons = []
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*len(job_l1_order) + [False]*(len(fig.data)-len(job_l1_order))}, {'title': '전체 직무별 근속년수 분포', 'barmode': 'stack', 'showlegend': True}]))
    for job_l1_name in job_l1_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in job_l2_traces_map.get(job_l1_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{job_l1_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{job_l1_name} 내 직무별 근속년수 분포', 'barmode': 'stack', 'showlegend': False}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직무별 근속년수 분포 현황', xaxis_title='근속년수 (년)', yaxis_title='직원 수', font_size=14, height=700,
        bargap=0.2, barmode='stack', legend_title_text='직무',
        annotations=[dict(text="직무 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis_range=fixed_x_range
    )
    fig.update_xaxes(dtick=1)

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. 근속년수 구간을 새로 정의
    tenure_bins_agg = [-np.inf, 3, 7, np.inf]
    tenure_labels_agg = ['3년 이하', '3년초과~7년이하', '7년초과']
    analysis_df['TENURE_GROUP'] = pd.cut(analysis_df['TENURE_YEARS'], bins=tenure_bins_agg, labels=tenure_labels_agg)

    # 2. 피벗 테이블 생성
    aggregate_df = pd.pivot_table(
        analysis_df,
        index='TENURE_GROUP',
        columns='JOB_L1_NAME',
        values='EMP_ID',
        aggfunc='count',
        margins=True,
        margins_name='합계',
        observed=False
    ).fillna(0).astype(int)

    # 3. '합계' 컬럼을 맨 앞으로 이동
    if '합계' in aggregate_df.columns:
        cols = ['합계'] + [col for col in aggregate_df.columns if col != '합계']
        aggregate_df = aggregate_df[cols]
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




