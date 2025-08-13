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
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_table import department_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.job_table import job_df

random.seed(42)
np.random.seed(42)

job_info_records = []
today = datetime.datetime.now().date()

# --- 2. 헬퍼 데이터 준비 ---
dept_job_keyword_map = {
    'Planning': ['Planning', 'Planner', 'Analysis'], 'Strategy': ['Strategic', 'Planner', 'Analysis'],
    'Finance': ['Finance', 'Accountant', 'Treasury'], 'Accounting': ['Accountant'],
    'HR': ['HR', 'Recruiter', 'Generalist'],
    'Development': ['Developer', 'Engineer', 'Data'], 'R&D': ['Developer', 'Engineer', 'Data'],
    'QA': ['QA'], 'Sales': ['Sales'], 'Marketing': ['Marketer', 'Marketing'],
    'Engineering': ['Engineer', 'Production'], 'Production': ['Production', 'Manager'],
    'Support': ['Support', 'Generalist'], 'Data':['Data']
}
common_job_keywords = ['Planner', 'Analyst']

level_3_jobs = job_df[job_df['JOB_LEVEL'] == 3].copy().reset_index(drop=True)

# --- 3. 직원별 직무 이력 생성 ---
for _, emp_row in emp_df.iterrows():
    emp_id = emp_row['EMP_ID']
    emp_in_date = emp_row['IN_DATE'].date()
    emp_out_date = emp_row['OUT_DATE'].date() if pd.notna(emp_row['OUT_DATE']) else None
    emp_is_current = emp_row['CURRENT_EMP_YN'] == 'Y'

    current_assignment_start_date = emp_in_date

    while True:
        if (emp_out_date and current_assignment_start_date > emp_out_date) or \
           (current_assignment_start_date > today):
            break

        emp_dept_history = department_info_df[department_info_df['EMP_ID'] == emp_id]
        current_dept_assignment = emp_dept_history[
            (emp_dept_history['DEP_APP_START_DATE'] <= pd.to_datetime(current_assignment_start_date)) &
            (pd.isna(emp_dept_history['DEP_APP_END_DATE']) | (emp_dept_history['DEP_APP_END_DATE'] >= pd.to_datetime(current_assignment_start_date)))
        ]

        if current_dept_assignment.empty:
            break

        dept_name = department_df.loc[department_df['DEP_ID'] == current_dept_assignment.iloc[0]['DEP_ID'], 'DEP_NAME'].iloc[0]

        suitable_keywords = [kw for d_kw, j_kws in dept_job_keyword_map.items() if d_kw in dept_name for kw in j_kws]

        if random.random() < 0.8 and suitable_keywords:
            keyword_regex = '|'.join(suitable_keywords)
            candidate_jobs = level_3_jobs[level_3_jobs['JOB_NAME'].str.contains(keyword_regex, na=False)]
        else:
            keyword_regex = '|'.join(common_job_keywords)
            candidate_jobs = level_3_jobs[level_3_jobs['JOB_NAME'].str.contains(keyword_regex, na=False)]

        if candidate_jobs.empty:
            candidate_jobs = level_3_jobs

        assigned_job_id = candidate_jobs.sample(1)['JOB_ID'].iloc[0]

        years_in_job = 0
        job_end_date = None
        temp_date = current_assignment_start_date
        while True:
            next_year_date = temp_date + timedelta(days=365)
            if (emp_out_date and next_year_date > emp_out_date) or (next_year_date > today):
                job_end_date = emp_out_date if not emp_is_current else None
                break
            change_probability = 0.04 + max(0, years_in_job - 4) * 0.10
            if random.random() < change_probability and years_in_job > 0:
                job_end_date = next_year_date
                break
            years_in_job += 1
            temp_date = next_year_date

        job_info_records.append({
            'EMP_ID': emp_id,
            'JOB_ID': assigned_job_id,
            'JOB_APP_START_DATE': current_assignment_start_date,
            'JOB_APP_END_DATE': job_end_date,
        })

        if job_end_date is None:
            break
        else:
            current_assignment_start_date = job_end_date + timedelta(days=1)

# --- 4. 원본/Google Sheets용 DataFrame 분리 ---
job_info_df = pd.DataFrame(job_info_records)
date_cols = ['JOB_APP_START_DATE', 'JOB_APP_END_DATE']
if not job_info_df.empty:
    for col in date_cols:
        job_info_df[col] = pd.to_datetime(job_info_df[col], errors='coerce')

job_info_df_for_gsheet = job_info_df.copy()
if not job_info_df_for_gsheet.empty:
    for col in date_cols:
        job_info_df_for_gsheet[col] = job_info_df_for_gsheet[col].dt.strftime('%Y-%m-%d')
    for col in job_info_df_for_gsheet.columns:
        job_info_df_for_gsheet[col] = job_info_df_for_gsheet[col].astype(str)
    job_info_df_for_gsheet = job_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})

