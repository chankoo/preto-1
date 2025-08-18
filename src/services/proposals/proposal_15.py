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
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure():
    """
    제안 15: 부서 변경 전후 초과근무 패턴 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    # 2-1. '부서 변경' 이벤트 추출
    dept_changes = department_info_df.sort_values(['EMP_ID', 'DEP_APP_START_DATE'])
    dept_changes['PREV_DEP_ID'] = dept_changes.groupby('EMP_ID')['DEP_ID'].shift(1)
    dept_changes = dept_changes[dept_changes['PREV_DEP_ID'].notna() & (dept_changes['DEP_ID'] != dept_changes['PREV_DEP_ID'])].copy()
    dept_changes = dept_changes.rename(columns={'DEP_APP_START_DATE': 'CHANGE_DATE'})

    # 분석 기간 제한
    start_date_filter = pd.to_datetime('2022-01-01')
    daily_work_filtered_df = daily_work_info_df[daily_work_info_df['DATE'] >= start_date_filter].copy()

    # 2-2. 변경 전/후 3개월간의 초과근무 데이터 계산
    pattern_records = []
    if not dept_changes.empty:
        for _, row in dept_changes.iterrows():
            emp_id, change_date = row['EMP_ID'], row['CHANGE_DATE']
            before_start, after_end = change_date - pd.DateOffset(months=3), change_date + pd.DateOffset(months=3)
            emp_work_df = daily_work_filtered_df[daily_work_filtered_df['EMP_ID'] == emp_id]
            ot_before = emp_work_df[emp_work_df['DATE'].between(before_start, change_date - pd.DateOffset(days=1))]['OVERTIME_MINUTES'].mean()
            ot_after = emp_work_df[emp_work_df['DATE'].between(change_date, after_end)]['OVERTIME_MINUTES'].mean()
            if pd.notna(ot_before) and pd.notna(ot_after):
                pattern_records.append({'EMP_ID': emp_id, 'CHANGE_DATE': change_date, 'NEW_DEP_ID': row['DEP_ID'], 'OT_BEFORE': ot_before, 'OT_AFTER': ot_after})
    analysis_df = pd.DataFrame(pattern_records)

    # 2-3. 조직별 평소 평균 초과근무 시간 계산
    if not analysis_df.empty:
        daily_work_with_dept = pd.merge_asof(daily_work_filtered_df.sort_values('DATE'), department_info_df.sort_values('DEP_APP_START_DATE'), left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward')
        parent_info_daily = daily_work_with_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        daily_work_with_dept = pd.concat([daily_work_with_dept, parent_info_daily], axis=1)
        daily_work_with_dept = daily_work_with_dept.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])
        div_overall_avg = daily_work_with_dept.groupby('DIVISION_NAME', observed=False)['OVERTIME_MINUTES'].mean().reset_index().rename(columns={'OVERTIME_MINUTES': 'DEPT_AVG'})
        office_overall_avg = daily_work_with_dept.groupby(['DIVISION_NAME','OFFICE_NAME'], observed=False)['OVERTIME_MINUTES'].mean().reset_index().rename(columns={'OVERTIME_MINUTES': 'DEPT_AVG'})

        parent_info = analysis_df['NEW_DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        analysis_df = pd.concat([analysis_df, parent_info], axis=1)
        analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])
        div_summary = analysis_df.groupby('DIVISION_NAME', observed=False)[['OT_BEFORE', 'OT_AFTER']].mean()
        div_summary = pd.merge(div_summary, div_overall_avg, on='DIVISION_NAME').reset_index()
        office_summary = analysis_df.groupby(['DIVISION_NAME', 'OFFICE_NAME'], observed=False)[['OT_BEFORE', 'OT_AFTER']].mean()
        office_summary = pd.merge(office_summary, office_overall_avg, on=['DIVISION_NAME','OFFICE_NAME']).reset_index()

        div_summary['DIVISION_NAME'] = pd.Categorical(div_summary['DIVISION_NAME'], categories=division_order, ordered=True)
        div_summary = div_summary.sort_values('DIVISION_NAME')
        office_summary['OFFICE_NAME'] = pd.Categorical(office_summary['OFFICE_NAME'], categories=office_order, ordered=True)
        office_summary = office_summary.sort_values('OFFICE_NAME')

        all_values = pd.concat([
            div_summary['OT_BEFORE'], div_summary['OT_AFTER'], div_summary['DEPT_AVG'],
            office_summary['OT_BEFORE'], office_summary['OT_AFTER'], office_summary['DEPT_AVG']
        ])
        y_min, y_max = all_values.min(), all_values.max()
        y_padding = (y_max - y_min) * 0.1
        fixed_y_range = [y_min - y_padding, y_max + y_padding]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    periods = {'변경 전': 'OT_BEFORE', '변경 후': 'OT_AFTER', '부서 평균': 'DEPT_AVG'}
    if not analysis_df.empty:
        for period_name, col_name in periods.items():
            fig.add_trace(go.Bar(x=div_summary['DIVISION_NAME'], y=div_summary[col_name], name=period_name))

        office_traces_map = {}
        trace_idx_counter = len(fig.data)
        for div_name in division_order:
            office_div_df = office_summary[office_summary['DIVISION_NAME'] == div_name]
            office_traces_map[div_name] = []
            for period_name, col_name in periods.items():
                if not office_div_df.empty:
                    fig.add_trace(go.Bar(x=office_div_df['OFFICE_NAME'], y=office_div_df[col_name], name=period_name, visible=False))
                    office_traces_map[div_name].append(trace_idx_counter)
                    trace_idx_counter += 1

        buttons = []
        buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*3 + [False]*(len(fig.data)-3)}, {'title': '부서 변경 전후 3개월간 일평균 초과근무 시간 비교', 'xaxis': {'title': 'Division', 'categoryorder':'array', 'categoryarray': division_order}}]))
        for div_name in division_order:
            visibility_mask = [False] * len(fig.data)
            for trace_idx in office_traces_map.get(div_name, []):
                visibility_mask[trace_idx] = True
            offices_in_div = office_summary[office_summary['DIVISION_NAME'] == div_name]['OFFICE_NAME'].unique().tolist()
            buttons.append(dict(label=f'{div_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{div_name} 내 Office별 초과근무 시간 비교', 'xaxis': {'title': 'Office', 'categoryorder':'array', 'categoryarray': offices_in_div}}]))

        fig.update_layout(
            updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
            title_text='부서변경 전후 초과근무 패턴 분석',
            yaxis_title='일평균 초과근무 시간 (분)',
            font_size=14, height=700, barmode='group', legend_title_text='시점',
            annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
            yaxis_range=fixed_y_range
        )
    else:
        fig.update_layout(title_text="분석할 부서 변경 데이터가 없습니다.")

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
if __name__ == '__main__':
    pio.renderers.default = 'vscode'
    fig = create_figure()
    fig.show()


# In[ ]:




