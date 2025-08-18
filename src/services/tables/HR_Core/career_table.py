#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import random

# ==============================================================================
# --- 6. CAREER TABLE (경력관리) ---
# ==============================================================================

# 재현성을 위한 시드 설정
random.seed(42)

# --- 1. 기본 데이터 정의 및 함수 ---
prefixes = [
    "Neo", "Hyper", "Quantum", "Alpha", "Next", "Blue", "Red", "Smart", "Core", "Bright",
    "Future", "Global", "Synergy", "Vertex", "Zenith", "Nova", "Stellar", "Dynamic", "Agile", "Pinnacle"
]
suffixes = [
    "Tech", "Systems", "Solutions", "Logics", "Networks", "Digital", "Soft", "Works", "Vision", "Cloud",
    "Dynamics", "Corp", "Group", "Labs", "Enterprises", "Data", "AI", "Insights", "Connect", "Innovations"
]

def generate_company_name():
    return random.choice(prefixes) + random.choice(suffixes)

# --- 2. 초기 DataFrame 생성 ---
total_companies = 120
domestic_count = int(total_companies * 0.83)
foreign_count = total_companies - domestic_count

ids = [f"CC{i+1:03}" for i in range(total_companies)]
random.shuffle(ids)

companies = []
used_names = set()
for i in range(total_companies):
    while True:
        name = generate_company_name()
        if name not in used_names:
            used_names.add(name)
            break

    is_domestic = "Y" if i < domestic_count else "N"

    company = {
        "CAREER_COMPANY_ID": ids[i],
        "CAREER_COMPANY_NAME": name,
        "CAREER_DOMESTIC_YN": is_domestic
    }
    companies.append(company)

# --- 3. 원본 DataFrame (분석용) ---
career_df = pd.DataFrame(companies)
career_df = career_df.sort_values(by='CAREER_COMPANY_ID', ascending=True).reset_index(drop=True)

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
career_df_for_gsheet = career_df.copy()
for col in career_df_for_gsheet.columns:
    career_df_for_gsheet[col] = career_df_for_gsheet[col].astype(str)
career_df_for_gsheet = career_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})


# In[ ]:




