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
from services.tables.HR_Core.career_info_table import career_info_df
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job
from services.tables.HR_Core.department_table import division_order, dept_level_map, parent_map_dept, dept_name_map
from services.helpers.utils import find_division_name_for_dept, get_level1_ancestor

def create_figure():
    """
    제안 7: 경력 유형 및 첫 직무별 재직기간 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    # 2-1. 직원별 경력 유형 및 재직기간
    career_summary = career_info_df.groupby('EMP_ID')['CAREER_REL_YN'].apply(
        lambda x: '관련 경력' if 'Y' in x.values else '비관련 경력'
    ).reset_index().rename(columns={'CAREER_REL_YN': 'CAREER_TYPE'})
    analysis_df = emp_df[['EMP_ID', 'DURATION']].copy()
    analysis_df = pd.merge(analysis_df, career_summary, on='EMP_ID', how='left')
    analysis_df['CAREER_TYPE'] = analysis_df['CAREER_TYPE'].fillna('경력 없음')
    analysis_df['TENURE_YEARS'] = analysis_df['DURATION'] / 365.25

    # 2-2. Division 및 첫 직무 대분류 정보 추가
    first_dept = department_info_df.sort_values('DEP_APP_START_DATE').groupby('EMP_ID').first().reset_index()
    first_job = job_info_df.sort_values('JOB_APP_START_DATE').groupby('EMP_ID').first().reset_index()

    first_dept['DIVISION_NAME'] = first_dept['DEP_ID'].apply(lambda x: find_division_name_for_dept(x, dept_level_map, parent_map_dept, dept_name_map))
    job_l1_map = job_df[job_df['JOB_LEVEL'] == 1].set_index('JOB_ID')['JOB_NAME'].to_dict()
    first_job['JOB_CATEGORY'] = first_job['JOB_ID'].apply(lambda x: job_l1_map.get(get_level1_ancestor(x, job_df_indexed, parent_map_job)))

    analysis_df = pd.merge(analysis_df, first_dept[['EMP_ID', 'DIVISION_NAME']], on='EMP_ID', how='left')
    analysis_df = pd.merge(analysis_df, first_job[['EMP_ID', 'JOB_CATEGORY']], on='EMP_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['DIVISION_NAME', 'JOB_CATEGORY'])

    # x축 순서 지정
    career_type_order = ['관련 경력', '비관련 경력', '경력 없음']
    analysis_df['CAREER_TYPE'] = pd.Categorical(analysis_df['CAREER_TYPE'], categories=career_type_order, ordered=True)
    analysis_df = analysis_df.sort_values('CAREER_TYPE')

    # y축 범위 미리 계산
    y_max = analysis_df['TENURE_YEARS'].max()
    fixed_y_range = [0, y_max * 1.1]

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    division_list = ['전체'] + division_order
    colors = px.colors.qualitative.Plotly

    for div_name in division_list:
        df_filtered_div = analysis_df if div_name == '전체' else analysis_df[analysis_df['DIVISION_NAME'] == div_name]

        for i, career_type in enumerate(career_type_order):
            df_filtered_career = df_filtered_div[df_filtered_div['CAREER_TYPE'] == career_type]
            fig.add_trace(
                go.Box(
                    y=df_filtered_career['TENURE_YEARS'],
                    x=df_filtered_career['JOB_CATEGORY'],
                    name=career_type,
                    marker_color=colors[i],
                    visible=(div_name == '전체')
                )
            )

    # --- 4. 드롭다운 메뉴 생성 및 레이아웃 업데이트 ---
    buttons = []
    for i, div_name in enumerate(division_list):
        visibility_mask = [False] * (len(division_list) * len(career_type_order))
        start_index = i * len(career_type_order)
        for j in range(len(career_type_order)):
            visibility_mask[start_index + j] = True

        buttons.append(
            dict(label=div_name, method='update', args=[{'visible': visibility_mask}])
        )

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='첫 직무 및 경력 유형에 따른 재직기간 분포',
        xaxis_title='첫 직무 대분류',
        yaxis_title='재직 기간 (년)',
        font_size=14, height=700,
        boxmode='group',
        legend_title_text='과거 경력 유형',
        annotations=[dict(text="조직 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")],
        yaxis_range=fixed_y_range
    )

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
if __name__ == '__main__':
    pio.renderers.default = 'vscode'
    fig = create_figure()
    fig.show()


# In[ ]:




