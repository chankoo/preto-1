import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import random

from services.data.jobs import job_df
from services.data.basic_info import emp_df
from services.data.careers import career_df
from services.data.position_info import position_info_df
from services.data.job_info import job_info_df

from services.data.basic_info import emp_df
from services.data.careers import career_df
from services.data.position_info import position_info_df
from services.data.job_info import job_info_df

# --- 16. CAREER INFO TABLE --- (경력정보)


# --- 1. 사전 준비 ---
# 모든 관련 DataFrame이 로드되어 있다고 가정
random.seed(42)
np.random.seed(42)

career_info_records = []

# --- 2. 헬퍼 데이터 준비 ---
# 날짜 타입 변환은 이 코드 내에서 직접 사용하므로, main df의 _DT 컬럼 생성은 불필요
level_1_job_ids_for_career = job_df[job_df["JOB_LEVEL"] == 1]["JOB_ID"].unique()
available_career_company_ids = career_df["CAREER_COMPANY_ID"].unique()

# CAREER_REL_YN 계산을 위한 헬퍼 함수 및 데이터
job_df_indexed = job_df.set_index("JOB_ID")
parent_map_job = job_df_indexed["UP_JOB_ID"].to_dict()


def get_level1_ancestor(job_id, df_indexed, p_map):
    if pd.isna(job_id):
        return None
    try:
        current_level = df_indexed.loc[job_id, "JOB_LEVEL"]
        current_id = job_id
        depth = 0
        while current_level != 1 and pd.notna(p_map.get(current_id)) and depth < 5:
            current_id = p_map.get(current_id)
            current_level = df_indexed.loc[current_id, "JOB_LEVEL"]
            depth += 1
        return current_id if current_level == 1 else None
    except KeyError:
        return None


emp_first_job = (
    job_info_df.sort_values("JOB_APP_START_DATE")
    .groupby("EMP_ID")
    .first()
    .reset_index()
)
emp_first_job["L1_JOB_ID"] = emp_first_job["JOB_ID"].apply(
    lambda x: get_level1_ancestor(x, job_df_indexed, parent_map_job)
)
emp_first_job_l1_map = emp_first_job.set_index("EMP_ID")["L1_JOB_ID"].to_dict()

# --- 3. 초기 직급에 따른 총 경력 기간 목표 설정 ---
first_assignments = (
    position_info_df.sort_values("GRADE_START_DATE")
    .groupby("EMP_ID")
    .first()
    .reset_index()
)
num_employees_with_career = int(len(job_df) * 0.5)
career_emp_ids = emp_df["EMP_ID"].sample(n=num_employees_with_career, random_state=42)
employees_for_career_df = pd.merge(
    emp_df[emp_df["EMP_ID"].isin(career_emp_ids)],
    first_assignments[["EMP_ID", "GRADE_ID"]],
    on="EMP_ID",
    how="left",
)
employees_for_career_df.dropna(subset=["GRADE_ID"], inplace=True)

grade_to_career_years_map = {
    "G1": (0, 3),
    "G2": (2, 6),
    "G3": (5, 10),
    "G4": (8, 15),
    "G5": (10, 18),
    "G6": (15, 20),
}
for i in range(7, 20):
    grade_to_career_years_map[f"G{i}"] = (15, 20)


def assign_target_career_years(grade):
    min_years, max_years = grade_to_career_years_map.get(grade, (0, 1))
    return random.uniform(min_years, max_years)


employees_for_career_df["TARGET_TOTAL_CAREER_YEARS"] = employees_for_career_df[
    "GRADE_ID"
].apply(assign_target_career_years)

# --- 4. 직원별 상세 경력 생성 ---
for _, emp_row in employees_for_career_df.iterrows():
    emp_id = emp_row["EMP_ID"]
    current_company_in_date = emp_row["IN_DATE"].date()
    target_total_career_days = int(emp_row["TARGET_TOTAL_CAREER_YEARS"] * 365)

    if target_total_career_days <= 0:
        continue

    accumulated_career_days, num_previous_jobs = 0, random.randint(1, 3)
    latest_possible_career_out_date = current_company_in_date - timedelta(
        days=random.randint(30, 180)
    )

    for job_spell_idx in range(num_previous_jobs):
        if accumulated_career_days >= target_total_career_days:
            break

        career_out_date = latest_possible_career_out_date
        remaining_days = target_total_career_days - accumulated_career_days
        max_days = min(remaining_days, 7 * 365)
        min_days = 180

        if max_days < min_days:
            if remaining_days > 0:
                spell_duration = max(1, remaining_days)
            else:
                break
        else:
            spell_duration = random.randint(min_days, max_days)

        career_in_date = career_out_date - timedelta(days=spell_duration)
        if career_in_date >= career_out_date:
            continue

        career_company_id = random.choice(available_career_company_ids)
        career_cont_category = (
            "Full-Time"
            if random.random() < 0.80
            else random.choice(["Contract", "Part-Time", "Temporary"])
        )
        career_in_job_l1_id = random.choice(level_1_job_ids_for_career)
        first_job_l1 = emp_first_job_l1_map.get(emp_id)
        career_rel_yn = (
            "Y" if first_job_l1 and career_in_job_l1_id == first_job_l1 else "N"
        )

        career_info_records.append(
            {
                "EMP_ID": emp_id,
                "CAREER_COMPANY_ID": career_company_id,
                "CAREER_IN_DATE": career_in_date,
                "CAREER_OUT_DATE": career_out_date,
                "CAREER_CONT_CATEGORY": career_cont_category,
                "CAREER_IN_JOB": career_in_job_l1_id,
                "CAREER_DURATION": (career_out_date - career_in_date).days,
                "CAREER_REL_YN": career_rel_yn,
            }
        )

        accumulated_career_days += spell_duration
        latest_possible_career_out_date = career_in_date - timedelta(
            days=random.randint(15, 90)
        )

# --- 5. 원본 DataFrame (분석용) ---
career_info_df = pd.DataFrame(career_info_records)
# 날짜 컬럼을 datetime 타입으로 변환
if not career_info_df.empty:
    date_cols = ["CAREER_IN_DATE", "CAREER_OUT_DATE"]
    for col in date_cols:
        career_info_df[col] = pd.to_datetime(career_info_df[col], errors="coerce")


# --- 6. Google Sheets용 복사본 생성 및 가공 ---
career_info_df_for_gsheet = career_info_df.copy()
if not career_info_df_for_gsheet.empty:
    # 날짜를 'YYYY-MM-DD' 문자열로 변환
    date_cols = ["CAREER_IN_DATE", "CAREER_OUT_DATE"]
    for col in date_cols:
        career_info_df_for_gsheet[col] = career_info_df_for_gsheet[col].dt.strftime(
            "%Y-%m-%d"
        )
    # 모든 컬럼을 문자열로 변환하고 정리
    for col in career_info_df_for_gsheet.columns:
        career_info_df_for_gsheet[col] = career_info_df_for_gsheet[col].astype(str)
    career_info_df_for_gsheet = career_info_df_for_gsheet.replace(
        {"None": "", "NaT": "", "nan": ""}
    )


# --- 결과 확인 (원본 DataFrame 출력) ---
career_info_df
