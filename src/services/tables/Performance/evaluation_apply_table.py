#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import random

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임을 임포트
from services.tables.Performance.evaluation_system_table import evaluation_system_df

random.seed(42)

# --- 2. 초기 DataFrame 생성 ---
eval_periods = []
for year in range(2021, 2026):
    eval_periods.append(f"{year}-상반기")
    # 2025년은 상반기까지만
    if year < 2025:
        eval_periods.append(f"{year}-하반기")

eval_apply_records = []
post_2023_systems = ['ES002', 'ES003', 'ES009']
mandatory_pre_2023 = 'ES001'
optional_pre_2023_systems = list(
    set(evaluation_system_df['EVAL_SYS_ID']) - set(post_2023_systems) - {mandatory_pre_2023}
)

for period in eval_periods:
    active_system_ids = []
    year_part = int(period.split('-')[0])

    if year_part >= 2023:
        active_system_ids = post_2023_systems
    else: # 2023년 이전
        active_system_ids.append(mandatory_pre_2023)
        num_optional = random.randint(1, 2)
        num_to_sample = min(num_optional, len(optional_pre_2023_systems))
        active_system_ids.extend(random.sample(optional_pre_2023_systems, k=num_to_sample))

    for sys_id in active_system_ids:
        sys_row = evaluation_system_df[evaluation_system_df['EVAL_SYS_ID'] == sys_id].iloc[0]
        sys_name = sys_row['EVAL_SYS_NAME']

        comparing_score, score_process = '', ''
        if '상시 성과 리뷰' in sys_name:
            comparing_score, score_process = '파이분배방식', '100점 환산'
        elif any(keyword in sys_name for keyword in ['역량', '피드백', '동료', '리더십']):
            comparing_score, score_process = '절대적 점수 비교', '100점 환산'
        else:
            comparing_score = random.choice(['평균-표준편차방식', '절대적 점수 비교'])
            if comparing_score == '평균-표준편차방식':
                score_process = '등급화'
            else:
                score_process = random.choice(['100점 환산', '등급화'])

        record = {
            'EVAL_TIME': period, 'EVAL_SYS_ID': sys_id,
            'COMPARING_SCORE': comparing_score, 'SCORE_PROCESS': score_process
        }
        eval_apply_records.append(record)

# --- 3. 원본/Google Sheets용 DataFrame 분리 ---
evaluation_apply_df = pd.DataFrame(eval_apply_records)
evaluation_apply_df = evaluation_apply_df.drop_duplicates()
evaluation_apply_df = evaluation_apply_df.sort_values(by=['EVAL_TIME', 'EVAL_SYS_ID']).reset_index(drop=True)

evaluation_apply_df_for_gsheet = evaluation_apply_df.copy()
for col in evaluation_apply_df_for_gsheet.columns:
    evaluation_apply_df_for_gsheet[col] = evaluation_apply_df_for_gsheet[col].astype(str)
evaluation_apply_df_for_gsheet = evaluation_apply_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

