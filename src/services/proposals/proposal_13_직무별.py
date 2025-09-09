#!/usr/bin/env python
# coding: utf-8

# In[4]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job, job_l1_order, job_l2_order
from services.helpers.utils import get_level1_ancestor, get_level2_ancestor

def create_figure_and_df():
    """
    제안 13-2: 직무별 워라밸 변화 추이 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    daily_work_df = daily_work_info_df.copy()
    daily_work_df['DATE'] = pd.to_datetime(daily_work_df['DATE'])
    daily_work_df['PAY_PERIOD'] = daily_work_df['DATE'].dt.strftime('%Y-%m')

    job_info_sorted = job_info_df.sort_values('JOB_APP_START_DATE')
    analysis_df = daily_work_df.sort_values('DATE')
    analysis_df = pd.merge_asof(
        analysis_df, job_info_sorted[['EMP_ID', 'JOB_APP_START_DATE', 'JOB_ID']],
        left_on='DATE', right_on='JOB_APP_START_DATE', by='EMP_ID', direction='backward'
    )
    job_name_map = job_df.set_index('JOB_ID')['JOB_NAME'].to_dict()
    analysis_df['JOB_L1_NAME'] = analysis_df['JOB_ID'].apply(lambda x: job_name_map.get(get_level1_ancestor(x, job_df_indexed, parent_map_job)))
    analysis_df['JOB_L2_NAME'] = analysis_df['JOB_ID'].apply(lambda x: job_name_map.get(get_level2_ancestor(x, job_df_indexed, parent_map_job)))
    analysis_df = analysis_df.dropna(subset=['JOB_L1_NAME', 'JOB_L2_NAME'])

    # --- 3. 계층별 데이터 집계 ---
    job_l1_monthly_summary = analysis_df.groupby(['JOB_L1_NAME', 'PAY_PERIOD'], observed=False).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'), HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    job_l1_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (job_l1_monthly_summary['TOTAL_OVERTIME_MINUTES'] / job_l1_monthly_summary['HEADCOUNT']) / 60

    job_l2_monthly_summary = analysis_df.groupby(['JOB_L1_NAME', 'JOB_L2_NAME', 'PAY_PERIOD'], observed=False).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'), HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    job_l2_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (job_l2_monthly_summary['TOTAL_OVERTIME_MINUTES'] / job_l2_monthly_summary['HEADCOUNT']) / 60

    all_overtime_values = pd.concat([job_l1_monthly_summary['AVG_OVERTIME_PER_PERSON'], job_l2_monthly_summary['AVG_OVERTIME_PER_PERSON']])
    y_min, y_max = (all_overtime_values.min(), all_overtime_values.max()) if not all_overtime_values.empty else (0, 0)
    y_padding = (y_max - y_min) * 0.1 if (y_max - y_min) > 0 else 10
    fixed_y_range = [y_min - y_padding, y_max + y_padding]

    # --- 4. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, job_l1_name in enumerate(job_l1_order):
        df_filtered = job_l1_monthly_summary[job_l1_monthly_summary['JOB_L1_NAME'] == job_l1_name]
        if not df_filtered.empty:
            fig.add_trace(go.Scatter(x=df_filtered['PAY_PERIOD'], y=df_filtered['AVG_OVERTIME_PER_PERSON'], mode='lines+markers', name=job_l1_name, line=dict(color=colors[i])))
    job_l2_traces_map = {}
    trace_idx_counter = len(fig.data)
    for job_l1_name in job_l1_order:
        job_l2_df = job_l2_monthly_summary[job_l2_monthly_summary['JOB_L1_NAME'] == job_l1_name]
        jobs_in_l1 = [j for j in job_l2_order if j in job_l2_df['JOB_L2_NAME'].unique()]
        job_l2_traces_map[job_l1_name] = []
        for j, job_l2_name in enumerate(jobs_in_l1):
            df_filtered = job_l2_df[job_l2_df['JOB_L2_NAME'] == job_l2_name]
            if not df_filtered.empty:
                fig.add_trace(go.Scatter(x=df_filtered['PAY_PERIOD'], y=df_filtered['AVG_OVERTIME_PER_PERSON'], mode='lines+markers', name=job_l2_name, visible=False, line=dict(color=colors[j % len(colors)])))
                job_l2_traces_map[job_l1_name].append(trace_idx_counter)
                trace_idx_counter += 1
    buttons = []
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*len(job_l1_order) + [False]*(len(fig.data)-len(job_l1_order))}, {'title': '전체 직무별 월 평균 초과근무 시간 추이'}]))
    for job_l1_name in job_l1_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in job_l2_traces_map.get(job_l1_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{job_l1_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{job_l1_name} 내 직무별 월 평균 초과근무 시간 추이'}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직무별 월 평균 1인당 초과근무 시간 드릴다운 분석',
        xaxis_title='월(YYYY-MM)', yaxis_title='1인당 평균 초과근무 (시간)',
        font_size=14, height=700,
        legend_title_text='직무',
        annotations=[dict(text="직무 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis_range=['2019-12', '2026-01'],
        yaxis_range=fixed_y_range
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. '전체 평균' 계산을 위한 데이터 준비
    overall_monthly_summary = analysis_df.groupby('PAY_PERIOD', observed=False).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'), HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    overall_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (overall_monthly_summary['TOTAL_OVERTIME_MINUTES'] / overall_monthly_summary['HEADCOUNT']) / 60

    # 2. 연도별로 데이터 집계
    job_l1_monthly_summary['YEAR'] = pd.to_datetime(job_l1_monthly_summary['PAY_PERIOD']).dt.year
    yearly_summary = job_l1_monthly_summary.groupby(['YEAR', 'JOB_L1_NAME'], observed=False)['AVG_OVERTIME_PER_PERSON'].mean().reset_index()

    overall_monthly_summary['YEAR'] = pd.to_datetime(overall_monthly_summary['PAY_PERIOD']).dt.year
    overall_yearly_summary = overall_monthly_summary.groupby('YEAR')['AVG_OVERTIME_PER_PERSON'].mean()

    # 3. 피벗 테이블 생성 및 '전체 평균' 추가
    aggregate_df = yearly_summary.pivot_table(
        index='YEAR',
        columns='JOB_L1_NAME',
        values='AVG_OVERTIME_PER_PERSON',
        observed=False
    )
    aggregate_df['전체 평균'] = overall_yearly_summary

    # 4. 연도 필터링 및 정렬
    aggregate_df = aggregate_df.reindex(range(2020, 2026)).sort_index()

    # 5. 컬럼 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in job_l1_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols].round(2)
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




