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
from services.tables.HR_Core.career_info_table import career_info_df

def create_figure():
    """
    제안 0-5: 총 경력연차별 분기 인원 변동 현황 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    prior_career_years = career_info_df.groupby('EMP_ID')['CAREER_DURATION'].sum() / 365.25
    emp_for_tenure = pd.merge(
        emp_df[['EMP_ID', 'IN_DATE', 'OUT_DATE']],
        prior_career_years.rename('PRIOR_CAREER_YEARS'),
        on='EMP_ID',
        how='left'
    )
    emp_for_tenure['PRIOR_CAREER_YEARS'] = emp_for_tenure['PRIOR_CAREER_YEARS'].fillna(0)

    tenure_bins = [-1, 1, 3, 7, 15, 150]
    tenure_labels = ['1년 미만', '1~3년', '3~7년', '7~15년', '15년 이상']

    start_month = emp_for_tenure['IN_DATE'].min().to_period('M').to_timestamp()
    end_month = pd.to_datetime(datetime.datetime.now()).to_period('M').to_timestamp()
    monthly_periods = pd.date_range(start=start_month, end=end_month, freq='MS')

    monthly_summary_records = []
    for period_start in monthly_periods:
        period_end = period_start + pd.offsets.MonthEnd(0)
        hires_df = emp_for_tenure[emp_for_tenure['IN_DATE'].between(period_start, period_end)].copy()
        leavers_df = emp_for_tenure[emp_for_tenure['OUT_DATE'].between(period_start, period_end)].copy()
        active_df = emp_for_tenure[(emp_for_tenure['IN_DATE'] <= period_end) & ((emp_for_tenure['OUT_DATE'].isnull()) | (emp_for_tenure['OUT_DATE'] > period_end))].copy()

        if not hires_df.empty:
            hires_df['TOTAL_EXP'] = hires_df['PRIOR_CAREER_YEARS']
            hires_df['TENURE_BIN'] = pd.cut(hires_df['TOTAL_EXP'], bins=tenure_bins, labels=tenure_labels, right=False)
            hires_by_tenure = hires_df.groupby('TENURE_BIN', observed=False).size()
        else: hires_by_tenure = pd.Series(dtype=int)

        if not leavers_df.empty:
            leavers_df['TENURE_AT_LEAVE'] = (leavers_df['OUT_DATE'] - leavers_df['IN_DATE']).dt.days / 365.25
            leavers_df['TOTAL_EXP'] = leavers_df['PRIOR_CAREER_YEARS'] + leavers_df['TENURE_AT_LEAVE']
            leavers_df['TENURE_BIN'] = pd.cut(leavers_df['TOTAL_EXP'], bins=tenure_bins, labels=tenure_labels, right=False)
            leavers_by_tenure = leavers_df.groupby('TENURE_BIN', observed=False).size()
        else: leavers_by_tenure = pd.Series(dtype=int)

        if not active_df.empty:
            active_df['CURRENT_TENURE'] = (period_end - active_df['IN_DATE']).dt.days / 365.25
            active_df['TOTAL_EXP'] = active_df['PRIOR_CAREER_YEARS'] + active_df['CURRENT_TENURE']
            active_df['TENURE_BIN'] = pd.cut(active_df['TOTAL_EXP'], bins=tenure_bins, labels=tenure_labels, right=False)
            headcount_by_tenure = active_df.groupby('TENURE_BIN', observed=False).size()
        else: headcount_by_tenure = pd.Series(dtype=int)

        all_bins_in_period = set(hires_by_tenure.index) | set(leavers_by_tenure.index) | set(headcount_by_tenure.index)

        for tenure_bin in all_bins_in_period:
            if pd.notna(tenure_bin):
                monthly_summary_records.append({
                    'PERIOD_DT': period_start, 'TENURE_BIN': tenure_bin,
                    'NEW_HIRES': hires_by_tenure.get(tenure_bin, 0), 'LEAVERS': leavers_by_tenure.get(tenure_bin, 0), 'HEADCOUNT': headcount_by_tenure.get(tenure_bin, 0)
                })

    monthly_tenure_summary_df = pd.DataFrame(monthly_summary_records)

    monthly_tenure_summary_df['QUARTER'] = monthly_tenure_summary_df['PERIOD_DT'].dt.to_period('Q')
    quarterly_tenure_summary_df = monthly_tenure_summary_df.groupby(['QUARTER', 'TENURE_BIN'], observed=False).agg(
        NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'last')
    ).reset_index()
    quarterly_overall_summary_df = quarterly_tenure_summary_df.groupby('QUARTER').agg(
        NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'sum')
    ).reset_index()
    for df in [quarterly_tenure_summary_df, quarterly_overall_summary_df]:
        df['PERIOD'] = df['QUARTER'].apply(lambda q: f"{q.year}년 {q.quarter}분기")

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    tenure_bin_list = ['전체'] + tenure_labels

    trace_map = {'전체': quarterly_overall_summary_df}
    for tenure_bin in tenure_labels:
        trace_map[tenure_bin] = quarterly_tenure_summary_df[quarterly_tenure_summary_df['TENURE_BIN'] == tenure_bin]

    for name, df in trace_map.items():
        is_visible = (name == '전체')
        df_plot = df.tail(12).copy()
        fig.add_trace(go.Bar(x=df_plot['PERIOD'], y=df_plot['NEW_HIRES'], name='입사자', marker_color='blue', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Bar(x=df_plot['PERIOD'], y=df_plot['LEAVERS'], name='퇴사자', marker_color='red', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_plot['PERIOD'], y=df_plot['HEADCOUNT'], name='총원', mode='lines+markers+text', text=df_plot['HEADCOUNT'], textposition='top center', line=dict(color='black'), visible=is_visible), secondary_y=True)

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    num_traces_per_group = 3
    for i, name in enumerate(tenure_bin_list):
        visibility_mask = [False] * (len(tenure_bin_list) * num_traces_per_group)
        for j in range(num_traces_per_group):
            visibility_mask[i * num_traces_per_group + j] = True
        df_for_range = trace_map[name].tail(12)
        max_hires_leavers = max(df_for_range['NEW_HIRES'].max(), df_for_range['LEAVERS'].max()) if not df_for_range.empty else 0
        y1_range = [0, max_hires_leavers * 2.2]
        buttons.append(dict(label=name, method='update', args=[{'visible': visibility_mask}, {'yaxis.range': y1_range}]))

    initial_df = trace_map['전체'].tail(12)
    initial_max = max(initial_df['NEW_HIRES'].max(), initial_df['LEAVERS'].max()) if not initial_df.empty else 0
    initial_y1_range = [0, initial_max * 2.2]

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='총 경력연차별 분기 인원 변동 현황',
        xaxis_title='분기',
        font_size=14, height=700,
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(text="경력연차 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )
    fig.update_yaxes(title_text="입사/퇴사자 수", secondary_y=False, range=initial_y1_range)
    fig.update_yaxes(title_text="총원", secondary_y=True, rangemode='tozero')

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




