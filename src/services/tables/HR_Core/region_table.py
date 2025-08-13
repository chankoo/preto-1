#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd

# ==============================================================================
# --- 9. REGION TABLE (지역관리) ---
# ==============================================================================

# --- 1. 기본 데이터 정의 ---
# 국내 지역 (광역시 및 도 기준)
domestic_regions = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원도",
    "충청북도", "충청남도", "전라북도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도"
]

# 해외 국가 예시
foreign_regions = [
    "United States", "Mexico", "Germany", "France",
    "Hungary", "China", "Vietnam", "Philippines"
]

# --- 2. 초기 DataFrame 생성 ---
regions = []
reg_counter = 1

for region in domestic_regions:
    regions.append({
        "REG_ID": f"R{reg_counter:03d}",
        "REG_NAME": region,
        "DOMESTIC_YN": "Y"
    })
    reg_counter += 1

for region in foreign_regions:
    regions.append({
        "REG_ID": f"R{reg_counter:03d}",
        "REG_NAME": region,
        "DOMESTIC_YN": "N"
    })
    reg_counter += 1

# --- 3. 원본 DataFrame (분석용) ---
region_df = pd.DataFrame(regions)

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
region_df_for_gsheet = region_df.copy()
for col in region_df_for_gsheet.columns:
    region_df_for_gsheet[col] = region_df_for_gsheet[col].astype(str)
region_df_for_gsheet = region_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

