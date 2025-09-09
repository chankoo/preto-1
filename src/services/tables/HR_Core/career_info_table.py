#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import random

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임 및 헬퍼 데이터/함수를 임포트
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.career_table import career_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job
from services.helpers.utils import get_level1_ancestor

random.seed(42)
np.random.seed(42)

career_info_records = []

# --- 2. 헬퍼 데이터 준비 ---
level_1_job_ids_for_career = job_df[job_df['JOB_LEVEL'] == 1]['JOB_ID'].unique()
available_career_company_ids = career_df['CAREER_COMPANY_ID'].unique()

# CAREER_REL_YN 계산을 위한 헬퍼 데이터
emp_first_job = job_info_df.sort_values('JOB_APP_START_DATE').groupby('EMP_ID').first().reset_index()
emp_first_job['L1_JOB_ID'] = emp_first_job['JOB_ID'].apply(lambda x: get_level1_ancestor(x, job_df_indexed, parent_map_job))
emp_first_job_l1_map = emp_first_job.set_index('EMP_ID')['L1_JOB_ID'].to_dict()

# --- 3. 초기 직급에 따른 총 경력 기간 목표 설정 ---
first_assignments = position_info_df.sort_values('GRADE_START_DATE').groupby('EMP_ID').first().reset_index()
num_employees_with_career = int(len(emp_df) * 0.5)
career_emp_ids = emp_df['EMP_ID'].sample(n=num_employees_with_career, random_state=42)
employees_for_career_df = pd.merge(emp_df[emp_df['EMP_ID'].isin(career_emp_ids)], first_assignments[['EMP_ID', 'GRADE_ID']], on='EMP_ID', how='left')
employees_for_career_df = employees_for_career_df.dropna(subset=['GRADE_ID'])

grade_to_career_years_map = {
    'G1': (0, 3), 'G2': (2, 6), 'G3': (5, 10),
    'G4': (8, 15), 'G5': (10, 18), 'G6': (15, 20)
}
for i in range(7, 20): grade_to_career_years_map[f'G{i}'] = (15, 20)
def assign_target_career_years(grade):
    min_years, max_years = grade_to_career_years_map.get(grade, (0, 1))
    return random.uniform(min_years, max_years)
employees_for_career_df['TARGET_TOTAL_CAREER_YEARS'] = employees_for_career_df['GRADE_ID'].apply(assign_target_career_years)

# --- 4. 직원별 상세 경력 생성 ---
for _, emp_row in employees_for_career_df.iterrows():
    emp_id = emp_row['EMP_ID']
    current_company_in_date = emp_row['IN_DATE'].date()
    target_total_career_days = int(emp_row['TARGET_TOTAL_CAREER_YEARS'] * 365)

    if target_total_career_days <= 0: continue

    accumulated_career_days, num_previous_jobs = 0, random.randint(1, 3)
    latest_possible_career_out_date = current_company_in_date - timedelta(days=random.randint(30, 180))

    for job_spell_idx in range(num_previous_jobs):
        if accumulated_career_days >= target_total_career_days: break

        career_out_date = latest_possible_career_out_date
        remaining_days = target_total_career_days - accumulated_career_days
        max_days = min(remaining_days, 7 * 365); min_days = 180

        if max_days < min_days:
            if remaining_days > 0: spell_duration = max(1, remaining_days)
            else: break
        else:
            spell_duration = random.randint(min_days, max_days)

        career_in_date = career_out_date - timedelta(days=spell_duration)
        if career_in_date >= career_out_date: continue

        career_company_id = random.choice(available_career_company_ids)
        career_cont_category = "Full-Time" if random.random() < 0.80 else random.choice(["Contract", "Part-Time", "Temporary"])
        career_in_job_l1_id = random.choice(level_1_job_ids_for_career)
        first_job_l1 = emp_first_job_l1_map.get(emp_id)
        career_rel_yn = 'Y' if first_job_l1 and career_in_job_l1_id == first_job_l1 else 'N'

        career_info_records.append({
            "EMP_ID": emp_id, "CAREER_COMPANY_ID": career_company_id,
            "CAREER_IN_DATE": career_in_date, "CAREER_OUT_DATE": career_out_date,
            "CAREER_CONT_CATEGORY": career_cont_category, "CAREER_IN_JOB": career_in_job_l1_id,
            "CAREER_DURATION": (career_out_date - career_in_date).days, "CAREER_REL_YN": career_rel_yn
        })

        accumulated_career_days += spell_duration
        latest_possible_career_out_date = career_in_date - timedelta(days=random.randint(15, 90))

# --- 5. 원본/Google Sheets용 DataFrame 분리 ---
career_info_df = pd.DataFrame(career_info_records)
if not career_info_df.empty:
    date_cols = ['CAREER_IN_DATE', 'CAREER_OUT_DATE']
    for col in date_cols:
        career_info_df[col] = pd.to_datetime(career_info_df[col], errors='coerce')

career_info_df_for_gsheet = career_info_df.copy()
if not career_info_df_for_gsheet.empty:
    for col in date_cols:
        career_info_df_for_gsheet[col] = career_info_df_for_gsheet[col].dt.strftime('%Y-%m-%d')
    for col in career_info_df_for_gsheet.columns:
        career_info_df_for_gsheet[col] = career_info_df_for_gsheet[col].astype(str)
    career_info_df_for_gsheet = career_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})


# In[ ]:




