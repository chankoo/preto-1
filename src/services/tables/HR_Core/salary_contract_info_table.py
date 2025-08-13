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
from services.tables.HR_Core.job_table import job_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.career_info_table import career_info_df

random.seed(42)
np.random.seed(42)

salary_contract_info_records = []
today = datetime.datetime.now().date()
today_ts = pd.to_datetime(today)

# --- 2. 헬퍼 데이터 및 함수 준비 ---
high_salary_jobs = ['Backend Developer', 'Mobile Developer', 'DevOps Engineer', 'Strategic Planner']
low_salary_jobs = ['Recruiter', 'Content Marketer', 'Production Manager', 'QA Engineer']
job_name_map = job_df.set_index('JOB_ID')['JOB_NAME'].to_dict()
high_salary_job_ids = {jid for jid, name in job_name_map.items() if name in high_salary_jobs}
low_salary_job_ids = {jid for jid, name in job_name_map.items() if name in low_salary_jobs}

def get_job_tier(job_id):
    if job_id in high_salary_job_ids: return 'High'
    if job_id in low_salary_job_ids: return 'Low'
    return 'Normal'

emp_prior_career_days = {}
if not career_info_df.empty:
    emp_prior_career_days = career_info_df.groupby('EMP_ID')['CAREER_DURATION'].sum().to_dict()

special_pay_categories = ["월급", "주급", "일급", "시급"]
special_pay_emp_map = {}
if len(emp_df) >= len(special_pay_categories):
    special_emp_ids = emp_df['EMP_ID'].sample(n=len(special_pay_categories), random_state=42).tolist()
    special_pay_emp_map = dict(zip(special_emp_ids, special_pay_categories))

leavers_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'N']
low_raise_leaver_ids = set(leavers_df.sample(frac=0.5, random_state=27)['EMP_ID'])

# --- 3. 직원별 임금 계약 이력 생성 ---
for _, emp_row in emp_df.iterrows():
    emp_id = emp_row['EMP_ID']
    emp_in_date = emp_row['IN_DATE'].date()
    emp_out_date = emp_row['OUT_DATE'].date() if pd.notna(emp_row['OUT_DATE']) else None

    emp_job_history = job_info_df[job_info_df['EMP_ID'] == emp_id].sort_values('JOB_APP_START_DATE')
    emp_promotions_dates = position_info_df[
        (position_info_df['EMP_ID'] == emp_id) & (position_info_df['CHANGE_REASON'] != 'Initial Assignment')
    ]['GRADE_START_DATE'].dt.date.tolist()
    if emp_job_history.empty: continue

    first_job_id = emp_job_history.iloc[0]['JOB_ID']
    first_job_tier = get_job_tier(first_job_id)
    prior_career_years = emp_prior_career_days.get(emp_id, 0) / 365.0
    career_bonus = prior_career_years * random.uniform(2_000_000, 3_000_000)
    base_start_salary = random.uniform(35_000_000, 45_000_000)
    initial_annual_salary = base_start_salary + career_bonus
    if first_job_tier == 'High': initial_annual_salary *= random.uniform(1.05, 1.15)
    elif first_job_tier == 'Low': initial_annual_salary *= random.uniform(0.85, 0.95)
    initial_annual_salary = round(min(initial_annual_salary, 70_000_000) / 100_000) * 100_000

    event_dates = [emp_in_date] + [date(year, 1, 1) for year in range(emp_in_date.year + 1, (emp_out_date or today).year + 2)]
    timeline = sorted(list(set([d for d in event_dates if d <= (emp_out_date or today)])))
    last_annual_salary = 0

    for i, start_date in enumerate(timeline):
        if i == 0:
            current_annual_salary = initial_annual_salary
        else:
            previous_start_date = timeline[i-1]
            total_increase_rate = 0
            is_low_raise_leaver_period = (emp_id in low_raise_leaver_ids) and (emp_out_date is not None) and ((emp_out_date - start_date).days <= 365 * 2)
            if is_low_raise_leaver_period:
                total_increase_rate = random.uniform(0.00, 0.03)
            else:
                had_promotion = any(previous_start_date <= promo_date < start_date for promo_date in emp_promotions_dates)
                job_before_df = emp_job_history[emp_job_history['JOB_APP_START_DATE'].dt.date <= previous_start_date]
                job_at_start_df = emp_job_history[emp_job_history['JOB_APP_START_DATE'].dt.date <= start_date]
                special_increase = 0
                if not job_before_df.empty and not job_at_start_df.empty:
                    job_tier_before, job_tier_after = get_job_tier(job_before_df.iloc[-1]['JOB_ID']), get_job_tier(job_at_start_df.iloc[-1]['JOB_ID'])
                    if job_tier_before != job_tier_after:
                        if job_tier_before == 'Low' and job_tier_after == 'High': special_increase = random.uniform(0.05, 0.07)
                        elif (job_tier_before == 'Normal' and job_tier_after == 'High') or (job_tier_before == 'Low' and job_tier_after == 'Normal'):
                            special_increase = random.uniform(0.03, 0.05)
                increase_rate = random.uniform(0.10, 0.15) if had_promotion else (max(0.01, np.random.normal(loc=0.06, scale=0.03)) + special_increase)
                total_increase_rate = increase_rate
            if start_date.year == emp_in_date.year + 1 and not is_low_raise_leaver_period:
                days_worked = 365 - emp_in_date.timetuple().tm_yday
                total_increase_rate *= (days_worked / 365.0)
            current_annual_salary = round((last_annual_salary * (1 + total_increase_rate)) / 100_000) * 100_000

        end_date = emp_out_date if i == len(timeline) - 1 else timeline[i+1] - timedelta(days=1)
        if end_date and (emp_out_date and end_date > emp_out_date): end_date = emp_out_date
        if emp_row['CURRENT_EMP_YN'] == 'Y' and (end_date is None or end_date >= today): end_date = None

        pay_category = special_pay_emp_map.get(emp_id, "연봉")
        sal_amount = current_annual_salary
        if pay_category == "월급": sal_amount = round(current_annual_salary / 12)
        elif pay_category == "주급": sal_amount = round(current_annual_salary / 52)
        elif pay_category == "일급": sal_amount = round(current_annual_salary / 250)
        elif pay_category == "시급": sal_amount = round(current_annual_salary / 2080)

        salary_contract_info_records.append({"EMP_ID": emp_id, "SAL_START_DATE": start_date, "PAY_CATEGORY": pay_category, "SAL_AMOUNT": sal_amount, "SAL_END_DATE": end_date})
        last_annual_salary = current_annual_salary

# --- 4. 원본/Google Sheets용 DataFrame 분리 ---
salary_contract_info_df = pd.DataFrame(salary_contract_info_records)
date_cols = ['SAL_START_DATE', 'SAL_END_DATE']
if not salary_contract_info_df.empty:
    for col in date_cols:
        salary_contract_info_df[col] = pd.to_datetime(salary_contract_info_df[col], errors='coerce')

salary_contract_info_df_for_gsheet = salary_contract_info_df.copy()
if not salary_contract_info_df_for_gsheet.empty:
    for col in date_cols:
        salary_contract_info_df_for_gsheet[col] = salary_contract_info_df_for_gsheet[col].dt.strftime('%Y-%m-%d')
    for col in salary_contract_info_df_for_gsheet.columns:
        salary_contract_info_df_for_gsheet[col] = salary_contract_info_df_for_gsheet[col].astype(str)
    salary_contract_info_df_for_gsheet = salary_contract_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})

