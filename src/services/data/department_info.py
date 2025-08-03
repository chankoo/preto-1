import pandas as pd
import numpy as np
from datetime import timedelta, datetime, date
import random

from services.data.departments import department_df
from services.data.basic_info import emp_df


# --- 11. DEPARTMENT INFO TABLE --- (부서정보)

# --- 1. 사전 준비 ---
random.seed(42)
np.random.seed(42)
today = datetime.now().date()
today_ts = pd.to_datetime(today)


# --- 2. 헬퍼 함수 정의 ---
def find_next_quarter_start(current_date):
    """주어진 날짜 이후의 가장 가까운 분기 시작일을 찾습니다."""
    if current_date.month < 4:
        return date(current_date.year, 4, 1)
    elif current_date.month < 7:
        return date(current_date.year, 7, 1)
    elif current_date.month < 10:
        return date(current_date.year, 10, 1)
    else:
        return date(current_date.year + 1, 1, 1)


parent_map = department_df.set_index("DEP_ID")["UP_DEP_ID"].to_dict()
dept_name_map = department_df.set_index("DEP_ID")["DEP_NAME"].to_dict()
dept_level_map = department_df.set_index("DEP_ID")["DEP_LEVEL"].to_dict()


def find_parents(dep_id):
    """부서 ID를 바탕으로 Division과 Office 이름을 찾는 함수"""
    path = {"DIVISION_NAME": None, "OFFICE_NAME": None}
    level = dept_level_map.get(dep_id)
    if not level:
        return pd.Series(path)

    current_id = dep_id
    if level == 4:  # Team
        office_id = parent_map.get(current_id)
        path["OFFICE_NAME"] = dept_name_map.get(office_id)
        if office_id:
            path["DIVISION_NAME"] = dept_name_map.get(parent_map.get(office_id))
    elif level == 3:  # Office
        path["OFFICE_NAME"] = dept_name_map.get(current_id)
        path["DIVISION_NAME"] = dept_name_map.get(parent_map.get(current_id))
    elif level == 2:  # Division
        path["DIVISION_NAME"] = dept_name_map.get(current_id)

    return pd.Series(path)


# --- 3. 1단계: 모든 직원의 기본 부서 배치 이력 생성 (분기별 이동) ---
base_assignment_records = []
assignable_departments_df = department_df[department_df["DEP_USE_YN"] == "Y"].copy()

if not assignable_departments_df.empty:
    for _, emp_row in emp_df.iterrows():
        emp_id, in_date, out_date = (
            emp_row["EMP_ID"],
            emp_row["IN_DATE"].date(),
            emp_row["OUT_DATE"].date() if pd.notna(emp_row["OUT_DATE"]) else None,
        )

        current_start_date = in_date
        num_assignments = random.randint(1, 5)
        last_dept_id = None

        for i in range(num_assignments):
            if (out_date and current_start_date > out_date) or (
                current_start_date > today
            ):
                break

            candidate_depts = assignable_departments_df
            if last_dept_id and random.random() < 0.70:
                last_dept_info = find_parents(last_dept_id)
                if last_dept_info["DIVISION_NAME"]:
                    div_members_df = department_df[
                        department_df["DEP_ID"].apply(find_parents)["DIVISION_NAME"]
                        == last_dept_info["DIVISION_NAME"]
                    ]
                    if not div_members_df.empty:
                        candidate_depts = div_members_df

            dept_row = candidate_depts.sample(n=1).iloc[0]

            end_date = None
            if i == num_assignments - 1:
                end_date = out_date
            else:
                # 다음 분기 시작일에 이동하도록 종료일 설정
                stay_duration = timedelta(days=random.randint(365, 2 * 365))
                next_move_date = find_next_quarter_start(
                    current_start_date + stay_duration
                )
                end_date = next_move_date - timedelta(days=1)

            if out_date and end_date > out_date:
                end_date = out_date
            if end_date and end_date > today:
                end_date = today

            base_assignment_records.append(
                {
                    "EMP_ID": emp_id,
                    "DEP_ID": dept_row["DEP_ID"],
                    "DEP_APP_START_DATE": current_start_date,
                    "DEP_APP_END_DATE": end_date,
                }
            )

            last_dept_id = dept_row["DEP_ID"]
            if end_date is None or end_date >= (out_date or today):
                break
            current_start_date = end_date + timedelta(days=1)

base_assignments_df = pd.DataFrame(base_assignment_records)
base_assignments_df["DEP_APP_START_DATE"] = pd.to_datetime(
    base_assignments_df["DEP_APP_START_DATE"]
)
base_assignments_df["DEP_APP_END_DATE"] = pd.to_datetime(
    base_assignments_df["DEP_APP_END_DATE"]
)

# --- 4. 2단계: 부서별, 기간별 부서장 선출 및 기록 단편화 ---
fragmented_records = []
emp_ages = (
    emp_df.set_index("EMP_ID")["PERSONAL_ID"]
    .apply(
        lambda pid: (
            today.year - (1900 + int(str(pid)[:2]))
            if str(pid)[7] in ["1", "2", "5", "6"]
            else 2000 + int(str(pid)[:2])
        )
    )
    .to_dict()
)

all_event_dates = sorted(
    pd.to_datetime(
        pd.concat(
            [
                base_assignments_df["DEP_APP_START_DATE"],
                base_assignments_df["DEP_APP_END_DATE"].dropna(),
            ]
        ).unique()
    )
)

for i in range(len(all_event_dates)):
    period_start = all_event_dates[i]
    period_end = (
        all_event_dates[i + 1] - timedelta(days=1)
        if i + 1 < len(all_event_dates)
        else today_ts
    )
    if period_start > period_end:
        continue

    active_assignments = base_assignments_df[
        (base_assignments_df["DEP_APP_START_DATE"] <= period_start)
        & (
            base_assignments_df["DEP_APP_END_DATE"].isnull()
            | (base_assignments_df["DEP_APP_END_DATE"] >= period_end)
        )
    ]

    for dep_id in active_assignments["DEP_ID"].unique():
        members_in_dept = active_assignments[active_assignments["DEP_ID"] == dep_id]
        member_ids = members_in_dept["EMP_ID"].tolist()
        if not member_ids:
            continue

        member_ages_df = pd.DataFrame(
            [{"EMP_ID": mid, "AGE": emp_ages.get(mid, 25)} for mid in member_ids]
        )
        head_id = member_ages_df.sort_values(
            by=["AGE", "EMP_ID"], ascending=[False, True]
        )["EMP_ID"].iloc[0]

        for emp_id in member_ids:
            fragmented_records.append(
                {
                    "EMP_ID": emp_id,
                    "DEP_ID": dep_id,
                    "TITLE_INFO": "Head" if emp_id == head_id else "Member",
                    "PERIOD_START": period_start,
                    "PERIOD_END": period_end,
                }
            )

# --- 5. 3단계: 연속된 기록 병합 ---
fragmented_df = pd.DataFrame(fragmented_records)
if not fragmented_df.empty:
    fragmented_df = fragmented_df.sort_values(
        ["EMP_ID", "DEP_ID", "TITLE_INFO", "PERIOD_START"]
    )
    group_ids = (
        (
            fragmented_df[["EMP_ID", "DEP_ID", "TITLE_INFO"]]
            != fragmented_df[["EMP_ID", "DEP_ID", "TITLE_INFO"]].shift()
        )
        .any(axis=1)
        .cumsum()
    )

    department_info_df = (
        fragmented_df.groupby(group_ids)
        .agg(
            EMP_ID=("EMP_ID", "first"),
            DEP_ID=("DEP_ID", "first"),
            TITLE_INFO=("TITLE_INFO", "first"),
            DEP_APP_START_DATE=("PERIOD_START", "min"),
            DEP_APP_END_DATE=("PERIOD_END", "max"),
        )
        .reset_index(drop=True)
    )
else:
    department_info_df = pd.DataFrame()

# --- 6. 원본 DataFrame (분석용) ---
if not department_info_df.empty:
    department_info_df = pd.merge(
        department_info_df,
        department_df[["DEP_ID", "DEPT_TYPE", "DEP_REL_START_DATE"]],
        on="DEP_ID",
        how="left",
    )
    department_info_df["MAIN_DEP"] = "Y"
    department_info_df["DEP_DURATION"] = (
        department_info_df["DEP_APP_END_DATE"]
        - department_info_df["DEP_APP_START_DATE"]
    ).dt.days

    final_cols = [
        "EMP_ID",
        "DEP_ID",
        "DEPT_TYPE",
        "DEP_REL_START_DATE",
        "DEP_APP_START_DATE",
        "DEP_APP_END_DATE",
        "MAIN_DEP",
        "TITLE_INFO",
        "DEP_DURATION",
    ]
    department_info_df = department_info_df.reindex(columns=final_cols)
    department_info_df["DEP_APP_END_DATE"] = department_info_df.apply(
        lambda row: (
            None
            if emp_df.loc[emp_df["EMP_ID"] == row["EMP_ID"], "CURRENT_EMP_YN"].iloc[0]
            == "Y"
            and row["DEP_APP_END_DATE"] == today_ts
            else row["DEP_APP_END_DATE"]
        ),
        axis=1,
    )

    # 요청하신 EMP_ID 순서로 최종 정렬
    department_info_df = department_info_df.sort_values(
        by=["EMP_ID", "DEP_APP_START_DATE"]
    ).reset_index(drop=True)

# # --- 7. Google Sheets용 복사본 생성 및 가공 ---
# department_info_df_for_gsheet = department_info_df.copy()
# if not department_info_df_for_gsheet.empty:
#     for col in date_cols:
#         department_info_df_for_gsheet[col] = department_info_df_for_gsheet[
#             col
#         ].dt.strftime("%Y-%m-%d")
#     for col in department_info_df_for_gsheet.columns:
#         department_info_df_for_gsheet[col] = department_info_df_for_gsheet[col].astype(
#             str
#         )
#     department_info_df_for_gsheet = department_info_df_for_gsheet.replace(
#         {"None": "", "NaT": "", "nan": ""}
#     )

# --- 결과 확인 (원본 DataFrame 출력) ---
department_info_df
