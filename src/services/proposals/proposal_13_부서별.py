#!/usr/bin/env python
# coding: utf-8

# In[6]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure_and_df():
    """
    제안 13: 조직 워라밸 변화 추이 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    daily_work_df = daily_work_info_df.copy()
    daily_work_df['DATE'] = pd.to_datetime(daily_work_df['DATE'])
    daily_work_df['PAY_PERIOD'] = daily_work_df['DATE'].dt.strftime('%Y-%m')
    dept_info_sorted = department_info_df.sort_values(['DEP_APP_START_DATE', 'EMP_ID'])
    analysis_df = daily_work_df.sort_values(['DATE', 'EMP_ID'])
    analysis_df = pd.merge_asof(
        analysis_df, dept_info_sorted[['EMP_ID', 'DEP_APP_START_DATE', 'DEP_ID']],
        left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward'
    )
    parent_info = analysis_df['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    analysis_df = pd.concat([analysis_df, parent_info], axis=1)
    analysis_df['OFFICE_NAME'] = analysis_df['OFFICE_NAME'].fillna('(Division 직속)')
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])
    analysis_df['DIVISION_NAME'] = pd.Categorical(analysis_df['DIVISION_NAME'], categories=division_order, ordered=True)
    analysis_df = analysis_df.sort_values('DIVISION_NAME')

    # --- 3. 계층별 데이터 집계 ---
    div_monthly_summary = analysis_df.groupby(['DIVISION_NAME', 'PAY_PERIOD'], observed=True).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'), HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    div_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (div_monthly_summary['TOTAL_OVERTIME_MINUTES'] / div_monthly_summary['HEADCOUNT']) / 60
    office_monthly_summary = analysis_df.groupby(['DIVISION_NAME', 'OFFICE_NAME', 'PAY_PERIOD'], observed=True).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'), HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    office_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (office_monthly_summary['TOTAL_OVERTIME_MINUTES'] / office_monthly_summary['HEADCOUNT']) / 60

    all_overtime_values = pd.concat([div_monthly_summary['AVG_OVERTIME_PER_PERSON'], office_monthly_summary['AVG_OVERTIME_PER_PERSON']])
    y_min, y_max = (all_overtime_values.min(), all_overtime_values.max()) if not all_overtime_values.empty else (0, 0)
    y_padding = (y_max - y_min) * 0.1 if (y_max - y_min) > 0 else 10
    fixed_y_range = [y_min - y_padding, y_max + y_padding]

    # --- 4. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly

    for i, div_name in enumerate(division_order):
        df_filtered = div_monthly_summary[div_monthly_summary['DIVISION_NAME'] == div_name]
        if not df_filtered.empty:
            fig.add_trace(go.Scatter(x=df_filtered['PAY_PERIOD'], y=df_filtered['AVG_OVERTIME_PER_PERSON'], mode='lines+markers', name=div_name, line=dict(color=colors[i]), legendgroup='divisions'))

    office_traces_map = {}
    for i, div_name in enumerate(division_order):
        office_df = office_monthly_summary[office_monthly_summary['DIVISION_NAME'] == div_name]
        sorted_offices = [o for o in office_order if o in office_df['OFFICE_NAME'].unique()]
        office_traces_map[div_name] = []
        for j, office_name in enumerate(sorted_offices):
            df_filtered = office_df[office_df['OFFICE_NAME'] == office_name]
            if not df_filtered.empty:
                fig.add_trace(go.Scatter(x=df_filtered['PAY_PERIOD'], y=df_filtered['AVG_OVERTIME_PER_PERSON'], mode='lines+markers', name=office_name, visible=False, line=dict(color=colors[j % len(colors)]), legendgroup=div_name))

    buttons = []
    visible_div = [True]*len(division_order) + [False]*(len(fig.data)-len(division_order))
    buttons.append(dict(label='전체', method='update', args=[{'visible': visible_div}, {'title': '전체 Division별 월 평균 초과근무 시간 추이'}]))

    trace_idx_counter = len(division_order)
    for div_name in division_order:
        visibility_mask = [False] * len(fig.data)
        # --- 수정된 부분: office_summary -> office_monthly_summary ---
        offices_in_div = [o for o in office_order if o in office_monthly_summary[office_monthly_summary['DIVISION_NAME'] == div_name]['OFFICE_NAME'].unique()]
        # --- 수정 완료 ---
        num_offices = len(offices_in_div)
        for i in range(num_offices):
            visibility_mask[trace_idx_counter + i] = True

        buttons.append(dict(label=f'{div_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{div_name} 내 Office별 월 평균 초과근무 시간 추이'}]))
        trace_idx_counter += num_offices

    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='조직별 월 평균 1인당 초과근무 시간 드릴다운 분석',
        xaxis_title='월(YYYY-MM)', yaxis_title='1인당 평균 초과근무 (시간)',
        font_size=14, height=700,
        legend_title_text='조직',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis_range=['2019-12', '2026-01'],
        yaxis_range=fixed_y_range
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. '전체 평균' 계산을 위한 데이터 준비
    overall_monthly_summary = analysis_df.groupby('PAY_PERIOD', observed=False).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'),
        HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    overall_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (overall_monthly_summary['TOTAL_OVERTIME_MINUTES'] / overall_monthly_summary['HEADCOUNT']) / 60

    # 2. 연도별로 데이터 집계
    div_monthly_summary['YEAR'] = pd.to_datetime(div_monthly_summary['PAY_PERIOD']).dt.year
    yearly_summary = div_monthly_summary.groupby(['YEAR', 'DIVISION_NAME'], observed=False)['AVG_OVERTIME_PER_PERSON'].mean().reset_index()

    overall_monthly_summary['YEAR'] = pd.to_datetime(overall_monthly_summary['PAY_PERIOD']).dt.year
    overall_yearly_summary = overall_monthly_summary.groupby('YEAR')['AVG_OVERTIME_PER_PERSON'].mean()

    # 3. 피벗 테이블 생성 및 '전체 평균' 추가
    aggregate_df = yearly_summary.pivot_table(
        index='YEAR',
        columns='DIVISION_NAME',
        values='AVG_OVERTIME_PER_PERSON',
        observed=False
    )
    aggregate_df['전체 평균'] = overall_yearly_summary

    # 4. 연도 필터링 및 정렬
    aggregate_df = aggregate_df.reindex(range(2020, 2026)).sort_index()

    # 5. 컬럼 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in division_order if col in aggregate_df.columns]
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




