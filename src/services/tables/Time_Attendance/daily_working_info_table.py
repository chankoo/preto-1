#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import datetime
import random
from datetime import date, timedelta

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임 및 헬퍼 데이터/함수를 임포트
from services.tables.Time_Attendance.detailed_working_info_table import detailed_work_info_df
from services.tables.Time_Attendance.working_info_table import work_info_df
from services.tables.Time_Attendance.working_type_table import work_type_df
from services.helpers.utils import calculate_night_minutes

random.seed(42)
np.random.seed(42)

# --- 2. 데이터 가공 및 실제 근무시간 계산 ---
daily_work_df = detailed_work_info_df[
    (detailed_work_info_df['DATE_START_TIME'] != '-') & (detailed_work_info_df['DATE_END_TIME'] != '-')
].copy()

daily_work_df['START_DT'] = pd.to_datetime(daily_work_df['DATE'].dt.strftime('%Y-%m-%d') + ' ' + daily_work_df['DATE_START_TIME'], errors='coerce')
daily_work_df['END_DT'] = pd.to_datetime(daily_work_df['DATE'].dt.strftime('%Y-%m-%d') + ' ' + daily_work_df['DATE_END_TIME'], errors='coerce')
daily_work_df = daily_work_df.dropna(subset=['START_DT', 'END_DT']).copy()

night_shift_mask = daily_work_df['END_DT'] < daily_work_df['START_DT']
daily_work_df.loc[night_shift_mask, 'END_DT'] += timedelta(days=1)

daily_work_df['GROSS_DURATION_MINUTES'] = (daily_work_df['END_DT'] - daily_work_df['START_DT']).dt.total_seconds() / 60
break_conditions = [daily_work_df['GROSS_DURATION_MINUTES'] >= 10 * 60, daily_work_df['GROSS_DURATION_MINUTES'] >= 6 * 60]
break_choices = [120, 60]
daily_work_df['BREAK_MINUTES'] = np.select(break_conditions, break_choices, default=0)
daily_work_df['ACTUAL_WORK_MINUTES'] = (daily_work_df['GROSS_DURATION_MINUTES'] - daily_work_df['BREAK_MINUTES']).round()

# --- 3. 예정 근무시간 계산 ---
merged_df = pd.merge_asof(
    daily_work_df.sort_values('DATE'),
    work_info_df.sort_values('WORK_ASSIGN_START_DATE'),
    left_on='DATE', right_on='WORK_ASSIGN_START_DATE', by='EMP_ID', direction='backward'
)
merged_df = merged_df.copy()
merged_df['WORK_TYPE_NAME'] = merged_df['WORK_ETC'].str.extract(r'\((.*?)\)')[0]
merged_df.loc[merged_df['WORK_ETC'] == '일반 근무(평일)', 'WORK_TYPE_NAME'] = '주간'

wt_df_calc = work_type_df.copy()
wt_df_calc = wt_df_calc[wt_df_calc['WORK_START_TIME'] != '-'].copy()
wt_df_calc['SCHEDULED_START'] = pd.to_datetime(wt_df_calc['WORK_START_TIME'], format='%H:%M')
wt_df_calc['SCHEDULED_END'] = pd.to_datetime(wt_df_calc['WORK_END_TIME'], format='%H:%M')
night_mask_wt = wt_df_calc['SCHEDULED_END'] < wt_df_calc['SCHEDULED_START']
wt_df_calc.loc[night_mask_wt, 'SCHEDULED_END'] += timedelta(days=1)
wt_df_calc['SCHEDULED_DURATION'] = (wt_df_calc['SCHEDULED_END'] - wt_df_calc['SCHEDULED_START']).dt.total_seconds() / 60
wt_df_calc['SCHEDULED_WORK_MINUTES'] = np.where(wt_df_calc['SCHEDULED_DURATION'] > 480, wt_df_calc['SCHEDULED_DURATION'] - 60, wt_df_calc['SCHEDULED_DURATION'])

merged_df = pd.merge(
    merged_df,
    wt_df_calc[['WORK_SYS_ID', 'WORK_TYPE_NAME', 'SCHEDULED_WORK_MINUTES']],
    on=['WORK_SYS_ID', 'WORK_TYPE_NAME'], how='left'
)
merged_df['SCHEDULED_WORK_MINUTES'] = merged_df['SCHEDULED_WORK_MINUTES'].fillna(0)

# --- 4. 연장근로 및 야간근로 시간 계산 ---
merged_df['OVERTIME_MINUTES'] = merged_df['ACTUAL_WORK_MINUTES'] - merged_df['SCHEDULED_WORK_MINUTES']
merged_df['NIGHT_WORK_MINUTES'] = merged_df.apply(lambda row: calculate_night_minutes(row['START_DT'], row['END_DT']), axis=1)

# --- 5. 원본/Google Sheets용 DataFrame 분리 ---
final_cols = ['EMP_ID', 'DATE', 'WORK_SYS_ID', 'WORK_TYPE_NAME', 'SCHEDULED_WORK_MINUTES', 'ACTUAL_WORK_MINUTES', 'OVERTIME_MINUTES', 'NIGHT_WORK_MINUTES']
daily_work_info_df = merged_df[final_cols].copy()
numeric_cols = ['SCHEDULED_WORK_MINUTES', 'ACTUAL_WORK_MINUTES', 'OVERTIME_MINUTES', 'NIGHT_WORK_MINUTES']
for col in numeric_cols:
    daily_work_info_df[col] = pd.to_numeric(daily_work_info_df[col], errors='coerce').fillna(0)

daily_work_info_df_for_gsheet = daily_work_info_df.copy()
start_date_for_sheet = pd.to_datetime('2023-01-01')
daily_work_info_df_for_gsheet = daily_work_info_df_for_gsheet[
    daily_work_info_df_for_gsheet['DATE'] >= start_date_for_sheet
].copy()
daily_work_info_df_for_gsheet['DATE'] = daily_work_info_df_for_gsheet['DATE'].dt.strftime('%Y-%m-%d')
for col in daily_work_info_df_for_gsheet.columns:
    daily_work_info_df_for_gsheet[col] = daily_work_info_df_for_gsheet[col].astype(str)
daily_work_info_df_for_gsheet = daily_work_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})


# In[ ]:




