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
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job, job_l1_order
from services.tables.HR_Core.department_table import division_order, dept_level_map, parent_map_dept, dept_name_map
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df, position_order
from services.helpers.utils import get_level1_ancestor, find_division_name_for_dept

def create_figure_and_df():
    """
    제안 8-3: 직무별 인력 유지 현황 분석 (입사 시점 직위별 필터) 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    emp_base_df = emp_df[['EMP_ID', 'CURRENT_EMP_YN', 'DURATION']].copy()
    emp_base_df['TENURE_YEARS'] = emp_base_df['DURATION'] / 365.25

    last_job = job_info_df.sort_values('JOB_APP_START_DATE').groupby('EMP_ID').last()
    job_l1_map = job_df[job_df['JOB_LEVEL'] == 1].set_index('JOB_ID')['JOB_NAME'].to_dict()
    last_job['JOB_CATEGORY'] = last_job['JOB_ID'].apply(lambda x: job_l1_map.get(get_level1_ancestor(x, job_df_indexed, parent_map_job)))

    first_pos = position_info_df.sort_values('GRADE_START_DATE').groupby('EMP_ID').first().reset_index()
    first_pos = pd.merge(first_pos, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID')

    analysis_df = pd.merge(emp_base_df, last_job[['JOB_CATEGORY']], on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, first_pos[['EMP_ID', 'POSITION_NAME']], on='EMP_ID', how='left')
    analysis_df['STATUS'] = np.where(analysis_df['CURRENT_EMP_YN'] == 'Y', '재직자', '퇴사자')

    overall_analysis_df = analysis_df.dropna(subset=['JOB_CATEGORY'])
    overall_summary = overall_analysis_df.groupby(['JOB_CATEGORY', 'STATUS'], observed=False).agg(
        AVG_TENURE=('TENURE_YEARS', 'mean'), HEADCOUNT=('EMP_ID', 'nunique')
    ).unstack(level='STATUS').fillna(0)
    overall_summary.columns = [f'{val}_{stat}' for val, stat in overall_summary.columns]
    overall_summary = overall_summary.reset_index()

    analysis_df_pos = analysis_df.dropna(subset=['POSITION_NAME'])
    summary_df = analysis_df_pos.groupby(['POSITION_NAME', 'JOB_CATEGORY', 'STATUS'], observed=False).agg(
        AVG_TENURE=('TENURE_YEARS', 'mean'), HEADCOUNT=('EMP_ID', 'nunique')
    ).unstack(level='STATUS').fillna(0)
    summary_df.columns = [f'{val}_{stat}' for val, stat in summary_df.columns]
    summary_df = summary_df.reset_index()

    x_max_values = pd.concat([summary_df['AVG_TENURE_재직자'], summary_df['AVG_TENURE_퇴사자'], overall_summary['AVG_TENURE_재직자'], overall_summary['AVG_TENURE_퇴사자']])
    x_max = x_max_values.max() if not x_max_values.empty else 10
    fixed_x_range = [0, x_max * 1.15]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    position_filter_list = ['전체'] + [p for p in position_order if p != 'C-Level']
    for i, pos_name in enumerate(position_filter_list):
        is_visible = (i == 0)
        if pos_name == '전체':
            df_grouped = overall_summary
        else:
            df_grouped = summary_df[summary_df['POSITION_NAME'] == pos_name]
        fig.add_trace(go.Bar(y=df_grouped['JOB_CATEGORY'], x=df_grouped['AVG_TENURE_재직자'], name='재직자', orientation='h', visible=is_visible, customdata=df_grouped['HEADCOUNT_재직자'], text=df_grouped['AVG_TENURE_재직자'].round(2), textposition='outside', hovertemplate='평균 재직기간: %{x:.2f}년<br>인원: %{customdata}명<extra></extra>'))
        fig.add_trace(go.Bar(y=df_grouped['JOB_CATEGORY'], x=df_grouped['AVG_TENURE_퇴사자'], name='퇴사자', orientation='h', visible=is_visible, customdata=df_grouped['HEADCOUNT_퇴사자'], text=df_grouped['AVG_TENURE_퇴사자'].round(2), textposition='outside', hovertemplate='평균 재직기간: %{x:.2f}년<br>인원: %{customdata}명<extra></extra>'))
    buttons = []
    for i, pos_name in enumerate(position_filter_list):
        visibility_mask = [False] * (len(position_filter_list) * 2)
        visibility_mask[i*2], visibility_mask[i*2 + 1] = True, True
        buttons.append(dict(label=pos_name, method='update', args=[{'visible': visibility_mask}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10}, showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직무별 평균 재직기간 비교 (재직자 vs 퇴사자)', xaxis_title='평균 재직 기간 (년)', font_size=14, height=700,
        barmode='group', legend_title_text='상태',
        annotations=[dict(text="입사 시점 직위 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis_range=fixed_x_range,
        yaxis=dict(title='마지막 직무 대분류', categoryorder='array', categoryarray=job_l1_order[::-1])
    )

    # --- 수정된 부분: aggregate_df 생성 ---
    # 1. 피벗 테이블 생성
    analysis_df['STATUS'] = pd.Categorical(analysis_df['STATUS'], categories=['퇴사자', '재직자'], ordered=True)
    aggregate_df = analysis_df.pivot_table(
        index=['JOB_CATEGORY', 'STATUS'],
        columns='POSITION_NAME',
        values='TENURE_YEARS',
        aggfunc='mean',
        observed=False
    )

    # 2. '전체 평균' 컬럼 추가
    aggregate_df['전체 평균'] = analysis_df.groupby(['JOB_CATEGORY', 'STATUS'], observed=False)['TENURE_YEARS'].mean()

    # 3. 컬럼 순서 재배치 및 포맷팅
    cols = ['전체 평균'] + [col for col in position_order if col in aggregate_df.columns]
    aggregate_df = aggregate_df[cols].round(2).fillna('-')
    # --- 수정 완료 ---

    return fig, aggregate_df

# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




