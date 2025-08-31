#!/usr/bin/env python
# coding: utf-8

# In[3]:


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

def create_figure_and_df():
    """
    제안 5: 조직 건강도 위험 신호 탐지 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    leaver_years = emp_df.dropna(subset=['OUT_DATE'])['OUT_DATE'].dt.year.unique()
    analysis_years = sorted([y for y in leaver_years if y < datetime.datetime.now().year])

    turnover_records = []
    overall_turnover_records = []

    for year in analysis_years:
        year_start, year_end = pd.to_datetime(f'{year}-01-01'), pd.to_datetime(f'{year}-12-31')

        leavers_in_year = emp_df[(emp_df['OUT_DATE'] >= year_start) & (emp_df['OUT_DATE'] <= year_end)]
        active_in_year = emp_df[(emp_df['IN_DATE'] <= year_end) & (emp_df['OUT_DATE'].isnull() | (emp_df['OUT_DATE'] >= year_start))]

        if not active_in_year.empty:
            overall_rate = (len(leavers_in_year) / len(active_in_year)) * 100 if len(active_in_year) > 0 else 0
            overall_turnover_records.append({'YEAR': year, 'TURNOVER_RATE': overall_rate})

        if leavers_in_year.empty: continue

        leavers_dept = pd.merge_asof(leavers_in_year[['EMP_ID', 'OUT_DATE']].sort_values('OUT_DATE'), department_info_df.sort_values('DEP_APP_START_DATE'), left_on='OUT_DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward')
        parent_info_leavers = leavers_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        leavers_dept = pd.concat([leavers_dept, parent_info_leavers], axis=1).dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])

        active_dept = pd.merge_asof(active_in_year[['EMP_ID', 'IN_DATE']].sort_values('IN_DATE'), department_info_df.sort_values('DEP_APP_START_DATE'), left_on='IN_DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward')
        parent_info_active = active_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        active_dept = pd.concat([active_dept, parent_info_active], axis=1).dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])

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
    overall_turnover_df = pd.DataFrame(overall_turnover_records)

    if analysis_df.empty and overall_turnover_df.empty:
        # 빈 Figure와 빈 DataFrame 반환
        return go.Figure().update_layout(title_text="분석할 퇴사율 데이터가 없습니다."), pd.DataFrame()

    all_rates = pd.concat([analysis_df['TURNOVER_RATE'], overall_turnover_df['TURNOVER_RATE']])
    y_max = all_rates.max()
    fixed_y_range = [0, y_max * 1.15]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    fig.add_trace(go.Scatter(x=overall_turnover_df['YEAR'], y=overall_turnover_df['TURNOVER_RATE'], mode='lines+markers+text', name='전사 평균', line=dict(color='black', dash='dot'), text=overall_turnover_df['TURNOVER_RATE'].round(2).astype(str) + '%', textposition='top center', visible=True))
    div_df = analysis_df[analysis_df['GROUP_TYPE'] == 'DIVISION_NAME']
    for i, div_name in enumerate(division_order):
        df_filtered = div_df[div_df['GROUP_NAME'] == div_name].sort_values('YEAR')
        if not df_filtered.empty:
            fig.add_trace(go.Scatter(x=df_filtered['YEAR'], y=df_filtered['TURNOVER_RATE'], mode='lines+markers+text', name=div_name, line=dict(color=colors[i]), text=df_filtered['TURNOVER_RATE'].round(2).astype(str) + '%', textposition='top center', visible=False))
    office_df = analysis_df[analysis_df['GROUP_TYPE'] == 'OFFICE_NAME']
    office_traces_map = {}
    trace_idx_counter = 1 + len(division_order)
    for div_name in division_order:
        offices_in_div = office_df[office_df['DIVISION_NAME'] == div_name]['GROUP_NAME'].unique()
        office_traces_map[div_name] = []
        sorted_offices_in_div = [o for o in office_order if o in offices_in_div]
        for j, office_name in enumerate(sorted_offices_in_div):
            df_filtered = office_df[office_df['GROUP_NAME'] == office_name].sort_values('YEAR')
            if not df_filtered.empty:
                fig.add_trace(go.Scatter(x=df_filtered['YEAR'], y=df_filtered['TURNOVER_RATE'], mode='lines+markers+text', name=office_name, visible=False, line=dict(color=colors[j % len(colors)]), text=df_filtered['TURNOVER_RATE'].round(2).astype(str) + '%', textposition='top center'))
                office_traces_map[div_name].append(trace_idx_counter)
                trace_idx_counter += 1
    buttons = []
    num_div_traces = len(division_order)
    buttons.append(dict(label='전사 평균', method='update', args=[{'visible': [True] + [False]*(len(fig.data)-1)}]))
    buttons.append(dict(label='전체', method='update', args=[{'visible': [False] + [True]*num_div_traces + [False]*(len(fig.data)-1-num_div_traces)}]))
    for div_name in division_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in office_traces_map.get(div_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{div_name}', method='update', args=[{'visible': visibility_mask}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='연간 퇴사율 변화 추이', xaxis_title='연도', yaxis_title='연간 퇴사율 (%)', font_size=14, height=700,
        legend_title_text='조직', annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis=dict(type='category'), yaxis=dict(ticksuffix="%", tickformat='.2f', range=fixed_y_range)
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. Division별 데이터와 전체 평균 데이터 결합
    div_pivot_df = div_df.pivot_table(index='YEAR', columns='GROUP_NAME', values='TURNOVER_RATE').reset_index()
    overall_pivot_df = overall_turnover_df.rename(columns={'TURNOVER_RATE': '전체 평균'})

    aggregate_df = pd.merge(div_pivot_df, overall_pivot_df, on='YEAR', how='outer')

    # 2. 연도 필터링 및 정렬
    aggregate_df = aggregate_df[(aggregate_df['YEAR'] >= 2011) & (aggregate_df['YEAR'] <= 2024)].sort_values('YEAR')
    aggregate_df = aggregate_df.set_index('YEAR')

    # 3. 컬럼 순서 재배치 및 포맷팅
    cols_ordered = ['전체 평균'] + [col for col in division_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols_ordered]

    for col in aggregate_df.columns:
        aggregate_df[col] = aggregate_df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else '-')
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




