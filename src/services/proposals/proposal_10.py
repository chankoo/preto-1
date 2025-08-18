#!/usr/bin/env python
# coding: utf-8

# In[11]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.salary_contract_info_table import salary_contract_info_df
from services.tables.HR_Core.school_info_table import school_info_df
from services.tables.HR_Core.school_table import school_df
from services.tables.HR_Core.career_info_table import career_info_df

def create_figure():
    """
    제안 10: 학력/경력과 초봉의 관계 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    initial_contracts = salary_contract_info_df[salary_contract_info_df['PAY_CATEGORY'] == '연봉'].sort_values('SAL_START_DATE').groupby('EMP_ID').first().reset_index()
    initial_contracts = initial_contracts[['EMP_ID', 'SAL_AMOUNT']].rename(columns={'SAL_AMOUNT': 'INITIAL_SALARY'})

    school_history = school_info_df.copy()
    school_history = pd.merge(school_history, school_df, on='SCHOOL_ID', how='left')
    final_education = school_history.sort_values('GRAD_YEAR').groupby('EMP_ID').last().reset_index()
    final_education = final_education[['EMP_ID', 'SCHOOL_LEVEL', 'MAJOR_CATEGORY']]

    prior_career = career_info_df.copy()
    prior_career_summary = prior_career.groupby('EMP_ID')['CAREER_DURATION'].sum().reset_index()
    prior_career_summary['TOTAL_PRIOR_CAREER_YEARS'] = prior_career_summary['CAREER_DURATION'] / 365.25

    analysis_df = pd.merge(initial_contracts, final_education, on='EMP_ID', how='inner')
    analysis_df = pd.merge(analysis_df, prior_career_summary[['EMP_ID', 'TOTAL_PRIOR_CAREER_YEARS']], on='EMP_ID', how='left')
    analysis_df['TOTAL_PRIOR_CAREER_YEARS'] = analysis_df['TOTAL_PRIOR_CAREER_YEARS'].fillna(0)
    analysis_df = analysis_df.dropna(subset=['INITIAL_SALARY', 'SCHOOL_LEVEL', 'MAJOR_CATEGORY'])

    bins = [-1, 3, 7, 100]
    labels = ['신입 (0~3년)', '주니어 (3~7년)', '시니어 (7년+)']
    analysis_df['CAREER_BIN'] = pd.cut(analysis_df['TOTAL_PRIOR_CAREER_YEARS'], bins=bins, labels=labels, right=True)

    # x축 순서 정의
    school_level_order = sorted(pd.to_numeric(analysis_df['SCHOOL_LEVEL'].unique()))
    major_order = [
        "상경계열", "사회과학계열", "인문계열", "어문계열", "STEM계열",
        "기타공학계열", "자연과학계열", "디자인계열", "기타"
    ]
    analysis_df['SCHOOL_LEVEL'] = pd.Categorical(analysis_df['SCHOOL_LEVEL'], categories=school_level_order, ordered=True)
    analysis_df['MAJOR_CATEGORY'] = pd.Categorical(analysis_df['MAJOR_CATEGORY'], categories=major_order, ordered=True)

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    career_bins_sorted = ['신입 (0~3년)', '주니어 (3~7년)', '시니어 (7년+)']

    # '학교 레벨별' 트레이스
    for career_bin in career_bins_sorted:
        df_filtered = analysis_df[analysis_df['CAREER_BIN'] == career_bin]
        fig.add_trace(go.Box(x=df_filtered['SCHOOL_LEVEL'], y=df_filtered['INITIAL_SALARY'], name=career_bin, visible=True))
    # '전공 계열별' 트레이스
    for career_bin in career_bins_sorted:
        df_filtered = analysis_df[analysis_df['CAREER_BIN'] == career_bin]
        fig.add_trace(go.Box(x=df_filtered['MAJOR_CATEGORY'], y=df_filtered['INITIAL_SALARY'], name=career_bin, visible=False))

    # --- 4. 드롭다운 메뉴 생성 및 레이아웃 업데이트 ---
    num_career_bins = len(career_bins_sorted)
    buttons = [
        dict(label='학교 레벨별',
             method='update',
             args=[
                 {'visible': [True]*num_career_bins + [False]*num_career_bins},
                 {'xaxis': {'title': '학교 레벨', 'categoryorder': 'array', 'categoryarray': [str(s) for s in school_level_order]}}
             ]),
        dict(label='전공 계열별',
             method='update',
             args=[
                 {'visible': [False]*num_career_bins + [True]*num_career_bins},
                 {'xaxis': {'title': '전공 계열', 'categoryorder': 'array', 'categoryarray': major_order}}
             ])
    ]

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='학력/경력과 초봉 관계 분석',
        xaxis_title='학교 레벨',
        yaxis_title='초봉 (연봉)',
        font_size=14, height=700,
        boxmode='group',
        legend_title_text='과거 경력',
        yaxis_tickformat=',.0f',
        annotations=[dict(text="비교 기준:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )

    return fig


pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




