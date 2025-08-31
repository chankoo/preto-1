#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure_and_df():
    """
    제안 1: Division/Office별 성장 속도 비교 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    pos_info = position_info_df.copy()
    pos_info = pd.merge(pos_info, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID')
    position_start_dates = pos_info.groupby(['EMP_ID', 'POSITION_NAME'])['GRADE_START_DATE'].min().unstack()
    if 'Staff' in position_start_dates.columns and 'Manager' in position_start_dates.columns:
        position_start_dates['TIME_TO_MANAGER'] = (position_start_dates['Manager'] - position_start_dates['Staff']).dt.days / 365.25
    if 'Manager' in position_start_dates.columns and 'Director' in position_start_dates.columns:
        position_start_dates['TIME_TO_DIRECTOR'] = (position_start_dates['Director'] - position_start_dates['Manager']).dt.days / 365.25
    promo_speed_df = position_start_dates.reset_index()

    first_dept = department_info_df.sort_values('DEP_APP_START_DATE').groupby('EMP_ID').first().reset_index()
    parent_info = first_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    first_dept = pd.concat([first_dept, parent_info], axis=1)
    first_dept['OFFICE_NAME'] = first_dept['OFFICE_NAME'].fillna('(Division 직속)')
    analysis_df = pd.merge(promo_speed_df, first_dept[['EMP_ID', 'DIVISION_NAME', 'OFFICE_NAME']], on='EMP_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])

    analysis_df['DIVISION_NAME'] = pd.Categorical(analysis_df['DIVISION_NAME'], categories=division_order, ordered=True)
    analysis_df['OFFICE_NAME'] = pd.Categorical(analysis_df['OFFICE_NAME'], categories=office_order, ordered=True)
    analysis_df = analysis_df.sort_values(['DIVISION_NAME', 'OFFICE_NAME'])

    y_max_series = pd.concat([analysis_df['TIME_TO_MANAGER'], analysis_df['TIME_TO_DIRECTOR']])
    y_max = y_max_series.max() if not y_max_series.empty else 10
    fixed_y_range = [0, y_max * 1.1]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    fig.add_trace(go.Box(y=analysis_df['TIME_TO_MANAGER'], x=analysis_df['DIVISION_NAME'], name='Staff → Manager'))
    fig.add_trace(go.Box(y=analysis_df['TIME_TO_DIRECTOR'], x=analysis_df['DIVISION_NAME'], name='Manager → Director'))
    for div_name in division_order:
        office_df = analysis_df[analysis_df['DIVISION_NAME'] == div_name]
        fig.add_trace(go.Box(y=office_df['TIME_TO_MANAGER'], x=office_df['OFFICE_NAME'], name='Staff → Manager', visible=False))
        fig.add_trace(go.Box(y=office_df['TIME_TO_DIRECTOR'], x=office_df['OFFICE_NAME'], name='Manager → Director', visible=False))
    buttons = []
    buttons.append(dict(label='전체', method='update',
                        args=[{'visible': [True, True] + [False] * (len(division_order) * 2)},
                              {'title': '전체 Division별 승진 소요 기간 비교',
                               'xaxis': {'title': 'Division', 'categoryorder': 'array', 'categoryarray': division_order}}]))
    for i, div_name in enumerate(division_order):
        visibility_mask = [False] * (2 + len(division_order) * 2)
        start_index = 2 + (i * 2)
        visibility_mask[start_index] = True; visibility_mask[start_index + 1] = True
        offices_in_div = [o for o in office_order if o in analysis_df[analysis_df['DIVISION_NAME'] == div_name]['OFFICE_NAME'].unique()]
        buttons.append(dict(label=f'{div_name}', method='update',
                            args=[{'visible': visibility_mask},
                                  {'title': f'{div_name} 내 Office별 승진 소요 기간 비교',
                                   'xaxis': {'title': 'Office', 'categoryorder': 'array', 'categoryarray': offices_in_div}}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10},
                          showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='조직별 승진 소요 기간 드릴다운 분석',
        yaxis_title='승진 소요 기간 (년)',
        font_size=14, height=700,
        boxmode='group',
        legend_title_text='승진 단계',
        yaxis_range=fixed_y_range
    )

    # --- aggregate_df 생성 ---
    df_melted = analysis_df.melt(
        id_vars=['DIVISION_NAME'],
        value_vars=['TIME_TO_MANAGER', 'TIME_TO_DIRECTOR'],
        var_name='PROMOTION_STEP',
        value_name='YEARS'
    )
    df_melted['PROMOTION_STEP'] = df_melted['PROMOTION_STEP'].map({
        'TIME_TO_MANAGER': 'Staff → Manager',
        'TIME_TO_DIRECTOR': 'Manager → Director'
    })

    aggregate_df = df_melted.pivot_table(
        index='PROMOTION_STEP',
        columns='DIVISION_NAME',
        values='YEARS',
        aggfunc='mean'
    ).round(2)

    # --- 수정된 부분: aggregate_df의 행 순서 지정 ---
    promotion_step_order = ['Staff → Manager', 'Manager → Director']
    aggregate_df = aggregate_df.reindex(promotion_step_order)
    # --- 수정 완료 ---

    return fig, aggregate_df


# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




