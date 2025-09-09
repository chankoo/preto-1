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
from services.tables.HR_Core.contract_info_table import contract_info_df

def create_figure():
    """
    제안 0-8: 계약 유형별 분기 인원 변동 현황 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    emp_dates_df = emp_df[['EMP_ID', 'IN_DATE', 'OUT_DATE']].copy()
    emp_dates_df['IN_DATE'] = pd.to_datetime(emp_dates_df['IN_DATE'])
    emp_dates_df['OUT_DATE'] = pd.to_datetime(emp_dates_df['OUT_DATE'])

    contract_info_sorted = contract_info_df.sort_values('CONT_START_DATE')

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

        hires_with_cont = pd.merge_asof(hires_df.sort_values('IN_DATE'), contract_info_sorted, left_on='IN_DATE', right_on='CONT_START_DATE', by='EMP_ID', direction='backward')
        leavers_with_cont = pd.merge_asof(leavers_df.sort_values('OUT_DATE'), contract_info_sorted, left_on='OUT_DATE', right_on='CONT_START_DATE', by='EMP_ID', direction='backward')
        active_with_cont = pd.merge_asof(active_df.sort_values('DATE_SNAPSHOT'), contract_info_sorted, left_on='DATE_SNAPSHOT', right_on='CONT_START_DATE', by='EMP_ID', direction='backward')

        hires_by_cont = hires_with_cont.groupby('CONT_CATEGORY').size() if not hires_with_cont.empty else pd.Series(dtype=int)
        leavers_by_cont = leavers_with_cont.groupby('CONT_CATEGORY').size() if not leavers_with_cont.empty else pd.Series(dtype=int)
        headcount_by_cont = active_with_cont.groupby('CONT_CATEGORY').size() if not active_with_cont.empty else pd.Series(dtype=int)

        all_cont_in_period = set(hires_by_cont.index) | set(leavers_by_cont.index) | set(headcount_by_cont.index)

        for cont_type in all_cont_in_period:
            if pd.notna(cont_type):
                monthly_summary_records.append({
                    'PERIOD_DT': period_start, 'CONT_CATEGORY': cont_type,
                    'NEW_HIRES': hires_by_cont.get(cont_type, 0), 'LEAVERS': leavers_by_cont.get(cont_type, 0), 'HEADCOUNT': headcount_by_cont.get(cont_type, 0)
                })

    monthly_cont_summary_df = pd.DataFrame(monthly_summary_records)

    monthly_cont_summary_df['QUARTER'] = monthly_cont_summary_df['PERIOD_DT'].dt.to_period('Q')
    quarterly_cont_summary_df = monthly_cont_summary_df.groupby(['QUARTER', 'CONT_CATEGORY']).agg(
        NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'last')
    ).reset_index()

    quarterly_overall_summary_df = quarterly_cont_summary_df.groupby('QUARTER').agg(
        NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'sum')
    ).reset_index()

    for df in [quarterly_cont_summary_df, quarterly_overall_summary_df]:
        df['PERIOD'] = df['QUARTER'].apply(lambda q: f"{q.year}년 {q.quarter}분기")

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    contract_type_list = ['전체', '정규직', '계약직']

    trace_map = {'전체': quarterly_overall_summary_df}
    for cont_type in ['정규직', '계약직']:
        trace_map[cont_type] = quarterly_cont_summary_df[quarterly_cont_summary_df['CONT_CATEGORY'] == cont_type]

    for name, df in trace_map.items():
        is_visible = (name == '전체')
        df_plot = df.tail(12).copy()
        fig.add_trace(go.Bar(x=df_plot['PERIOD'], y=df_plot['NEW_HIRES'], name='입사자', marker_color='blue', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Bar(x=df_plot['PERIOD'], y=df_plot['LEAVERS'], name='퇴사자', marker_color='red', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_plot['PERIOD'], y=df_plot['HEADCOUNT'], name='총원', mode='lines+markers+text', text=df_plot['HEADCOUNT'], textposition='top center', line=dict(color='black'), visible=is_visible), secondary_y=True)

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    num_traces_per_group = 3
    for i, name in enumerate(contract_type_list):
        visibility_mask = [False] * (len(contract_type_list) * num_traces_per_group)
        for j in range(num_traces_per_group):
            visibility_mask[i * num_traces_per_group + j] = True
        df_for_range = trace_map[name].tail(12)
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
        title_text='계약 유형별 분기 인원 변동 현황',
        xaxis_title='분기',
        font_size=14, height=700,
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(text="계약 유형 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )
    fig.update_yaxes(title_text="입사/퇴사자 수", secondary_y=False, range=initial_y1_range)
    fig.update_yaxes(title_text="총원", secondary_y=True, rangemode='tozero')

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




