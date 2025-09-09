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

def create_figure():
    """
    제안 0-1: 기간별 인원 변동 현황 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    emp_dates_df = emp_df[['EMP_ID', 'IN_DATE', 'OUT_DATE']].copy()
    emp_dates_df['IN_DATE'] = pd.to_datetime(emp_dates_df['IN_DATE'])
    emp_dates_df['OUT_DATE'] = pd.to_datetime(emp_dates_df['OUT_DATE'])

    start_month = emp_dates_df['IN_DATE'].min().to_period('M').to_timestamp()
    end_month = pd.to_datetime(datetime.datetime.now()).to_period('M').to_timestamp()
    monthly_periods = pd.date_range(start=start_month, end=end_month, freq='MS')

    monthly_summary_records = []
    for period_start in monthly_periods:
        period_end = period_start + pd.offsets.MonthEnd(0)
        hires = emp_dates_df[emp_dates_df['IN_DATE'].between(period_start, period_end)].shape[0]
        leavers = emp_dates_df[emp_dates_df['OUT_DATE'].between(period_start, period_end)].shape[0]
        headcount = emp_dates_df[
            (emp_dates_df['IN_DATE'] <= period_end) & 
            (emp_dates_df['OUT_DATE'].isnull() | (emp_dates_df['OUT_DATE'] > period_end))
        ].shape[0]
        monthly_summary_records.append({
            'PERIOD_DT': period_start,
            'HEADCOUNT': headcount, 'NEW_HIRES': hires, 'LEAVERS': leavers
        })
    monthly_df = pd.DataFrame(monthly_summary_records)

    monthly_df['YEAR'] = monthly_df['PERIOD_DT'].dt.year
    yearly_df = monthly_df.groupby('YEAR').agg(NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'last')).reset_index()
    yearly_df['PERIOD'] = yearly_df['YEAR'].astype(str) + '년'

    monthly_df['HALF'] = monthly_df['PERIOD_DT'].apply(lambda d: f"{d.year}-H{1 if d.month <= 6 else 2}")
    half_yearly_df = monthly_df.groupby('HALF').agg(NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'last')).reset_index()
    half_yearly_df['PERIOD'] = half_yearly_df['HALF'].apply(lambda h: f"{h.split('-')[0]}년 {'상반기' if h.split('-')[1] == 'H1' else '하반기'}")

    monthly_df['QUARTER'] = monthly_df['PERIOD_DT'].dt.to_period('Q')
    quarterly_df = monthly_df.groupby('QUARTER').agg(NEW_HIRES=('NEW_HIRES', 'sum'), LEAVERS=('LEAVERS', 'sum'), HEADCOUNT=('HEADCOUNT', 'last')).reset_index()
    quarterly_df['PERIOD'] = quarterly_df['QUARTER'].apply(lambda q: f"{q.year}년 {q.quarter}분기")

    monthly_df['PERIOD'] = monthly_df['PERIOD_DT'].dt.strftime('%Y년 %m월')

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    data_map = {
        '연간': yearly_df.tail(12),
        '반기간': half_yearly_df.tail(12),
        '분기간': quarterly_df.tail(12),
        '월간': monthly_df.tail(12)
    }

    for period_name, df in data_map.items():
        is_visible = (period_name == '연간')
        fig.add_trace(go.Bar(x=df['PERIOD'], y=df['NEW_HIRES'], name='입사자', marker_color='blue', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Bar(x=df['PERIOD'], y=df['LEAVERS'], name='퇴사자', marker_color='red', visible=is_visible), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=df['PERIOD'], y=df['HEADCOUNT'], name='총원', 
            mode='lines+markers+text', text=df['HEADCOUNT'], textposition='top center',
            line=dict(color='black'), visible=is_visible
        ), secondary_y=True)

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    num_traces_per_period = 3
    for i, (period_name, df) in enumerate(data_map.items()):
        visibility_mask = [False] * (len(data_map) * num_traces_per_period)
        for j in range(num_traces_per_period):
            visibility_mask[i * num_traces_per_period + j] = True

        max_hires_leavers = max(df['NEW_HIRES'].max(), df['LEAVERS'].max()) if not df.empty else 0
        y1_range = [0, max_hires_leavers * 2.2]

        buttons.append(dict(
            label=period_name, 
            method='update', 
            args=[
                {'visible': visibility_mask},
                {'xaxis.title': f'기간 ({period_name})', 'yaxis.range': y1_range}
            ]
        ))

    initial_df = data_map['연간']
    initial_max = max(initial_df['NEW_HIRES'].max(), initial_df['LEAVERS'].max()) if not initial_df.empty else 0
    initial_y1_range = [0, initial_max * 2.2]

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='기간별 인원 변동 현황',
        font_size=14, height=700,
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(text="조회 기간:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )

    fig.update_yaxes(title_text="입사/퇴사자 수", secondary_y=False, range=initial_y1_range)
    fig.update_yaxes(title_text="총원", secondary_y=True, rangemode='tozero')

    return fig

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




