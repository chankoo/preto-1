#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.Time_Attendance.detailed_working_info_table import detailed_work_info_df
from services.tables.Time_Attendance.leave_type_table import leave_type_df
from services.tables.Time_Attendance.detailed_leave_info_table import detailed_leave_info_df
from services.tables.Time_Attendance.working_info_table import work_info_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df, position_order, grade_order

def create_figure_and_df():
    """
    제안 17-3: 직위별 주간 리듬 분석 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    start_date_filter = pd.to_datetime('2022-01-01')
    normal_work_emp_ids = work_info_df[work_info_df['WORK_SYS_ID'] == 'WS001']['EMP_ID'].unique()

    pos_info_with_name = pd.merge(position_info_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID')
    pos_info_sorted = pos_info_with_name.sort_values(['GRADE_START_DATE', 'EMP_ID'])

    def add_position_categories(df):
        df_sorted = df.sort_values(['DATE', 'EMP_ID'])
        df_merged = pd.merge_asof(df_sorted, pos_info_sorted[['EMP_ID', 'GRADE_START_DATE', 'POSITION_NAME', 'GRADE_ID']], left_on='DATE', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward')
        return df_merged.dropna(subset=['POSITION_NAME', 'GRADE_ID'])

    overtime_df = daily_work_info_df[(daily_work_info_df['EMP_ID'].isin(normal_work_emp_ids)) & (pd.to_datetime(daily_work_info_df['DATE']) >= start_date_filter)].copy()
    overtime_df['DAY_OF_WEEK'] = overtime_df['DATE'].dt.day_name()
    overtime_df = add_position_categories(overtime_df)

    annual_leave_id = leave_type_df[leave_type_df['LEAVE_TYPE_NAME'] == '연차휴가']['LEAVE_TYPE_ID'].iloc[0]
    leave_df = detailed_leave_info_df[(detailed_leave_info_df['LEAVE_TYPE_ID'] == annual_leave_id) & (detailed_leave_info_df['EMP_ID'].isin(normal_work_emp_ids)) & (pd.to_datetime(detailed_leave_info_df['DATE']) >= start_date_filter)].copy()
    leave_df['DAY_OF_WEEK'] = leave_df['DATE'].dt.day_name()
    leave_df = add_position_categories(leave_df)

    workable_days = detailed_work_info_df[(~detailed_work_info_df['WORK_ETC'].isin(['휴가', '주말 휴무', '비번', '휴무'])) & (detailed_work_info_df['EMP_ID'].isin(normal_work_emp_ids)) & (pd.to_datetime(detailed_work_info_df['DATE']) >= start_date_filter)].copy()
    workable_days['DAY_OF_WEEK'] = workable_days['DATE'].dt.day_name()
    workable_days = add_position_categories(workable_days)

    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    ot_pos_summary = overtime_df.groupby(['POSITION_NAME', 'DAY_OF_WEEK'], observed=False)['OVERTIME_MINUTES'].mean().reset_index()

    workday_headcount_pos = workable_days.groupby(['POSITION_NAME', 'DAY_OF_WEEK'], observed=False).size().reset_index(name='WORK_DAY_COUNT')
    leave_days_sum_pos = leave_df.groupby(['POSITION_NAME', 'DAY_OF_WEEK'], observed=False)['LEAVE_LENGTH'].sum().reset_index()
    leave_pos_summary = pd.merge(leave_days_sum_pos, workday_headcount_pos, on=['POSITION_NAME', 'DAY_OF_WEEK'], how='left').fillna(0)
    leave_pos_summary['LEAVE_USAGE_RATE'] = (leave_pos_summary['LEAVE_LENGTH'] / leave_pos_summary['WORK_DAY_COUNT']) * 100

    ot_min, ot_max = (ot_pos_summary['OVERTIME_MINUTES'].min(), ot_pos_summary['OVERTIME_MINUTES'].max()) if not ot_pos_summary.empty else (0, 0)
    leave_rate_max = leave_pos_summary['LEAVE_USAGE_RATE'].max() if not leave_pos_summary.empty else 0
    y_padding = (ot_max - ot_min) * 0.1 if (ot_max - ot_min) > 0 else 10
    fixed_y1_range = [ot_min - y_padding, ot_max + y_padding]
    fixed_y2_range = [0, leave_rate_max * 1.2]

     # --- 3. Plotly 인터랙티브 그래프 생성 ---
    ot_min, ot_max = (ot_pos_summary['OVERTIME_MINUTES'].min(), ot_pos_summary['OVERTIME_MINUTES'].max()) if not ot_pos_summary.empty else (0, 0)
    leave_rate_max = leave_pos_summary['LEAVE_USAGE_RATE'].max() if not leave_pos_summary.empty else 0
    y_padding = (ot_max - ot_min) * 0.1 if (ot_max - ot_min) > 0 else 10
    fixed_y1_range = [ot_min - y_padding, ot_max + y_padding]
    fixed_y2_range = [0, leave_rate_max * 1.15]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    position_filter_list = ['전체'] + [p for p in position_order if p != 'C-Level']

    for i, job_name in enumerate(position_filter_list):
        is_visible = (i == 0)
        ot_filtered = (ot_pos_summary if job_name == '전체' else ot_pos_summary[ot_pos_summary['POSITION_NAME'] == job_name]).copy()
        leave_filtered = (leave_pos_summary if job_name == '전체' else leave_pos_summary[leave_pos_summary['POSITION_NAME'] == job_name]).copy()

        ot_grouped = ot_filtered.groupby('DAY_OF_WEEK', observed=False)['OVERTIME_MINUTES'].mean().reset_index()
        if job_name == '전체':
            total_leave = leave_pos_summary.groupby('DAY_OF_WEEK', observed=False)['LEAVE_LENGTH'].sum()
            total_workdays = workday_headcount_pos.groupby('DAY_OF_WEEK', observed=False)['WORK_DAY_COUNT'].sum()
            leave_grouped = (total_leave / total_workdays * 100).reset_index(name='LEAVE_USAGE_RATE')
        else:
            leave_grouped = leave_filtered

        for df in [ot_grouped, leave_grouped]:
            if not df.empty:
                df['DAY_OF_WEEK'] = pd.Categorical(df['DAY_OF_WEEK'], categories=weekday_order, ordered=True)
                df.sort_values('DAY_OF_WEEK', inplace=True)

        fig.add_trace(go.Bar(x=ot_grouped['DAY_OF_WEEK'], y=ot_grouped['OVERTIME_MINUTES'], name='평균 초과근무(분)', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Scatter(x=leave_grouped['DAY_OF_WEEK'], y=leave_grouped['LEAVE_USAGE_RATE'], name='연차 사용률(%)', visible=is_visible, mode='lines+markers'), secondary_y=True)

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    for i, job_name in enumerate(position_filter_list):
        visibility_mask = [False] * (len(position_filter_list) * 2)
        visibility_mask[i*2] = True; visibility_mask[i*2 + 1] = True
        buttons.append(dict(label=job_name, method='update', args=[{'visible': visibility_mask}]))

    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직무별 주간 리듬 분석',
        font_size=14, height=700, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(text="직무(L1) 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis_range=fixed_y1_range,
        yaxis2_range=fixed_y2_range
    )
    fig.update_xaxes(title_text="요일")
    fig.update_yaxes(title_text="평균 초과근무 시간 (분)", secondary_y=False)
    fig.update_yaxes(title_text="요일별 연차 사용률 (%)", secondary_y=True, ticksuffix="%")

    # --- 수정된 부분: aggregate_df 생성 ---
    ot_pivot = ot_pos_summary.pivot_table(index='DAY_OF_WEEK', columns='POSITION_NAME', values='OVERTIME_MINUTES', observed=False)
    ot_pivot['METRIC'] = '평균 초과근무시간(분)'
    leave_pivot = leave_pos_summary.pivot_table(index='DAY_OF_WEEK', columns='POSITION_NAME', values='LEAVE_USAGE_RATE', observed=False)
    leave_pivot['METRIC'] = '요일별 연차사용률(%)'
    combined_df = pd.concat([ot_pivot, leave_pivot]).reset_index().set_index(['METRIC', 'DAY_OF_WEEK'])

    overall_ot = overtime_df.groupby('DAY_OF_WEEK', observed=False)['OVERTIME_MINUTES'].mean()
    overall_total_leave = leave_df.groupby('DAY_OF_WEEK', observed=False)['LEAVE_LENGTH'].sum()
    overall_total_workdays = workable_days.groupby('DAY_OF_WEEK', observed=False).size()
    overall_leave_rate = (overall_total_leave / overall_total_workdays) * 100
    overall_df = pd.DataFrame({'평균 초과근무시간(분)': overall_ot, '요일별 연차사용률(%)': overall_leave_rate}).T
    overall_df.index.name = 'METRIC'
    overall_df = overall_df.reset_index().melt(id_vars='METRIC', var_name='DAY_OF_WEEK', value_name='전체 평균').set_index(['METRIC', 'DAY_OF_WEEK'])

    aggregate_df = pd.merge(combined_df, overall_df, left_index=True, right_index=True, how='outer')

    cols_ordered = ['전체 평균'] + [p for p in position_order if p in aggregate_df.columns]
    aggregate_df = aggregate_df[cols_ordered]

    metric_order = ['평균 초과근무시간(분)', '요일별 연차사용률(%)']
    aggregate_df = aggregate_df.reindex(index=pd.MultiIndex.from_product([metric_order, weekday_order], names=['METRIC', 'DAY_OF_WEEK']))

    for col in aggregate_df.columns:
        aggregate_df[col] = aggregate_df.apply(
            lambda row: f"{row[col]:.2f}%" if row.name[0] == '요일별 연차사용률(%)' and pd.notna(row[col]) else (f"{row[col]:.2f}" if pd.notna(row[col]) else '-'),
            axis=1
        )
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




