#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure():
    """
    제안 11: 근무 유연성 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    daily_work_df = daily_work_info_df.copy()
    current_depts = department_info_df[department_info_df['DEP_APP_END_DATE'].isnull()][['EMP_ID', 'DEP_ID']]
    analysis_df = pd.merge(daily_work_df, current_depts, on='EMP_ID', how='inner')

    parent_info = analysis_df['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    analysis_df = pd.concat([analysis_df, parent_info], axis=1)
    analysis_df['OFFICE_NAME'] = analysis_df['OFFICE_NAME'].fillna('(Division 직속)')
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])

    # Division 및 Office 순서 지정
    analysis_df['DIVISION_NAME'] = pd.Categorical(analysis_df['DIVISION_NAME'], categories=division_order, ordered=True)
    analysis_df['OFFICE_NAME'] = pd.Categorical(analysis_df['OFFICE_NAME'], categories=office_order, ordered=True)
    analysis_df = analysis_df.sort_values(['DIVISION_NAME', 'OFFICE_NAME'])

    # y축 범위 미리 계산
    y_min = analysis_df['OVERTIME_MINUTES'].min()
    y_max = analysis_df['OVERTIME_MINUTES'].max()
    y_padding = (y_max - y_min) * 0.1
    fixed_y_range = [y_min - y_padding, y_max + y_padding]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()

    # 1. Division 레벨 트레이스 추가
    fig.add_trace(
        go.Violin(
            x=analysis_df['DIVISION_NAME'],
            y=analysis_df['OVERTIME_MINUTES'],
            box_visible=True, points='outliers'
        )
    )

    # 2. Office 레벨 트레이스 추가 (초기에는 숨김)
    for div_name in division_order:
        office_df = analysis_df[analysis_df['DIVISION_NAME'] == div_name]
        fig.add_trace(
            go.Violin(
                x=office_df['OFFICE_NAME'],
                y=office_df['OVERTIME_MINUTES'],
                name=div_name,
                box_visible=True, points='outliers',
                visible=False
            )
        )

    # --- 4. 드롭다운 메뉴 버튼 생성 ---
    buttons = []
    buttons.append(
        dict(label='전체', method='update',
             args=[{'visible': [True] + [False] * len(division_order)},
                   {'title': '전체 Division별 근무 유연성 분석',
                    'xaxis': {'title': 'Division', 'categoryorder':'array', 'categoryarray': division_order}}])
    )
    for i, div_name in enumerate(division_order):
        visibility_mask = [False] * (len(division_order) + 1)
        visibility_mask[i + 1] = True
        offices_in_div = [o for o in office_order if o in analysis_df[analysis_df['DIVISION_NAME'] == div_name]['OFFICE_NAME'].unique()]

        buttons.append(
            dict(label=f'{div_name}', method='update',
                 args=[{'visible': visibility_mask},
                       {'title': f'{div_name} 내 Office별 근무 유연성 분석',
                        'xaxis': {'title': 'Office', 'categoryorder': 'array', 'categoryarray': offices_in_div}}])
        )

    # 5. 레이아웃 업데이트
    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='조직별 근무 유연성 드릴다운 분석',
        yaxis_title='일별 초과근무 시간 (분)',
        font_size=14, height=700,
        showlegend=False,
        yaxis_range=fixed_y_range
    )

    fig.add_hline(y=0, line_width=2, line_dash="dash", line_color="black")

    return fig



pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




