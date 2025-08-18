#!/usr/bin/env python
# coding: utf-8

# In[4]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure():
    """
    제안 9: 조직 활력도 진단 (연도별 직무 이동률) 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    job_changes = job_info_df.copy()
    job_changes = pd.merge(job_changes, emp_df[['EMP_ID', 'IN_DATE']], on='EMP_ID', how='left')
    job_changes = job_changes[job_changes['JOB_APP_START_DATE'] > job_changes['IN_DATE']]
    job_changes['YEAR'] = job_changes['JOB_APP_START_DATE'].dt.year

    dept_info_sorted = department_info_df.sort_values(['DEP_APP_START_DATE', 'EMP_ID'])
    job_changes_with_dept = pd.merge_asof(
        job_changes.sort_values('JOB_APP_START_DATE'),
        dept_info_sorted[['EMP_ID', 'DEP_APP_START_DATE', 'DEP_ID']],
        left_on='JOB_APP_START_DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward'
    )
    parent_info = job_changes_with_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    job_changes_with_dept = pd.concat([job_changes_with_dept, parent_info], axis=1)
    job_changes_with_dept = job_changes_with_dept.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])

    analysis_records = []
    all_years = sorted(job_changes_with_dept['YEAR'].unique())
    for year in all_years:
        year_start, year_end = pd.to_datetime(f'{year}-01-01'), pd.to_datetime(f'{year}-12-31')

        active_in_year = emp_df[(emp_df['IN_DATE'] <= year_end) & (emp_df['OUT_DATE'].isnull() | (emp_df['OUT_DATE'] >= year_start))]
        active_dept = pd.merge_asof(
            active_in_year[['EMP_ID', 'IN_DATE']].sort_values('IN_DATE'),
            department_info_df.sort_values('DEP_APP_START_DATE'),
            left_on='IN_DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward'
        )
        parent_info_active = active_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        active_dept = pd.concat([active_dept, parent_info_active], axis=1)
        active_dept = active_dept.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])

        headcount_div = active_dept.groupby('DIVISION_NAME', observed=False).size()
        headcount_office = active_dept.groupby(['DIVISION_NAME', 'OFFICE_NAME'], observed=False).size()

        changes_in_year = job_changes_with_dept[job_changes_with_dept['YEAR'] == year]
        changes_div = changes_in_year.groupby('DIVISION_NAME', observed=False).size()
        changes_office = changes_in_year.groupby(['DIVISION_NAME', 'OFFICE_NAME'], observed=False).size()

        for div_name, count in headcount_div.items():
            change_count = changes_div.get(div_name, 0)
            rate = (change_count / count) * 100 if count > 0 else 0
            analysis_records.append({'YEAR': year, 'GROUP_TYPE': 'DIVISION', 'GROUP_NAME': div_name, 'MOBILITY_RATE': rate})

        for (div_name, office_name), count in headcount_office.items():
            change_count = changes_office.get((div_name, office_name), 0)
            rate = (change_count / count) * 100 if count > 0 else 0
            analysis_records.append({'YEAR': year, 'GROUP_TYPE': 'OFFICE', 'DIVISION_NAME': div_name, 'GROUP_NAME': office_name, 'MOBILITY_RATE': rate})

    analysis_df = pd.DataFrame(analysis_records)

    div_df = analysis_df[analysis_df['GROUP_TYPE'] == 'DIVISION'].copy()
    office_df = analysis_df[analysis_df['GROUP_TYPE'] == 'OFFICE'].copy()

    div_df['GROUP_NAME'] = pd.Categorical(div_df['GROUP_NAME'], categories=division_order, ordered=True)
    office_df['DIVISION_NAME'] = pd.Categorical(office_df['DIVISION_NAME'], categories=division_order, ordered=True)
    office_df['GROUP_NAME'] = pd.Categorical(office_df['GROUP_NAME'], categories=office_order, ordered=True)

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    y_max = analysis_df['MOBILITY_RATE'].max()
    fixed_y_range = [0, y_max * 1.15]

    fig = go.Figure()
    colors = px.colors.qualitative.Plotly

    # 1. Division 레벨 트레이스
    for i, div_name in enumerate(division_order):
        df_filtered = div_df[div_df['GROUP_NAME'] == div_name].sort_values('YEAR')
        if not df_filtered.empty:
            fig.add_trace(go.Scatter(
                x=df_filtered['YEAR'], y=df_filtered['MOBILITY_RATE'], mode='lines+markers+text', name=div_name,
                line=dict(color=colors[i]),
                text=df_filtered['MOBILITY_RATE'].round(2).astype(str) + '%', textposition='top center'
            ))

    # 2. Office 레벨 트레이스
    office_traces_map = {}
    trace_idx_counter = len(fig.data)
    for div_name in division_order:
        office_div_df = office_df[office_df['DIVISION_NAME'] == div_name]
        offices_in_div_sorted = office_div_df['GROUP_NAME'].unique()
        office_traces_map[div_name] = []
        for j, office_name in enumerate(offices_in_div_sorted):
            df_filtered = office_div_df[office_div_df['GROUP_NAME'] == office_name].sort_values('YEAR')
            if not df_filtered.empty:
                fig.add_trace(go.Scatter(
                    x=df_filtered['YEAR'], y=df_filtered['MOBILITY_RATE'], mode='lines+markers+text',
                    name=str(office_name), visible=False, line=dict(color=colors[j % len(colors)]),
                    text=df_filtered['MOBILITY_RATE'].round(2).astype(str) + '%', textposition='top center'
                ))
                office_traces_map[div_name].append(trace_idx_counter)
                trace_idx_counter += 1

    # 3. 드롭다운 메뉴 및 레이아웃 업데이트
    buttons = [dict(label='전체', method='update', args=[{'visible': [True]*len(division_order) + [False]*(len(fig.data)-len(division_order))}])]
    for div_name in division_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in office_traces_map.get(div_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{div_name}', method='update', args=[{'visible': visibility_mask}]))

    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='연도별/조직별 직무 이동률(%) 변화 추이',
        xaxis_title='연도', yaxis_title='직무 이동률 (%)',
        font_size=14, height=700,
        legend_title_text='조직',
        xaxis=dict(type='category'),
        yaxis=dict(ticksuffix="%", range=fixed_y_range)
    )

    return fig


pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




