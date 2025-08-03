import pandas as pd
import numpy as np
from datetime import timedelta, datetime, date
import random

from services.data.positions import position_df
from services.data.basic_info import emp_df
from services.data.department_info import (
    department_info_df,
    find_parents,
    dept_level_map,
    parent_map,
    dept_name_map,
)

# --- 1. 사전 준비 ---
# 모든 관련 DataFrame이 로드되어 있다고 가정
random.seed(42)
np.random.seed(42)

# --- 2. 헬퍼 데이터 및 함수 준비 ---
position_info_records = []
today = datetime.now().date()
today_ts = pd.to_datetime(today)

if not position_df.empty:
    ordered_grades = sorted(position_df["GRADE_ID"].unique())
    grade_to_position_map = pd.Series(
        position_df.POSITION_ID.values, index=position_df.GRADE_ID
    ).to_dict()
else:
    ordered_grades = []
    grade_to_position_map = {}

# --- 2-1. 부서 경로 탐색을 위한 헬퍼 함수 및 데이터 ---
pass


# --- 2-2. 직원별 첫 부서 정보 미리 준비 ---
emp_first_dept = (
    department_info_df.sort_values("DEP_APP_START_DATE")
    .groupby("EMP_ID")
    .first()
    .reset_index()
)
parent_info = emp_first_dept["DEP_ID"].apply(find_parents)
emp_first_dept = pd.concat([emp_first_dept, parent_info], axis=1)
emp_first_dept_map = emp_first_dept.set_index("EMP_ID")[
    ["DIVISION_NAME", "OFFICE_NAME"]
].to_dict("index")

# --- 2-3. 퇴사자 중 '승진 정체 그룹' 선정 ---
leavers_df = emp_df[emp_df["CURRENT_EMP_YN"] == "N"]
late_promotion_leaver_ids = set(leavers_df.sample(frac=0.5, random_state=21)["EMP_ID"])


# --- 3. 직원별 직위/직급 이력 생성 ---
for _, emp_row in emp_df.iterrows():
    emp_id = emp_row["EMP_ID"]
    emp_in_date = emp_row["IN_DATE"].date()
    emp_out_date = emp_row["OUT_DATE"].date() if pd.notna(emp_row["OUT_DATE"]) else None
    emp_is_current = emp_row["CURRENT_EMP_YN"] == "Y"

    if not ordered_grades:
        continue

    # --- 수정된 부분: 부서 특성 및 나이에 따른 초기 직급 결정 ---
    emp_start_org = emp_first_dept_map.get(emp_id, {})
    start_division = emp_start_org.get("DIVISION_NAME")
    start_office = emp_start_org.get("OFFICE_NAME")

    try:
        birth_yy = int(str(emp_row["PERSONAL_ID"])[:2])
        gender_code = str(emp_row["PERSONAL_ID"])[7]
        birth_year = (
            (1900 + birth_yy)
            if gender_code in ["1", "2", "5", "6"]
            else (2000 + birth_yy)
        )
        age_at_hire = emp_in_date.year - birth_year
    except:
        age_at_hire = 28

    # 부서 특성에 따라 나이대별 확률 조정
    if start_office == "Production Office":
        if age_at_hire < 32:
            probs = [0.70, 0.25, 0.05, 0, 0, 0]
        elif age_at_hire < 38:
            probs = [0.10, 0.60, 0.25, 0.05, 0, 0]
        else:
            probs = [0, 0.10, 0.60, 0.25, 0.05, 0]
    elif start_division == "Development Division":
        if age_at_hire < 27:
            probs = [0.60, 0.35, 0.05, 0, 0, 0]
        elif age_at_hire < 32:
            probs = [0.10, 0.50, 0.35, 0.05, 0, 0]
        else:
            probs = [0, 0.10, 0.50, 0.35, 0.05, 0]
    else:  # 그 외 모든 부서
        if age_at_hire < 28:
            probs = [0.70, 0.25, 0.05, 0, 0, 0]
        elif age_at_hire < 35:
            probs = [0.10, 0.60, 0.25, 0.05, 0, 0]
        else:
            probs = [0, 0.10, 0.60, 0.25, 0.05, 0]

    valid_grades = ["G1", "G2", "G3", "G4", "G5", "G6"]
    chosen_initial_grade = random.choices(valid_grades, weights=probs, k=1)[0]
    # --- 수정 완료 ---

    current_grade_list_idx = ordered_grades.index(chosen_initial_grade)

    employee_grade_progression_records = []
    current_assignment_flow_date = emp_in_date
    date_entered_current_pos_id_spell = None
    last_recorded_pos_id = None
    change_reason = "Initial Assignment"
    promotion_type = ""

    while True:  # (이하 승진 시뮬레이션 로직은 이전과 동일)
        if (emp_out_date and current_assignment_flow_date > emp_out_date) or (
            current_assignment_flow_date > today
        ):
            break
        if current_grade_list_idx >= len(ordered_grades):
            break

        grade_id = ordered_grades[current_grade_list_idx]
        position_id = grade_to_position_map[grade_id]
        grade_start_date = current_assignment_flow_date

        if position_id != last_recorded_pos_id:
            position_start_date = grade_start_date
            date_entered_current_pos_id_spell = position_start_date
        else:
            position_start_date = date_entered_current_pos_id_spell

        grade_end_date, next_assignment_date = None, None
        is_max_grade = current_grade_list_idx == len(ordered_grades) - 1
        if is_max_grade:
            grade_end_date = emp_out_date if not emp_is_current else None
        else:
            is_late_promotion_target = emp_id in late_promotion_leaver_ids
            if is_late_promotion_target and random.random() < 0.7:
                duration_choice = 0.9
            else:
                duration_choice = random.random()

            if duration_choice < 0.20:
                stay_days = random.randint(700, 1000)
                promotion_type = "Early Promotion"
            elif duration_choice < 0.80:
                stay_days = random.randint(1001, 2000)
                promotion_type = "Normal Promotion"
            else:
                stay_days = random.randint(2001, 2500)
                promotion_type = "Late Promotion"

            eligibility_date = grade_start_date + timedelta(days=stay_days)
            eligibility_year = eligibility_date.year
            if eligibility_date <= date(eligibility_year, 7, 1):
                next_assignment_date = date(eligibility_year, 7, 1)
            else:
                next_assignment_date = date(eligibility_year + 1, 1, 1)

            potential_grade_end_date = next_assignment_date - timedelta(days=1)

            if next_assignment_date > today:
                if emp_is_current and (emp_out_date is None or emp_out_date > today):
                    grade_end_date = None
                else:
                    grade_end_date = min(emp_out_date if emp_out_date else today, today)
                next_assignment_date = None
            else:
                grade_end_date = potential_grade_end_date
                if emp_out_date and grade_end_date >= emp_out_date:
                    grade_end_date, next_assignment_date = emp_out_date, None

        employee_grade_progression_records.append(
            {
                "EMP_ID": emp_id,
                "POSITION_ID": position_id,
                "GRADE_ID": grade_id,
                "POSITION_START_DATE": position_start_date,
                "GRADE_START_DATE": grade_start_date,
                "POSITION_END_DATE": None,
                "GRADE_END_DATE": grade_end_date,
                "CHANGE_REASON": change_reason,
            }
        )

        last_recorded_pos_id = position_id
        if next_assignment_date is None:
            break
        current_assignment_flow_date, change_reason = (
            next_assignment_date,
            promotion_type,
        )
        current_grade_list_idx += 1

    # 2차 패스
    for j in range(len(employee_grade_progression_records)):
        record = employee_grade_progression_records[j]
        current_pos_id = record["POSITION_ID"]
        pos_end_date = record["GRADE_END_DATE"]
        for k in range(j + 1, len(employee_grade_progression_records)):
            if employee_grade_progression_records[k]["POSITION_ID"] == current_pos_id:
                pos_end_date = employee_grade_progression_records[k]["GRADE_END_DATE"]
            else:
                break
        record["POSITION_END_DATE"] = pos_end_date
        gs_date = record["GRADE_START_DATE"]
        ge_date = record["GRADE_END_DATE"]
        record["GRADE_DURATION"] = None
        if pd.notna(gs_date):
            gs_ts = pd.to_datetime(gs_date)
            if pd.notna(ge_date):
                record["GRADE_DURATION"] = (pd.to_datetime(ge_date) - gs_ts).days
            elif (
                emp_is_current
                and j == len(employee_grade_progression_records) - 1
                and ge_date is None
            ):
                record["GRADE_DURATION"] = (today_ts - gs_ts).days
        position_info_records.append(record)

# --- 4. 원본 DataFrame (분석용) ---
position_info_df = pd.DataFrame(position_info_records)
if not position_info_df.empty:
    date_cols = [
        "POSITION_START_DATE",
        "GRADE_START_DATE",
        "POSITION_END_DATE",
        "GRADE_END_DATE",
    ]
    for col in date_cols:
        position_info_df[col] = pd.to_datetime(position_info_df[col], errors="coerce")

# --- 5. Google Sheets용 복사본 생성 및 가공 ---
position_info_df_for_gsheet = position_info_df.copy()
if not position_info_df_for_gsheet.empty:
    date_cols = [
        "POSITION_START_DATE",
        "GRADE_START_DATE",
        "POSITION_END_DATE",
        "GRADE_END_DATE",
    ]
    for col in date_cols:
        position_info_df_for_gsheet[col] = position_info_df_for_gsheet[col].dt.strftime(
            "%Y-%m-%d"
        )
    for col in position_info_df_for_gsheet.columns:
        position_info_df_for_gsheet[col] = position_info_df_for_gsheet[col].astype(str)
    position_info_df_for_gsheet = position_info_df_for_gsheet.replace(
        {"None": "", "NaT": "", "nan": ""}
    )

# --- 결과 확인 (원본 DataFrame 출력) ---
position_info_df
