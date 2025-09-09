#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.detailed_working_info_table import detailed_work_info_df
from services.tables.Time_Attendance.working_info_table import work_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure():
    """
    제안 12: 조직별/직위별 출근 문화 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    # 2-1. 분석 대상 직원 샘플링 (30%)
    normal_work_emp_ids = work_info_df[work_info_df['WORK_SYS_ID'] == 'WS001']['EMP_ID'].unique()

    if len(normal_work_emp_ids) > 0:
        num_to_sample = int(len(normal_work_emp_ids) * 0.3)
        np.random.seed(42)
        sampled_emp_ids = np.random.choice(normal_work_emp_ids, size=num_to_sample, replace=False)
    else:
        sampled_emp_ids = []

    work_records = detailed_work_info_df[
        (detailed_work_info_df['EMP_ID'].isin(sampled_emp_ids)) &
        (~detailed_work_info_df['WORK_ETC'].isin(['휴가', '주말 휴무', '비번', '휴무'])) &
        (detailed_work_info_df['DATE_START_TIME'] != '-')
    ].copy()

    # 2-2. 날짜별 부서 및 직위 정보 추가
    work_records['DATE'] = pd.to_datetime(work_records['DATE'])
    dept_info_sorted = department_info_df.sort_values(['DEP_APP_START_DATE', 'EMP_ID'])
    pos_info_sorted = position_info_df.sort_values(['GRADE_START_DATE', 'EMP_ID'])
    analysis_df = work_records.sort_values(['DATE', 'EMP_ID'])

    analysis_df = pd.merge_asof(
        analysis_df, dept_info_sorted[['EMP_ID', 'DEP_APP_START_DATE', 'DEP_ID']],
        left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward'
    )
    analysis_df = pd.merge_asof(
        analysis_df, pos_info_sorted[['EMP_ID', 'GRADE_START_DATE', 'POSITION_ID']],
        left_on='DATE', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward'
    )

    parent_info = analysis_df['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    analysis_df = pd.concat([analysis_df, parent_info], axis=1)
    analysis_df = pd.merge(analysis_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'])

    # 2-3. 출근 시간 계산
    analysis_df['START_HOUR'] = pd.to_datetime(analysis_df['DATE_START_TIME'], format='%H:%M', errors='coerce').dt.hour + \
                                pd.to_datetime(analysis_df['DATE_START_TIME'], format='%H:%M', errors='coerce').dt.minute / 60
    analysis_df = analysis_df.dropna(subset=['START_HOUR'])

    # 순서 지정
    position_order = ['Staff', 'Manager', 'Director', 'C-Level']
    analysis_df['DIVISION_NAME'] = pd.Categorical(analysis_df['DIVISION_NAME'], categories=division_order, ordered=True)
    analysis_df['OFFICE_NAME'] = pd.Categorical(analysis_df['OFFICE_NAME'], categories=office_order, ordered=True)
    analysis_df['POSITION_NAME'] = pd.Categorical(analysis_df['POSITION_NAME'], categories=position_order, ordered=True)
    analysis_df = analysis_df.sort_values(['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'])

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()

    for pos_name in position_order:
        df_filtered = analysis_df[analysis_df['POSITION_NAME'] == pos_name]
        fig.add_trace(go.Violin(x=df_filtered['DIVISION_NAME'], y=df_filtered['START_HOUR'], name=pos_name))
    for div_name in division_order:
        office_df = analysis_df[analysis_df['DIVISION_NAME'] == div_name]
        for pos_name in position_order:
            df_filtered = office_df[office_df['POSITION_NAME'] == pos_name]
            fig.add_trace(go.Violin(x=df_filtered['OFFICE_NAME'], y=df_filtered['START_HOUR'], name=pos_name, visible=False))

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    num_positions = len(position_order)
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*num_positions + [False]*(num_positions*len(division_order))}]))
    for i, div_name in enumerate(division_order):
        visibility_mask = [False] * (num_positions + num_positions*len(division_order))
        start_index = num_positions + (i * num_positions)
        for j in range(num_positions):
            visibility_mask[start_index + j] = True
        buttons.append(dict(label=f'{div_name}', method='update', args=[{'visible': visibility_mask}]))

    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='조직별/직위별 출근 시간 분포',
        yaxis_title='출근 시간 (24시간 기준)',
        font_size=14, height=700,
        violinmode='group', legend_title_text='직위',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis=dict(range=[7.5, 11.5], tickvals=[8, 9, 10, 11], ticktext=['08:00', '09:00', '10:00', '11:00'])
    )

    return fig



pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




