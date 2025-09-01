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
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df

def create_figure():
    """
    제안 0-7: 직위별 분기 인원 변동 현황 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    emp_dates_df = emp_df[['EMP_ID', 'IN_DATE', 'OUT_DATE']].copy()
    emp_dates_df['IN_DATE'] = pd.to_datetime(emp_dates_df['IN_DATE'])
    emp_dates_df['OUT_DATE'] = pd.to_datetime(emp_dates_df['OUT_DATE'])

    pos_info_with_name = pd.merge(position_info_df, position_df[['POSITION_ID', 'POSITION_NAME']], on='POSITION_ID', how='left')
    pos_info_sorted = pos_info_with_name.sort_values('GRADE_START_DATE')
    position_order = ['Staff', 'Manager', 'Director', 'C-Level']

    start_month = emp_dates_df['IN_DATE'].min().to_period('M').to_timestamp()
    end_month = pd.to_datetime(datetime.datetime.now()).to_period('M').to_timestamp()
    monthly_periods = pd.date_range(start=start_month, end=end_month, freq='MS')

    monthly_summary_records = []
    for period_start in monthly_periods:
        period_end = period_start + pd.offsets.MonthEnd(0)

        hires_df = emp_dates_df[emp_dates_df['IN_DATE'].between(period_start, period_end)]
        leavers_df = emp_dates_df[emp_dates_df['OUT_DATE'].between(period_start, period_end)]
        active_df = emp_dates_df[(emp_dates_df['IN_DATE'] <= period_end) & ((emp_dates_df['OUT_DATE'].isnull()) | (emp_dates_df['OUT_DATE'] > period_end))].copy()
        active_df['DATE_SNAPSHOT'] = period_end

        hires_with_pos = pd.merge_asof(hires_df.sort_values('IN_DATE'), pos_info_sorted, left_on='IN_DATE', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward')
        leavers_with_pos = pd.merge_asof(leavers_df.sort_values('OUT_DATE'), pos_info_sorted, left_on='OUT_DATE', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward')
        active_with_pos = pd.merge_asof(active_df.sort_values('DATE_SNAPSHOT'), pos_info_sorted, left_on='DATE_SNAPSHOT', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward')

        hires_by_pos = hires_with_pos.groupby('POSITION_NAME').size() if not hires_with_pos.empty else pd.Series(dtype=int)
        leavers_by_pos = leavers_with_pos.groupby('POSITION_NAME').size() if not leavers_with_pos.empty else pd.Series(dtype=int)
        headcount_by_pos = active_with_pos.groupby('POSITION_NAME').size() if not active_with_pos.empty else pd.Series(dtype=int)

        all_pos_in_period = set(hires_by_pos.index) | set(leavers_by_pos.index) | set(headcount_by_pos.index)

        for pos in all_pos_in_period:
            if pd.notna(pos):
                monthly_summary_records.append({
                    'PERIOD_DT': period_start, 'POSITION_NAME': pos,
                    'NEW_HIRES': hires_by_pos.get(pos, 0), 'LEAVERS': leavers_by_pos.get(pos, 0), 'HEADCOUNT': headcount_by_pos.get(pos, 0)
                })

    monthly_pos_summary_df = pd.DataFrame(monthly_summary_records)

    monthly_pos_summary_df['QUARTER'] = monthly_pos_summary_df['PERIOD_DT'].dt.to_period('Q')
    quarterly_pos_summary_df = monthly_pos_summary_df.groupby(['QUARTER', 'POSITION_NAME']).agg(
        NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'last')
    ).reset_index()

    quarterly_overall_summary_df = quarterly_pos_summary_df.groupby('QUARTER').agg(
        NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'sum')
    ).reset_index()

    for df in [quarterly_pos_summary_df, quarterly_overall_summary_df]:
        df['PERIOD'] = df['QUARTER'].apply(lambda q: f"{q.year}년 {q.quarter}분기")

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    position_filter_list = ['전체', 'Staff', 'Manager', 'Director']

    trace_map = {'전체': quarterly_overall_summary_df}
    for pos_name in position_order:
        trace_map[pos_name] = quarterly_pos_summary_df[quarterly_pos_summary_df['POSITION_NAME'] == pos_name]

    for name in position_filter_list:
        is_visible = (name == '전체')
        df_plot = trace_map.get(name, pd.DataFrame()).tail(12).copy()

        fig.add_trace(go.Bar(x=df_plot['PERIOD'], y=df_plot['NEW_HIRES'], name='입사자', marker_color='blue', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Bar(x=df_plot['PERIOD'], y=df_plot['LEAVERS'], name='퇴사자', marker_color='red', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_plot['PERIOD'], y=df_plot['HEADCOUNT'], name='총원', mode='lines+markers+text', text=df_plot['HEADCOUNT'], textposition='top center', line=dict(color='black'), visible=is_visible), secondary_y=True)

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    num_traces_per_group = 3
    for i, name in enumerate(position_filter_list):
        visibility_mask = [False] * (len(position_filter_list) * num_traces_per_group)
        for j in range(num_traces_per_group):
            visibility_mask[i * num_traces_per_group + j] = True

        df_for_range = trace_map.get(name, pd.DataFrame()).tail(12)
        max_hires_leavers = max(df_for_range['NEW_HIRES'].max(), df_for_range['LEAVERS'].max()) if not df_for_range.empty else 0
        y1_range = [0, max_hires_leavers * 2.2]

        buttons.append(dict(label=name, method='update', args=[
            {'visible': visibility_mask},
            {'yaxis.range': y1_range}
        ]))

    initial_df = trace_map['전체'].tail(12)
    initial_max = max(initial_df['NEW_HIRES'].max(), initial_df['LEAVERS'].max()) if not initial_df.empty else 0
    initial_y1_range = [0, initial_max * 2.2]

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='직위별 분기 인원 변동 현황',
        xaxis_title='분기',
        font_size=14, height=700,
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(text="직위 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )
    fig.update_yaxes(title_text="입사/퇴사자 수", secondary_y=False, range=initial_y1_range)
    fig.update_yaxes(title_text="총원", secondary_y=True, rangemode='tozero')

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




