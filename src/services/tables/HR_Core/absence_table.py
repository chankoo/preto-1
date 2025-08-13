#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd

# ==============================================================================
# --- 5. ABSENCE TABLE (휴직관리) ---
# ==============================================================================

# --- 1. 기본 데이터 정의 ---
absence_data = [
    {"ABSENCE_ID": "ABS001", "ABSENCE_NAME": "Parental Leave", "ABSENCE_PAY_MIN": 0.0},
    {"ABSENCE_ID": "ABS002", "ABSENCE_NAME": "Hospital Leave", "ABSENCE_PAY_MIN": 0.0},
    {"ABSENCE_ID": "ABS003", "ABSENCE_NAME": "Educational Leave", "ABSENCE_PAY_MIN": 0.3},
    {"ABSENCE_ID": "ABS004", "ABSENCE_NAME": "General Leave", "ABSENCE_PAY_MIN": 0.0},
]

# --- 2. 원본 DataFrame (분석용) ---
absence_df = pd.DataFrame(absence_data)

# --- 3. Google Sheets용 복사본 생성 및 가공 ---
absence_df_for_gsheet = absence_df.copy()
for col in absence_df_for_gsheet.columns:
    absence_df_for_gsheet[col] = absence_df_for_gsheet[col].astype(str)
absence_df_for_gsheet = absence_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

