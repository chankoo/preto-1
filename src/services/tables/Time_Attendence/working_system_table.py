#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd

# ==============================================================================
# --- 1. 근무 시스템 관리 (Working System Table) ---
# ==============================================================================

# --- 1. 기본 데이터 정의 ---
working_system_names = [
    '일반 근무',
    '4조 3교대',
    '4조 2교대',
    '3조 2교대',
    '2조 2교대'
]

# --- 2. 초기 DataFrame 생성 ---
work_sys_records = []
for i, name in enumerate(working_system_names, start=1):
    record = {
        'WORK_SYS_ID': f'WS{i:03d}',
        'WORK_SYS_NAME': name
    }
    work_sys_records.append(record)

# --- 3. 원본 DataFrame (분석용) ---
work_sys_df = pd.DataFrame(work_sys_records)

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
work_sys_df_for_gsheet = work_sys_df.copy()
for col in work_sys_df_for_gsheet.columns:
    work_sys_df_for_gsheet[col] = work_sys_df_for_gsheet[col].astype(str)
work_sys_df_for_gsheet = work_sys_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

