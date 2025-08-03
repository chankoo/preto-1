import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import random

from services.data.absences import absence_df
from services.data.basic_info import emp_df

# --- 20. CONTRACT INFO TABLE --- (계약정보)

# --- 1. 사전 준비 ---
# emp_df DataFrame이 로드되어 있다고 가정
random.seed(42)
np.random.seed(42)

contract_info_records = []
today = datetime.now().date()
today_ts = pd.to_datetime(today)

# --- 2. 직원별 계약 이력 생성 ---
for _, emp_row in emp_df.iterrows():
    emp_id = emp_row["EMP_ID"]
    try:
        emp_in_date = emp_row["IN_DATE"].date()
        emp_out_date = (
            emp_row["OUT_DATE"].date() if pd.notna(emp_row["OUT_DATE"]) else None
        )
    except Exception as e:
        continue

    emp_is_current = emp_row["CURRENT_EMP_YN"] == "Y"

    current_start_date = emp_in_date
    contract_type = "정규직" if random.random() < 0.70 else "계약직"

    while True:
        if (emp_out_date and current_start_date > emp_out_date) or (
            current_start_date > today
        ):
            break

        if contract_type == "정규직":
            end_date = emp_out_date
            duration = (
                pd.to_datetime(end_date or today) - pd.to_datetime(current_start_date)
            ).days

            contract_info_records.append(
                {
                    "EMP_ID": emp_id,
                    "CONT_START_DATE": current_start_date,
                    "CONT_CATEGORY": "정규직",
                    "CONT_END_DATE": end_date,
                    "CONT_DURATION": duration,
                }
            )
            break

        elif contract_type == "계약직":
            duration_days = random.randint(365, 2 * 365)
            potential_end_date = current_start_date + timedelta(days=duration_days - 1)

            upper_bound_date = min(d for d in [emp_out_date, today] if d is not None)

            end_date = None
            if potential_end_date > today:
                if emp_is_current and (emp_out_date is None or emp_out_date > today):
                    end_date = None
                else:
                    end_date = upper_bound_date
            else:
                end_date = min(potential_end_date, upper_bound_date)

            duration = (
                pd.to_datetime(end_date or today) - pd.to_datetime(current_start_date)
            ).days

            contract_info_records.append(
                {
                    "EMP_ID": emp_id,
                    "CONT_START_DATE": current_start_date,
                    "CONT_CATEGORY": "계약직",
                    "CONT_END_DATE": end_date,
                    "CONT_DURATION": duration,
                }
            )

            if end_date is None or (emp_out_date and end_date == emp_out_date):
                break
            else:
                current_start_date = end_date + timedelta(days=1)
                contract_type = "정규직" if random.random() < 0.60 else "계약직"

# --- 3. 원본 DataFrame (분석용) ---
contract_info_df = pd.DataFrame(contract_info_records)
# 날짜 컬럼들을 datetime 타입으로 변환
if not contract_info_df.empty:
    date_cols = ["CONT_START_DATE", "CONT_END_DATE"]
    for col in date_cols:
        contract_info_df[col] = pd.to_datetime(contract_info_df[col], errors="coerce")


# --- 4. Google Sheets용 복사본 생성 및 가공 ---
contract_info_df_for_gsheet = contract_info_df.copy()
if not contract_info_df_for_gsheet.empty:
    # 날짜를 'YYYY-MM-DD' 문자열로 변환
    date_cols = ["CONT_START_DATE", "CONT_END_DATE"]
    for col in date_cols:
        contract_info_df_for_gsheet[col] = contract_info_df_for_gsheet[col].dt.strftime(
            "%Y-%m-%d"
        )

    # 모든 컬럼을 문자열로 변환하고 정리
    for col in contract_info_df_for_gsheet.columns:
        contract_info_df_for_gsheet[col] = contract_info_df_for_gsheet[col].astype(str)
    contract_info_df_for_gsheet = contract_info_df_for_gsheet.replace(
        {"None": "", "NaT": "", "nan": ""}
    )


# --- 결과 확인 (원본 DataFrame 출력) ---
contract_info_df
