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
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure_and_df():
    """
    제안 16: 주말 근무 패턴 분석 그래프 및 피벗 테이블을 생성합니다.
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

    current_depts = department_info_df[department_info_df['DEP_APP_END_DATE'].isnull()]
    current_positions = position_info_df[position_info_df['GRADE_END_DATE'].isnull()]
    analysis_df = pd.merge(analysis_df, current_depts[['EMP_ID', 'DEP_ID']], on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, current_positions[['EMP_ID', 'POSITION_ID']], on='EMP_ID', how='left')

    parent_info = analysis_df['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    analysis_df = pd.concat([analysis_df, parent_info], axis=1)
    analysis_df['OFFICE_NAME'] = analysis_df['OFFICE_NAME'].fillna('(Division 직속)')
    analysis_df = pd.merge(analysis_df, position_df[['POSITION_ID', 'POSITION_NAME']], on='POSITION_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'])

    div_summary = analysis_df.groupby(['DIVISION_NAME', 'POSITION_NAME'], observed=False)['WEEKEND_WORK_DAYS'].mean().reset_index()
    office_summary = analysis_df.groupby(['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'], observed=False)['WEEKEND_WORK_DAYS'].mean().reset_index()

    div_summary['DIVISION_NAME'] = pd.Categorical(div_summary['DIVISION_NAME'], categories=division_order, ordered=True)
    office_summary['OFFICE_NAME'] = pd.Categorical(office_summary['OFFICE_NAME'], categories=office_order, ordered=True)
    div_summary = div_summary.sort_values('DIVISION_NAME')
    office_summary = office_summary.sort_values('OFFICE_NAME')

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    y_max = pd.concat([div_summary['WEEKEND_WORK_DAYS'], office_summary['WEEKEND_WORK_DAYS']]).max()
    fixed_y_range = [0, y_max * 1.2]
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, pos_name in enumerate(position_order):
        df_filtered = div_summary[div_summary['POSITION_NAME'] == pos_name]
        fig.add_trace(go.Bar(
            x=df_filtered['DIVISION_NAME'], y=df_filtered['WEEKEND_WORK_DAYS'], name=pos_name, marker_color=colors[i],
            text=df_filtered['WEEKEND_WORK_DAYS'].round(2), textposition='outside'
        ))
    office_traces_map = {}
    trace_idx_counter = len(fig.data)
    for div_name in division_order:
        office_div_df = office_summary[office_summary['DIVISION_NAME'] == div_name]
        office_traces_map[div_name] = []
        for j, pos_name in enumerate(position_order):
            df_filtered = office_div_df[office_div_df['POSITION_NAME'] == pos_name]
            fig.add_trace(go.Bar(
                x=df_filtered['OFFICE_NAME'], y=df_filtered['WEEKEND_WORK_DAYS'], name=pos_name, visible=False, marker_color=colors[j],
                text=df_filtered['WEEKEND_WORK_DAYS'].round(2), textposition='outside'
            ))
            office_traces_map[div_name].append(trace_idx_counter)
            trace_idx_counter += 1
    buttons = []
    visible_div = [True]*len(position_order) + [False]*(len(fig.data)-len(position_order))
    buttons.append(dict(label='전체', method='update', 
                        args=[{'visible': visible_div},
                              {'title': '전체 Division별 월 평균 주말 근무일수'}]))
    for div_name in division_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in office_traces_map.get(div_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{div_name}', method='update',
                            args=[{'visible': visibility_mask},
                                  {'title': f'{div_name} 내 Office별 월 평균 주말 근무일수'}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='조직별/직위별 월 평균 주말 근무일수',
        yaxis_title='월 평균 주말 근무일수 (일)',
        font_size=14, height=700,
        barmode='group', legend_title_text='직위',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis_range=fixed_y_range
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. 피벗 테이블 생성
    aggregate_df = div_summary.pivot_table(
        index='POSITION_NAME',
        columns='DIVISION_NAME',
        values='WEEKEND_WORK_DAYS',
        observed=False
    )

    # 2. '전체 평균' 컬럼 추가
    overall_summary = analysis_df.groupby('POSITION_NAME', observed=False)['WEEKEND_WORK_DAYS'].mean()
    aggregate_df['전체 평균'] = overall_summary

    # 3. 컬럼/행 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in division_order if col in aggregate_df.columns]
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




