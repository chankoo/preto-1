#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import random

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임을 임포트
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.Time_Attendance.working_system_table import work_sys_df

random.seed(42)
np.random.seed(42)

work_info_records = []
today = datetime.datetime.now().date()
shift_change_date = date(2022, 1, 1)

# --- 2. 헬퍼 데이터 준비 ---
ws_id_map = {}
if not work_sys_df.empty:
    for _, row in work_sys_df.iterrows():
        ws_id_map[row['WORK_SYS_NAME']] = row['WORK_SYS_ID']
ws_normal = ws_id_map.get('일반 근무')
ws_4_2_shift = ws_id_map.get('4조 2교대')
ws_4_3_shift = ws_id_map.get('4조 3교대')

# --- 3. 직원별 근무 시스템 이력 생성 ---
if not all([ws_normal, ws_4_2_shift, ws_4_3_shift]):
    print("경고: 필수 근무 시스템이 work_sys_df에 모두 존재해야 합니다.")
else:
    for emp_id in emp_df['EMP_ID'].unique():
        emp_dept_history = department_info_df[department_info_df['EMP_ID'] == emp_id].sort_values(by='DEP_APP_START_DATE')
        if emp_dept_history.empty:
            continue

        for _, dept_row in emp_dept_history.iterrows():
            dept_type = dept_row['DEPT_TYPE']
            assign_start = dept_row['DEP_APP_START_DATE'].date()
            assign_end = dept_row['DEP_APP_END_DATE'].date() if pd.notna(dept_row['DEP_APP_END_DATE']) else None

            if dept_type == '본사':
                work_info_records.append({
                    "EMP_ID": emp_id, "WORK_SYS_ID": ws_normal,
                    "WORK_ASSIGN_START_DATE": assign_start, "WORK_ASSIGN_END_DATE": assign_end
                })
            elif dept_type == '현장':
                if assign_end and assign_end < shift_change_date:
                    work_info_records.append({
                        "EMP_ID": emp_id, "WORK_SYS_ID": ws_4_2_shift,
                        "WORK_ASSIGN_START_DATE": assign_start, "WORK_ASSIGN_END_DATE": assign_end
                    })
                elif assign_start >= shift_change_date:
                    work_info_records.append({
                        "EMP_ID": emp_id, "WORK_SYS_ID": ws_4_3_shift,
                        "WORK_ASSIGN_START_DATE": assign_start, "WORK_ASSIGN_END_DATE": assign_end
                    })
                else: # 기간이 변경일을 포함하는 경우
                    work_info_records.append({
                        "EMP_ID": emp_id, "WORK_SYS_ID": ws_4_2_shift,
                        "WORK_ASSIGN_START_DATE": assign_start,
                        "WORK_ASSIGN_END_DATE": shift_change_date - timedelta(days=1)
                    })
                    work_info_records.append({
                        "EMP_ID": emp_id, "WORK_SYS_ID": ws_4_3_shift,
                        "WORK_ASSIGN_START_DATE": shift_change_date,
                        "WORK_ASSIGN_END_DATE": assign_end
                    })

# --- 4. 원본/Google Sheets용 DataFrame 분리 ---
work_info_df = pd.DataFrame(work_info_records)
date_cols = ['WORK_ASSIGN_START_DATE', 'WORK_ASSIGN_END_DATE']
if not work_info_df.empty:
    for col in date_cols:
        work_info_df[col] = pd.to_datetime(work_info_df[col], errors='coerce')

work_info_df_for_gsheet = work_info_df.copy()
if not work_info_df_for_gsheet.empty:
    for col in date_cols:
        work_info_df_for_gsheet[col] = work_info_df_for_gsheet[col].dt.strftime('%Y-%m-%d')
    for col in work_info_df_for_gsheet.columns:
        work_info_df_for_gsheet[col] = work_info_df_for_gsheet[col].astype(str)
    work_info_df_for_gsheet = work_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})

