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
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df, position_order, grade_order

def create_figure_and_df():
    """
    제안 13-3: 직위별 워라밸 변화 추이 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    daily_work_df = daily_work_info_df.copy()
    daily_work_df['DATE'] = pd.to_datetime(daily_work_df['DATE'])
    daily_work_df['PAY_PERIOD'] = daily_work_df['DATE'].dt.strftime('%Y-%m')

    pos_info_with_name = pd.merge(position_info_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID')
    pos_info_sorted = pos_info_with_name.sort_values('GRADE_START_DATE')
    analysis_df = daily_work_df.sort_values('DATE')
    analysis_df = pd.merge_asof(
        analysis_df, pos_info_sorted[['EMP_ID', 'GRADE_START_DATE', 'POSITION_NAME', 'GRADE_ID']],
        left_on='DATE', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward'
    )
    analysis_df = analysis_df.dropna(subset=['POSITION_NAME', 'GRADE_ID'])

    pos_monthly_summary = analysis_df.groupby(['POSITION_NAME', 'PAY_PERIOD'], observed=False).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'), HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    pos_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (pos_monthly_summary['TOTAL_OVERTIME_MINUTES'] / pos_monthly_summary['HEADCOUNT']) / 60

    grade_monthly_summary = analysis_df.groupby(['POSITION_NAME', 'GRADE_ID', 'PAY_PERIOD'], observed=False).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'), HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    grade_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (grade_monthly_summary['TOTAL_OVERTIME_MINUTES'] / grade_monthly_summary['HEADCOUNT']) / 60

    all_overtime_values = pd.concat([pos_monthly_summary['AVG_OVERTIME_PER_PERSON'], grade_monthly_summary['AVG_OVERTIME_PER_PERSON']])
    y_min, y_max = (all_overtime_values.min(), all_overtime_values.max()) if not all_overtime_values.empty else (0, 0)
    y_padding = (y_max - y_min) * 0.1 if (y_max - y_min) > 0 else 10
    fixed_y_range = [y_min - y_padding, y_max + y_padding]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    position_filter_list = [p for p in position_order if p != 'C-Level']
    for i, pos_name in enumerate(position_filter_list):
        df_filtered = pos_monthly_summary[pos_monthly_summary['POSITION_NAME'] == pos_name]
        if not df_filtered.empty:
            fig.add_trace(go.Scatter(x=df_filtered['PAY_PERIOD'], y=df_filtered['AVG_OVERTIME_PER_PERSON'], mode='lines+markers', name=pos_name, line=dict(color=colors[i])))
    grade_traces_map = {}
    trace_idx_counter = len(fig.data)
    for pos_name in position_filter_list:
        grade_df = grade_monthly_summary[grade_monthly_summary['POSITION_NAME'] == pos_name]
        grades_in_pos = [g for g in grade_order if g in grade_df['GRADE_ID'].unique()]
        grade_traces_map[pos_name] = []
        for j, grade_id in enumerate(grades_in_pos):
            df_filtered = grade_df[grade_df['GRADE_ID'] == grade_id]
            if not df_filtered.empty:
                fig.add_trace(go.Scatter(x=df_filtered['PAY_PERIOD'], y=df_filtered['AVG_OVERTIME_PER_PERSON'], mode='lines+markers', name=grade_id, visible=False, line=dict(color=colors[j % len(colors)])))
                grade_traces_map[pos_name].append(trace_idx_counter)
                trace_idx_counter += 1
    buttons = []
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*len(position_filter_list) + [False]*(len(fig.data)-len(position_filter_list))}, {'title': '전체 직위별 월 평균 초과근무 시간 추이'}]))
    for pos_name in position_filter_list:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in grade_traces_map.get(pos_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{pos_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{pos_name} 내 직급별 월 평균 초과근무 시간 추이'}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직위/직급별 월 평균 1인당 초과근무 시간 드릴다운 분석',
        xaxis_title='월(YYYY-MM)', yaxis_title='1인당 평균 초과근무 (시간)',
        font_size=14, height=700,
        legend_title_text='직위/직급',
        annotations=[dict(text="직위/직급 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis_range=['2019-12', '2026-01'],
        yaxis_range=fixed_y_range
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. '전체 평균' 계산을 위한 데이터 준비
    overall_monthly_summary = analysis_df.groupby('PAY_PERIOD', observed=False).agg(
        TOTAL_OVERTIME_MINUTES=('OVERTIME_MINUTES', 'sum'), HEADCOUNT=('EMP_ID', 'nunique')
    ).reset_index()
    overall_monthly_summary['AVG_OVERTIME_PER_PERSON'] = (overall_monthly_summary['TOTAL_OVERTIME_MINUTES'] / overall_monthly_summary['HEADCOUNT']) / 60

    # 2. 연도별로 데이터 집계
    pos_monthly_summary['YEAR'] = pd.to_datetime(pos_monthly_summary['PAY_PERIOD']).dt.year
    yearly_summary = pos_monthly_summary.groupby(['YEAR', 'POSITION_NAME'], observed=False)['AVG_OVERTIME_PER_PERSON'].mean().reset_index()

    overall_monthly_summary['YEAR'] = pd.to_datetime(overall_monthly_summary['PAY_PERIOD']).dt.year
    overall_yearly_summary = overall_monthly_summary.groupby('YEAR')['AVG_OVERTIME_PER_PERSON'].mean()

    # 3. 피벗 테이블 생성 및 '전체 평균' 추가
    aggregate_df = yearly_summary.pivot_table(
        index='YEAR',
        columns='POSITION_NAME',
        values='AVG_OVERTIME_PER_PERSON',
        observed=False
    )
    aggregate_df['전체 평균'] = overall_yearly_summary

    # 4. 연도 필터링 및 정렬
    aggregate_df = aggregate_df.reindex(range(2020, 2026)).sort_index()

    # 5. 컬럼 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in position_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols].round(2)
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




