#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df, position_order, grade_order

def create_figure_and_df():
    """
    제안 4-3: 직위/직급별 경험 자산 현황 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    current_emps_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y'].copy()
    current_emps_df['TENURE_YEARS'] = current_emps_df['DURATION'] / 365.25

    current_positions = position_info_df[position_info_df['GRADE_END_DATE'].isnull()][['EMP_ID', 'POSITION_ID', 'GRADE_ID']]
    analysis_df = pd.merge(current_emps_df, current_positions, on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID', how='left')

    analysis_df = analysis_df.dropna(subset=['POSITION_NAME', 'GRADE_ID', 'TENURE_YEARS'])

    # --- 3. Plotly 인터랙티브 그래프 생성 (그래프용 데이터 준비) ---
    analysis_df['TENURE_BIN'] = pd.cut(analysis_df['TENURE_YEARS'], bins=range(0, int(analysis_df['TENURE_YEARS'].max()) + 2), right=False, labels=range(0, int(analysis_df['TENURE_YEARS'].max()) + 1))
    pos_summary = analysis_df.groupby(['POSITION_NAME', 'TENURE_BIN'], observed=False).size().reset_index(name='COUNT')
    grade_summary = analysis_df.groupby(['POSITION_NAME', 'GRADE_ID', 'TENURE_BIN'], observed=False).size().reset_index(name='COUNT')

    x_max = analysis_df['TENURE_YEARS'].max()
    fixed_x_range = [-0.5, x_max + 1.5]

    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, pos_name in enumerate(position_order):
        df_filtered = pos_summary[pos_summary['POSITION_NAME'] == pos_name]
        fig.add_trace(go.Bar(x=df_filtered['TENURE_BIN'], y=df_filtered['COUNT'], name=pos_name, marker_color=colors[i]))
    grade_traces_map = {}
    trace_idx_counter = len(fig.data)
    for pos_name in position_order:
        grade_pos_df = grade_summary[grade_summary['POSITION_NAME'] == pos_name]
        grades_in_pos = [g for g in grade_order if g in grade_pos_df['GRADE_ID'].unique()]
        grade_traces_map[pos_name] = []
        for j, grade_id in enumerate(grades_in_pos):
            df_filtered = grade_pos_df[grade_pos_df['GRADE_ID'] == grade_id]
            fig.add_trace(go.Bar(x=df_filtered['TENURE_BIN'], y=df_filtered['COUNT'], name=grade_id, visible=False, marker_color=colors[j % len(colors)], showlegend=False))
            grade_traces_map[pos_name].append(trace_idx_counter)
            trace_idx_counter += 1
    buttons = []
    buttons.append(dict(label='전체', method='update', args=[{'visible': [True]*len(position_order) + [False]*(len(fig.data)-len(position_order))}, {'title': '전체 직위별 근속년수 분포', 'barmode': 'stack', 'showlegend': True, 'legend_title_text': '직위'}]))
    for pos_name in position_order:
        visibility_mask = [False] * len(fig.data)
        for trace_idx in grade_traces_map.get(pos_name, []):
            visibility_mask[trace_idx] = True
        buttons.append(dict(label=f'{pos_name}', method='update', args=[{'visible': visibility_mask}, {'title': f'{pos_name} 내 직급별 근속년수 분포', 'barmode': 'stack', 'showlegend': False}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직위/직급별 근속년수 분포 현황', xaxis_title='근속년수 (년)', yaxis_title='직원 수', font_size=14, height=700,
        bargap=0.2, barmode='stack', legend_title_text='직위',
        annotations=[dict(text="직위/직급 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis_range=fixed_x_range
    )
    fig.update_xaxes(dtick=1)

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. 근속년수 구간을 새로 정의
    tenure_bins_agg = [-np.inf, 3, 7, np.inf]
    tenure_labels_agg = ['3년 이하', '3년초과~7년이하', '7년초과']
    analysis_df['TENURE_GROUP'] = pd.cut(analysis_df['TENURE_YEARS'], bins=tenure_bins_agg, labels=tenure_labels_agg, right=False)

    # 2. 피벗 테이블 생성
    aggregate_df = pd.pivot_table(
        analysis_df,
        index='TENURE_GROUP',
        columns='POSITION_NAME',
        values='EMP_ID',
        aggfunc='count',
        margins=True,
        margins_name='합계',
        observed=False
    ).fillna(0).astype(int)

    # 3. '합계' 컬럼을 맨 앞으로 이동하고, 컬럼 순서 지정
    if '합계' in aggregate_df.columns:
        # position_order에 있고, 실제 데이터에도 있는 컬럼만 순서대로 정렬
        ordered_cols = [p for p in position_order if p in aggregate_df.columns]
        final_cols = ['합계'] + ordered_cols
        aggregate_df = aggregate_df[final_cols]
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




