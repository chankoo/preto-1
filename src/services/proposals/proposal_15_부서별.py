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
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order, office_order
)
from services.helpers.utils import find_parents

def create_figure_and_df():
    """
    제안 15: 부서 변경 전후 초과근무 패턴 분석 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    dept_changes = department_info_df.sort_values(['EMP_ID', 'DEP_APP_START_DATE'])
    dept_changes['PREV_DEP_ID'] = dept_changes.groupby('EMP_ID')['DEP_ID'].shift(1)
    dept_changes = dept_changes[dept_changes['PREV_DEP_ID'].notna() & (dept_changes['DEP_ID'] != dept_changes['PREV_DEP_ID'])].copy()
    dept_changes = dept_changes.rename(columns={'DEP_APP_START_DATE': 'CHANGE_DATE'})

    start_date_filter = pd.to_datetime('2022-01-01')
    daily_work_filtered_df = daily_work_info_df[daily_work_info_df['DATE'] >= start_date_filter].copy()

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

    if not analysis_df.empty:
        daily_work_with_dept = pd.merge_asof(daily_work_filtered_df.sort_values('DATE'), department_info_df.sort_values('DEP_APP_START_DATE'), left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward')
        parent_info_daily = daily_work_with_dept['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        daily_work_with_dept = pd.concat([daily_work_with_dept, parent_info_daily], axis=1)
        daily_work_with_dept = daily_work_with_dept.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])
        div_overall_avg = daily_work_with_dept.groupby('DIVISION_NAME', observed=False)['OVERTIME_MINUTES'].mean().reset_index().rename(columns={'OVERTIME_MINUTES': 'DEPT_AVG'})
        office_overall_avg = daily_work_with_dept.groupby(['DIVISION_NAME','OFFICE_NAME'], observed=False)['OVERTIME_MINUTES'].mean().reset_index().rename(columns={'OVERTIME_MINUTES': 'DEPT_AVG'})

        parent_info = analysis_df['NEW_DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
        analysis_df_with_org = pd.concat([analysis_df, parent_info], axis=1)
        analysis_df_with_org = analysis_df_with_org.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME'])
        div_summary = analysis_df_with_org.groupby('DIVISION_NAME', observed=False)[['OT_BEFORE', 'OT_AFTER']].mean()
        div_summary = pd.merge(div_summary, div_overall_avg, on='DIVISION_NAME').reset_index()
        office_summary = analysis_df_with_org.groupby(['DIVISION_NAME', 'OFFICE_NAME'], observed=False)[['OT_BEFORE', 'OT_AFTER']].mean()
        office_summary = pd.merge(office_summary, office_overall_avg, on=['DIVISION_NAME','OFFICE_NAME']).reset_index()

        div_summary['DIVISION_NAME'] = pd.Categorical(div_summary['DIVISION_NAME'], categories=division_order, ordered=True)
        div_summary = div_summary.sort_values('DIVISION_NAME')
        office_summary['OFFICE_NAME'] = pd.Categorical(office_summary['OFFICE_NAME'], categories=office_order, ordered=True)
        office_summary = office_summary.sort_values('OFFICE_NAME')

        all_values = pd.concat([div_summary['OT_BEFORE'], div_summary['OT_AFTER'], div_summary['DEPT_AVG'], office_summary['OT_BEFORE'], office_summary['OT_AFTER'], office_summary['DEPT_AVG']])
        y_min, y_max = (all_values.min(), all_values.max()) if not all_values.empty else (0,0)
        y_padding = (y_max - y_min) * 0.1
        fixed_y_range = [y_min - y_padding, y_max + y_padding]

        # --- 3. Plotly 인터랙티브 그래프 생성 ---
        # (그래프 생성 코드는 이전과 동일)
        fig = go.Figure()
        periods = {'변경 전': 'OT_BEFORE', '변경 후': 'OT_AFTER', '부서 평균': 'DEPT_AVG'}
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
            title_text='부서변경 전후 초과근무 패턴 분석', yaxis_title='일평균 초과근무 시간 (분)',
            font_size=14, height=700, barmode='group', legend_title_text='시점',
            annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
            yaxis_range=fixed_y_range
        )
    else:
        fig = go.Figure()
        fig.update_layout(title_text="분석할 부서 변경 데이터가 없습니다.")
        div_summary = pd.DataFrame() # 빈 데이터프레임 생성

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. 피벗 테이블 생성을 위해 데이터프레임 변환
    aggregate_df = div_summary.melt(
        id_vars=['DIVISION_NAME'],
        value_vars=['OT_BEFORE', 'OT_AFTER', 'DEPT_AVG'],
        var_name='TIMING',
        value_name='AVG_OVERTIME'
    ).rename(columns={'TIMING': '시점'})

    # 2. '시점' 이름 변경
    aggregate_df['시점'] = aggregate_df['시점'].map({
        'OT_BEFORE': '변경 전',
        'OT_AFTER': '변경 후',
        'DEPT_AVG': '부서 평균'
    })

    # 3. 피벗 테이블 생성
    aggregate_df = aggregate_df.pivot_table(
        index='시점',
        columns='DIVISION_NAME',
        values='AVG_OVERTIME',
        observed=False
    )

    # 4. '전체 평균' 컬럼 추가
    overall_avg = analysis_df[['OT_BEFORE', 'OT_AFTER']].mean()
    overall_dept_avg = daily_work_with_dept['OVERTIME_MINUTES'].mean()
    aggregate_df['전체 평균'] = [overall_avg['OT_BEFORE'], overall_avg['OT_AFTER'], overall_dept_avg]

    # 5. 컬럼/행 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in division_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols]
    row_order = ['변경 전', '변경 후', '부서 평균']
    aggregate_df = aggregate_df.reindex(row_order).round(2)
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




