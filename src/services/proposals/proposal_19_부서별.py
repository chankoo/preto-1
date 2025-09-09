#!/usr/bin/env python
# coding: utf-8

# In[2]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.Time_Attendance.detailed_leave_info_table import detailed_leave_info_df
from services.tables.Time_Attendance.leave_type_table import leave_type_df
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import (
    dept_level_map, parent_map_dept, dept_name_map,
    division_order
)
from services.helpers.utils import find_division_name_for_dept

def create_figure_and_df():
    """
    제안 19: 퇴사 예측 선행 지표 분석 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    leave_df = detailed_leave_info_df.copy()
    leave_df = pd.merge(leave_df, leave_type_df, on='LEAVE_TYPE_ID')
    leave_df['DATE'] = pd.to_datetime(leave_df['DATE'])
    leave_df['LEAVE_LENGTH'] = pd.to_numeric(leave_df['LEAVE_LENGTH'])

    leavers = emp_df[emp_df['CURRENT_EMP_YN'] == 'N'][['EMP_ID', 'OUT_DATE']].copy()
    leaver_leave_data = pd.merge(leavers, leave_df, on='EMP_ID', how='left')
    leaver_leave_data = leaver_leave_data[
        (leaver_leave_data['DATE'] < leaver_leave_data['OUT_DATE']) &
        (leaver_leave_data['DATE'] >= (leaver_leave_data['OUT_DATE'] - pd.DateOffset(months=12)))
    ].copy()

    if not leaver_leave_data.empty:
        leaver_leave_data['MONTHS_BEFORE_LEAVING'] = (leaver_leave_data['OUT_DATE'].dt.year - leaver_leave_data['DATE'].dt.year) * 12 + (leaver_leave_data['OUT_DATE'].dt.month - leaver_leave_data['DATE'].dt.month)
        leaver_pattern_df = leaver_leave_data.groupby(['EMP_ID', 'MONTHS_BEFORE_LEAVING'])['LEAVE_LENGTH'].sum().reset_index()
    else:
        leaver_pattern_df = pd.DataFrame(columns=['EMP_ID', 'MONTHS_BEFORE_LEAVING', 'LEAVE_LENGTH'])

    stayers = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y'].copy()
    stayer_leaves = leave_df[(leave_df['EMP_ID'].isin(stayers['EMP_ID'])) & (leave_df['DATE'].dt.year == 2024)]
    stayer_monthly_avg = (stayer_leaves['LEAVE_LENGTH'].sum() / stayers['EMP_ID'].nunique()) / 12 if not stayers.empty and stayers['EMP_ID'].nunique() > 0 else 0

    first_dept = department_info_df.sort_values('DEP_APP_START_DATE').groupby('EMP_ID').first().reset_index()
    first_dept['DIVISION_NAME'] = first_dept['DEP_ID'].apply(lambda x: find_division_name_for_dept(x, dept_level_map, parent_map_dept, dept_name_map))

    leaver_pattern_df = pd.merge(leaver_pattern_df, first_dept[['EMP_ID', 'DIVISION_NAME']], on='EMP_ID', how='left')
    leaver_pattern_df = leaver_pattern_df.dropna(subset=['DIVISION_NAME'])

    stayers_with_div = pd.merge(stayers, first_dept[['EMP_ID', 'DIVISION_NAME']], on='EMP_ID', how='left')
    stayers_with_div = stayers_with_div.dropna(subset=['DIVISION_NAME'])

    leaver_avg_by_month = leaver_pattern_df.groupby('MONTHS_BEFORE_LEAVING')['LEAVE_LENGTH'].mean().reset_index()
    leaver_avg_by_month_div = leaver_pattern_df.groupby(['DIVISION_NAME', 'MONTHS_BEFORE_LEAVING'], observed=False)['LEAVE_LENGTH'].mean().reset_index()

    stayer_avg_by_div = stayer_leaves.groupby('EMP_ID')['LEAVE_LENGTH'].sum().reset_index()
    stayer_avg_by_div = pd.merge(stayer_avg_by_div, stayers_with_div[['EMP_ID', 'DIVISION_NAME']], on='EMP_ID').groupby('DIVISION_NAME', observed=False)['LEAVE_LENGTH'].mean().reset_index()

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    if not leaver_pattern_df.empty:
        y_max = pd.concat([leaver_avg_by_month['LEAVE_LENGTH'], leaver_avg_by_month_div['LEAVE_LENGTH']]).max()
        fixed_y_range = [0, y_max * 1.2]
        division_list = ['전체'] + division_order
        for i, div_name in enumerate(division_list):
            is_visible = (i == 0)
            if div_name == '전체':
                leaver_data, stayer_data_y = leaver_avg_by_month, [stayer_monthly_avg] * 12
            else:
                leaver_data = leaver_avg_by_month_div[leaver_avg_by_month_div['DIVISION_NAME'] == div_name]
                stayer_div_avg = stayer_avg_by_div[stayer_avg_by_div['DIVISION_NAME'] == div_name]['LEAVE_LENGTH'].iloc[0] if not stayer_avg_by_div[stayer_avg_by_div['DIVISION_NAME'] == div_name].empty else 0
                stayer_data_y = [stayer_div_avg / 12] * 12
            x_axis_months = -np.arange(12, 0, -1)
            leaver_data_aligned = pd.DataFrame({'MONTHS_BEFORE_LEAVING': np.arange(1, 13)})
            leaver_data_aligned = pd.merge(leaver_data_aligned, leaver_data, on='MONTHS_BEFORE_LEAVING', how='left').fillna(0)
            fig.add_trace(go.Scatter(x=x_axis_months, y=leaver_data_aligned['LEAVE_LENGTH'], mode='lines+markers+text', name='퇴사자', line=dict(color='red'), visible=is_visible, text=leaver_data_aligned['LEAVE_LENGTH'].round(2).astype(str), textposition='top center'))
            fig.add_trace(go.Scatter(x=x_axis_months, y=stayer_data_y, mode='lines', name='재직자(기준선)', line=dict(color='grey', dash='dash'), visible=is_visible))
        buttons = []
        for i, div_name in enumerate(division_list):
            visibility_mask = [False] * (len(division_list) * 2)
            visibility_mask[i*2], visibility_mask[i*2 + 1] = True, True
            buttons.append(dict(label=div_name, method='update', args=[{'visible': visibility_mask}]))
        fig.update_layout(
            updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
            title_text='퇴사 직전 12개월간 월 평균 총 휴가 사용일수 비교',
            xaxis_title='퇴사 N개월 전', yaxis_title='월 평균 총 휴가 사용일수',
            font_size=14, height=700,
            annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
            yaxis_range=fixed_y_range
        )
    else:
        fig.update_layout(title_text="분석할 퇴사자 휴가 데이터가 없습니다.")

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. Division별 데이터 피벗
    aggregate_df = leaver_avg_by_month_div.pivot_table(
        index='MONTHS_BEFORE_LEAVING',
        columns='DIVISION_NAME',
        values='LEAVE_LENGTH',
        observed=False
    )

    # 2. '전체 평균' 데이터 추가
    overall_pivot_df = leaver_avg_by_month.set_index('MONTHS_BEFORE_LEAVING')
    aggregate_df['전체 평균'] = overall_pivot_df['LEAVE_LENGTH']

    # 3. 행 순서 및 인덱스 이름 변경
    aggregate_df = aggregate_df.reindex(range(12, 0, -1)) # 12개월 전 ~ 1개월 전
    aggregate_df.index = [f'{13-i}개월 전' for i in aggregate_df.index]

    # 4. 컬럼 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in division_order if col in aggregate_df.columns]
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




