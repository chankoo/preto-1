#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import random


# In[ ]:


# --- 7. SCHOOL TABLE --- (학력관리) - User Specified Revision

# 재현성을 위한 시드 설정
random.seed(42)

# --- 1. 기본 정보 및 데이터 목록 정의 ---
korean_universities_4yr = [
    "서울대학교", "연세대학교", "고려대학교", "카이스트", "포항공과대학교", "서강대학교",
    "성균관대학교", "한양대학교", "경희대학교", "이화여자대학교", "중앙대학교", "한국외국어대학교",
    "서울시립대학교", "건국대학교", "동국대학교", "홍익대학교", "국민대학교", "숭실대학교",
    "세종대학교", "단국대학교", "인하대학교", "아주대학교", "부산대학교", "경북대학교",
    "전남대학교", "전북대학교", "충남대학교", "충북대학교", "강원대학교", "제주대학교",
    "울산과학기술원", "광주과학기술원", "대구경북과학기술원", "한국교원대학교", "한국예술종합학교",
    "한국전통문화대학교", "한국체육대학교", "한국해양대학교", "부경대학교", "한국항공대학교",
    "광운대학교", "명지대학교", "상명대학교", "가톨릭대학교", "덕성여자대학교", "동덕여자대학교",
    "삼육대학교", "서울여자대학교", "성신여자대학교", "숙명여자대학교", "한성대학교",
    "공주대학교", "군산대학교", "목포대학교", "안동대학교", "창원대학교", "한밭대학교",
    "금오공과대학교", "목포해양대학교", "한국기술교육대학교", "한경대학교"
]
korean_colleges_2_3yr = [
    "영진전문대학교", "인덕대학교", "동양미래대학교", "명지전문대학", "부천대학교", "서일대학교",
    "유한대학교", "경기과학기술대학교", "대림대학교", "인하공업전문대학", "한국영상대학교",
    "계원예술대학교", "백석예술대학교", "서울예술대학교", "청강문화산업대학교", "수원여자대학교",
    "한양여자대학교", "동서울대학교", "오산대학교", "경민대학교", "경복대학교", "신구대학교",
    "연성대학교", "용인송담대학교", "김포대학교", "두원공과대학교", "안산대학교", "울산과학대학교",
    "대전보건대학교", "부산과학기술대학교", "대구공업대학교", "광주보건대학교", "제주한라대학교",
    "서정대학교", "배화여자대학교"
]
foreign_universities_list = [
    "Harvard University", "Stanford University", "Massachusetts Institute of Technology (MIT)",
    "University of Cambridge", "University of Oxford", "California Institute of Technology (Caltech)",
    "Princeton University", "Yale University", "University of Chicago", "Columbia University",
    "ETH Zurich (Swiss Federal Institute of Technology Zurich)", "University of Tokyo", "Peking University",
    "National University of Singapore (NUS)", "Tsinghua University", "University of California, Berkeley (UCB)",
    "Imperial College London", "Johns Hopkins University", "University of Pennsylvania",
    "Cornell University", "University of Michigan-Ann Arbor", "University of Toronto",
    "Kyoto University", "Sorbonne University", "Heidelberg University"
]

# --- 2. 학교 목록 샘플링 및 레벨 할당 ---
num_4yr_target, num_2_3yr_target, num_foreign_target = 50, 30, 20
selected_4yr_details = [{"name": name, "type": "4년제", "is_domestic": "Y"} for name in random.sample(korean_universities_4yr, min(num_4yr_target, len(korean_universities_4yr)))]
selected_2_3yr_details = [{"name": name, "type": "전문학사", "is_domestic": "Y"} for name in random.sample(korean_colleges_2_3yr, min(num_2_3yr_target, len(korean_colleges_2_3yr)))]
selected_foreign_details = [{"name": name, "type": "외국대학", "is_domestic": "N"} for name in random.sample(foreign_universities_list, min(num_foreign_target, len(foreign_universities_list)))]

pool_A_data = selected_4yr_details + selected_foreign_details
pool_B_data = selected_2_3yr_details
random.shuffle(pool_A_data)
random.shuffle(pool_B_data)

count_L1, count_L2, count_L3, count_L4 = 15, 25, 35, 25
fixed_top_level_names = {
    "서울대학교", "연세대학교", "고려대학교", "카이스트", "포항공과대학교", "성균관대학교", "서강대학교",
    "Harvard University", "Stanford University", "Massachusetts Institute of Technology (MIT)",
    "University of Cambridge", "University of Oxford"
}
level_1_assigned, level_2_assigned, level_3_assigned, level_4_assigned = [], [], [], []
temp_pool_A = list(pool_A_data)
found_fixed, remaining_A = [], []
for school in temp_pool_A:
    if school["name"] in fixed_top_level_names: found_fixed.append(school)
    else: remaining_A.append(school)
random.shuffle(remaining_A)

level_1_assigned.extend(found_fixed)
needed_L1 = count_L1 - len(level_1_assigned)
if needed_L1 > 0:
    take_L1 = min(needed_L1, len(remaining_A))
    level_1_assigned.extend(remaining_A[:take_L1]); del remaining_A[:take_L1]

current_pool_A = remaining_A
take_L2 = min(count_L2, len(current_pool_A))
level_2_assigned.extend(current_pool_A[:take_L2]); del current_pool_A[:take_L2]

level_3_assigned.extend(current_pool_A)
needed_L3 = count_L3 - len(level_3_assigned)
current_pool_B = list(pool_B_data)
if needed_L3 > 0:
    take_L3_B = min(needed_L3, len(current_pool_B))
    level_3_assigned.extend(current_pool_B[:take_L3_B]); del current_pool_B[:take_L3_B]
level_4_assigned.extend(current_pool_B)

all_assigned_schools = []
for school in level_1_assigned: school["SCHOOL_LEVEL"] = 1; all_assigned_schools.append(school)
for school in level_2_assigned: school["SCHOOL_LEVEL"] = 2; all_assigned_schools.append(school)
for school in level_3_assigned: school["SCHOOL_LEVEL"] = 3; all_assigned_schools.append(school)
for school in level_4_assigned: school["SCHOOL_LEVEL"] = 4; all_assigned_schools.append(school)

random.shuffle(all_assigned_schools)
schools_final_data = []
for idx, info in enumerate(all_assigned_schools, start=1):
    schools_final_data.append({
        "SCHOOL_ID": f"SC{idx:03d}", "SCHOOL_NAME": info["name"],
        "SCHOOL_DOMESTIC_YN": info["is_domestic"], "SCHOOL_TYPE": info["type"],
        "SCHOOL_LEVEL": info["SCHOOL_LEVEL"]
    })

# --- 3. 원본 DataFrame (분석용) ---
school_df = pd.DataFrame(schools_final_data)
school_df = school_df.sort_values(by=["SCHOOL_ID"]).reset_index(drop=True)
# 데이터 타입을 그대로 유지 (SCHOOL_LEVEL은 int)
school_df['SCHOOL_LEVEL'] = school_df['SCHOOL_LEVEL'].astype(int)

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
school_df_for_gsheet = school_df.copy()
# 모든 컬럼을 문자열로 변환하고 정리
for col in school_df_for_gsheet.columns:
    school_df_for_gsheet[col] = school_df_for_gsheet[col].astype(str)
school_df_for_gsheet = school_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})


# --- 결과 확인 (원본 DataFrame 출력) ---
school_df

