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
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    department_df, dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure():
    """
    제안 5: 조직 건강도 위험 신호 탐지 (연간 퇴사율 변화 추이) 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    analysis_years = [y for y in emp_df['IN_DATE'].dt.year.unique() if y < datetime.datetime.now().year]
    turnover_records = []

    for year in analysis_years:
        year_start, year_end = pd.to_datetime(f'{year}-01-01'), pd.to_datetime(f'{year}-12-31')

        leavers_in_year = emp_df[(emp_df['OUT_DATE'] >= year_start) & (emp_df['OUT_DATE'] <= year_end)]
        if leavers_in_year.empty: continue

        leavers_dept = pd.merge_asof(
            leavers_in_year[['EMP_ID', 'OUT_DATE']].sort_values('OUT_DATE'),
            department_info_df.sort_values('DEP_APP_START_DATE'),
            left_on='OUT_DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward'
        )
        parent_info_leavers = leavers_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        leavers_dept = pd.concat([leavers_dept, parent_info_leavers], axis=1)
        leavers_dept = leavers_dept.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])

        active_in_year = emp_df[(emp_df['IN_DATE'] <= year_end) & (emp_df['OUT_DATE'].isnull() | (emp_df['OUT_DATE'] >= year_start))]
        active_dept = pd.merge_asof(
            active_in_year[['EMP_ID', 'IN_DATE']].sort_values('IN_DATE'),
            department_info_df.sort_values('DEP_APP_START_DATE'),
            left_on='IN_DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward'
        )
        parent_info_active = active_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        active_dept = pd.concat([active_dept, parent_info_active], axis=1)
        active_dept = active_dept.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])

        # Division / Office 별 퇴사율 계산
        leavers_by_div = leavers_dept.groupby('DIVISION_NAME', observed=False).size()
        headcount_by_div = active_dept.groupby('DIVISION_NAME', observed=False).size()
        turnover_div = (leavers_by_div / headcount_by_div * 100).fillna(0)
        for group_name, rate in turnover_div.items():
            turnover_records.append({'YEAR': year, 'GROUP_TYPE': 'DIVISION_NAME', 'GROUP_NAME': group_name, 'TURNOVER_RATE': rate})

        leavers_by_office = leavers_dept.groupby(['DIVISION_NAME', 'OFFICE_NAME'], observed=False).size()
        headcount_by_office = active_dept.groupby(['DIVISION_NAME', 'OFFICE_NAME'], observed=False).size()
        turnover_office = (leavers_by_office / headcount_by_office * 100).fillna(0)
        for (div_name, office_name), rate in turnover_office.items():
            turnover_records.append({'YEAR': year, 'GROUP_TYPE': 'OFFICE_NAME', 'DIVISION_NAME': div_name, 'GROUP_NAME': office_name, 'TURNOVER_RATE': rate})

    analysis_df = pd.DataFrame(turnover_records)
    if analysis_df.empty:
        return go.Figure().update_layout(title_text="분석할 퇴사율 데이터가 없습니다.")

    # y축 범위 미리 계산
    y_max = analysis_df['TURNOVER_RATE'].max()
    fixed_y_range = [0, y_max * 1.15]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly

    div_df = analysis_df[analysis_df['GROUP_TYPE'] == 'DIVISION_NAME']
    for i, div_name in enumerate(division_order):
        df_filtered = div_df[div_df['GROUP_NAME'] == div_name].sort_values('YEAR')
        if not df_filtered.empty:
            fig.add_trace(go.Scatter(
                x=df_filtered['YEAR'], y=df_filtered['TURNOVER_RATE'], mode='lines+markers+text', name=div_name, 
                line=dict(color=colors[i]), text=df_filtered['TURNOVER_RATE'].round(2).astype(str) + '%', textposition='top center'
            ))

    office_df = analysis_df[analysis_df['GROUP_TYPE'] == 'OFFICE_NAME']
    office_traces_map = {}
    trace_idx_counter = len(fig.data)
    for div_name in division_order:
        offices_in_div = office_df[office_df['DIVISION_NAME'] == div_name]['GROUP_NAME'].unique()
        office_traces_map[div_name] = []
        sorted_offices_in_div = [o for o in office_order if o in offices_in_div]
        for j, office_name in enumerate(sorted_offices_in_div):
            df_filtered = office_df[office_df['GROUP_NAME'] == office_name].sort_values('YEAR')
            if not df_filtered.empty:
                fig.add_trace(go.Scatter(
                    x=df_filtered['YEAR'], y=df_filtered['TURNOVER_RATE'], mode='lines+markers+text', name=office_name, 
                    visible=False, line=dict(color=colors[j % len(colors)]), text=df_filtered['TURNOVER_RATE'].round(2).astype(str) + '%', textposition='top center'
                ))
                office_traces_map[div_name].append(trace_idx_counter)
                trace_idx_counter += 1

    buttons = []
    num_div_traces = len(division_order)
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*num_div_traces + [False]*(len(fig.data) - num_div_traces)}]))
    for div_name in division_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in office_traces_map.get(div_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{div_name}', method='update', args=[{'visible': visibility_mask}]))

    # --- 4. 레이아웃 업데이트 ---
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='연간 퇴사율 변화 추이',
        xaxis_title='연도', yaxis_title='연간 퇴사율 (%)',
        font_size=14, height=700,
        legend_title_text='조직',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis=dict(type='category'),
        yaxis=dict(ticksuffix="%", tickformat='.2f', range=fixed_y_range)
    )

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
if __name__ == '__main__':
    pio.renderers.default = 'vscode'
    fig = create_figure()
    fig.show()


# In[ ]:




