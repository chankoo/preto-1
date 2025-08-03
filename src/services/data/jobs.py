#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np


# In[ ]:


# --- 3. JOB TABLE --- (직무관리)

# --- 1. 직무 계층 구조 정의 ---
job_hierarchy = [
    # IT
    {"JOB_ID": "JOB001", "JOB_NAME": "IT", "UP_JOB_ID": None, "JOB_LEVEL": 1},
    {"JOB_ID": "JOB002", "JOB_NAME": "SW Developer", "UP_JOB_ID": "JOB001", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB003", "JOB_NAME": "Backend Developer", "UP_JOB_ID": "JOB002", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB004", "JOB_NAME": "Frontend Developer", "UP_JOB_ID": "JOB002", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB005", "JOB_NAME": "Mobile Developer", "UP_JOB_ID": "JOB002", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB006", "JOB_NAME": "Infrastructure", "UP_JOB_ID": "JOB001", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB007", "JOB_NAME": "DevOps Engineer", "UP_JOB_ID": "JOB006", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB008", "JOB_NAME": "Data Scientist", "UP_JOB_ID": "JOB001", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB009", "JOB_NAME": "Data Analyst", "UP_JOB_ID": "JOB008", "JOB_LEVEL": 3},

    # HR & Finance
    {"JOB_ID": "JOB010", "JOB_NAME": "Management Support", "UP_JOB_ID": None, "JOB_LEVEL": 1},
    {"JOB_ID": "JOB011", "JOB_NAME": "HR", "UP_JOB_ID": "JOB010", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB012", "JOB_NAME": "Recruiter", "UP_JOB_ID": "JOB011", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB013", "JOB_NAME": "HR Generalist", "UP_JOB_ID": "JOB011", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB014", "JOB_NAME": "Finance", "UP_JOB_ID": "JOB010", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB015", "JOB_NAME": "Accountant", "UP_JOB_ID": "JOB014", "JOB_LEVEL": 3},

    # Sales & Marketing
    {"JOB_ID": "JOB016", "JOB_NAME": "Sales & Marketing", "UP_JOB_ID": None, "JOB_LEVEL": 1},
    {"JOB_ID": "JOB017", "JOB_NAME": "Marketing", "UP_JOB_ID": "JOB016", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB018", "JOB_NAME": "Performance Marketer", "UP_JOB_ID": "JOB017", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB019", "JOB_NAME": "Content Marketer", "UP_JOB_ID": "JOB017", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB020", "JOB_NAME": "Sales", "UP_JOB_ID": "JOB016", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB021", "JOB_NAME": "Sales Manager", "UP_JOB_ID": "JOB020", "JOB_LEVEL": 3},

    # Planning
    {"JOB_ID": "JOB022", "JOB_NAME": "Planning", "UP_JOB_ID": None, "JOB_LEVEL": 1},
    {"JOB_ID": "JOB023", "JOB_NAME": "Business Planning", "UP_JOB_ID": "JOB022", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB024", "JOB_NAME": "Strategic Planner", "UP_JOB_ID": "JOB023", "JOB_LEVEL": 3},

    # Production & Engineering
    {"JOB_ID": "JOB025", "JOB_NAME": "Production & Engineering", "UP_JOB_ID": None, "JOB_LEVEL": 1},
    {"JOB_ID": "JOB026", "JOB_NAME": "Production Management", "UP_JOB_ID": "JOB025", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB027", "JOB_NAME": "Production Manager", "UP_JOB_ID": "JOB026", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB028", "JOB_NAME": "Engineering", "UP_JOB_ID": "JOB025", "JOB_LEVEL": 2},
    {"JOB_ID": "JOB029", "JOB_NAME": "Process Engineer", "UP_JOB_ID": "JOB028", "JOB_LEVEL": 3},
    {"JOB_ID": "JOB030", "JOB_NAME": "QA Engineer", "UP_JOB_ID": "JOB028", "JOB_LEVEL": 3},
]

# --- 2. 초기 DataFrame 생성 ---
job_df = pd.DataFrame(job_hierarchy)
# UP_JOB_ID의 None 값을 np.nan으로 변경하여 일관성 유지
job_df['UP_JOB_ID'] = job_df['UP_JOB_ID'].replace({None: np.nan})

# --- 3. JOB_CONN 컬럼 추가 (전체 경로 생성) ---
id_to_name = job_df.set_index("JOB_ID")["JOB_NAME"].to_dict()
id_to_parent = job_df.set_index("JOB_ID")["UP_JOB_ID"].to_dict()

def build_conn(job_id):
    names = []
    current_id = job_id
    while pd.notna(current_id):
        names.insert(0, id_to_name.get(current_id, ''))
        current_id = id_to_parent.get(current_id)
    return " - ".join(filter(None, names))

job_df["JOB_CONN"] = job_df["JOB_ID"].apply(build_conn)

# --- 4. 최종 데이터 타입 정리 ---
# 원본 DataFrame (분석용)
# JOB_LEVEL은 숫자형(int)으로 유지
job_df['JOB_LEVEL'] = job_df['JOB_LEVEL'].astype(int)

# --- 5. Google Sheets용 복사본 생성 및 가공 ---
job_df_for_gsheet = job_df.copy()
# 모든 컬럼을 문자열로 변환하고 정리
for col in job_df_for_gsheet.columns:
    job_df_for_gsheet[col] = job_df_for_gsheet[col].astype(str)
job_df_for_gsheet = job_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

# --- 결과 확인 (원본 DataFrame 출력) ---
job_df

