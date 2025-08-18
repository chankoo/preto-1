#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.detailed_leave_info_table import detailed_leave_info_df
from services.tables.Time_Attendance.leave_type_table import leave_type_df
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order
)
from services.helpers.utils import find_parents

def create_figure():
    """
    제안 18: 직원 번아웃 신호 감지 (연차-병가 사용 패턴) 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    leave_df = detailed_leave_info_df.copy()
    leave_df = pd.merge(leave_df, leave_type_df, on='LEAVE_TYPE_ID')
    leave_df['DATE'] = pd.to_datetime(leave_df['DATE'])
    leave_df['YEAR'] = leave_df['DATE'].dt.year

    leave_summary = leave_df.groupby(['YEAR', 'EMP_ID', 'LEAVE_TYPE_NAME'])['LEAVE_LENGTH'].sum().unstack(fill_value=0).reset_index()
    required_leave_types = ['연차휴가', '병휴가']
    for leave_type in required_leave_types:
        if leave_type not in leave_summary.columns: leave_summary[leave_type] = 0

    scaffold_records = []
    analysis_years_list = range(emp_df['IN_DATE'].min().year, datetime.datetime.now().year + 1)
    for year in analysis_years_list:
        year_start, year_end = pd.to_datetime(f'{year}-01-01'), pd.to_datetime(f'{year}-12-31')
        active_emps_in_year = emp_df[(emp_df['IN_DATE'] <= year_end) & (emp_df['OUT_DATE'].isnull() | (emp_df['OUT_DATE'] >= year_start))]['EMP_ID'].unique()
        for emp_id in active_emps_in_year:
            scaffold_records.append({'YEAR': year, 'EMP_ID': emp_id})
    scaffold_df = pd.DataFrame(scaffold_records)

    analysis_df = pd.merge(scaffold_df, leave_summary, on=['YEAR', 'EMP_ID'], how='left')
    analysis_df[required_leave_types] = analysis_df[required_leave_types].fillna(0)

    analysis_df['YEAR_START_DATE'] = pd.to_datetime(analysis_df['YEAR'].astype(str) + '-01-01')
    analysis_df = analysis_df.sort_values(['YEAR_START_DATE', 'EMP_ID'])
    dept_info_sorted = department_info_df.sort_values(['DEP_APP_START_DATE', 'EMP_ID'])
    analysis_df = pd.merge_asof(analysis_df, dept_info_sorted[['EMP_ID', 'DEP_APP_START_DATE', 'DEP_ID']], left_on='YEAR_START_DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward')

    parent_info = analysis_df['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    analysis_df = pd.concat([analysis_df, parent_info], axis=1)
    analysis_df = pd.merge(analysis_df, emp_df[['EMP_ID', 'NAME']], on='EMP_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME'])

    # 지터링(Jittering)을 위한 데이터 추가
    jitter_strength = 0.15
    num_points = len(analysis_df)
    analysis_df['연차휴가_jitter'] = analysis_df['연차휴가'] + np.random.uniform(-jitter_strength, jitter_strength, num_points)
    analysis_df['병휴가_jitter'] = analysis_df['병휴가'] + np.random.uniform(-jitter_strength, jitter_strength, num_points)

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    analysis_years = sorted(analysis_df['YEAR'].unique())
    division_list = ['전체'] + division_order

    for year in analysis_years:
        for div_name in division_list:
            df_filtered = analysis_df[analysis_df['YEAR'] == year]
            if div_name != '전체':
                df_filtered = df_filtered[df_filtered['DIVISION_NAME'] == div_name]

            fig.add_trace(go.Scatter(
                x=df_filtered['연차휴가_jitter'], y=df_filtered['병휴가_jitter'],
                mode='markers', name=f'{year} - {div_name}',
                marker=dict(opacity=0.6),
                customdata=df_filtered[['NAME', '연차휴가', '병휴가']],
                hovertemplate='<b>%{customdata[0]}</b><br>연차: %{customdata[1]:.1f}일<br>병가: %{customdata[2]:.1f}일<extra></extra>',
                visible=False
            ))

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    trace_index = 0
    for year in analysis_years:
        for div_name in division_list:
            visibility_mask = [False] * (len(analysis_years) * len(division_list))
            visibility_mask[trace_index] = True
            buttons.append(dict(label=f"{year}년 - {div_name}", method='update', args=[{'visible': visibility_mask}]))
            trace_index += 1

    y_max = analysis_df['병휴가'].max()
    fixed_y_range = [-1, y_max + 2]

    if len(fig.data) > 0:
        default_trace_index = (len(analysis_years) - 1) * len(division_list)
        if default_trace_index < len(fig.data):
            fig.data[default_trace_index].visible = True

    fig.update_layout(
        updatemenus=[dict(active=len(buttons) - len(division_list), buttons=buttons, direction="down",
                          pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='연차-병가 사용 패턴 분석 (밀도 표현)',
        xaxis_title='연간 연차 사용일수', yaxis_title='연간 병가 사용일수',
        font_size=14, height=700,
        yaxis_range=fixed_y_range
    )
    avg_annual = analysis_df['연차휴가'].median(); avg_sick = analysis_df['병휴가'].median()
    fig.add_vline(x=avg_annual, line_width=1, line_dash="dash", line_color="grey")
    fig.add_hline(y=avg_sick, line_width=1, line_dash="dash", line_color="grey")

    return fig



pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




