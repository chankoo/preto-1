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
from services.tables.HR_Core.school_table import school_df
from services.helpers.utils import calculate_age

random.seed(42)
np.random.seed(42)

school_info_records = []
REFERENCE_YEAR_FOR_STATUS = 2025 # 기준 연도
today = datetime.datetime.now().date()

# --- 2. 헬퍼 데이터 준비 ---
schools_associate_df, schools_bachelor_higher_df = pd.DataFrame(), pd.DataFrame()
if not school_df.empty:
    schools_associate_df = school_df[school_df['SCHOOL_TYPE'] == '전문학사']
    schools_bachelor_higher_df = school_df[school_df['SCHOOL_TYPE'].isin(['4년제', '외국대학'])]

major_categories_list = [
    "상경계열", "사회과학계열", "인문계열", "어문계열",
    "STEM계열", "기타공학계열", "자연과학계열", "디자인계열", "기타"
]
degree_details_map = {
    "전문학사": {"min_dur": 2, "max_dur": 3, "typical_adm_age_min": 18, "typical_adm_age_max": 20},
    "학사": {"min_dur": 3, "max_dur": 5, "typical_adm_age_min": 18, "typical_adm_age_max": 20},
    "석사": {"min_dur": 1, "max_dur": 3, "typical_adm_age_min": 21, "typical_adm_age_max": 30},
    "박사": {"min_dur": 3, "max_dur": 5, "typical_adm_age_min": 23, "typical_adm_age_max": 35}
}

# --- 3. 직원별 학력 정보 생성 ---
for _, emp_row in emp_df.iterrows():
    emp_id = emp_row['EMP_ID']
    try:
        emp_in_year = emp_row['IN_DATE'].year
        employee_birth_year = emp_row['IN_DATE'].year - calculate_age(emp_row['PERSONAL_ID'], base_date=emp_row['IN_DATE'])
    except Exception as e:
        continue

    last_grad_year_for_emp = employee_birth_year + 17

    # 학력 경로 시뮬레이션
    prob_first_degree = random.random()
    current_degree_sequence = ['전문학사'] if prob_first_degree < 0.20 else ['학사']
    has_bachelor = (current_degree_sequence[0] == '학사')

    if not has_bachelor and random.random() < 0.15:
        current_degree_sequence.append('학사'); has_bachelor = True

    master_pursued = False
    if has_bachelor and random.random() < 0.15:
        current_degree_sequence.append('석사'); master_pursued = True

    if master_pursued and random.random() < 0.10:
        current_degree_sequence.append('박사')

    # 선택된 경로에 따라 레코드 생성
    is_first_degree = True
    for degree in current_degree_sequence:
        degree_info = degree_details_map.get(degree)
        if not degree_info: continue

        assignable_schools = schools_associate_df if degree == "전문학사" else schools_bachelor_higher_df
        if assignable_schools.empty: continue

        chosen_school_id = random.choice(assignable_schools['SCHOOL_ID'].unique())
        major_cat = random.choice(major_categories_list)
        actual_duration = random.randint(degree_info["min_dur"], degree_info["max_dur"])

        if is_first_degree:
            admission_age = random.randint(degree_info["typical_adm_age_min"], degree_info["typical_adm_age_max"])
            adm_year = employee_birth_year + admission_age
        else:
            adm_year = last_grad_year_for_emp + random.randint(0, 2)

        if not is_first_degree and adm_year > REFERENCE_YEAR_FOR_STATUS: break

        grad_year = adm_year + actual_duration

        is_foundational = (is_first_degree and degree in ["전문학사", "학사"]) or \
                          (not is_first_degree and degree == "학사" and current_degree_sequence[0] == "전문학사")

        if is_foundational and grad_year >= emp_in_year:
            max_grad_year = emp_in_year - random.randint(1, 2)
            if max_grad_year < adm_year + degree_info["min_dur"]: break
            grad_year = max_grad_year
            adm_year = grad_year - actual_duration
            if adm_year <= employee_birth_year + 16: break

        grad_category = "졸업"
        if not is_foundational or grad_year >= emp_in_year:
            if grad_year == REFERENCE_YEAR_FOR_STATUS: grad_category = random.choice(["졸업", "졸업예정"])
            elif grad_year > REFERENCE_YEAR_FOR_STATUS: grad_category = "재학중"
        if grad_category != "졸업" and grad_year < REFERENCE_YEAR_FOR_STATUS:
            grad_category = "졸업"

        school_info_records.append({
            "EMP_ID": emp_id, "SCHOOL_ID": chosen_school_id, "GRAD_CATEGORY": grad_category,
            "EDU_DEGREE": degree, "ADM_YEAR": adm_year, "GRAD_YEAR": grad_year,
            "MAJOR_CATEGORY": major_cat
        })

        last_grad_year_for_emp = grad_year
        is_first_degree = False
        if grad_category in ["재학중", "졸업예정"]: break

# --- 4. 원본/Google Sheets용 DataFrame 분리 ---
school_info_df = pd.DataFrame(school_info_records)
if not school_info_df.empty:
    school_info_df['ADM_YEAR'] = pd.to_numeric(school_info_df['ADM_YEAR'])
    school_info_df['GRAD_YEAR'] = pd.to_numeric(school_info_df['GRAD_YEAR'])

school_info_df_for_gsheet = school_info_df.copy()
if not school_info_df_for_gsheet.empty:
    for col in school_info_df_for_gsheet.columns:
        school_info_df_for_gsheet[col] = school_info_df_for_gsheet[col].astype(str)
    school_info_df_for_gsheet = school_info_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

