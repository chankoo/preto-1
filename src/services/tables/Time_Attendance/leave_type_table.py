#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd

# ==============================================================================
# --- 6. 휴가 유형 관리 (Leave Type Table) ---
# ==============================================================================

# --- 1. 기본 데이터 정의 ---
leave_type_names = [
    '연차휴가',
    '병휴가',
    '경조휴가',
    '포상휴가'
]

# --- 2. 초기 DataFrame 생성 ---
leave_type_records = []
for i, name in enumerate(leave_type_names, start=1):
    record = {
        'LEAVE_TYPE_ID': f'LT{i:03d}',
        'LEAVE_TYPE_NAME': name
    }
    leave_type_records.append(record)

# --- 3. 원본 DataFrame (분석용) ---
leave_type_df = pd.DataFrame(leave_type_records)

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
leave_type_df_for_gsheet = leave_type_df.copy()
for col in leave_type_df_for_gsheet.columns:
    leave_type_df_for_gsheet[col] = leave_type_df_for_gsheet[col].astype(str)
leave_type_df_for_gsheet = leave_type_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

