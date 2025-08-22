#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd

# ==============================================================================
# --- 2. POSITION TABLE (직위/직급관리) ---
# ==============================================================================

# --- 1. 기본 데이터 정의 ---
position_data = [
    {"POSITION_ID": "POS001", "POSITION_NAME": "Staff", "GRADES": [("G1", "Staff Grade 1"), ("G2", "Staff Grade 2")]},
    {"POSITION_ID": "POS002", "POSITION_NAME": "Manager", "GRADES": [("G3", "Manager Grade 1"), ("G4", "Manager Grade 2")]},
    {"POSITION_ID": "POS003", "POSITION_NAME": "Director", "GRADES": [("G5", "Director Grade 1"), ("G6", "Director Grade 2")]},
    {"POSITION_ID": "POS004", "POSITION_NAME": "C-Level", "GRADES": [("G7", "Executive Grade")]}
]

# --- 2. 초기 DataFrame 생성 ---
position_rows = []
for pos in position_data:
    for grade_id, grade_name in pos["GRADES"]:
        row = {
            "POSITION_ID": pos["POSITION_ID"],
            "GRADE_ID": grade_id,
            "POSITION_NAME": pos["POSITION_NAME"],
            "GRADE_NAME": grade_name,
            "POSITION_CONN": f"{pos['POSITION_NAME']} - {grade_id}"
        }
        position_rows.append(row)

# --- 3. 원본 DataFrame (분석용) ---
position_df = pd.DataFrame(position_rows)

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
position_df_for_gsheet = position_df.copy()
for col in position_df_for_gsheet.columns:
    position_df_for_gsheet[col] = position_df_for_gsheet[col].astype(str)
position_df_for_gsheet = position_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

# --- 5. 헬퍼 데이터 생성 (다른 테이블/분석에서 사용) ---
position_order = ['Staff', 'Manager', 'Director', 'C-Level']
grade_order = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7']


# In[ ]:




