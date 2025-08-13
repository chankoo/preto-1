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
from services.tables.HR_Core.project_table import pjt_df

random.seed(42)
np.random.seed(42)

pjt_info_records = []
today = datetime.datetime.now().date()
today_ts = pd.to_datetime(today)

# --- 2. 데이터 생성 ---
# pjt_df에서 할당 가능한 프로젝트 버전 목록 준비
assignable_projects_df = pd.DataFrame()
if not pjt_df.empty and 'PJT_USE_YN' in pjt_df.columns:
    assignable_projects_df = pjt_df[pjt_df['PJT_USE_YN'] == 'Y'].copy()

# 프로젝트에 참여할 직원 선택
num_total_employees = len(emp_df)
num_participating_employees_target = 100
actual_num_participating = min(num_total_employees, num_participating_employees_target)
participating_emp_df = pd.DataFrame()
if actual_num_participating > 0:
    participating_emp_ids = emp_df['EMP_ID'].sample(n=actual_num_participating, random_state=42).tolist()
    participating_emp_df = emp_df[emp_df['EMP_ID'].isin(participating_emp_ids)]

# 선택된 직원별 프로젝트 참여 이력 생성
if not participating_emp_df.empty and not assignable_projects_df.empty:
    for _, emp_row in participating_emp_df.iterrows():
        emp_id = emp_row['EMP_ID']
        emp_in_date = emp_row['IN_DATE'].date()
        emp_out_date = emp_row['OUT_DATE'].date() if pd.notna(emp_row['OUT_DATE']) else None
        emp_is_current_overall = emp_row['CURRENT_EMP_YN'] == 'Y'

        num_projects_for_employee = random.randint(1, 3)
        earliest_next_pjt_app_start_date = emp_in_date

        for _ in range(num_projects_for_employee):
            if earliest_next_pjt_app_start_date is None or (emp_out_date and earliest_next_pjt_app_start_date > emp_out_date) or (earliest_next_pjt_app_start_date > today):
                break

            comparison_date_ts = pd.to_datetime(emp_out_date or today_ts)
            candidate_projects = assignable_projects_df[
                (assignable_projects_df['PJT_START_DATE'] <= comparison_date_ts) &
                (pd.isna(assignable_projects_df['PJT_END_DATE']) | (assignable_projects_df['PJT_END_DATE'] >= pd.to_datetime(earliest_next_pjt_app_start_date)))
            ]
            if candidate_projects.empty: break

            selected_project_row = candidate_projects.sample(n=1).iloc[0]

            pjt_id = selected_project_row['PJT_ID']
            pjt_start_date = selected_project_row['PJT_START_DATE'].date()
            pjt_end_date = selected_project_row['PJT_END_DATE'].date() if pd.notna(selected_project_row['PJT_END_DATE']) else None

            min_app_start = max(earliest_next_pjt_app_start_date, pjt_start_date)
            pjt_app_start_date = min_app_start + timedelta(days=random.randint(0, 30))

            if (pjt_end_date and pjt_app_start_date > pjt_end_date) or (emp_out_date and pjt_app_start_date > emp_out_date) or (pjt_app_start_date > today):
                continue

            stay_duration = timedelta(days=random.randint(90, 365 * 2))
            potential_pjt_app_end_date = pjt_app_start_date + stay_duration

            upper_bound_date = min(d for d in [pjt_end_date, emp_out_date, today] if d is not None)

            pjt_app_end_date = None
            if potential_pjt_app_end_date > today:
                if emp_is_current_overall and (pjt_end_date is None or pjt_end_date > today):
                    pjt_app_end_date = None
                else:
                    pjt_app_end_date = upper_bound_date
            else:
                pjt_app_end_date = min(potential_pjt_app_end_date, upper_bound_date)

            if pjt_app_end_date is not None and pjt_app_start_date > pjt_app_end_date:
                pjt_app_end_date = pjt_app_start_date

            pjt_title = random.choice(["Leader", "Member", "Support"])

            pjt_duration_days = None
            if pd.notna(pjt_app_start_date):
                start_ts = pd.to_datetime(pjt_app_start_date)
                end_ts = pd.to_datetime(pjt_app_end_date or today_ts)
                pjt_duration_days = (end_ts - start_ts).days

            pjt_info_records.append({
                "EMP_ID": emp_id, "PJT_ID": pjt_id,
                "PJT_APP_START_DATE": pjt_app_start_date,
                "PJT_APP_END_DATE": pjt_app_end_date,
                "PJT_TITLE_INFO": pjt_title,
                "PJT_DURATION": pjt_duration_days
            })

            if pjt_app_end_date is None:
                break
            else:
                earliest_next_pjt_app_start_date = pjt_app_end_date + timedelta(days=random.randint(60, 180))


# --- 3. 원본/Google Sheets용 DataFrame 분리 ---
pjt_info_df = pd.DataFrame(pjt_info_records)
date_cols = ['PJT_APP_START_DATE', 'PJT_APP_END_DATE']
if not pjt_info_df.empty:
    for col in date_cols:
        pjt_info_df[col] = pd.to_datetime(pjt_info_df[col], errors='coerce')

pjt_info_df_for_gsheet = pjt_info_df.copy()
if not pjt_info_df_for_gsheet.empty:
    for col in date_cols:
        pjt_info_df_for_gsheet[col] = pjt_info_df_for_gsheet[col].dt.strftime('%Y-%m-%d')
    for col in pjt_info_df_for_gsheet.columns:
        pjt_info_df_for_gsheet[col] = pjt_info_df_for_gsheet[col].astype(str)
    pjt_info_df_for_gsheet = pjt_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})

