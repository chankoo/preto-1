#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import time
import datetime
from pathlib import Path
import os
import io
from datetime import date, timedelta
import time
from faker import Faker
import random
import matplotlib.pyplot as plt

plt.rc("font", family="NanumBarunGothic")
plt.rc("axes", unicode_minus=False)
import seaborn as sns
from itertools import product
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dateutil.relativedelta import relativedelta

from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.department_table import department_df
from services.tables.HR_Core.department_table import division_order

# In[ ]:


# 제안 2 (수정): Division/Office별 성장 속도 비교
# 분석 유형: 현재 기준 분석 (계층별 드릴다운 기능 포함)
# 필요 데이터: HR코어

# --- 1. Plotly 설정 ---
pio.renderers.default = "colab"

# --- 2. 데이터 준비 및 가공 ---
pos_info = position_info_df.copy()
pos_info = pd.merge(
    pos_info,
    position_df[["POSITION_ID", "POSITION_NAME"]].drop_duplicates(),
    on="POSITION_ID",
)
position_start_dates = (
    pos_info.groupby(["EMP_ID", "POSITION_NAME"])["GRADE_START_DATE"].min().unstack()
)
if (
    "Staff" in position_start_dates.columns
    and "Manager" in position_start_dates.columns
):
    position_start_dates["TIME_TO_MANAGER"] = (
        position_start_dates["Manager"] - position_start_dates["Staff"]
    ).dt.days / 365.25
if (
    "Manager" in position_start_dates.columns
    and "Director" in position_start_dates.columns
):
    position_start_dates["TIME_TO_DIRECTOR"] = (
        position_start_dates["Director"] - position_start_dates["Manager"]
    ).dt.days / 365.25
promo_speed_df = position_start_dates.reset_index()

# Division 및 Office 정보 추가
first_dept = (
    department_info_df.sort_values("DEP_APP_START_DATE")
    .groupby("EMP_ID")
    .first()
    .reset_index()
)
parent_map = department_df.set_index("DEP_ID")["UP_DEP_ID"].to_dict()
dept_name_map = department_df.set_index("DEP_ID")["DEP_NAME"].to_dict()
dept_level_map = department_df.set_index("DEP_ID")["DEP_LEVEL"].to_dict()


def find_parents(dep_id):
    path = {"DIVISION_NAME": None, "OFFICE_NAME": None}
    level = dept_level_map.get(dep_id)
    if not level:
        return pd.Series(path)
    current_id = dep_id
    if level == 4:
        office_id = parent_map.get(current_id)
        path["OFFICE_NAME"] = dept_name_map.get(office_id)
        path["DIVISION_NAME"] = dept_name_map.get(parent_map.get(office_id))
    elif level == 3:
        path["OFFICE_NAME"] = dept_name_map.get(current_id)
        path["DIVISION_NAME"] = dept_name_map.get(parent_map.get(current_id))
    elif level == 2:
        path["DIVISION_NAME"] = dept_name_map.get(current_id)
    return pd.Series(path)


parent_info = first_dept["DEP_ID"].apply(find_parents)
first_dept = pd.concat([first_dept, parent_info], axis=1)
first_dept["OFFICE_NAME"].fillna("(Division 직속)", inplace=True)
analysis_df = pd.merge(
    promo_speed_df,
    first_dept[["EMP_ID", "DIVISION_NAME", "OFFICE_NAME"]],
    on="EMP_ID",
    how="left",
)
analysis_df.dropna(subset=["DIVISION_NAME", "OFFICE_NAME"], inplace=True)

# --- 수정된 부분: Office 순서 커스텀 정렬 ---
# 1. Division 순서 지정
division_order = [
    "Planning Division",
    "Sales Division",
    "Development Division",
    "Operating Division",
]
analysis_df["DIVISION_NAME"] = pd.Categorical(
    analysis_df["DIVISION_NAME"], categories=division_order, ordered=True
)
# 2. Office 정렬용 키 컬럼 생성 ('(Division 직속)'을 뒤로 보내기 위함)
analysis_df["OFFICE_SORT_KEY"] = np.where(
    analysis_df["OFFICE_NAME"] == "(Division 직속)", 1, 0
)
# 3. Division > 정렬키 > Office 이름(abc) 순으로 정렬
analysis_df = analysis_df.sort_values(
    ["DIVISION_NAME", "OFFICE_SORT_KEY", "OFFICE_NAME"]
)
# --- 수정 완료 ---


# --- 3. Plotly 인터랙티브 그래프 생성 ---
fig = go.Figure()
division_list = division_order  # 정렬된 순서 사용
promo_stages = ["TIME_TO_MANAGER", "TIME_TO_DIRECTOR"]
stage_names = {
    "TIME_TO_MANAGER": "Staff → Manager",
    "TIME_TO_DIRECTOR": "Manager → Director",
}

# Division 레벨 트레이스
fig.add_trace(
    go.Box(
        y=analysis_df["TIME_TO_MANAGER"],
        x=analysis_df["DIVISION_NAME"],
        name="Staff → Manager",
    )
)
fig.add_trace(
    go.Box(
        y=analysis_df["TIME_TO_DIRECTOR"],
        x=analysis_df["DIVISION_NAME"],
        name="Manager → Director",
    )
)

# Office 레벨 트레이스
for div_name in division_list:
    office_df = analysis_df[analysis_df["DIVISION_NAME"] == div_name]
    fig.add_trace(
        go.Box(
            y=office_df["TIME_TO_MANAGER"],
            x=office_df["OFFICE_NAME"],
            name=f"{div_name} Offices",
            visible=False,
        )
    )
    fig.add_trace(
        go.Box(
            y=office_df["TIME_TO_DIRECTOR"],
            x=office_df["OFFICE_NAME"],
            name=f"{div_name} Offices",
            visible=False,
        )
    )

# --- 4. 드롭다운 메뉴 생성 및 레이아웃 업데이트 ---
buttons = [
    dict(
        label="전체 (Division 보기)",
        method="update",
        args=[
            {"visible": [True, True] + [False] * (len(division_list) * 2)},
            {"title": "전체 Division별 승진 소요 기간 비교"},
        ],
    )
]
trace_counter = 2
for i, div_name in enumerate(division_list):
    visibility_mask = [False] * (2 + len(division_list) * 2)
    start_index = 2 + (i * 2)
    visibility_mask[start_index] = True
    visibility_mask[start_index + 1] = True
    buttons.append(
        dict(
            label=f"{div_name} 상세",
            method="update",
            args=[
                {"visible": visibility_mask},
                {"title": f"{div_name} 내 Office별 승진 소요 기간 비교"},
            ],
        )
    )

fig.update_layout(
    updatemenus=[
        dict(
            active=0,
            buttons=buttons,
            direction="down",
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.01,
            xanchor="left",
            y=1.1,
            yanchor="top",
        )
    ],
    title_text="조직별 승진 소요 기간 드릴다운 분석",
    yaxis_title="승진 소요 기간 (년)",
    font_size=14,
    height=700,
    boxmode="group",
)
fig.show()
