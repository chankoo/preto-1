#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.detailed_working_info_table import detailed_work_info_df
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df, position_order
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job, job_l1_order, job_l2_order
from services.helpers.utils import get_level1_ancestor, get_level2_ancestor

def create_figure_and_df():
    """
    제안 16-2: 직무별/직위별 주말 근무 패턴 분석 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    work_records = detailed_work_info_df.copy()
    work_records['DATE'] = pd.to_datetime(work_records['DATE'])
    work_records['DAY_OF_WEEK'] = work_records['DATE'].dt.weekday
    weekend_work_df = work_records[
        (~work_records['WORK_ETC'].isin(['휴가', '주말 휴무', '비번', '휴무'])) &
        (work_records['DAY_OF_WEEK'] >= 5)
    ].copy()
    weekend_work_df['PAY_PERIOD'] = weekend_work_df['DATE'].dt.strftime('%Y-%m')

    monthly_weekend_days = weekend_work_df.groupby(['EMP_ID', 'PAY_PERIOD']).size().reset_index(name='WEEKEND_WORK_DAYS')
    avg_weekend_days = monthly_weekend_days.groupby('EMP_ID')['WEEKEND_WORK_DAYS'].mean().reset_index()

    analysis_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y'][['EMP_ID']].copy()
    analysis_df = pd.merge(analysis_df, avg_weekend_days, on='EMP_ID', how='left').fillna(0)

    current_positions = position_info_df[position_info_df['GRADE_END_DATE'].isnull()]
    current_job = job_info_df[job_info_df['JOB_APP_END_DATE'].isnull()]
    analysis_df = pd.merge(analysis_df, current_positions[['EMP_ID', 'POSITION_ID']], on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, current_job[['EMP_ID', 'JOB_ID']], on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, position_df[['POSITION_ID', 'POSITION_NAME']], on='POSITION_ID', how='left')

    job_name_map = job_df.set_index('JOB_ID')['JOB_NAME'].to_dict()
    analysis_df['JOB_L1_NAME'] = analysis_df['JOB_ID'].apply(lambda x: job_name_map.get(get_level1_ancestor(x, job_df_indexed, parent_map_job)))
    analysis_df['JOB_L2_NAME'] = analysis_df['JOB_ID'].apply(lambda x: job_name_map.get(get_level2_ancestor(x, job_df_indexed, parent_map_job)))

    analysis_df = analysis_df.dropna(subset=['JOB_L1_NAME', 'JOB_L2_NAME', 'POSITION_NAME'])

    job_l1_summary = analysis_df.groupby(['JOB_L1_NAME', 'POSITION_NAME'], observed=False)['WEEKEND_WORK_DAYS'].mean().reset_index()
    job_l2_summary = analysis_df.groupby(['JOB_L1_NAME', 'JOB_L2_NAME', 'POSITION_NAME'], observed=False)['WEEKEND_WORK_DAYS'].mean().reset_index()

    y_max = pd.concat([job_l1_summary['WEEKEND_WORK_DAYS'], job_l2_summary['WEEKEND_WORK_DAYS']]).max()
    fixed_y_range = [0, y_max * 1.2] if y_max > 0 else [0, 1]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, pos_name in enumerate(position_order):
        df_filtered = job_l1_summary[job_l1_summary['POSITION_NAME'] == pos_name]
        fig.add_trace(go.Bar(x=df_filtered['JOB_L1_NAME'], y=df_filtered['WEEKEND_WORK_DAYS'], name=pos_name, marker_color=colors[i], text=df_filtered['WEEKEND_WORK_DAYS'].round(2), textposition='outside'))
    job_l2_traces_map = {}
    trace_idx_counter = len(fig.data)
    for job_l1_name in job_l1_order:
        job_l1_df = job_l2_summary[job_l2_summary['JOB_L1_NAME'] == job_l1_name]
        job_l2_traces_map[job_l1_name] = []
        for j, pos_name in enumerate(position_order):
            df_filtered = job_l1_df[job_l1_df['POSITION_NAME'] == pos_name]
            fig.add_trace(go.Bar(x=df_filtered['JOB_L2_NAME'], y=df_filtered['WEEKEND_WORK_DAYS'], name=pos_name, visible=False, marker_color=colors[j], text=df_filtered['WEEKEND_WORK_DAYS'].round(2), textposition='outside'))
            job_l2_traces_map[job_l1_name].append(trace_idx_counter)
            trace_idx_counter += 1
    buttons = []
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*len(position_order) + [False]*(len(fig.data)-len(position_order))}, {'title': '전체 직무별 월 평균 주말 근무일수', 'xaxis.title': 'Job Level 1'}]))
    for job_l1_name in job_l1_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in job_l2_traces_map.get(job_l1_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{job_l1_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{job_l1_name} 내 직무별 월 평균 주말 근무일수', 'xaxis.title': 'Job Level 2'}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직무별/직위별 월 평균 주말 근무일수',
        yaxis_title='월 평균 주말 근무일수 (일)', font_size=14, height=700,
        barmode='group', legend_title_text='직위',
        annotations=[dict(text="직무 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis_range=fixed_y_range
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. 피벗 테이블 생성
    aggregate_df = job_l1_summary.pivot_table(
        index='POSITION_NAME',
        columns='JOB_L1_NAME',
        values='WEEKEND_WORK_DAYS',
        observed=False
    )

    # 2. '전체 평균' 컬럼 추가
    overall_summary = analysis_df.groupby('POSITION_NAME', observed=False)['WEEKEND_WORK_DAYS'].mean()
    aggregate_df['전체 평균'] = overall_summary

    # 3. 컬럼/행 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in job_l1_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols]
    aggregate_df = aggregate_df.reindex(position_order).round(2)
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




