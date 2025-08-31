#!/usr/bin/env python
# coding: utf-8

# In[3]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import datetime

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df, position_order

def create_cohort_data(df):
    """
    주어진 데이터프레임에 대한 코호트 데이터를 생성합니다.
    """
    df = df.copy()
    if df.empty:
        return pd.DataFrame()

    today = datetime.datetime.now()
    df['HIRE_YEAR'] = df['IN_DATE'].dt.year
    df['TENURE_YEAR_INDEX'] = np.floor(
        (df['OUT_DATE'].fillna(pd.to_datetime(today)) - df['IN_DATE']).dt.days / 365.25
    ).astype(int)

    cohort_data_list = []
    for _, row in df.iterrows():
        if pd.isna(row['HIRE_YEAR']) or pd.isna(row['TENURE_YEAR_INDEX']): continue
        for i in range(row['TENURE_YEAR_INDEX'] + 1):
            cohort_data_list.append({
                'HIRE_YEAR': int(row['HIRE_YEAR']), 'TENURE_YEAR': i, 'EMP_ID': row['EMP_ID']
            })

    if not cohort_data_list: return pd.DataFrame()

    cohort_df = pd.DataFrame(cohort_data_list)
    cohort_counts = cohort_df.groupby(['HIRE_YEAR', 'TENURE_YEAR'])['EMP_ID'].nunique().unstack()

    if cohort_counts.empty: return pd.DataFrame()

    cohort_sizes = cohort_counts.iloc[:, 0]
    cohort_retention = cohort_counts.divide(cohort_sizes, axis=0) * 100

    current_year = today.year
    for hire_year in cohort_retention.index:
        max_completed_tenure = current_year - hire_year - 1
        cohort_retention.loc[hire_year, cohort_retention.columns > max_completed_tenure] = np.nan

    return cohort_retention

def create_figure():
    """
    제안 6-3: 직위별 입사 연도 잔존율 코호트 분석 그래프를 생성합니다.
    """
    # --- 2. 데이터 준비 및 가공 ---
    first_pos = position_info_df.sort_values('GRADE_START_DATE').groupby('EMP_ID').first().reset_index()
    first_pos = pd.merge(first_pos, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID')

    analysis_df = emp_df[['EMP_ID', 'IN_DATE', 'OUT_DATE']].copy()
    analysis_df = pd.merge(analysis_df, first_pos[['EMP_ID', 'POSITION_NAME']], on='EMP_ID', how='left')
    analysis_df = analysis_df.dropna(subset=['POSITION_NAME'])

    # --- 3. Plotly 인터랙티브 그래프 생성 ---
    fig = go.Figure()
    position_list = ['전체'] + position_order

    cohort_data_map = {}
    for pos_name in position_list:
        df_filtered = analysis_df if pos_name == '전체' else analysis_df[analysis_df['POSITION_NAME'] == pos_name]
        cohort_data_map[pos_name] = create_cohort_data(df_filtered)

    for pos_name in position_list:
        cohort_pivot = cohort_data_map[pos_name]
        if not cohort_pivot.empty:
            text_labels = cohort_pivot.map(lambda x: f'{x:.0f}%' if pd.notna(x) else '')
            fig.add_trace(
                go.Heatmap(
                    z=cohort_pivot.values,
                    x=[f"{int(c)}년차" for c in cohort_pivot.columns],
                    y=cohort_pivot.index,
                    colorscale='Blues',
                    text=text_labels,
                    texttemplate="%{text}",
                    showscale=False,
                    visible=(pos_name == '전체'),
                    connectgaps=False
                )
            )
        else: # 데이터가 없는 경우 빈 히트맵 트레이스 추가
             fig.add_trace(go.Heatmap(visible=(pos_name == '전체')))

    # --- 4. 드롭다운 메뉴 및 레이아웃 업데이트 ---
    buttons = []
    for i, pos_name in enumerate(position_list):
        visibility_mask = [False] * len(position_list)
        visibility_mask[i] = True
        buttons.append(
            dict(label=pos_name, method='update', args=[{'visible': visibility_mask}])
        )

    fig.update_layout(
        updatemenus=[dict(
            active=0, buttons=buttons, direction="down",
            pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text='직위별 입사 연도 잔존율 코호트 분석',
        xaxis_title='근속년수',
        yaxis_title='입사 연도 (코호트)',
        font_size=14, height=700,
        annotations=[dict(text="직위 선택:", showarrow=False, x=0, y=1.08, yref="paper", align="left")]
    )

    return fig

# 이 파일을 직접 실행할 경우 그래프를 생성하여 보여줍니다.
pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




