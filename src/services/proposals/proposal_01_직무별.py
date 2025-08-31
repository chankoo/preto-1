#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job, job_l1_order, job_l2_order
from services.helpers.utils import get_level1_ancestor, get_level2_ancestor

def create_figure_and_df():
    """
    제안 1-2: 직무별 성장 속도 비교 그래프 및 피벗 테이블을 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    pos_info = position_info_df.copy()
    pos_info = pd.merge(pos_info, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID')
    position_start_dates = pos_info.groupby(['EMP_ID', 'POSITION_NAME'])['GRADE_START_DATE'].min().unstack()
    if 'Staff' in position_start_dates.columns and 'Manager' in position_start_dates.columns:
        position_start_dates['TIME_TO_MANAGER'] = (position_start_dates['Manager'] - position_start_dates['Staff']).dt.days / 365.25
    if 'Manager' in position_start_dates.columns and 'Director' in position_start_dates.columns:
        position_start_dates['TIME_TO_DIRECTOR'] = (position_start_dates['Director'] - position_start_dates['Manager']).dt.days / 365.25
    promo_speed_df = position_start_dates.reset_index()

    first_job = job_info_df.sort_values('JOB_APP_START_DATE').groupby('EMP_ID').first().reset_index()
    job_name_map = job_df.set_index('JOB_ID')['JOB_NAME'].to_dict()
    first_job['JOB_L1_NAME'] = first_job['JOB_ID'].apply(lambda x: job_name_map.get(get_level1_ancestor(x, job_df_indexed, parent_map_job)))
    first_job['JOB_L2_NAME'] = first_job['JOB_ID'].apply(lambda x: job_name_map.get(get_level2_ancestor(x, job_df_indexed, parent_map_job)))

    analysis_df = pd.merge(promo_speed_df, first_job[['EMP_ID', 'JOB_L1_NAME', 'JOB_L2_NAME']], on='EMP_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['JOB_L1_NAME', 'JOB_L2_NAME'])

    analysis_df['JOB_L1_NAME'] = pd.Categorical(analysis_df['JOB_L1_NAME'], categories=job_l1_order, ordered=True)
    analysis_df['JOB_L2_NAME'] = pd.Categorical(analysis_df['JOB_L2_NAME'], categories=job_l2_order, ordered=True)
    analysis_df = analysis_df.sort_values(['JOB_L1_NAME', 'JOB_L2_NAME'])

    y_max_series = pd.concat([analysis_df['TIME_TO_MANAGER'], analysis_df['TIME_TO_DIRECTOR']])
    y_max = y_max_series.max() if not y_max_series.empty else 10
    fixed_y_range = [0, y_max * 1.1]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    # (그래프 생성 코드는 이전과 동일)
    fig = go.Figure()
    fig.add_trace(go.Box(y=analysis_df['TIME_TO_MANAGER'], x=analysis_df['JOB_L1_NAME'], name='Staff → Manager'))
    fig.add_trace(go.Box(y=analysis_df['TIME_TO_DIRECTOR'], x=analysis_df['JOB_L1_NAME'], name='Manager → Director'))
    for job_l1_name in job_l1_order:
        job_df_filtered = analysis_df[analysis_df['JOB_L1_NAME'] == job_l1_name]
        fig.add_trace(go.Box(y=job_df_filtered['TIME_TO_MANAGER'], x=job_df_filtered['JOB_L2_NAME'], name='Staff → Manager', visible=False))
        fig.add_trace(go.Box(y=job_df_filtered['TIME_TO_DIRECTOR'], x=job_df_filtered['JOB_L2_NAME'], name='Manager → Director', visible=False))
    buttons = []
    buttons.append(dict(label='전체', method='update',
                        args=[{'visible': [True, True] + [False] * (len(job_l1_order) * 2)},
                              {'title': '전체 직무별 승진 소요 기간 비교',
                               'xaxis': {'title': 'Job Level 1', 'categoryorder': 'array', 'categoryarray': job_l1_order}}]))
    for i, job_l1_name in enumerate(job_l1_order):
        visibility_mask = [False] * (2 + len(job_l1_order) * 2)
        start_index = 2 + (i * 2)
        visibility_mask[start_index] = True; visibility_mask[start_index + 1] = True
        jobs_in_l1 = [j for j in job_l2_order if j in analysis_df[analysis_df['JOB_L1_NAME'] == job_l1_name]['JOB_L2_NAME'].unique()]
        buttons.append(dict(label=f'{job_l1_name}', method='update',
                            args=[{'visible': visibility_mask},
                                  {'title': f'{job_l1_name} 내 직무별 승진 소요 기간 비교',
                                   'xaxis': {'title': 'Job Level 2', 'categoryorder': 'array', 'categoryarray': jobs_in_l1}}]))
    fig.update_layout(
        updatemenus=[dict(active=0, buttons=buttons, direction="down", pad={"r": 10, "t": 10},
                          showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top")],
        title_text='직무별 승진 소요 기간 드릴다운 분석',
        yaxis_title='승진 소요 기간 (년)',
        font_size=14, height=700,
        boxmode='group',
        legend_title_text='승진 단계',
        yaxis_range=fixed_y_range
    )

    # --- aggregate_df 생성 ---
    df_melted = analysis_df.melt(
        id_vars=['JOB_L1_NAME'],
        value_vars=['TIME_TO_MANAGER', 'TIME_TO_DIRECTOR'],
        var_name='PROMOTION_STEP',
        value_name='YEARS'
    )
    df_melted['PROMOTION_STEP'] = df_melted['PROMOTION_STEP'].map({
        'TIME_TO_MANAGER': 'Staff → Manager',
        'TIME_TO_DIRECTOR': 'Manager → Director'
    })

    aggregate_df = df_melted.pivot_table(
        index='PROMOTION_STEP',
        columns='JOB_L1_NAME',
        values='YEARS',
        aggfunc='mean'
    ).round(2)

    promotion_step_order = ['Staff → Manager', 'Manager → Director']
    aggregate_df = aggregate_df.reindex(promotion_step_order)

    return fig, aggregate_df


# --- 실행 코드 ---
pio.renderers.default = 'vscode'
fig, aggregate_df = create_figure_and_df()
fig.show()

print("\n--- Aggregate DataFrame ---")
aggregate_df


# In[ ]:




