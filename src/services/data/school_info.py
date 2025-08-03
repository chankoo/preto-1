import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import random

from services.data.schools import school_df
from services.data.basic_info import emp_df


# --- 17. SCHOOL INFO TABLE --- (학력정보)

# --- 1. 사전 준비 ---
# emp_df, school_df DataFrame이 로드되어 있다고 가정
random.seed(42)
np.random.seed(42)

school_info_records = []
REFERENCE_YEAR_FOR_STATUS = 2025
today_date_obj = datetime.now().date()
today_ts = pd.to_datetime(today_date_obj)

schools_associate_df, schools_bachelor_higher_df = pd.DataFrame(), pd.DataFrame()
if not school_df.empty:
    schools_associate_df = school_df[school_df["SCHOOL_TYPE"] == "전문학사"]
    schools_bachelor_higher_df = school_df[
        school_df["SCHOOL_TYPE"].isin(["4년제", "외국대학"])
    ]

major_categories_list = [
    "상경계열",
    "사회과학계열",
    "인문계열",
    "어문계열",
    "STEM계열",
    "기타공학계열",
    "자연과학계열",
    "디자인계열",
    "기타",
]
degree_details_map = {
    "전문학사": {
        "min_dur": 2,
        "max_dur": 3,
        "typical_adm_age_min": 18,
        "typical_adm_age_max": 20,
    },
    "학사": {
        "min_dur": 3,
        "max_dur": 5,
        "typical_adm_age_min": 18,
        "typical_adm_age_max": 20,
    },
    "석사": {
        "min_dur": 1,
        "max_dur": 3,
        "typical_adm_age_min": 21,
        "typical_adm_age_max": 30,
    },
    "박사": {
        "min_dur": 3,
        "max_dur": 5,
        "typical_adm_age_min": 23,
        "typical_adm_age_max": 35,
    },
}

# --- 2. 직원별 학력 정보 생성 ---
for _, emp_row in emp_df.iterrows():
    emp_id = emp_row["EMP_ID"]
    try:
        emp_in_year = pd.to_datetime(emp_row["IN_DATE"]).year
        birth_yy = int(str(emp_row["PERSONAL_ID"])[:2])
        employee_birth_year = (
            1900 + birth_yy
            if birth_yy > (REFERENCE_YEAR_FOR_STATUS % 100) + 5
            else 2000 + birth_yy
        )
    except Exception as e:
        continue

    last_grad_year_for_emp = employee_birth_year + 17

    # 학력 경로 시뮬레이션
    prob_first_degree = random.random()
    current_degree_sequence = ["전문학사"] if prob_first_degree < 0.20 else ["학사"]
    has_bachelor = current_degree_sequence[0] == "학사"

    if not has_bachelor and random.random() < 0.15:
        current_degree_sequence.append("학사")
        has_bachelor = True

    master_pursued = False
    if has_bachelor and random.random() < 0.15:
        current_degree_sequence.append("석사")
        master_pursued = True

    if master_pursued and random.random() < 0.10:
        current_degree_sequence.append("박사")

    # 선택된 경로에 따라 레코드 생성
    is_first_degree = True
    for degree in current_degree_sequence:
        degree_info = degree_details_map.get(degree)
        if not degree_info:
            continue

        assignable_schools = (
            schools_associate_df if degree == "전문학사" else schools_bachelor_higher_df
        )
        if assignable_schools.empty:
            continue

        chosen_school_id = random.choice(assignable_schools["SCHOOL_ID"].unique())
        major_cat = random.choice(major_categories_list)
        actual_duration = random.randint(degree_info["min_dur"], degree_info["max_dur"])

        if is_first_degree:
            admission_age = random.randint(
                degree_info["typical_adm_age_min"], degree_info["typical_adm_age_max"]
            )
            adm_year = employee_birth_year + admission_age
        else:
            adm_year = last_grad_year_for_emp + random.randint(0, 2)

        if not is_first_degree and adm_year > REFERENCE_YEAR_FOR_STATUS:
            break

        grad_year = adm_year + actual_duration

        is_foundational = (is_first_degree and degree in ["전문학사", "학사"]) or (
            not is_first_degree
            and degree == "학사"
            and current_degree_sequence[0] == "전문학사"
        )

        if is_foundational and grad_year >= emp_in_year:
            max_grad_year = emp_in_year - random.randint(1, 2)
            if max_grad_year < adm_year + degree_info["min_dur"]:
                break
            grad_year = max_grad_year
            adm_year = grad_year - actual_duration
            if adm_year <= employee_birth_year + 16:
                break

        grad_category = "졸업"
        if not is_foundational or grad_year >= emp_in_year:
            if grad_year == REFERENCE_YEAR_FOR_STATUS:
                grad_category = random.choice(["졸업", "졸업예정"])
            elif grad_year > REFERENCE_YEAR_FOR_STATUS:
                grad_category = "재학중"
        if grad_category != "졸업" and grad_year < REFERENCE_YEAR_FOR_STATUS:
            grad_category = "졸업"

        school_info_records.append(
            {
                "EMP_ID": emp_id,
                "SCHOOL_ID": chosen_school_id,
                "GRAD_CATEGORY": grad_category,
                "EDU_DEGREE": degree,
                "ADM_YEAR": adm_year,
                "GRAD_YEAR": grad_year,
                "MAJOR_CATEGORY": major_cat,
            }
        )

        last_grad_year_for_emp = grad_year
        is_first_degree = False
        if grad_category in ["재학중", "졸업예정"]:
            break

# --- 3. 원본 DataFrame (분석용) ---
school_info_df = pd.DataFrame(school_info_records)
# 숫자 타입 유지
if not school_info_df.empty:
    school_info_df["ADM_YEAR"] = pd.to_numeric(school_info_df["ADM_YEAR"])
    school_info_df["GRAD_YEAR"] = pd.to_numeric(school_info_df["GRAD_YEAR"])

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
school_info_df_for_gsheet = school_info_df.copy()
# 모든 컬럼을 문자열로 변환하고 정리
if not school_info_df_for_gsheet.empty:
    for col in school_info_df_for_gsheet.columns:
        school_info_df_for_gsheet[col] = school_info_df_for_gsheet[col].astype(str)
    school_info_df_for_gsheet = school_info_df_for_gsheet.replace(
        {"None": "", "nan": "", "NaT": ""}
    )

# --- 결과 확인 (원본 DataFrame 출력) ---
school_info_df
