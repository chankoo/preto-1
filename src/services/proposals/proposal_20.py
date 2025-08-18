#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import plotly.express as px

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.leave_type_table import leave_type_df
from services.tables.Time_Attendance.detailed_leave_info_table import detailed_leave_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    department_df, dept_level_map, parent_map_dept, dept_name_map,
    division_order
)
from services.helpers.utils import find_parents

def calculate_ratios(df):
    """휴가 패턴 비율을 계산하는 로컬 헬퍼 함수"""
    if df.empty: return pd.Series({'LONG_LEAVE_RATIO': 0, 'BRIDGE_LEAVE_RATIO': 0})
    total_leaves = df['LEAVE_LENGTH'].sum()
    long_leaves = df[df['IS_LONG_LEAVE']]['LEAVE_LENGTH'].sum()
    bridge_leaves = df[df['IS_BRIDGE']]['LEAVE_LENGTH'].sum()
    return pd.Series({
        'LONG_LEAVE_RATIO': (long_leaves / total_leaves) * 100 if total_leaves > 0 else 0,
        'BRIDGE_LEAVE_RATIO': (bridge_leaves / total_leaves) * 100 if total_leaves > 0 else 0
    })

def create_figure():
    """
    제안 20: 조직별 휴가 사용 패턴 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    annual_leave_id = leave_type_df[leave_type_df['LEAVE_TYPE_NAME'] == '연차휴가']['LEAVE_TYPE_ID'].iloc[0]
    analysis_df = detailed_leave_info_df[detailed_leave_info_df['LEAVE_TYPE_ID'] == annual_leave_id].copy()
    analysis_df['DATE'] = pd.to_datetime(analysis_df['DATE'])
    analysis_df['DAY_OF_WEEK'] = analysis_df['DATE'].dt.weekday

    dept_info_sorted = department_info_df.sort_values(['DEP_APP_START_DATE', 'EMP_ID'])
    analysis_df = analysis_df.sort_values(['DATE', 'EMP_ID'])
    analysis_df = pd.merge_asof(
        analysis_df, dept_info_sorted[['EMP_ID', 'DEP_APP_START_DATE', 'DEP_ID']],
        left_on='DATE', right_on='DEP_APP_START_DATE', by='EMP_ID', direction='backward'
    )

    parent_info = analysis_df['DEP_ID'].apply(lambda x: find_parents(x, dept_level_map, parent_map_dept, dept_name_map))
    analysis_df = pd.concat([analysis_df, parent_info], axis=1)
    analysis_df = pd.merge(analysis_df, department_df[['DEP_ID', 'DEP_NAME']], on='DEP_ID')
    analysis_df = analysis_df.rename(columns={'DEP_NAME': 'TEAM_NAME'})
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'OFFICE_NAME', 'TEAM_NAME'])

    analysis_df['IS_BRIDGE'] = analysis_df['DAY_OF_WEEK'].isin([0, 4])
    analysis_df = analysis_df.sort_values(['EMP_ID', 'DATE'])
    analysis_df['DATE_DIFF'] = analysis_df.groupby('EMP_ID')['DATE'].diff().dt.days
    analysis_df['BLOCK_ID'] = (analysis_df['DATE_DIFF'] != 1).cumsum()
    block_lengths = analysis_df.groupby(['EMP_ID', 'BLOCK_ID'])['DATE'].count().rename('BLOCK_LENGTH')
    analysis_df = pd.merge(analysis_df, block_lengths, on=['EMP_ID', 'BLOCK_ID'])
    analysis_df['IS_LONG_LEAVE'] = analysis_df['BLOCK_LENGTH'] >= 3

    team_summary = analysis_df.groupby(['DIVISION_NAME', 'OFFICE_NAME', 'TEAM_NAME'], observed=False).apply(calculate_ratios, include_groups=False).reset_index()

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly

    for i, div_name in enumerate(division_order):
        df_filtered = team_summary[team_summary['DIVISION_NAME'] == div_name]
        fig.add_trace(go.Scatter(
            x=df_filtered['BRIDGE_LEAVE_RATIO'], y=df_filtered['LONG_LEAVE_RATIO'],
            mode='markers', text=df_filtered['TEAM_NAME'],
            marker=dict(size=10, color=colors[i]),
            hovertemplate='%{text}<extra></extra>', name=div_name,
            visible=True
        ))

    for i, div_name in enumerate(division_order):
        df_filtered = team_summary[team_summary['DIVISION_NAME'] == div_name]
        fig.add_trace(go.Scatter(
            x=df_filtered['BRIDGE_LEAVE_RATIO'], y=df_filtered['LONG_LEAVE_RATIO'],
            mode='markers+text', text=df_filtered['TEAM_NAME'],
            textposition='bottom center',
            marker=dict(size=12, color=colors[i]),
            hovertemplate='%{text}<extra></extra>', name=div_name,
            visible=False
        ))

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    buttons.append(dict(label='전체', method='update',
                        args=[{'visible': [True]*len(division_order) + [False]*len(division_order)}]))
    for i, div_name in enumerate(division_order):
        visibility_mask = [False] * (len(division_order) * 2)
        visibility_mask[len(division_order) + i] = True
        buttons.append(dict(label=f'{div_name}', method='update', args=[{'visible': visibility_mask}]))

    x_median = team_summary['BRIDGE_LEAVE_RATIO'].median()
    y_median = team_summary['LONG_LEAVE_RATIO'].median()
    x_max = team_summary['BRIDGE_LEAVE_RATIO'].max()
    y_max = team_summary['LONG_LEAVE_RATIO'].max()

    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='Team별 휴가 사용 패턴 분석',
        xaxis_title='징검다리 휴가 비율 (%)', yaxis_title='장기휴가 비율 (%)',
        font_size=14, height=800,
        legend_title_text='Division',
        xaxis_range=[0, x_max*1.1], yaxis_range=[0, y_max*1.1],
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )
    fig.add_vline(x=x_median, line_width=1, line_dash="dash", line_color="grey")
    fig.add_hline(y=y_median, line_width=1, line_dash="dash", line_color="grey")
    fig.add_annotation(x=0.98, y=0.98, xref="paper", yref="paper", text="스마트 휴식형", showarrow=False, bgcolor="rgba(255, 255, 255, 0.5)")
    fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper", text="집중 휴식형", showarrow=False, bgcolor="rgba(255, 255, 255, 0.5)")
    fig.add_annotation(x=0.02, y=0.02, xref="paper", yref="paper", text="파편적 휴식형", showarrow=False, bgcolor="rgba(255, 255, 255, 0.5)")
    fig.add_annotation(x=0.98, y=0.02, xref="paper", yref="paper", text="짧은 재충전형", showarrow=False, bgcolor="rgba(255, 255, 255, 0.5)")

    return fig


pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




