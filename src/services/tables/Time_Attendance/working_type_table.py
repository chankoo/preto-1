#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임을 임포트
from services.tables.Time_Attendance.working_system_table import work_sys_df

# ==============================================================================
# --- 2. 근무 유형 관리 (Working Type Table) ---
# ==============================================================================

# --- 1. 기본 데이터 정의 ---
work_type_definitions = {
    '주간': 'WT001', '오후': 'WT002', '야간': 'WT003',
    '비번': 'WT004', '휴무': 'WT005'
}
system_to_types_map = {
    '일반 근무': ['주간'],
    '4조 3교대': ['주간', '오후', '야간', '휴무'],
    '4조 2교대': ['주간', '야간', '비번', '휴무'],
    '3조 2교대': ['주간', '야간', '비번', '휴무'],
    '2조 2교대': ['주간', '야간', '비번', '휴무']
}
recommended_times = {
    ('일반 근무', '주간'): ('09:00', '18:00'),
    ('4조 3교대', '주간'): ('07:00', '15:00'), ('4조 3교대', '오후'): ('15:00', '23:00'), ('4조 3교대', '야간'): ('23:00', '07:00'),
    ('4조 2교대', '주간'): ('07:00', '19:00'), ('4조 2교대', '야간'): ('19:00', '07:00'),
    ('3조 2교대', '주간'): ('08:00', '20:00'), ('3조 2교대', '야간'): ('20:00', '08:00'),
    ('2조 2교대', '주간'): ('09:00', '21:00'), ('2조 2교대', '야간'): ('21:00', '09:00'),
}

# --- 2. 초기 DataFrame 생성 ---
work_type_records = []
if not work_sys_df.empty:
    for _, sys_row in work_sys_df.iterrows():
        work_sys_id = sys_row['WORK_SYS_ID']
        work_sys_name = sys_row['WORK_SYS_NAME']

        required_types = system_to_types_map.get(work_sys_name, [])

        for type_name in required_types:
            work_type_id = work_type_definitions.get(type_name)
            start_time, end_time = recommended_times.get((work_sys_name, type_name), ('-', '-'))

            record = {
                'WORK_TYPE_ID': work_type_id,
                'WORK_SYS_ID': work_sys_id,
                'WORK_TYPE_NAME': type_name,
                'WORK_START_TIME': start_time,
                'WORK_END_TIME': end_time
            }
            work_type_records.append(record)

# --- 3. 원본 DataFrame (분석용) ---
work_type_df = pd.DataFrame(work_type_records)


# --- 4. Google Sheets용 복사본 생성 및 가공 ---
work_type_df_for_gsheet = work_type_df.copy()
for col in work_type_df_for_gsheet.columns:
    work_type_df_for_gsheet[col] = work_type_df_for_gsheet[col].astype(str)
work_type_df_for_gsheet = work_type_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

