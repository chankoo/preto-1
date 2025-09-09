#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import random

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임을 임포트
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.absence_table import absence_df

random.seed(42)
np.random.seed(42)

absence_info_records = []
today = datetime.datetime.now().date()
today_ts = pd.to_datetime(today)

# --- 2. 데이터 생성 ---
if absence_df.empty or not {'ABSENCE_ID', 'ABSENCE_PAY_MIN'}.issubset(absence_df.columns):
    available_absences_df = pd.DataFrame()
else:
    available_absences_df = absence_df.copy()
    available_absences_df['ABSENCE_PAY_MIN_FLOAT'] = pd.to_numeric(available_absences_df['ABSENCE_PAY_MIN'], errors='coerce').fillna(0.0)

num_total_employees = len(emp_df)
num_employees_with_absence_target = int(num_total_employees * 0.20)
absence_eligible_emp_df = pd.DataFrame()

if num_employees_with_absence_target > 0 and num_total_employees > 0 :
    emp_ids_with_absence = emp_df['EMP_ID'].sample(n=min(num_employees_with_absence_target, num_total_employees), random_state=42).tolist()
    absence_eligible_emp_df = emp_df[emp_df['EMP_ID'].isin(emp_ids_with_absence)]

if not absence_eligible_emp_df.empty and not available_absences_df.empty:
    for _, emp_row in absence_eligible_emp_df.iterrows():
        emp_id = emp_row['EMP_ID']
        emp_in_date = emp_row['IN_DATE'].date()
        emp_out_date = emp_row['OUT_DATE'].date() if pd.notna(emp_row['OUT_DATE']) else None
        emp_is_current_overall = emp_row['CURRENT_EMP_YN'] == 'Y'

        num_absence_periods = random.randint(1, 2)
        min_next_absence_start_date = emp_in_date + timedelta(days=random.randint(6 * 30, 3 * 365))

        for _ in range(num_absence_periods):
            if min_next_absence_start_date is None or (emp_out_date and min_next_absence_start_date > emp_out_date) or (min_next_absence_start_date > today):
                break

            absence_start_date = min_next_absence_start_date
            selected_absence = available_absences_df.sample(n=1).iloc[0]
            absence_id = selected_absence['ABSENCE_ID']
            pay_ratio = selected_absence.get('ABSENCE_PAY_MIN_FLOAT', 0.0)
            pay_yn = 'Y' if pay_ratio > 0.0 else 'N'

            duration_days = random.randint(30, 365)
            potential_end_date = absence_start_date + timedelta(days=duration_days - 1)

            upper_bound_date = min(d for d in [emp_out_date, today] if d is not None)

            absence_end_date = None
            if potential_end_date > today:
                if emp_is_current_overall and (emp_out_date is None or emp_out_date > today):
                    absence_end_date = None
                else:
                    absence_end_date = upper_bound_date
            else:
                absence_end_date = min(potential_end_date, upper_bound_date)

            if absence_end_date is not None and absence_start_date > absence_end_date:
                min_next_absence_start_date = None
                continue

            duration = None
            start_ts = pd.to_datetime(absence_start_date)
            end_ts = pd.to_datetime(absence_end_date or today_ts)
            duration = (end_ts - start_ts).days

            absence_info_records.append({
                "EMP_ID": emp_id, "ABSENCE_ID": absence_id,
                "ABSENCE_START_DATE": absence_start_date,
                "ABSENCE_END_DATE": absence_end_date,
                "ABSENCE_PAY_YN": pay_yn,
                "ABSENCE_PAY_RATIO": pay_ratio,
                "ABSENCE_DURATION": duration
            })

            if absence_end_date is not None:
                min_next_absence_start_date = absence_end_date + timedelta(days=random.randint(6 * 30, 5 * 365))
            else:
                break

# --- 3. 원본/Google Sheets용 DataFrame 분리 ---
absence_info_df = pd.DataFrame(absence_info_records)
date_cols = ['ABSENCE_START_DATE', 'ABSENCE_END_DATE']
if not absence_info_df.empty:
    for col in date_cols:
        absence_info_df[col] = pd.to_datetime(absence_info_df[col], errors='coerce')

absence_info_df_for_gsheet = absence_info_df.copy()
if not absence_info_df_for_gsheet.empty:
    for col in date_cols:
        absence_info_df_for_gsheet[col] = absence_info_df_for_gsheet[col].dt.strftime('%Y-%m-%d')
    for col in absence_info_df_for_gsheet.columns:
        absence_info_df_for_gsheet[col] = absence_info_df_for_gsheet[col].astype(str)
    absence_info_df_for_gsheet = absence_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})


# In[ ]:




