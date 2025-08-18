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
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job
from services.tables.HR_Core.department_table import division_order, dept_level_map, parent_map_dept, dept_name_map
from services.helpers.utils import get_level1_ancestor, find_division_name_for_dept

def create_figure():
    """
    제안 8: 직무별 인력 유지 현황 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    emp_base_df = emp_df[['EMP_ID', 'CURRENT_EMP_YN', 'DURATION']].copy()
    emp_base_df['TENURE_YEARS'] = emp_base_df['DURATION'] / 365.25

    last_job = job_info_df.sort_values('JOB_APP_START_DATE').groupby('EMP_ID').last()
    last_dept = department_info_df.sort_values('DEP_APP_START_DATE').groupby('EMP_ID').last()

    job_l1_map = job_df[job_df['JOB_LEVEL'] == 1].set_index('JOB_ID')['JOB_NAME'].to_dict()
    last_job['JOB_CATEGORY'] = last_job['JOB_ID'].apply(lambda x: job_l1_map.get(get_level1_ancestor(x, job_df_indexed, parent_map_job)))
    last_dept['DIVISION_NAME'] = last_dept['DEP_ID'].apply(lambda x: find_division_name_for_dept(x, dept_level_map, parent_map_dept, dept_name_map))

    analysis_df = pd.merge(emp_base_df, last_job[['JOB_CATEGORY']], on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, last_dept[['DIVISION_NAME']], on='EMP_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['JOB_CATEGORY', 'DIVISION_NAME'])
    analysis_df['STATUS'] = np.where(analysis_df['CURRENT_EMP_YN'] == 'Y', '재직자', '퇴사자')

    summary_df = analysis_df.groupby(['DIVISION_NAME', 'JOB_CATEGORY', 'STATUS'], observed=False).agg(
        AVG_TENURE=('TENURE_YEARS', 'mean'),
        HEADCOUNT=('EMP_ID', 'nunique')
    ).unstack(level='STATUS').fillna(0)

    summary_df.columns = [f'{val}_{stat}' for val, stat in summary_df.columns]
    summary_df = summary_df.reset_index()

    global_job_order = summary_df.groupby('JOB_CATEGORY')['AVG_TENURE_재직자'].mean().sort_values(ascending=True).index.tolist()
    x_max = pd.concat([summary_df['AVG_TENURE_재직자'], summary_df['AVG_TENURE_퇴사자']]).max()
    fixed_x_range = [0, x_max * 1.15]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    division_list = ['전체'] + division_order

    for i, div_name in enumerate(division_list):
        is_visible = (i == 0)
        if div_name == '전체':
            df_grouped = summary_df.groupby('JOB_CATEGORY', observed=False).agg({
                'AVG_TENURE_재직자': 'mean', 'HEADCOUNT_재직자': 'sum',
                'AVG_TENURE_퇴사자': 'mean', 'HEADCOUNT_퇴사자': 'sum'
            }).reset_index()
        else:
            df_grouped = summary_df[summary_df['DIVISION_NAME'] == div_name]

        fig.add_trace(go.Bar(
            y=df_grouped['JOB_CATEGORY'], x=df_grouped['AVG_TENURE_재직자'],
            name='재직자', orientation='h', visible=is_visible,
            customdata=df_grouped['HEADCOUNT_재직자'], text=df_grouped['AVG_TENURE_재직자'].round(2),
            textposition='outside', hovertemplate='평균 재직기간: %{x:.2f}년<br>인원: %{customdata}명<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            y=df_grouped['JOB_CATEGORY'], x=df_grouped['AVG_TENURE_퇴사자'],
            name='퇴사자', orientation='h', visible=is_visible,
            customdata=df_grouped['HEADCOUNT_퇴사자'], text=df_grouped['AVG_TENURE_퇴사자'].round(2),
            textposition='outside', hovertemplate='평균 재직기간: %{x:.2f}년<br>인원: %{customdata}명<extra></extra>'
        ))

    # --- 4. 드롭다운 메뉴 생성 및 레이아웃 업데이트 ---
    buttons = []
    for i, div_name in enumerate(division_list):
        visibility_mask = [False] * (len(division_list) * 2)
        visibility_mask[i*2], visibility_mask[i*2 + 1] = True, True
        buttons.append(
            dict(label=div_name, method='update', args=[{'visible': visibility_mask}])
        )

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='직무별 평균 재직기간 비교 (재직자 vs 퇴사자)',
        xaxis_title='평균 재직 기간 (년)',
        font_size=14, height=700,
        barmode='group',
        legend_title_text='상태',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        xaxis_range=fixed_x_range,
        yaxis=dict(
            title='직무 대분류',
            categoryorder='array',
            categoryarray=global_job_order
        )
    )

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
if __name__ == '__main__':
    pio.renderers.default = 'vscode'
    fig = create_figure()
    fig.show()


# In[ ]:




