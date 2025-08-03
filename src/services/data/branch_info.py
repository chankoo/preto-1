import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import random

from services.data.basic_info import emp_df
from services.data.branches import corp_branch_df

# --- 18. CORPORATION/BRANCH INFO TABLE --- (법인/지사정보)

# --- 1. 사전 준비 ---
# emp_df, corp_branch_df DataFrame이 로드되어 있다고 가정
random.seed(42)
np.random.seed(42)

corp_branch_info_records = []
today = datetime.now().date()
today_ts = pd.to_datetime(today)

# --- 2. 데이터 생성 ---
# corp_branch_df에서 할당 가능한 'Branch' 버전 목록 준비
assignable_cb_df = pd.DataFrame()
if not corp_branch_df.empty:
    temp_cb_df = corp_branch_df.copy()
    temp_cb_df["CORP_REL_START_DATE_DT"] = pd.to_datetime(
        temp_cb_df["CORP_REL_START_DATE"], errors="coerce"
    )
    temp_cb_df["CORP_REL_END_DATE_DT"] = pd.to_datetime(
        temp_cb_df["CORP_REL_END_DATE"], errors="coerce"
    )
    assignable_cb_df = temp_cb_df[
        (temp_cb_df["CORP_USE_YN"] == "Y") & (temp_cb_df["CORP_REG_LEVEL"] == "Branch")
    ].copy()

# 법인/지사 배정을 받을 직원 선택 (전체 직원의 10%)
num_total_employees = len(emp_df)
num_participating_employees_target = int(num_total_employees * 0.10)
participating_emp_df = pd.DataFrame()
if num_participating_employees_target > 0:
    emp_ids_with_assignments = (
        emp_df["EMP_ID"]
        .sample(
            n=min(num_participating_employees_target, num_total_employees),
            random_state=42,
        )
        .tolist()
    )
    participating_emp_df = emp_df[emp_df["EMP_ID"].isin(emp_ids_with_assignments)]

# 선택된 직원별 법인/지사 배정 이력 생성
if not participating_emp_df.empty and not assignable_cb_df.empty:
    for _, emp_row in participating_emp_df.iterrows():
        emp_id = emp_row["EMP_ID"]
        emp_in_date = emp_row["IN_DATE"].date()
        emp_out_date = (
            emp_row["OUT_DATE"].date() if pd.notna(emp_row["OUT_DATE"]) else None
        )
        emp_is_current_overall = emp_row["CURRENT_EMP_YN"] == "Y"

        num_assignments = random.randint(1, 2)
        earliest_next_app_start_date = emp_in_date

        for _ in range(num_assignments):
            if (
                earliest_next_app_start_date is None
                or (emp_out_date and earliest_next_app_start_date > emp_out_date)
                or (earliest_next_app_start_date > today)
            ):
                break

            candidate_cbs = assignable_cb_df[
                (
                    assignable_cb_df["CORP_REL_START_DATE_DT"]
                    <= pd.to_datetime(earliest_next_app_start_date)
                )
                & (
                    pd.isna(assignable_cb_df["CORP_REL_END_DATE_DT"])
                    | (
                        assignable_cb_df["CORP_REL_END_DATE_DT"]
                        >= pd.to_datetime(earliest_next_app_start_date)
                    )
                )
            ]
            if candidate_cbs.empty:
                break

            selected_cb = candidate_cbs.sample(n=1).iloc[0]
            corp_id = selected_cb["CORP_ID"]
            corp_rel_start = selected_cb["CORP_REL_START_DATE_DT"].date()
            corp_rel_end = (
                selected_cb["CORP_REL_END_DATE_DT"].date()
                if pd.notna(selected_cb["CORP_REL_END_DATE_DT"])
                else None
            )

            app_start = max(earliest_next_app_start_date, corp_rel_start) + timedelta(
                days=random.randint(0, 30)
            )
            if (
                (corp_rel_end and app_start > corp_rel_end)
                or (emp_out_date and app_start > emp_out_date)
                or (app_start > today)
            ):
                earliest_next_app_start_date = None
                break

            stay_duration = timedelta(days=random.randint(365, 4 * 365))
            potential_end_date = app_start + stay_duration
            upper_bound_date = min(
                d for d in [corp_rel_end, emp_out_date, today] if d is not None
            )

            app_end = None
            if potential_end_date > today:
                if emp_is_current_overall and (
                    corp_rel_end is None or corp_rel_end > today
                ):
                    app_end = None
                else:
                    app_end = upper_bound_date
            else:
                app_end = min(potential_end_date, upper_bound_date)

            if app_end and app_start > app_end:
                continue

            duration_days = (
                pd.to_datetime(app_end or today) - pd.to_datetime(app_start)
            ).days

            corp_branch_info_records.append(
                {
                    "EMP_ID": emp_id,
                    "CORP_ID": corp_id,
                    "CORP_REL_START_DATE": corp_rel_start,
                    "CORP_APP_START_DATE": app_start,
                    "CORP_APP_END_DATE": app_end,
                    "CORP_DURATION": duration_days,
                }
            )

            if app_end is None:
                break
            else:
                earliest_next_app_start_date = app_end + timedelta(
                    days=random.randint(30, 90)
                )

# --- 3. 원본 DataFrame (분석용) ---
corp_branch_info_df = pd.DataFrame(corp_branch_info_records)
# 날짜 컬럼들을 datetime 타입으로 변환
if not corp_branch_info_df.empty:
    date_cols = ["CORP_REL_START_DATE", "CORP_APP_START_DATE", "CORP_APP_END_DATE"]
    for col in date_cols:
        corp_branch_info_df[col] = pd.to_datetime(
            corp_branch_info_df[col], errors="coerce"
        )


# --- 4. Google Sheets용 복사본 생성 및 가공 ---
corp_branch_info_df_for_gsheet = corp_branch_info_df.copy()
if not corp_branch_info_df_for_gsheet.empty:
    # 날짜를 'YYYY-MM-DD' 문자열로 변환
    for col in date_cols:
        corp_branch_info_df_for_gsheet[col] = corp_branch_info_df_for_gsheet[
            col
        ].dt.strftime("%Y-%m-%d")
    # 모든 컬럼을 문자열로 변환하고 정리
    for col in corp_branch_info_df_for_gsheet.columns:
        corp_branch_info_df_for_gsheet[col] = corp_branch_info_df_for_gsheet[
            col
        ].astype(str)
    corp_branch_info_df_for_gsheet = corp_branch_info_df_for_gsheet.replace(
        {"None": "", "NaT": "", "nan": ""}
    )


# --- 결과 확인 (원본 DataFrame 출력) ---
corp_branch_info_df
