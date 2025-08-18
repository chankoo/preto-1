#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import random

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임을 임포트
from services.tables.Performance.evaluation_original_score_info_table import evaluation_original_score_df

random.seed(42)

# --- 2. 초기 DataFrame 생성 ---
df = evaluation_original_score_df.copy()
grade_to_score_map = {'S': 100, 'A': 85, 'B': 70, 'C': 55, 'D': 40}

def convert_to_numeric(score):
    numeric_score = grade_to_score_map.get(score)
    if numeric_score is not None: return numeric_score
    try: return float(score)
    except (ValueError, TypeError): return np.nan

df['NUMERIC_SCORE'] = df['ORIGINAL_SCORE'].apply(convert_to_numeric)
df = df.dropna(subset=['NUMERIC_SCORE'])

weights_for_2_evals = [[0.6, 0.4], [0.5, 0.5], [0.4, 0.6]]
weights_for_3_evals = [[0.4, 0.3, 0.3], [0.3, 0.4, 0.3], [0.3, 0.3, 0.4]]

def calculate_weighted_average(group):
    scores = group['NUMERIC_SCORE'].to_numpy()
    num_evals = len(scores)
    if num_evals == 1: return scores[0]
    elif num_evals == 2: return np.dot(scores, random.choice(weights_for_2_evals))
    elif num_evals == 3: return np.dot(scores, random.choice(weights_for_3_evals))
    else: return group['NUMERIC_SCORE'].mean()

modified_scores = df.groupby(['EMP_ID', 'EVAL_TIME']).apply(calculate_weighted_average, include_groups=False)
evaluation_modified_score_df = modified_scores.reset_index(name='MODIFIED_SCORE')

# --- 3. 원본/Google Sheets용 DataFrame 분리 ---
evaluation_modified_score_df['MODIFIED_SCORE'] = pd.to_numeric(evaluation_modified_score_df['MODIFIED_SCORE']).round(2)
evaluation_modified_score_df['EVAL_YEAR'] = evaluation_modified_score_df['EVAL_TIME'].str.split('-').str[0] + '년'
evaluation_modified_score_df['YEAR_AVERAGE_SCORE'] = evaluation_modified_score_df.groupby(['EMP_ID', 'EVAL_YEAR'])['MODIFIED_SCORE'].transform('mean')
evaluation_modified_score_df['YEAR_AVERAGE_SCORE'] = evaluation_modified_score_df['YEAR_AVERAGE_SCORE'].round(2)

final_cols = ['EMP_ID', 'EVAL_TIME', 'EVAL_YEAR', 'MODIFIED_SCORE', 'YEAR_AVERAGE_SCORE']
evaluation_modified_score_df = evaluation_modified_score_df[final_cols]

evaluation_modified_score_df_for_gsheet = evaluation_modified_score_df.copy()
for col in evaluation_modified_score_df_for_gsheet.columns:
    evaluation_modified_score_df_for_gsheet[col] = evaluation_modified_score_df_for_gsheet[col].astype(str)
evaluation_modified_score_df_for_gsheet = evaluation_modified_score_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})


# In[ ]:




