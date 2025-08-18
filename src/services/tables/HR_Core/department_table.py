#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import random

# ==============================================================================
# --- 1. DEPARTMENT TABLE (부서관리) ---
# ==============================================================================

# --- 1. 기본 정보 정의 ---
company_founding_date = datetime.date(2010, 1, 1)
base_structure = [
    # Level 1
    {"DEP_ID": "DEP001", "DEP_NAME": "Headquarters", "UP_DEP_ID": None, "DEPT_TYPE": "본사"},
    # Level 2: Divisions
    {"DEP_ID": "DEP002", "DEP_NAME": "Planning Division", "UP_DEP_ID": "DEP001", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP003", "DEP_NAME": "Development Division", "UP_DEP_ID": "DEP001", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP004", "DEP_NAME": "Sales Division", "UP_DEP_ID": "DEP001", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP005", "DEP_NAME": "Operating Division", "UP_DEP_ID": "DEP001", "DEPT_TYPE": "현장"},
    # Level 3: Offices
    {"DEP_ID": "DEP006", "DEP_NAME": "Strategy Office", "UP_DEP_ID": "DEP002", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP007", "DEP_NAME": "Finance Office", "UP_DEP_ID": "DEP002", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP008", "DEP_NAME": "R&D Office", "UP_DEP_ID": "DEP003", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP009", "DEP_NAME": "QA Office", "UP_DEP_ID": "DEP003", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP010", "DEP_NAME": "Marketing Office", "UP_DEP_ID": "DEP004", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP011", "DEP_NAME": "Domestic Sales Office", "UP_DEP_ID": "DEP004", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP012", "DEP_NAME": "Global Sales Office", "UP_DEP_ID": "DEP004", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP013", "DEP_NAME": "Engineering Office", "UP_DEP_ID": "DEP005", "DEPT_TYPE": "현장"},
    {"DEP_ID": "DEP014", "DEP_NAME": "Production Office", "UP_DEP_ID": "DEP005", "DEPT_TYPE": "현장"},
    # Level 4: Teams
    {"DEP_ID": "DEP015", "DEP_NAME": "Planning Team", "UP_DEP_ID": "DEP006", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP016", "DEP_NAME": "Analysis Team", "UP_DEP_ID": "DEP006", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP017", "DEP_NAME": "HR Team", "UP_DEP_ID": "DEP006", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP018", "DEP_NAME": "Accounting Team", "UP_DEP_ID": "DEP007", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP019", "DEP_NAME": "Treasury Team", "UP_DEP_ID": "DEP007", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP020", "DEP_NAME": "Backend Team", "UP_DEP_ID": "DEP008", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP021", "DEP_NAME": "Frontend Team", "UP_DEP_ID": "DEP008", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP022", "DEP_NAME": "Mobile Team", "UP_DEP_ID": "DEP008", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP023", "DEP_NAME": "System QA Team", "UP_DEP_ID": "DEP009", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP024", "DEP_NAME": "Service QA Team", "UP_DEP_ID": "DEP009", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP025", "DEP_NAME": "Performance Marketing Team", "UP_DEP_ID": "DEP010", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP026", "DEP_NAME": "Content Marketing Team", "UP_DEP_ID": "DEP010", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP027", "DEP_NAME": "Domestic Sales Team 1", "UP_DEP_ID": "DEP011", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP028", "DEP_NAME": "Domestic Sales Team 2", "UP_DEP_ID": "DEP011", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP029", "DEP_NAME": "APAC Sales Team", "UP_DEP_ID": "DEP012", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP030", "DEP_NAME": "EU/NA Sales Team", "UP_DEP_ID": "DEP012", "DEPT_TYPE": "본사"},
    {"DEP_ID": "DEP031", "DEP_NAME": "Process Engineering Team", "UP_DEP_ID": "DEP013", "DEPT_TYPE": "현장"},
    {"DEP_ID": "DEP032", "DEP_NAME": "Quality Engineering Team", "UP_DEP_ID": "DEP013", "DEPT_TYPE": "현장"},
    {"DEP_ID": "DEP033", "DEP_NAME": "Production Team Alpha", "UP_DEP_ID": "DEP014", "DEPT_TYPE": "현장"},
    {"DEP_ID": "DEP034", "DEP_NAME": "Production Team Beta", "UP_DEP_ID": "DEP014", "DEPT_TYPE": "현장"},
    {"DEP_ID": "DEP035", "DEP_NAME": "Production Team Charlie", "UP_DEP_ID": "DEP014", "DEPT_TYPE": "현장"},
]

# --- 2. 초기 DataFrame 생성 ---
departments = []
dep_dates = {"DEP001": company_founding_date}
for dep in base_structure:
    dep_id, up_id, dept_type = dep["DEP_ID"], dep["UP_DEP_ID"], dep["DEPT_TYPE"]
    if up_id is None:
        rel_start = company_founding_date
    else:
        parent_date = dep_dates.get(up_id, company_founding_date)
        rel_start = parent_date + timedelta(days=random.randint(0, 300))
    dep_dates[dep_id] = rel_start
    departments.append({
        "DEP_ID": dep_id, "DEP_NAME": dep["DEP_NAME"], "UP_DEP_ID": up_id, "DEPT_TYPE": dept_type,
        "DEP_REL_START_DATE": rel_start, "DEP_REL_END_DATE": None, "DEP_USE_YN": "Y"
    })
department_df = pd.DataFrame(departments)

# --- 3. DEP_LEVEL 컬럼 추가 ---
def calculate_dep_level(dep_id, p_map):
    level = 1
    current_id = dep_id
    while pd.notna(p_map.get(current_id)) and current_id in p_map:
        current_id = p_map.get(current_id)
        level += 1
        if level > 10: return -1
    return level

temp_parent_map = department_df.set_index('DEP_ID')['UP_DEP_ID'].to_dict()
dept_level_map_temp = {dep_id: calculate_dep_level(dep_id, temp_parent_map) for dep_id in department_df['DEP_ID']}
department_df['DEP_LEVEL'] = department_df['DEP_ID'].map(dept_level_map_temp)

# --- 4. 최종 데이터 타입 정리 ---
department_df['DEP_REL_START_DATE'] = pd.to_datetime(department_df['DEP_REL_START_DATE'])
department_df['DEP_REL_END_DATE'] = pd.to_datetime(department_df['DEP_REL_END_DATE'], errors='coerce')
department_df['DEP_LEVEL'] = department_df['DEP_LEVEL'].astype(int)
final_cols = ['DEP_ID', 'DEP_NAME', 'UP_DEP_ID', 'DEP_LEVEL', 'DEPT_TYPE', 'DEP_REL_START_DATE', 'DEP_REL_END_DATE', 'DEP_USE_YN']
department_df = department_df[final_cols]

# --- 5. Google Sheets용 복사본 생성 및 가공 ---
department_df_for_gsheet = department_df.copy()
department_df_for_gsheet['DEP_REL_START_DATE'] = department_df_for_gsheet['DEP_REL_START_DATE'].dt.strftime('%Y-%m-%d')
department_df_for_gsheet['DEP_REL_END_DATE'] = department_df_for_gsheet['DEP_REL_END_DATE'].dt.strftime('%Y-%m-%d')
for col in department_df_for_gsheet.columns:
    department_df_for_gsheet[col] = department_df_for_gsheet[col].astype(str)
department_df_for_gsheet = department_df_for_gsheet.replace({'None':'', 'nan':'', 'NaT':''})

# --- 6. 헬퍼 데이터/맵 생성 (다른 테이블/분석에서 사용) ---
parent_map_dept = department_df.set_index('DEP_ID')['UP_DEP_ID'].to_dict()
dept_name_map = department_df.set_index('DEP_ID')['DEP_NAME'].to_dict()
dept_level_map = department_df.set_index('DEP_ID')['DEP_LEVEL'].to_dict()
hq_id = 'DEP001'
division_order = ['Planning Division', 'Sales Division', 'Development Division', 'Operating Division']
office_order = [
    'Strategy Office', 'Finance Office', 'Planning Division (직속)',
    'Marketing Office', 'Domestic Sales Office', 'Global Sales Office', 'Sales Division (직속)',
    'R&D Office', 'QA Office', 'Development Division (직속)',
    'Engineering Office', 'Production Office', 'Operating Division (직속)'
]


# In[ ]:




