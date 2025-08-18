#!/usr/bin/env python
# coding: utf-8

# In[2]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.position_table import position_df
from services.tables.HR_Core.department_table import division_order, dept_level_map, parent_map_dept, dept_name_map
from services.helpers.utils import calculate_age, find_division_name_for_dept

def create_figure():
    """
    제안 3: 조직 세대교체 현황 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    current_emps_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y'].copy()
    current_emps_df['AGE'] = current_emps_df['PERSONAL_ID'].apply(calculate_age)

    current_positions = position_info_df[position_info_df['GRADE_END_DATE'].isnull()][['EMP_ID', 'POSITION_ID']]
    current_depts = department_info_df[department_info_df['DEP_APP_END_DATE'].isnull()][['EMP_ID', 'DEP_ID']]

    analysis_df = pd.merge(current_emps_df, current_positions, on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, current_depts, on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID', how='left')

    # --- 수정된 부분 2: 함수 호출 시 모든 인수를 전달하도록 lambda 함수 사용 ---
    analysis_df['DIVISION_NAME'] = analysis_df['DEP_ID'].apply(lambda x: find_division_name_for_dept(x, dept_level_map, parent_map_dept, dept_name_map))
    # --- 수정 완료 ---
    analysis_df = analysis_df.dropna(subset=['POSITION_NAME', 'DIVISION_NAME', 'AGE'])

    position_order = ['Staff', 'Manager', 'Director', 'C-Level']
    analysis_df['POSITION_NAME'] = pd.Categorical(analysis_df['POSITION_NAME'], categories=position_order, ordered=True)
    analysis_df = analysis_df.sort_values('POSITION_NAME')

    y_min = analysis_df['AGE'].min()
    y_max = analysis_df['AGE'].max()
    fixed_y_range = [y_min - 5, y_max + 5]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    division_list = ['전체'] + division_order

    for i, div_name in enumerate(division_list):
        is_visible = (i == 0)
        df_filtered = analysis_df if div_name == '전체' else analysis_df[analysis_df['DIVISION_NAME'] == div_name]
        fig.add_trace(
            go.Violin(
                x=df_filtered['POSITION_NAME'], y=df_filtered['AGE'], name=div_name,
                box_visible=True, meanline_visible=True, visible=is_visible
            )
        )

    # --- 4. 드롭다운 메뉴 생성 및 레이아웃 업데이트 ---
    buttons = []
    for i, div_name in enumerate(division_list):
        visibility_mask = [False] * len(division_list)
        visibility_mask[i] = True
        buttons.append(dict(label=div_name, method='update', args=[{'visible': visibility_mask}]))

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='직위별 연령 분포 현황',
        xaxis_title='직위', yaxis_title='연령',
        font_size=14, height=700,
        legend_title_text='Division',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis_range=fixed_y_range
    )

    return fig


pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




