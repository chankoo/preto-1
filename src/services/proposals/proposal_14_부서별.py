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
from services.tables.Time_Attendance.detailed_working_info_table import detailed_work_info_df
from services.tables.Time_Attendance.working_info_table import work_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df, position_order
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure_and_df():
    """
    제안 14: 조직별/직위별 지각률(%) 분석 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    work_records = detailed_work_info_df.copy()
    work_records = work_records[~work_records['WORK_ETC'].isin(['휴가', '주말 휴무', '비번', '휴무'])]
    work_records = work_records[work_records['DATE_START_TIME'] != '-']
    normal_work_emp_ids = work_info_df[work_info_df['WORK_SYS_ID'] == 'WS001']['EMP_ID'].unique()
    work_records = work_records[work_records['EMP_ID'].isin(normal_work_emp_ids)].copy()
    work_records['DATE'] = pd.to_datetime(work_records['DATE'])

    dept_info_sorted = department_info_df.sort_values(['DEP_APP_START_DATE', 'EMP_ID'])
    pos_info_sorted = position_info_df.sort_values(['GRADE_START_DATE', 'EMP_ID'])
    analysis_df = work_records.sort_values(['DATE', 'EMP_ID'])
    analysis_df = pd.merge_asof(analysis_df, dept_info_sorted[['EMP_ID', 'DEP_APP_START_DATE', 'DEP_ID']],left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward')
    analysis_df = pd.merge_asof(analysis_df, pos_info_sorted[['EMP_ID', 'GRADE_START_DATE', 'POSITION_ID']],left_on='DATE', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward')

    parent_info = analysis_df['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    analysis_df = pd.concat([analysis_df, parent_info], axis=1)
    analysis_df = pd.merge(analysis_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'])
    analysis_df = analysis_df.copy()

    analysis_df['START_TIME_OBJ'] = pd.to_datetime(analysis_df['DATE_START_TIME'], format='%H:%M', errors='coerce').dt.time
    gso_mask = analysis_df['OFFICE_NAME'] == 'Global Sales Office'
    analysis_df.loc[gso_mask, 'IS_LATE'] = analysis_df.loc[gso_mask, 'START_TIME_OBJ'] > datetime.time(11, 0)
    analysis_df.loc[~gso_mask, 'IS_LATE'] = analysis_df.loc[~gso_mask, 'START_TIME_OBJ'] > datetime.time(10, 0)

    total_days = analysis_df.groupby(['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'], observed=False).size().reset_index(name='TOTAL_DAYS')
    late_days = analysis_df[analysis_df['IS_LATE']].groupby(['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'], observed=False).size().reset_index(name='LATE_DAYS')
    lateness_df = pd.merge(total_days, late_days, on=['DIVISION_NAME', 'OFFICE_NAME', 'POSITION_NAME'], how='left').fillna(0)
    lateness_df['LATENESS_RATE'] = (lateness_df['LATE_DAYS'] / lateness_df['TOTAL_DAYS']) * 100
    div_lateness_df = lateness_df.groupby(['DIVISION_NAME', 'POSITION_NAME'], observed=False).agg(TOTAL_DAYS=('TOTAL_DAYS', 'sum'), LATE_DAYS=('LATE_DAYS', 'sum')).reset_index()
    div_lateness_df['LATENESS_RATE'] = (div_lateness_df['LATE_DAYS'] / div_lateness_df['TOTAL_DAYS']) * 100

    div_lateness_df['DIVISION_NAME'] = pd.Categorical(div_lateness_df['DIVISION_NAME'], categories=division_order, ordered=True)
    lateness_df['OFFICE_NAME'] = pd.Categorical(lateness_df['OFFICE_NAME'], categories=office_order, ordered=True)
    div_lateness_df = div_lateness_df.sort_values('DIVISION_NAME')
    lateness_df = lateness_df.sort_values(['DIVISION_NAME', 'OFFICE_NAME'])

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    y_max = pd.concat([div_lateness_df['LATENESS_RATE'], lateness_df['LATENESS_RATE']]).max()
    fixed_y_range = [0, y_max * 1.2]

    fig = go.Figure()
    position_order = ['Staff', 'Manager', 'Director', 'C-Level']
    colors = px.colors.qualitative.Plotly

    for i, pos_name in enumerate(position_order):
        df_filtered = div_lateness_df[div_lateness_df['POSITION_NAME'] == pos_name]
        fig.add_trace(go.Bar(x=df_filtered['DIVISION_NAME'], y=df_filtered['LATENESS_RATE'], name=pos_name, marker_color=colors[i],
                             text=df_filtered['LATENESS_RATE'].round(2).astype(str) + '%', textposition='outside'))

    office_traces_map = {}
    trace_idx_counter = len(fig.data)
    for div_name in division_order:
        office_div_df = lateness_df[lateness_df['DIVISION_NAME'] == div_name]
        office_traces_map[div_name] = []
        for j, pos_name in enumerate(position_order):
            df_filtered = office_div_df[office_div_df['POSITION_NAME'] == pos_name]
            fig.add_trace(go.Bar(x=df_filtered['OFFICE_NAME'], y=df_filtered['LATENESS_RATE'], name=pos_name, visible=False, marker_color=colors[j],
                                     text=df_filtered['LATENESS_RATE'].round(2).astype(str) + '%', textposition='outside'))
            office_traces_map[div_name].append(trace_idx_counter)
            trace_idx_counter += 1

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    visible_div = [True]*len(position_order) + [False]*(len(fig.data)-len(position_order))
    text_div = [div_lateness_df[div_lateness_df['POSITION_NAME'] == p]['LATENESS_RATE'].round(2).astype(str) + '%' for p in position_order] + [None]*(len(fig.data)-len(position_order))
    buttons.append(dict(label='전체', method='update',
                        args=[{'visible': visible_div, 'text': text_div},
                              {'title': '전체 Division별 지각률(%) 분석', 'xaxis.title': 'Division'}]))

    for div_name in division_order:
        visibility_mask = [False] * len(fig.data)
        text_mask = [None] * len(fig.data)
        for trace_idx in office_traces_map.get(div_name, []):
            visibility_mask[trace_idx] = True
            pos_name = fig.data[trace_idx].name
            office_data = lateness_df[(lateness_df['DIVISION_NAME'] == div_name) & (lateness_df['POSITION_NAME'] == pos_name)]
            text_mask[trace_idx] = office_data['LATENESS_RATE'].round(2).astype(str) + '%'

        buttons.append(dict(label=f'{div_name}', method='update',
                            args=[{'visible': visibility_mask, 'text': text_mask},
                                  {'title': f'{div_name} 내 Office별 지각률(%) 분석', 'xaxis.title': 'Office'}]))

    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='조직별/직위별 지각률(%) 분석',
        yaxis_title='지각률 (%)',
        font_size=14, height=700,
        barmode='group',
        legend_title_text='직위',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis=dict(ticksuffix="%", range=fixed_y_range)
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. 피벗 테이블 생성
    aggregate_df = div_lateness_df.pivot_table(
        index='POSITION_NAME',
        columns='DIVISION_NAME',
        values='LATENESS_RATE',
        observed=False
    )

    # 2. '전체 평균' 컬럼 추가
    overall_summary = analysis_df.groupby('POSITION_NAME', observed=False).agg(
        TOTAL_DAYS=('EMP_ID', 'count'),
        LATE_DAYS=('IS_LATE', 'sum')
    )
    overall_summary['OVERALL_AVG_RATE'] = (overall_summary['LATE_DAYS'] / overall_summary['TOTAL_DAYS']) * 100
    aggregate_df['전체 평균'] = overall_summary['OVERALL_AVG_RATE']

    # 3. 컬럼/행 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in division_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols]
    aggregate_df = aggregate_df.reindex(position_order)

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




