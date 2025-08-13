#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import random

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임 및 헬퍼 데이터/함수를 임포트
from services.tables.Time_Attendance.daily_working_info_table import daily_work_info_df
from services.tables.Time_Attendance.detailed_working_info_table import detailed_work_info_df, burnout_leaver_ids, low_engagement_leaver_ids
from services.tables.Time_Attendance.leave_type_table import leave_type_df
from services.tables.Time_Attendance.working_info_table import work_info_df
from services.tables.Time_Attendance.working_system_table import work_sys_df

random.seed(42)
np.random.seed(42)

# --- 2. 헬퍼 데이터 준비 ---
# 초과근무 데이터 가공
ot_df = daily_work_info_df[['EMP_ID', 'DATE', 'OVERTIME_MINUTES']].copy()
ot_df['DATE'] = pd.to_datetime(ot_df['DATE'])
ot_df['OVERTIME_MINUTES'] = pd.to_numeric(ot_df['OVERTIME_MINUTES'], errors='coerce').fillna(0)
ot_df['YEAR'] = ot_df['DATE'].dt.year
ot_df['HALF'] = (ot_df['DATE'].dt.month - 1) // 6 + 1
avg_overtime_per_half = ot_df.groupby(['EMP_ID', 'YEAR', 'HALF'])['OVERTIME_MINUTES'].mean().to_dict()

# 휴가 대상일 필터링
leave_days_df = detailed_work_info_df[detailed_work_info_df['WORK_ETC'] == '휴가'].copy()
leave_days_df['DATE'] = pd.to_datetime(leave_days_df['DATE'])

# --- 3. 휴가 유형 할당 ---
detailed_leave_records = []
leave_type_id_map = pd.Series(leave_type_df.LEAVE_TYPE_ID.values, index=leave_type_df.LEAVE_TYPE_NAME).to_dict()
lt_annual_id, lt_sick_id = leave_type_id_map.get('연차휴가'), leave_type_id_map.get('병휴가')
other_leave_ids = [v for k, v in leave_type_id_map.items() if k not in ['연차휴가', '병휴가']]

leave_days_df['YEAR'] = leave_days_df['DATE'].dt.year
leave_days_df['HALF'] = (leave_days_df['DATE'].dt.month - 1) // 6 + 1

for name, group in leave_days_df.groupby(['EMP_ID', 'YEAR']):
    emp_id, year = name
    num_leaves = len(group)
    num_annual = min(15, num_leaves)
    num_other = num_leaves - num_annual

    leave_types = [lt_annual_id] * num_annual

    sick_prob = 0
    if emp_id in burnout_leaver_ids:
        sick_prob = random.uniform(0.05, 0.15)
    elif emp_id in low_engagement_leaver_ids:
        sick_prob = random.uniform(0.6, 0.9)
    else:
        prev_half = 2 if group['HALF'].iloc[0] == 1 else 1
        prev_year = year if prev_half == 2 else year - 1
        avg_ot = avg_overtime_per_half.get((emp_id, prev_year, prev_half), 0)
        sick_prob = min(avg_ot / 120, 0.9)

    num_sick = sum(1 for _ in range(num_other) if random.random() < sick_prob)
    leave_types.extend([lt_sick_id] * num_sick)

    num_remaining = num_leaves - len(leave_types)
    if num_remaining > 0 and other_leave_ids:
        leave_types.extend(random.choices(other_leave_ids, k=num_remaining))

    random.shuffle(leave_types)

    group_copy = group.copy()
    group_copy['LEAVE_TYPE_ID'] = leave_types
    detailed_leave_records.append(group_copy)

if detailed_leave_records:
    detailed_leave_info_df = pd.concat(detailed_leave_records, ignore_index=True)
else:
    detailed_leave_info_df = pd.DataFrame()

# --- 4. 휴가 길이(LEAVE_LENGTH) 할당 ---
if not detailed_leave_info_df.empty:
    detailed_leave_info_df = pd.merge_asof(
        detailed_leave_info_df.sort_values('DATE'),
        work_info_df.sort_values('WORK_ASSIGN_START_DATE'),
        left_on='DATE', right_on='WORK_ASSIGN_START_DATE', by='EMP_ID', direction='backward'
    )
    work_sys_name_map = work_sys_df.set_index('WORK_SYS_ID')['WORK_SYS_NAME'].to_dict()
    detailed_leave_info_df['WORK_SYS_NAME'] = detailed_leave_info_df['WORK_SYS_ID'].map(work_sys_name_map)

    detailed_leave_info_df['LEAVE_LENGTH'] = 1.0
    normal_work_mask = detailed_leave_info_df['WORK_SYS_NAME'] == '일반 근무'
    if normal_work_mask.any():
        leave_lengths = np.random.choice([1.0, 0.5], size=normal_work_mask.sum(), p=[0.8, 0.2])
        detailed_leave_info_df.loc[normal_work_mask, 'LEAVE_LENGTH'] = leave_lengths

    final_cols = ['EMP_ID', 'DATE', 'LEAVE_TYPE_ID', 'LEAVE_LENGTH']
    detailed_leave_info_df = detailed_leave_info_df[final_cols].copy()
else:
    final_cols = ['EMP_ID', 'DATE', 'LEAVE_TYPE_ID', 'LEAVE_LENGTH']
    detailed_leave_info_df = pd.DataFrame(columns=final_cols)

# --- 5. 원본/Google Sheets용 DataFrame 분리 ---
detailed_leave_info_df_for_gsheet = detailed_leave_info_df.copy()
if not detailed_leave_info_df_for_gsheet.empty:
    detailed_leave_info_df_for_gsheet['DATE'] = detailed_leave_info_df_for_gsheet['DATE'].dt.strftime('%Y-%m-%d')
    for col in detailed_leave_info_df_for_gsheet.columns:
        detailed_leave_info_df_for_gsheet[col] = detailed_leave_info_df_for_gsheet[col].astype(str)
    detailed_leave_info_df_for_gsheet = detailed_leave_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})

