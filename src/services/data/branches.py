#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import random


# In[ ]:


# --- 8. CORPORATION/BRANCH TABLE --- (법인/지사관리)

# --- 1. 기본 정보 및 헬퍼 함수 정의 ---
random.seed(42)

def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

start_date = datetime(2010, 1, 1)
end_date = datetime(2020, 12, 31)

corp_names = ["NeoTech", "KoreaDynamics", "BlueWave", "MetaSys"]
branch_pool = [
    "Seoul Branch", "Busan Branch", "Incheon Branch", "Jeju Branch",
    "Daejeon Branch", "Ulsan Branch"
]

# --- 2. 초기 DataFrame 생성 ---
# 법인 생성
corporation_entries = []
for i, name in enumerate(corp_names, start=1):
    corp_id = f"C{i:02d}"
    rel_start_date = random_date(start_date, end_date).date()
    corporation_entries.append({
        "CORP_ID": corp_id, "CORP_REL_START_DATE": rel_start_date,
        "CORP_NAME": name, "UP_CORP_ID": None, "CORP_USE_YN": "Y",
        "CORP_REL_END_DATE": None, "CORP_REG_LEVEL": "Corporation"
    })

# 지점 생성
branches = []
branch_id_counter = 1
selected_branches = random.sample(branch_pool, 6)
for name in selected_branches:
    branch_id = f"B{branch_id_counter:02d}"
    num_assignments = random.randint(1, 2)
    start_dates = sorted([random_date(start_date, end_date).date() for _ in range(num_assignments)])
    for i in range(num_assignments):
        assigned_corp = random.choice(corporation_entries)
        branches.append({
            "CORP_ID": branch_id, "CORP_REL_START_DATE": start_dates[i],
            "CORP_NAME": f"{assigned_corp['CORP_NAME']} {name}",
            "UP_CORP_ID": assigned_corp["CORP_ID"], "CORP_USE_YN": "Y",
            "CORP_REL_END_DATE": None, "CORP_REG_LEVEL": "Branch"
        })
    branch_id_counter += 1

corp_branch_df = pd.DataFrame(corporation_entries + branches)
corp_branch_df["SORT_KEY"] = corp_branch_df["CORP_REG_LEVEL"].apply(lambda x: 0 if x == "Corporation" else 1)
corp_branch_df = corp_branch_df.sort_values(by=["SORT_KEY", "CORP_ID", "CORP_REL_START_DATE"]).drop(columns=["SORT_KEY"])
corp_branch_df.reset_index(drop=True, inplace=True)
corp_branch_df['UP_CORP_ID'] = corp_branch_df['UP_CORP_ID'].replace({None: np.nan})

# --- 3. 원본 DataFrame (분석용) ---
# 날짜 컬럼을 datetime 타입으로 변환
corp_branch_df['CORP_REL_START_DATE'] = pd.to_datetime(corp_branch_df['CORP_REL_START_DATE'])
corp_branch_df['CORP_REL_END_DATE'] = pd.to_datetime(corp_branch_df['CORP_REL_END_DATE'], errors='coerce')


# --- 4. Google Sheets용 복사본 생성 및 가공 ---
corp_branch_df_for_gsheet = corp_branch_df.copy()
# 날짜를 'YYYY-MM-DD' 문자열로 변환
corp_branch_df_for_gsheet['CORP_REL_START_DATE'] = corp_branch_df_for_gsheet['CORP_REL_START_DATE'].dt.strftime('%Y-%m-%d')
corp_branch_df_for_gsheet['CORP_REL_END_DATE'] = corp_branch_df_for_gsheet['CORP_REL_END_DATE'].dt.strftime('%Y-%m-%d')

# 모든 컬럼을 문자열로 변환하고 정리
for col in corp_branch_df_for_gsheet.columns:
    corp_branch_df_for_gsheet[col] = corp_branch_df_for_gsheet[col].astype(str)
corp_branch_df_for_gsheet = corp_branch_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})


# --- 결과 확인 (원본 DataFrame 출력) ---
corp_branch_df

