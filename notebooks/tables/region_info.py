import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import random

from services.data.regions import region_df
from services.data.basic_info import emp_df
from services.data.department_info import department_info_df

# --- 19. REGION INFO TABLE --- (지역정보)

# --- 1. 사전 준비 ---
# 모든 관련 DataFrame이 로드되어 있다고 가정
random.seed(42)
np.random.seed(42)

region_info_records = []
today = datetime.now().date()
today_ts = pd.to_datetime(today)

# --- 2. 헬퍼 데이터 준비 ---
# 원본 DataFrame의 datetime 타입을 사용하므로 _DT 컬럼 불필요
# department_info_df 생성 시 DEPT_TYPE이 이미 포함되었다고 가정

seoul_reg_id, field_region_ids = None, []
if not region_df.empty:
    seoul_row = region_df[region_df["REG_NAME"] == "서울특별시"]
    if not seoul_row.empty:
        seoul_reg_id = seoul_row["REG_ID"].iloc[0]
        field_region_ids = region_df[region_df["REG_ID"] != seoul_reg_id][
            "REG_ID"
        ].tolist()

if not seoul_reg_id or not field_region_ids:
    print("경고: 서울 또는 현장 지역 ID가 준비되지 않았습니다.")

# --- 3. 직원별 근무 지역 이력 생성 ---
for _, emp_row in emp_df.iterrows():
    emp_id = emp_row["EMP_ID"]
    emp_in_date = emp_row["IN_DATE"].date()
    emp_out_date = emp_row["OUT_DATE"].date() if pd.notna(emp_row["OUT_DATE"]) else None
    emp_is_current_overall = emp_row["CURRENT_EMP_YN"] == "Y"

    emp_dept_history = department_info_df[
        department_info_df["EMP_ID"] == emp_id
    ].sort_values(by="DEP_APP_START_DATE")
    if emp_dept_history.empty:
        continue

    first_dept_type = emp_dept_history.iloc[0]["DEPT_TYPE"]
    base_region_id = (
        seoul_reg_id if first_dept_type == "본사" else random.choice(field_region_ids)
    )

    current_assignment_start_date = emp_in_date
    simulation_cursor_date = emp_in_date

    while True:
        effective_end_date = (
            emp_out_date if emp_out_date and emp_out_date <= today else today
        )
        if simulation_cursor_date >= effective_end_date:
            break

        if random.random() < 0.04 and field_region_ids:
            event_start_date = simulation_cursor_date + timedelta(
                days=random.randint(90, 365)
            )
            if event_start_date >= effective_end_date:
                break

            base_end_date = event_start_date - timedelta(days=1)
            if base_end_date >= current_assignment_start_date:
                duration = (base_end_date - current_assignment_start_date).days
                region_info_records.append(
                    {
                        "EMP_ID": emp_id,
                        "REG_ID": base_region_id,
                        "REG_APP_START_DATE": current_assignment_start_date,
                        "REG_APP_END_DATE": base_end_date,
                        "REG_APP_CATEGORY": (
                            "기본소속"
                            if base_region_id == seoul_reg_id
                            else "소속지역변경"
                        ),
                        "REG_DURATION": duration,
                    }
                )

            dept_at_event_time = emp_dept_history[
                emp_dept_history["DEP_APP_START_DATE"]
                <= pd.to_datetime(event_start_date)
            ].iloc[-1]
            emp_dept_type = dept_at_event_time["DEPT_TYPE"]

            target_region_id, event_category, event_duration_days = None, None, 0
            if emp_dept_type == "본사":
                event_category = "장기출장"
                target_region_id = random.choice(field_region_ids)
                event_duration_days = random.randint(30, 180)
            else:
                if random.random() < 0.7:
                    event_category = "장기출장"
                    target_region_id = seoul_reg_id
                    event_duration_days = random.randint(30, 180)
                else:
                    event_category = "소속지역변경"
                    available_fields = [
                        r for r in field_region_ids if r != base_region_id
                    ]
                    target_region_id = (
                        random.choice(available_fields)
                        if available_fields
                        else field_region_ids[0]
                    )
                    event_duration_days = random.randint(181, 365 * 3)

            event_end_date = event_start_date + timedelta(days=event_duration_days - 1)
            final_event_end_date = min(event_end_date, effective_end_date)

            if (
                emp_is_current_overall
                and final_event_end_date == today
                and event_end_date > today
            ):
                final_event_end_date = None
            if final_event_end_date and event_start_date > final_event_end_date:
                simulation_cursor_date = event_start_date + timedelta(days=1)
                continue

            event_duration = (
                pd.to_datetime(final_event_end_date or today)
                - pd.to_datetime(event_start_date)
            ).days
            region_info_records.append(
                {
                    "EMP_ID": emp_id,
                    "REG_ID": target_region_id,
                    "REG_APP_START_DATE": event_start_date,
                    "REG_APP_END_DATE": final_event_end_date,
                    "REG_APP_CATEGORY": event_category,
                    "REG_DURATION": event_duration,
                }
            )

            if final_event_end_date is None:
                break
            simulation_cursor_date = final_event_end_date + timedelta(days=1)
            current_assignment_start_date = simulation_cursor_date
            if event_category == "소속지역변경":
                base_region_id = target_region_id
        else:
            simulation_cursor_date += timedelta(days=365)

    if current_assignment_start_date <= effective_end_date:
        final_base_end_date = emp_out_date if not emp_is_current_overall else None
        if final_base_end_date and final_base_end_date > today:
            final_base_end_date = today
        if not (
            final_base_end_date and current_assignment_start_date > final_base_end_date
        ):
            duration = (
                pd.to_datetime(final_base_end_date or today)
                - pd.to_datetime(current_assignment_start_date)
            ).days
            region_info_records.append(
                {
                    "EMP_ID": emp_id,
                    "REG_ID": base_region_id,
                    "REG_APP_START_DATE": current_assignment_start_date,
                    "REG_APP_END_DATE": final_base_end_date,
                    "REG_APP_CATEGORY": (
                        "기본소속" if base_region_id == seoul_reg_id else "소속지역변경"
                    ),
                    "REG_DURATION": duration,
                }
            )

# --- 4. 원본 DataFrame (분석용) ---
region_info_df = pd.DataFrame(region_info_records)
# 날짜 컬럼들을 datetime 타입으로 변환
if not region_info_df.empty:
    date_cols = ["REG_APP_START_DATE", "REG_APP_END_DATE"]
    for col in date_cols:
        region_info_df[col] = pd.to_datetime(region_info_df[col], errors="coerce")


# --- 5. Google Sheets용 복사본 생성 및 가공 ---
region_info_df_for_gsheet = region_info_df.copy()
if not region_info_df_for_gsheet.empty:
    # 날짜를 'YYYY-MM-DD' 문자열로 변환
    date_cols = ["REG_APP_START_DATE", "REG_APP_END_DATE"]
    for col in date_cols:
        region_info_df_for_gsheet[col] = region_info_df_for_gsheet[col].dt.strftime(
            "%Y-%m-%d"
        )
    # 모든 컬럼을 문자열로 변환하고 정리
    for col in region_info_df_for_gsheet.columns:
        region_info_df_for_gsheet[col] = region_info_df_for_gsheet[col].astype(str)
    region_info_df_for_gsheet = region_info_df_for_gsheet.replace(
        {"None": "", "NaT": "", "nan": ""}
    )


# --- 결과 확인 (원본 DataFrame 출력) ---
region_info_df
