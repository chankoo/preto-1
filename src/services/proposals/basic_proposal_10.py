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
from services.tables.HR_Core.salary_contract_info_table import salary_contract_info_df

def create_figure():
    """
    제안 0-10: 연봉 구간별 분기 인원 변동 현황 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    salary_info_annual = salary_contract_info_df.copy()
    salary_info_annual['ANNUAL_SALARY'] = salary_info_annual['SAL_AMOUNT']
    salary_info_annual.loc[salary_info_annual['PAY_CATEGORY'] == '월급', 'ANNUAL_SALARY'] *= 12
    salary_info_annual.loc[salary_info_annual['PAY_CATEGORY'] == '주급', 'ANNUAL_SALARY'] *= 52
    salary_info_annual.loc[salary_info_annual['PAY_CATEGORY'] == '일급', 'ANNUAL_SALARY'] *= 250
    salary_info_annual.loc[salary_info_annual['PAY_CATEGORY'] == '시급', 'ANNUAL_SALARY'] *= 2080
    salary_info_sorted = salary_info_annual.sort_values('SAL_START_DATE')

    emp_dates_df = emp_df[['EMP_ID', 'IN_DATE', 'OUT_DATE']].copy()

    salary_bins = [-1, 39999999, 59999999, 79999999, 99999999, float('inf')]
    salary_labels = ['4,000만원 미만', '4,000~5,999만원', '6,000~7,999만원', '8,000~9,999만원', '1억원 이상']

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

        hires_with_sal = pd.merge_asof(hires_df.sort_values('IN_DATE'), salary_info_sorted, left_on='IN_DATE', right_on='SAL_START_DATE', by='EMP_ID', direction='backward')
        leavers_with_sal = pd.merge_asof(leavers_df.sort_values('OUT_DATE'), salary_info_sorted, left_on='OUT_DATE', right_on='SAL_START_DATE', by='EMP_ID', direction='backward')
        active_with_sal = pd.merge_asof(active_df.sort_values('DATE_SNAPSHOT'), salary_info_sorted, left_on='DATE_SNAPSHOT', right_on='SAL_START_DATE', by='EMP_ID', direction='backward')

        for df in [hires_with_sal, leavers_with_sal, active_with_sal]:
            if not df.empty:
                df['SALARY_BIN'] = pd.cut(df['ANNUAL_SALARY'], bins=salary_bins, labels=salary_labels, right=False)

        hires_by_sal = hires_with_sal.groupby('SALARY_BIN', observed=False).size() if not hires_with_sal.empty else pd.Series(dtype=int)
        leavers_by_sal = leavers_with_sal.groupby('SALARY_BIN', observed=False).size() if not leavers_with_sal.empty else pd.Series(dtype=int)
        headcount_by_sal = active_with_sal.groupby('SALARY_BIN', observed=False).size() if not active_with_sal.empty else pd.Series(dtype=int)

        all_bins_in_period = set(hires_by_sal.index) | set(leavers_by_sal.index) | set(headcount_by_sal.index)

        for sal_bin in all_bins_in_period:
            if pd.notna(sal_bin):
                monthly_summary_records.append({
                    'PERIOD_DT': period_start, 'SALARY_BIN': sal_bin,
                    'NEW_HIRES': hires_by_sal.get(sal_bin, 0), 'LEAVERS': leavers_by_sal.get(sal_bin, 0), 'HEADCOUNT': headcount_by_sal.get(sal_bin, 0)
                })

    monthly_sal_summary_df = pd.DataFrame(monthly_summary_records)

    monthly_sal_summary_df['QUARTER'] = monthly_sal_summary_df['PERIOD_DT'].dt.to_period('Q')
    quarterly_sal_summary_df = monthly_sal_summary_df.groupby(['QUARTER', 'SALARY_BIN'], observed=False).agg(
        NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'last')
    ).reset_index()
    quarterly_overall_summary_df = quarterly_sal_summary_df.groupby('QUARTER').agg(
        NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'sum')
    ).reset_index()
    for df in [quarterly_sal_summary_df, quarterly_overall_summary_df]:
        df['PERIOD'] = df['QUARTER'].apply(lambda q: f"{q.year}년 {q.quarter}분기")

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    salary_bin_list = ['전체'] + salary_labels

    trace_map = {'전체': quarterly_overall_summary_df}
    for sal_bin in salary_labels:
        trace_map[sal_bin] = quarterly_sal_summary_df[quarterly_sal_summary_df['SALARY_BIN'] == sal_bin]

    for name, df in trace_map.items():
        is_visible = (name == '전체')
        df_plot = df.tail(12).copy()
        fig.add_trace(go.Bar(x=df_plot['PERIOD'], y=df_plot['NEW_HIRES'], name='입사자', marker_color='blue', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Bar(x=df_plot['PERIOD'], y=df_plot['LEAVERS'], name='퇴사자', marker_color='red', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_plot['PERIOD'], y=df_plot['HEADCOUNT'], name='총원', mode='lines+markers+text', text=df_plot['HEADCOUNT'], textposition='top center', line=dict(color='black'), visible=is_visible), secondary_y=True)

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    num_traces_per_group = 3
    for i, name in enumerate(salary_bin_list):
        visibility_mask = [False] * (len(salary_bin_list) * num_traces_per_group)
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
        title_text='연봉 구간별 분기 인원 변동 현황',
        xaxis_title='분기',
        font_size=14, height=700,
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(text="연봉 구간 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )
    fig.update_yaxes(title_text="입사/퇴사자 수", secondary_y=False, range=initial_y1_range)
    fig.update_yaxes(title_text="총원", secondary_y=True, rangemode='tozero')

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




