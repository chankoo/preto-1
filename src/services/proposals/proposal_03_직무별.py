#!/usr/bin/env python
# coding: utf-8

# In[2]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.position_table import position_df
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job, job_l1_order, job_l2_order
from services.helpers.utils import calculate_age, get_level1_ancestor, get_level2_ancestor

def create_figure_and_df():
    """
    제안 3-2: 직무별/직위별 연령 분포 분석 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    current_emps_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y'].copy()
    current_emps_df['AGE'] = current_emps_df['PERSONAL_ID'].apply(calculate_age)

    current_positions = position_info_df[position_info_df['GRADE_END_DATE'].isnull()][['EMP_ID', 'POSITION_ID']]
    current_job = job_info_df[job_info_df['JOB_APP_END_DATE'].isnull()][['EMP_ID', 'JOB_ID']]

    analysis_df = pd.merge(current_emps_df, current_positions, on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, current_job, on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID', how='left')

    job_name_map = job_df.set_index('JOB_ID')['JOB_NAME'].to_dict()
    analysis_df['JOB_L1_NAME'] = analysis_df['JOB_ID'].apply(lambda x: job_name_map.get(get_level1_ancestor(x, job_df_indexed, parent_map_job)))
    analysis_df['JOB_L2_NAME'] = analysis_df['JOB_ID'].apply(lambda x: job_name_map.get(get_level2_ancestor(x, job_df_indexed, parent_map_job)))

    analysis_df = analysis_df.dropna(subset=['POSITION_NAME', 'JOB_L1_NAME', 'JOB_L2_NAME', 'AGE'])

    position_order = ['Staff', 'Manager', 'Director', 'C-Level']
    analysis_df['POSITION_NAME'] = pd.Categorical(analysis_df['POSITION_NAME'], categories=position_order, ordered=True)
    analysis_df['JOB_L1_NAME'] = pd.Categorical(analysis_df['JOB_L1_NAME'], categories=job_l1_order, ordered=True)
    analysis_df['JOB_L2_NAME'] = pd.Categorical(analysis_df['JOB_L2_NAME'], categories=job_l2_order, ordered=True)
    analysis_df = analysis_df.sort_values(['JOB_L1_NAME', 'JOB_L2_NAME', 'POSITION_NAME'])

    y_min, y_max = analysis_df['AGE'].min(), analysis_df['AGE'].max()
    fixed_y_range = [y_min - 5, y_max + 5]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly

    for i, job_l1_name in enumerate(job_l1_order):
        df_filtered = analysis_df[analysis_df['JOB_L1_NAME'] == job_l1_name]
        fig.add_trace(go.Box(x=df_filtered['POSITION_NAME'], y=df_filtered['AGE'], name=job_l1_name, marker_color=colors[i]))

    job_l2_traces_map = {}
    trace_idx_counter = len(fig.data)
    for i, job_l1_name in enumerate(job_l1_order):
        job_l1_df = analysis_df[analysis_df['JOB_L1_NAME'] == job_l1_name]
        jobs_in_l1 = [j for j in job_l2_order if j in job_l1_df['JOB_L2_NAME'].unique()]
        job_l2_traces_map[job_l1_name] = []
        for j, job_l2_name in enumerate(jobs_in_l1):
            df_filtered = job_l1_df[job_l1_df['JOB_L2_NAME'] == job_l2_name]
            fig.add_trace(go.Box(
                x=df_filtered['POSITION_NAME'], y=df_filtered['AGE'], name=job_l2_name, 
                visible=False, marker_color=colors[j % len(colors)]
            ))
            job_l2_traces_map[job_l1_name].append(trace_idx_counter)
            trace_idx_counter += 1

    buttons = []
    buttons.append(dict(label='전체', method='update', 
                        args=[{'visible': [True]*len(job_l1_order) + [False]*(len(fig.data)-len(job_l1_order))},
                              {'title': '전체 직무의 직위별 연령 분포', 'legend_title_text': 'Job Level 1'}]))
    for job_l1_name in job_l1_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in job_l2_traces_map.get(job_l1_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{job_l1_name}', method='update',
                            args=[{'visible': visibility_mask},
                                  {'title': f'{job_l1_name} 내 직위별 연령 분포', 'legend_title_text': 'Job Level 2'}]))

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='직무별/직위별 연령 분포 현황',
        xaxis_title='직위', yaxis_title='연령',
        font_size=14, height=700,
        boxmode='group',
        legend_title_text='Job Level 1',
        annotations=[dict(text="직무 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis_range=fixed_y_range
    )

    # --- aggregate_df 생성 ---
    aggregate_df = analysis_df.pivot_table(
        index='POSITION_NAME',
        columns='JOB_L1_NAME',
        values='AGE',
        aggfunc='mean',
        observed=False
    ).round(2)

    # 행 순서 고정
    aggregate_df = aggregate_df.reindex(position_order)

    return fig, aggregate_df

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




