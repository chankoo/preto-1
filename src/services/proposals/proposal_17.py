#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.Time_Attendance.detailed_working_info_table import detailed_work_info_df
from services.tables.Time_Attendance.leave_type_table import leave_type_df
from services.tables.Time_Attendance.detailed_leave_info_table import detailed_leave_info_df
from services.tables.Time_Attendance.working_info_table import work_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import division_order, dept_level_map, parent_map_dept, dept_name_map
from services.helpers.utils import find_division_name_for_dept

def create_figure():
    """
    제안 17: 조직의 주간 리듬 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    start_date_filter = pd.to_datetime('2022-01-01')

    # 2-1. 데이터 준비 (일반 근무 직원 & 특정 기간 필터링)
    normal_work_emp_ids = work_info_df[work_info_df['WORK_SYS_ID'] == 'WS001']['EMP_ID'].unique()

    overtime_df = daily_work_info_df[
        (daily_work_info_df['EMP_ID'].isin(normal_work_emp_ids)) &
        (pd.to_datetime(daily_work_info_df['DATE']) >= start_date_filter)
    ].copy()
    overtime_df['DAY_OF_WEEK'] = overtime_df['DATE'].dt.day_name()

    annual_leave_id = leave_type_df[leave_type_df['LEAVE_TYPE_NAME'] == '연차휴가']['LEAVE_TYPE_ID'].iloc[0]
    leave_df = detailed_leave_info_df[
        (detailed_leave_info_df['LEAVE_TYPE_ID'] == annual_leave_id) &
        (detailed_leave_info_df['EMP_ID'].isin(normal_work_emp_ids)) &
        (pd.to_datetime(detailed_leave_info_df['DATE']) >= start_date_filter)
    ].copy()
    leave_df['DAY_OF_WEEK'] = leave_df['DATE'].dt.day_name()

    dept_info_sorted = department_info_df.sort_values(['DEP_APP_START_DATE', 'EMP_ID'])

    # 조직 정보 결합
    overtime_df = overtime_df.sort_values(['DATE', 'EMP_ID'])
    overtime_df = pd.merge_asof(overtime_df, dept_info_sorted[['EMP_ID', 'DEP_APP_START_DATE', 'DEP_ID']],left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward')
    overtime_df['DIVISION_NAME'] = overtime_df['DEP_ID'].apply(lambda x: find_division_name_for_dept(x, dept_level_map, parent_map_dept, dept_name_map))
    overtime_df = overtime_df.dropna(subset=['DIVISION_NAME'])

    leave_df = leave_df.sort_values(['DATE', 'EMP_ID'])
    leave_df = pd.merge_asof(leave_df, dept_info_sorted[['EMP_ID', 'DEP_APP_START_DATE', 'DEP_ID']], left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward')
    leave_df['DIVISION_NAME'] = leave_df['DEP_ID'].apply(lambda x: find_division_name_for_dept(x, dept_level_map, parent_map_dept, dept_name_map))
    leave_df = leave_df.dropna(subset=['DIVISION_NAME'])

    # Operating Division 데이터 제외
    overtime_df = overtime_df[overtime_df['DIVISION_NAME'] != 'Operating Division']
    leave_df = leave_df[leave_df['DIVISION_NAME'] != 'Operating Division']

    # 2-2. 요일별 데이터 집계
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    ot_summary = overtime_df.groupby(['DIVISION_NAME', 'DAY_OF_WEEK'], observed=False)['OVERTIME_MINUTES'].mean().reset_index()

    workable_days = detailed_work_info_df[
        (~detailed_work_info_df['WORK_ETC'].isin(['휴가', '주말 휴무', '비번', '휴무'])) &
        (detailed_work_info_df['EMP_ID'].isin(normal_work_emp_ids)) &
        (pd.to_datetime(detailed_work_info_df['DATE']) >= start_date_filter)
    ].copy()
    workable_days['DAY_OF_WEEK'] = workable_days['DATE'].dt.day_name()
    workable_days = pd.merge_asof(workable_days.sort_values('DATE'), dept_info_sorted, left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID')
    workable_days['DIVISION_NAME'] = workable_days['DEP_ID'].apply(lambda x: find_division_name_for_dept(x, dept_level_map, parent_map_dept, dept_name_map))
    workable_days = workable_days.dropna(subset=['DIVISION_NAME'])
    workable_days = workable_days[workable_days['DIVISION_NAME'] != 'Operating Division']
    workday_headcount = workable_days.groupby(['DIVISION_NAME', 'DAY_OF_WEEK'], observed=False).size().reset_index(name='WORK_DAY_COUNT')

    leave_days_sum = leave_df.groupby(['DIVISION_NAME', 'DAY_OF_WEEK'], observed=False)['LEAVE_LENGTH'].sum().reset_index()
    leave_summary = pd.merge(leave_days_sum, workday_headcount, on=['DIVISION_NAME', 'DAY_OF_WEEK'], how='left').fillna(0)
    leave_summary['LEAVE_USAGE_RATE'] = (leave_summary['LEAVE_LENGTH'] / leave_summary['WORK_DAY_COUNT']) * 100 if 'WORK_DAY_COUNT' in leave_summary.columns else 0

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    ot_min, ot_max = ot_summary['OVERTIME_MINUTES'].min(), ot_summary['OVERTIME_MINUTES'].max()
    leave_rate_max = leave_summary['LEAVE_USAGE_RATE'].max()
    y_padding = (ot_max - ot_min) * 0.1 if (ot_max - ot_min) > 0 else 10
    fixed_y1_range = [ot_min - y_padding, ot_max + y_padding]
    fixed_y2_range = [0, leave_rate_max * 1.15]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    division_list_filtered = ['전체'] + [d for d in division_order if d != 'Operating Division']

    for i, div_name in enumerate(division_list_filtered):
        is_visible = (i == 0)
        ot_filtered = (ot_summary if div_name == '전체' else ot_summary[ot_summary['DIVISION_NAME'] == div_name]).copy()
        leave_filtered = (leave_summary if div_name == '전체' else leave_summary[leave_summary['DIVISION_NAME'] == div_name]).copy()

        ot_grouped = ot_filtered.groupby('DAY_OF_WEEK', observed=False)['OVERTIME_MINUTES'].mean().reset_index()
        if div_name == '전체':
            total_leave = leave_summary.groupby('DAY_OF_WEEK', observed=False)['LEAVE_LENGTH'].sum()
            total_workdays = workday_headcount.groupby('DAY_OF_WEEK', observed=False)['WORK_DAY_COUNT'].sum()
            leave_grouped = (total_leave / total_workdays * 100).reset_index(name='LEAVE_USAGE_RATE')
        else:
            leave_grouped = leave_filtered

        ot_grouped['DAY_OF_WEEK'] = pd.Categorical(ot_grouped['DAY_OF_WEEK'], categories=weekday_order, ordered=True)
        ot_grouped = ot_grouped.sort_values('DAY_OF_WEEK')
        leave_grouped['DAY_OF_WEEK'] = pd.Categorical(leave_grouped['DAY_OF_WEEK'], categories=weekday_order, ordered=True)
        leave_grouped = leave_grouped.sort_values('DAY_OF_WEEK')

        fig.add_trace(go.Bar(x=ot_grouped['DAY_OF_WEEK'], y=ot_grouped['OVERTIME_MINUTES'], name='평균 초과근무(분)', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Scatter(x=leave_grouped['DAY_OF_WEEK'], y=leave_grouped['LEAVE_USAGE_RATE'], name='연차 사용률(%)', visible=is_visible, mode='lines+markers'), secondary_y=True)

    buttons = []
    for i, div_name in enumerate(division_list_filtered):
        visibility_mask = [False] * (len(division_list_filtered) * 2)
        visibility_mask[i*2] = True; visibility_mask[i*2 + 1] = True
        buttons.append(dict(label=div_name, method='update', args=[{'visible': visibility_mask}]))

    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='요일별 업무 강도 및 휴가 사용 패턴',
        font_size=14, height=700, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis_range=fixed_y1_range,
        yaxis2_range=fixed_y2_range
    )
    fig.update_xaxes(title_text="요일")
    fig.update_yaxes(title_text="평균 초과근무 시간 (분)", secondary_y=False)
    fig.update_yaxes(title_text="요일별 연차 사용률 (%)", secondary_y=True, ticksuffix="%")

    return fig



pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




