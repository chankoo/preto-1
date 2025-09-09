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
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.salary_contract_info_table import salary_contract_info_df
from services.tables.Performance.evaluation_apply_table import evaluation_apply_df
from services.helpers.utils import get_period_dates

random.seed(42)
np.random.seed(42)

eval_score_records = []
today = datetime.datetime.now().date()
today_ts = pd.to_datetime(today)

# --- 2. 헬퍼 데이터 준비 ---
leavers_df = emp_df[emp_df['CURRENT_EMP_YN'] == 'N']
low_perf_leaver_ids = set(leavers_df.sample(frac=0.5, random_state=34)['EMP_ID'])

promotion_df = position_info_df[position_info_df['CHANGE_REASON'] != 'Initial Assignment'].copy()
promotion_dates_map = promotion_df.groupby('EMP_ID')['GRADE_START_DATE'].apply(list).to_dict()

salary_df_calc = salary_contract_info_df[salary_contract_info_df['PAY_CATEGORY'] == '연봉'].copy()
salary_df_calc['SAL_AMOUNT'] = pd.to_numeric(salary_df_calc['SAL_AMOUNT'])
salary_df_calc = salary_df_calc.sort_values(by=['EMP_ID', 'SAL_START_DATE'])
salary_df_calc['SAL_INCREASE_RATE'] = salary_df_calc.groupby('EMP_ID')['SAL_AMOUNT'].pct_change()
salary_df_calc['SAL_YEAR'] = salary_df_calc['SAL_START_DATE'].dt.year

# --- 3. 평가 시기별 점수/등급 생성 ---
last_eval_scores, last_eval_grades = {}, {}
sorted_eval_apply_df = evaluation_apply_df.sort_values(by='EVAL_TIME')
for _, apply_row in sorted_eval_apply_df.iterrows():
    eval_time, eval_sys_id, score_process_type = apply_row['EVAL_TIME'], apply_row['EVAL_SYS_ID'], apply_row['SCORE_PROCESS']
    period_start, period_end = get_period_dates(eval_time)
    period_start_ts, period_end_ts = pd.to_datetime(period_start), pd.to_datetime(period_end)
    eval_year = period_start.year

    eligible_emps_df = emp_df[(emp_df['IN_DATE'] <= period_end_ts) & (pd.isna(emp_df['OUT_DATE']) | (emp_df['OUT_DATE'] >= period_start_ts))].copy()
    if eval_sys_id == 'ES003': # 리더십 상향평가
        dept_info_in_period = department_info_df[(department_info_df['DEP_APP_START_DATE'] <= period_end_ts) & (pd.isna(department_info_df['DEP_APP_END_DATE']) | (department_info_df['DEP_APP_END_DATE'] >= period_start_ts))]
        leader_ids = dept_info_in_period[dept_info_in_period['TITLE_INFO'] == 'Head']['EMP_ID'].unique()
        eligible_emps_df = eligible_emps_df[eligible_emps_df['EMP_ID'].isin(leader_ids)]
    if eligible_emps_df.empty: continue

    yearly_increase_rates = salary_df_calc[salary_df_calc['SAL_YEAR'] == eval_year + 1][['EMP_ID', 'SAL_INCREASE_RATE']]
    eligible_emps_df = pd.merge(eligible_emps_df, yearly_increase_rates, on='EMP_ID', how='left')
    eligible_emps_df['SAL_INCREASE_RATE'] = eligible_emps_df['SAL_INCREASE_RATE'].fillna(0)

    eligible_emps_df = pd.merge_asof(
        eligible_emps_df.sort_values('IN_DATE'), 
        position_info_df.sort_values('GRADE_START_DATE'),
        left_on='IN_DATE', right_on='GRADE_START_DATE', by='EMP_ID', direction='backward'
    )
    eligible_emps_df = eligible_emps_df.dropna(subset=['POSITION_ID'])
    eligible_emps_df['SAL_INCREASE_RANK_PCT'] = eligible_emps_df.groupby('POSITION_ID')['SAL_INCREASE_RATE'].rank(pct=True, na_option='bottom')

    if score_process_type == '100점 환산':
        new_scores_this_period = {}
        for _, emp_eval_row in eligible_emps_df.iterrows():
            emp_id, out_date = emp_eval_row['EMP_ID'], emp_eval_row['OUT_DATE']
            is_low_perf = (emp_id in low_perf_leaver_ids) and pd.notna(out_date) and ((out_date - period_end_ts).days <= 365 * 2)
            if is_low_perf: score = round(random.uniform(40, 65), 1)
            else:
                promo_dates = promotion_dates_map.get(emp_id, [])
                is_promo_upcoming = any(period_end_ts < p <= (period_end_ts + pd.DateOffset(months=6)) for p in promo_dates)
                if is_promo_upcoming: score = round(random.uniform(85, 100), 1)
                else:
                    last_score = last_eval_scores.get(emp_id)
                    if last_score and random.random() < 0.8:
                        variation = last_score * 0.2
                        score = round(max(10, min(100, random.uniform(last_score - variation, last_score + variation))), 1)
                    else:
                        rank = emp_eval_row['SAL_INCREASE_RANK_PCT']
                        mode = 50 + (rank * 45)
                        score = round(np.random.triangular(10, mode, 100), 1)
            eval_score_records.append({'EMP_ID': emp_id, 'EVAL_TIME': eval_time, 'EVAL_SYS_ID': eval_sys_id, 'ORIGINAL_SCORE': score})
            new_scores_this_period[emp_id] = score
        last_eval_scores.update(new_scores_this_period)

    elif score_process_type == '등급화':
        emp_dept_info = department_info_df.sort_values('DEP_APP_START_DATE').groupby('EMP_ID').last()
        eligible_emps_df = pd.merge(eligible_emps_df, emp_dept_info[['DEP_ID']], on='EMP_ID', how='left')
        new_grades_this_period = {}
        for _, group in eligible_emps_df.groupby('DEP_ID'):
            grade_labels = ['D', 'C', 'B', 'A', 'S']
            expected_scores = 60 + (group['SAL_INCREASE_RANK_PCT'] * 30); raw_scores = np.random.normal(loc=expected_scores, scale=5)
            initial_grades = pd.cut(raw_scores, bins=[-np.inf, 60, 70, 85, 95, np.inf], labels=grade_labels, right=False).to_numpy()

            for i, emp_id in enumerate(group['EMP_ID'].to_list()):
                out_date = group.loc[group['EMP_ID'] == emp_id, 'OUT_DATE'].iloc[0]
                is_low_perf = (emp_id in low_perf_leaver_ids) and pd.notna(out_date) and ((out_date - period_end_ts).days <= 365 * 2)
                current_grade = initial_grades[i]
                if is_low_perf: grade = random.choice(['C', 'D'])
                else:
                    promo_dates = promotion_dates_map.get(emp_id, [])
                    is_promo_upcoming = any(period_end_ts < p <= (period_end_ts + pd.DateOffset(months=6)) for p in promo_dates)
                    if is_promo_upcoming: grade = random.choice(['S', 'A'])
                    else:
                        last_grade = last_eval_grades.get(emp_id); grade = current_grade
                        if last_grade and random.random() < 0.8 and pd.notna(grade) and grade in grade_labels:
                            last_idx = grade_labels.index(last_grade); current_idx = grade_labels.index(grade)
                            if abs(current_idx - last_idx) > 1:
                                min_idx = max(0, last_idx - 1); max_idx = min(len(grade_labels) - 1, last_idx + 1)
                                grade = random.choice(grade_labels[min_idx : max_idx+1])
                eval_score_records.append({'EMP_ID': emp_id, 'EVAL_TIME': eval_time, 'EVAL_SYS_ID': eval_sys_id, 'ORIGINAL_SCORE': grade})
                new_grades_this_period[emp_id] = grade
        last_eval_grades.update(new_grades_this_period)

# --- 4. 원본/Google Sheets용 DataFrame 분리 ---
evaluation_original_score_df = pd.DataFrame(eval_score_records)

evaluation_original_score_df_for_gsheet = evaluation_original_score_df.copy()
if not evaluation_original_score_df_for_gsheet.empty:
    for col in evaluation_original_score_df_for_gsheet.columns:
        evaluation_original_score_df_for_gsheet[col] = evaluation_original_score_df_for_gsheet[col].astype(str)
    evaluation_original_score_df_for_gsheet = evaluation_original_score_df_for_gsheet.replace({'None':'', 'nan':'', 'NaT':''})


# In[ ]:




