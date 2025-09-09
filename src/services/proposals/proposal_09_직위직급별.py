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
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df, position_order, grade_order

def create_figure_and_df():
    """
    제안 9-3: 직위/직급별 연간 직무 이동률 변화 추이 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    job_changes = job_info_df.copy()
    job_changes = pd.merge(job_changes, emp_df[['EMP_ID', 'IN_DATE']], on='EMP_ID', how='left')
    job_changes = job_changes[job_changes['JOB_APP_START_DATE'] > job_changes['IN_DATE']]
    job_changes['YEAR'] = job_changes['JOB_APP_START_DATE'].dt.year

    turnover_records = []
    overall_records = [] # '전체 평균' 계산을 위한 리스트
    all_years = sorted(job_changes['YEAR'].unique())

    pos_info_with_name = pd.merge(position_info_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID')
    pos_info_sorted = pos_info_with_name.sort_values('GRADE_START_DATE')

    for year in all_years:
        year_end = pd.to_datetime(f'{year}-12-31')
        active_in_year = emp_df[(emp_df['IN_DATE'] <= year_end) & (emp_df['OUT_DATE'].isnull() | (emp_df['OUT_DATE'] > year_end))].copy()
        active_in_year['DATE_SNAPSHOT'] = year_end
        changes_in_year = job_changes[job_changes['YEAR'] == year].copy()

        # 전체 평균 계산
        if not active_in_year.empty:
            overall_rate = (len(changes_in_year) / len(active_in_year)) * 100
            overall_records.append({'YEAR': year, 'MOBILITY_RATE': overall_rate})

        active_pos = pd.merge_asof(active_in_year[['EMP_ID', 'DATE_SNAPSHOT']].sort_values('DATE_SNAPSHOT'), pos_info_sorted, left_on='DATE_SNAPSHOT', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward')
        active_pos = active_pos.dropna(subset=['POSITION_NAME', 'GRADE_ID'])

        changes_pos = pd.merge_asof(changes_in_year.assign(DATE_SNAPSHOT=year_end).sort_values('DATE_SNAPSHOT'), pos_info_sorted, left_on='DATE_SNAPSHOT', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward')
        changes_pos = changes_pos.dropna(subset=['POSITION_NAME', 'GRADE_ID'])

        headcount_by_pos = active_pos.groupby('POSITION_NAME', observed=False).size()
        changes_by_pos = changes_pos.groupby('POSITION_NAME', observed=False).size()
        mobility_pos = (changes_by_pos / headcount_by_pos * 100).fillna(0)
        for group_name, rate in mobility_pos.items():
            turnover_records.append({'YEAR': year, 'GROUP_TYPE': 'POSITION', 'GROUP_NAME': group_name, 'MOBILITY_RATE': rate})

        headcount_by_grade = active_pos.groupby(['POSITION_NAME', 'GRADE_ID'], observed=False).size()
        changes_by_grade = changes_pos.groupby(['POSITION_NAME', 'GRADE_ID'], observed=False).size()
        mobility_grade = (changes_by_grade / headcount_by_grade * 100).fillna(0)
        for (pos_name, grade_name), rate in mobility_grade.items():
            turnover_records.append({'YEAR': year, 'GROUP_TYPE': 'GRADE', 'POSITION_NAME': pos_name, 'GROUP_NAME': grade_name, 'MOBILITY_RATE': rate})

    analysis_df = pd.DataFrame(turnover_records)
    overall_df = pd.DataFrame(overall_records)
    pos_df = analysis_df[analysis_df['GROUP_TYPE'] == 'POSITION'].copy()

    if analysis_df.empty:
        return go.Figure().update_layout(title_text="분석할 직무 이동 데이터가 없습니다."), pd.DataFrame()

    y_max = analysis_df['MOBILITY_RATE'].max()
    fixed_y_range = [0, y_max * 1.2]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    position_filter_list = [p for p in position_order if p != 'C-Level']
    for i, pos_name in enumerate(position_filter_list):
        df_filtered = pos_df[pos_df['GROUP_NAME'] == pos_name].sort_values('YEAR')
        if not df_filtered.empty:
            fig.add_trace(go.Scatter(x=df_filtered['YEAR'], y=df_filtered['MOBILITY_RATE'], mode='lines+markers+text', name=pos_name, line=dict(color=colors[i]), text=df_filtered['MOBILITY_RATE'].round(2).astype(str) + '%', textposition='top center'))
    grade_df = analysis_df[analysis_df['GROUP_TYPE'] == 'GRADE']
    grade_traces_map = {}
    trace_idx_counter = len(fig.data)
    for pos_name in position_filter_list:
        grade_pos_df = grade_df[grade_df['POSITION_NAME'] == pos_name]
        grades_in_pos = [g for g in grade_order if g in grade_pos_df['GROUP_NAME'].unique()]
        grade_traces_map[pos_name] = []
        for j, grade_name in enumerate(grades_in_pos):
            df_filtered = grade_pos_df[grade_pos_df['GROUP_NAME'] == grade_name].sort_values('YEAR')
            if not df_filtered.empty:
                fig.add_trace(go.Scatter(x=df_filtered['YEAR'], y=df_filtered['MOBILITY_RATE'], mode='lines+markers+text', name=grade_name, visible=False, line=dict(color=colors[j % len(colors)]), text=df_filtered['MOBILITY_RATE'].round(2).astype(str) + '%', textposition='top center'))
                grade_traces_map[pos_name].append(trace_idx_counter)
                trace_idx_counter += 1
    buttons = []
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*len(position_filter_list) + [False]*(len(fig.data)-len(position_filter_list))}, {'title': '전체 직위별 연간 직무 이동률(%) 변화 추이', 'legend_title_text': '직위'}]))
    for pos_name in position_filter_list:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in grade_traces_map.get(pos_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{pos_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{pos_name} 내 직급별 연간 직무 이동률(%) 변화 추이', 'legend_title_text': '직급'}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직위/직급별 연간 직무 이동률(%) 변화 추이',
        xaxis_title='연도', yaxis_title='직무 이동률 (%)', font_size=14, height=700,
        legend_title_text='직위',
        xaxis=dict(type='category'),
        yaxis=dict(ticksuffix="%", range=fixed_y_range),
        annotations=[dict(text="직위/직급 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    aggregate_df = pos_df.pivot_table(index='YEAR', columns='GROUP_NAME', values='MOBILITY_RATE', observed=False)
    overall_df.set_index('YEAR', inplace=True)
    aggregate_df['전체 평균'] = overall_df['MOBILITY_RATE']
    aggregate_df = aggregate_df.reindex(range(2012, 2026)).sort_index()
    cols = ['전체 평균'] + [col for col in position_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols]
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




