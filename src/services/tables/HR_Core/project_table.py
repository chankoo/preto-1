#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
import random

# ==============================================================================
# --- 4. PROJECT TABLE (프로젝트관리) ---
# ==============================================================================

# --- 1. 기본 정보 및 헬퍼 함수 정의 ---
def random_date_for_pjt(start_year=2020, end_year=2024):
    start = datetime.datetime(start_year, 1, 1)
    end = datetime.datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).date()

# 프로젝트 구성
projects = [
    # Major Categories
    {"PJT_ID": "PJT001", "PJT_NAME": "Global Expansion", "PJT_LEVEL": "Major-Category", "UP_PJT_ID": None},
    {"PJT_ID": "PJT002", "PJT_NAME": "Product Development", "PJT_LEVEL": "Major-Category", "UP_PJT_ID": None},
    {"PJT_ID": "PJT003", "PJT_NAME": "Digital Marketing", "PJT_LEVEL": "Major-Category", "UP_PJT_ID": None},
    {"PJT_ID": "PJT004", "PJT_NAME": "Customer Experience", "PJT_LEVEL": "Major-Category", "UP_PJT_ID": None},
    {"PJT_ID": "PJT005", "PJT_NAME": "Sustainability Initiative", "PJT_LEVEL": "Major-Category", "UP_PJT_ID": None},
    # Few Sub-Categories
    {"PJT_ID": "PJT006", "PJT_NAME": "Global Expansion / Korea Entry", "PJT_LEVEL": "Sub-Category", "UP_PJT_ID": "PJT001"},
    {"PJT_ID": "PJT007", "PJT_NAME": "Product Development / Backend Overhaul", "PJT_LEVEL": "Sub-Category", "UP_PJT_ID": "PJT002"},
]

# --- 2. 초기 DataFrame 생성 ---
for pjt in projects:
    pjt["PJT_START_DATE"] = random_date_for_pjt()
    if random.random() < 0.5:
        pjt["PJT_END_DATE"] = pjt["PJT_START_DATE"] + timedelta(days=random.randint(30, 365))
        pjt["PJT_USE_YN"] = "N"
    else:
        pjt["PJT_END_DATE"] = None
        pjt["PJT_USE_YN"] = "Y"

pjt_df = pd.DataFrame(projects)
pjt_df['UP_PJT_ID'] = pjt_df['UP_PJT_ID'].replace({None: np.nan})

# --- 3. 원본 DataFrame (분석용) ---
pjt_df['PJT_START_DATE'] = pd.to_datetime(pjt_df['PJT_START_DATE'])
pjt_df['PJT_END_DATE'] = pd.to_datetime(pjt_df['PJT_END_DATE'], errors='coerce')

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
pjt_df_for_gsheet = pjt_df.copy()
pjt_df_for_gsheet['PJT_START_DATE'] = pjt_df_for_gsheet['PJT_START_DATE'].dt.strftime('%Y-%m-%d')
pjt_df_for_gsheet['PJT_END_DATE'] = pjt_df_for_gsheet['PJT_END_DATE'].dt.strftime('%Y-%m-%d')
for col in pjt_df_for_gsheet.columns:
    pjt_df_for_gsheet[col] = pjt_df_for_gsheet[col].astype(str)
pjt_df_for_gsheet = pjt_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

