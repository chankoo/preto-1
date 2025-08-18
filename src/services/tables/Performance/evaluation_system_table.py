#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import random

# ==============================================================================
# --- 1. 평가 시스템 관리 (Evaluation System Table) ---
# ==============================================================================

# 재현성을 위한 시드 설정
random.seed(42)

# --- 1. 평가 시스템의 기본 데이터 정의 ---
evaluation_systems_base_data = [
    {'EVAL_SYS_NAME': 'MBO기반 성과평가', 'EVAL_DIRECTION': '하향평가', 'EVAL_KIND': '상대평가', 'EVAL_SCALE': '7점'},
    {'EVAL_SYS_NAME': '역량평가', 'EVAL_DIRECTION': '하향평가', 'EVAL_KIND': '절대평가', 'EVAL_SCALE': '5점'},
    {'EVAL_SYS_NAME': '리더십 상향평가', 'EVAL_DIRECTION': '상향평가', 'EVAL_KIND': '절대평가', 'EVAL_SCALE': '5점'},
    {'EVAL_SYS_NAME': '동료 피드백', 'EVAL_DIRECTION': '동료평가', 'EVAL_KIND': '절대평가', 'EVAL_SCALE': '4점'},
    {'EVAL_SYS_NAME': 'OKR 기반 성과평가', 'EVAL_DIRECTION': '하향평가', 'EVAL_KIND': '절대평가', 'EVAL_SCALE': '5점'},
    {'EVAL_SYS_NAME': '직무역량 심층평가', 'EVAL_DIRECTION': '하향평가', 'EVAL_KIND': '절대평가', 'EVAL_SCALE': '7점'},
    {'EVAL_SYS_NAME': '리더 360도 다면평가', 'EVAL_DIRECTION': '동료평가', 'EVAL_KIND': '절대평가', 'EVAL_SCALE': '5점'},
    {'EVAL_SYS_NAME': '연말 성과등급 조정', 'EVAL_DIRECTION': '하향평가', 'EVAL_KIND': '상대평가', 'EVAL_SCALE': '10점'},
    {'EVAL_SYS_NAME': '상시 성과 리뷰', 'EVAL_DIRECTION': '하향평가', 'EVAL_KIND': '절대평가', 'EVAL_SCALE': '10점'},
    {'EVAL_SYS_NAME': '협업 역량 동료평가', 'EVAL_DIRECTION': '동료평가', 'EVAL_KIND': '절대평가', 'EVAL_SCALE': '5점'}
]

# --- 2. 초기 DataFrame 생성 ---
eval_system_records = []
for i, system_data in enumerate(evaluation_systems_base_data, start=1):
    record = {
        'EVAL_SYS_ID': f'ES{i:03d}',
        'EVAL_SYS_NAME': system_data['EVAL_SYS_NAME'],
        'EVAL_DIRECTION': system_data['EVAL_DIRECTION'],
        'EVAL_KIND': system_data['EVAL_KIND'],
        'EVAL_SCALE': system_data['EVAL_SCALE'],
        'NUM_QUESTION': random.randint(3, 7)
    }
    eval_system_records.append(record)

# --- 3. 원본 DataFrame (분석용) ---
evaluation_system_df = pd.DataFrame(eval_system_records)
evaluation_system_df['NUM_QUESTION'] = evaluation_system_df['NUM_QUESTION'].astype(int)

# --- 4. Google Sheets용 복사본 생성 및 가공 ---
evaluation_system_df_for_gsheet = evaluation_system_df.copy()
for col in evaluation_system_df_for_gsheet.columns:
    evaluation_system_df_for_gsheet[col] = evaluation_system_df_for_gsheet[col].astype(str)
evaluation_system_df_for_gsheet = evaluation_system_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})


# In[ ]:




