#!/usr/bin/env python
# coding: utf-8

# In[2]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.position_table import position_df
from services.tables.HR_Core.department_table import division_order, office_order, department_df
from services.helpers.utils import calculate_age

def create_figure_and_df():
    """
    제안 3: 조직 세대교체 현황 분석 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    current_emps_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y'].copy()
    current_emps_df['AGE'] = current_emps_df['PERSONAL_ID'].apply(calculate_age)

    current_positions = position_info_df[position_info_df['GRADE_END_DATE'].isnull()][['EMP_ID', 'POSITION_ID']]
    current_depts = department_info_df[department_info_df['DEP_APP_END_DATE'].isnull()][['EMP_ID', 'DEP_ID']]

    analysis_df = pd.merge(current_emps_df, current_positions, on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, current_depts, on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID', how='left')

    div_map = department_df[department_df['DEP_LEVEL'] == 2][['DEP_ID', 'DEP_NAME']].rename(columns={'DEP_NAME': 'DIVISION_NAME'})
    office_map = pd.merge(department_df[department_df['DEP_LEVEL'] == 3], div_map, left_on='UP_DEP_ID', right_on='DEP_ID', suffixes=('', '_div'))[['DEP_ID', 'DIVISION_NAME']]
    team_map = pd.merge(department_df[department_df['DEP_LEVEL'] == 4], office_map, left_on='UP_DEP_ID', right_on='DEP_ID', suffixes=('', '_office'))[['DEP_ID', 'DIVISION_NAME']]
    dept_to_div_map = pd.concat([
        div_map.rename(columns={'DEP_ID': 'DEP_ID_MAP'}),
        office_map.rename(columns={'DEP_ID': 'DEP_ID_MAP'}),
        team_map.rename(columns={'DEP_ID': 'DEP_ID_MAP'})
    ]).rename(columns={'DEP_ID_MAP': 'DEP_ID'})
    analysis_df = pd.merge(analysis_df, dept_to_div_map[['DEP_ID', 'DIVISION_NAME']], on='DEP_ID', how='left')

    analysis_df = pd.merge(analysis_df, department_df[['DEP_ID', 'DEP_NAME']], on='DEP_ID', how='left')
    analysis_df['OFFICE_NAME'] = np.where(analysis_df['DEP_NAME'].str.contains('Office'), analysis_df['DEP_NAME'], analysis_df['DIVISION_NAME'] + ' (직속)')

    analysis_df = analysis_df.dropna(subset=['POSITION_NAME', 'DIVISION_NAME', 'AGE', 'OFFICE_NAME'])

    position_order = ['Staff', 'Manager', 'Director', 'C-Level']
    analysis_df['POSITION_NAME'] = pd.Categorical(analysis_df['POSITION_NAME'], categories=position_order, ordered=True)
    analysis_df['DIVISION_NAME'] = pd.Categorical(analysis_df['DIVISION_NAME'], categories=division_order, ordered=True)
    analysis_df['OFFICE_NAME'] = pd.Categorical(analysis_df['OFFICE_NAME'], categories=office_order, ordered=True)
    analysis_df = analysis_df.sort_values(['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'])

    y_min, y_max = analysis_df['AGE'].min(), analysis_df['AGE'].max()
    fixed_y_range = [y_min - 5, y_max + 5]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, div_name in enumerate(division_order):
        df_filtered = analysis_df[analysis_df['DIVISION_NAME'] == div_name]
        fig.add_trace(go.Box(x=df_filtered['POSITION_NAME'], y=df_filtered['AGE'], name=div_name, marker_color=colors[i]))
    office_traces_map = {}
    trace_idx_counter = len(fig.data)
    for i, div_name in enumerate(division_order):
        office_div_df = analysis_df[analysis_df['DIVISION_NAME'] == div_name]
        offices_in_div = [o for o in office_order if o in office_div_df['OFFICE_NAME'].unique()]
        office_traces_map[div_name] = []
        for j, office_name in enumerate(offices_in_div):
            df_filtered = office_div_df[office_div_df['OFFICE_NAME'] == office_name]
            fig.add_trace(go.Box(
                x=df_filtered['POSITION_NAME'], y=df_filtered['AGE'], name=office_name, 
                visible=False, marker_color=colors[j % len(colors)]
            ))
            office_traces_map[div_name].append(trace_idx_counter)
            trace_idx_counter += 1
    buttons = []
    buttons.append(dict(label='전체', method='update', 
                        args=[{'visible': [True]*len(division_order) + [False]*(len(fig.data)-len(division_order))},
                              {'title': '전체 조직의 직위별 연령 분포', 'legend_title_text': 'Division'}]))
    for div_name in division_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in office_traces_map.get(div_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{div_name}', method='update',
                            args=[{'visible': visibility_mask},
                                  {'title': f'{div_name} 내 직위별 연령 분포', 'legend_title_text': 'Office'}]))
    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='직위별 연령 분포 현황',
        xaxis_title='직위', yaxis_title='연령',
        font_size=14, height=700,
        boxmode='group',
        legend_title_text='Division',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis_range=fixed_y_range
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    aggregate_df = analysis_df.pivot_table(
        index='POSITION_NAME',
        columns='DIVISION_NAME',
        values='AGE',
        aggfunc='mean',
        observed=False
    )

    # 2. '전체 평균' 컬럼 추가
    aggregate_df['전체 평균'] = analysis_df.groupby('POSITION_NAME', observed=False)['AGE'].mean()

    # 3. 컬럼 순서 재배치
    cols = ['전체 평균'] + [col for col in division_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols]

    # 4. 포맷팅
    aggregate_df = aggregate_df.round(2).fillna('-')

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




