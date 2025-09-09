#!/usr/bin/env python
# coding: utf-8

# In[2]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure_and_df():
    """
    제안 4: 조직 경험 자산 현황 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    current_emps_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y'].copy()
    current_emps_df['TENURE_YEARS'] = current_emps_df['DURATION'] / 365.25

    current_depts = department_info_df[department_info_df['DEP_APP_END_DATE'].isnull()][['EMP_ID', 'DEP_ID']]
    analysis_df = pd.merge(current_emps_df, current_depts, on='EMP_ID', how='left')

    parent_info = analysis_df['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    analysis_df = pd.concat([analysis_df, parent_info], axis=1)
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME', 'TENURE_YEARS'])

    # --- 3. Plotly 인터랙티브 그래프 생성 (그래프용 데이터 준비) ---
    analysis_df['TENURE_BIN'] = pd.cut(analysis_df['TENURE_YEARS'], bins=range(0, int(analysis_df['TENURE_YEARS'].max()) + 2), right=False, labels=range(0, int(analysis_df['TENURE_YEARS'].max()) + 1))
    div_summary = analysis_df.groupby(['DIVISION_NAME', 'TENURE_BIN'], observed=False).size().reset_index(name='COUNT')
    office_summary = analysis_df.groupby(['DIVISION_NAME', 'OFFICE_NAME', 'TENURE_BIN'], observed=False).size().reset_index(name='COUNT')

    x_max = analysis_df['TENURE_YEARS'].max()
    fixed_x_range = [-0.5, x_max + 1.5]

    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, div_name in enumerate(division_order):
        df_filtered = div_summary[div_summary['DIVISION_NAME'] == div_name]
        fig.add_trace(go.Bar(x=df_filtered['TENURE_BIN'], y=df_filtered['COUNT'], name=div_name, marker_color=colors[i]))
    office_traces_map = {}
    trace_idx_counter = len(fig.data)
    for div_name in division_order:
        office_div_df = office_summary[office_summary['DIVISION_NAME'] == div_name]
        offices_in_div = [o for o in office_order if o in office_div_df['OFFICE_NAME'].unique()]
        office_traces_map[div_name] = []
        for j, office_name in enumerate(offices_in_div):
            df_filtered = office_div_df[office_div_df['OFFICE_NAME'] == office_name]
            fig.add_trace(go.Bar(x=df_filtered['TENURE_BIN'], y=df_filtered['COUNT'], name=office_name, visible=False, marker_color=colors[j % len(colors)], showlegend=False))
            office_traces_map[div_name].append(trace_idx_counter)
            trace_idx_counter += 1
    buttons = []
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*len(division_order) + [False]*(len(fig.data)-len(division_order))}, {'title': '전체 조직 근속년수 분포 (Division별)', 'barmode': 'stack', 'showlegend': True}]))
    for div_name in division_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in office_traces_map.get(div_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{div_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{div_name} 근속년수 분포 (Office별)', 'barmode': 'stack', 'showlegend': False}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='조직별 근속년수 분포 현황', xaxis_title='근속년수 (년)', yaxis_title='직원 수', font_size=14, height=700,
        bargap=0.2, barmode='stack', legend_title_text='조직',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis_range=fixed_x_range
    )
    fig.update_xaxes(dtick=1)

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. 근속년수 구간을 새로 정의
    tenure_bins_agg = [-np.inf, 3, 7, np.inf]
    tenure_labels_agg = ['3년 이하', '3년초과~7년이하', '7년 초과']
    analysis_df['TENURE_GROUP'] = pd.cut(analysis_df['TENURE_YEARS'], bins=tenure_bins_agg, labels=tenure_labels_agg)

    # 2. 피벗 테이블 생성
    aggregate_df = pd.pivot_table(
        analysis_df,
        index='TENURE_GROUP',
        columns='DIVISION_NAME',
        values='EMP_ID',
        aggfunc='count',
        margins=True, # 합계(All) 추가
        margins_name='합계',
        observed=False
    ).fillna(0).astype(int)

    # 3. '합계' 컬럼을 맨 앞으로 이동
    if '합계' in aggregate_df.columns:
        cols = ['합계'] + [col for col in aggregate_df.columns if col != '합계']
        aggregate_df = aggregate_df[cols]
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




