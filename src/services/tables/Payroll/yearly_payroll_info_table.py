#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import datetime
from datetime import date

# --- 1. 사전 준비 ---
# 다른 모듈에서 생성된 데이터프레임을 임포트
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.Payroll.detailed_monthly_payroll_info_table import detailed_monthly_payroll_df

# --- 2. 데이터 준비 및 가공 ---
df = detailed_monthly_payroll_df.copy()
df['PAY_YEAR'] = df['PAY_PERIOD'].str[:4]

# 데이터 집계
yearly_summary_pivot = df.pivot_table(
    index=['EMP_ID', 'PAY_YEAR'], columns='PAYROLL_ITEM_CATEGORY',
    values='PAY_AMOUNT', aggfunc='sum', fill_value=0
).reset_index()
yearly_summary_pivot.rename(columns={
    '기본급여': 'BASIC_PAY', '정기수당': 'REGULAR_ALLOWANCE', '변동급여': 'VARIABLE_PAY'
}, inplace=True)
expected_cols = ['BASIC_PAY', 'REGULAR_ALLOWANCE', 'VARIABLE_PAY']
for col in expected_cols:
    if col not in yearly_summary_pivot.columns:
        yearly_summary_pivot[col] = 0

# 추가 분석 컬럼 생성
yearly_payroll_df = yearly_summary_pivot.copy()
yearly_payroll_df['TOTAL_PAY'] = yearly_payroll_df['BASIC_PAY'] + yearly_payroll_df['REGULAR_ALLOWANCE'] + yearly_payroll_df['VARIABLE_PAY']
yearly_payroll_df['VARIABLE_PAY_RATIO'] = np.where(
    yearly_payroll_df['TOTAL_PAY'] > 0,
    (yearly_payroll_df['VARIABLE_PAY'] / yearly_payroll_df['TOTAL_PAY']) * 100, 0
)

# --- 3. 연간 근무일수 및 정규화된 연봉/성장률 계산 ---
yearly_payroll_df['PAY_YEAR_INT'] = yearly_payroll_df['PAY_YEAR'].astype(int)
merged_for_days = pd.merge(yearly_payroll_df, emp_df[['EMP_ID', 'IN_DATE', 'OUT_DATE']], on='EMP_ID')
today = datetime.datetime.now().date()

def calculate_days_worked_in_year(row):
    year = row['PAY_YEAR_INT']
    year_start = pd.Timestamp(date(year, 1, 1))
    year_end = min(pd.Timestamp(date(year, 12, 31)), pd.to_datetime(today))

    start_date = max(row['IN_DATE'], year_start)
    end_date = min(row['OUT_DATE'] if pd.notna(row['OUT_DATE']) else pd.Timestamp.max, year_end)

    if start_date > end_date: return 0
    return (end_date - start_date).days + 1

merged_for_days['DAYS_WORKED_IN_YEAR'] = merged_for_days.apply(calculate_days_worked_in_year, axis=1)

merged_for_days['NORMALIZED_TOTAL_PAY'] = np.where(
    merged_for_days['DAYS_WORKED_IN_YEAR'] > 0,
    merged_for_days['TOTAL_PAY'] * (365 / merged_for_days['DAYS_WORKED_IN_YEAR']),
    0
)
yearly_payroll_df = merged_for_days.copy()

yearly_payroll_df = yearly_payroll_df.sort_values(by=['EMP_ID', 'PAY_YEAR'])
yearly_payroll_df['YOY_GROWTH'] = yearly_payroll_df.groupby('EMP_ID')['NORMALIZED_TOTAL_PAY'].pct_change() * 100

# --- 4. 원본/Google Sheets용 DataFrame 분리 ---
final_cols = [
    'EMP_ID', 'PAY_YEAR', 'BASIC_PAY', 'REGULAR_ALLOWANCE', 'VARIABLE_PAY',
    'TOTAL_PAY', 'VARIABLE_PAY_RATIO', 'YOY_GROWTH'
]
yearly_payroll_df = yearly_payroll_df[final_cols]
yearly_payroll_df = yearly_payroll_df.fillna(0).round(2)

yearly_payroll_df_for_gsheet = yearly_payroll_df.copy()
for col in yearly_payroll_df_for_gsheet.columns:
    yearly_payroll_df_for_gsheet[col] = yearly_payroll_df_for_gsheet[col].astype(str)
yearly_payroll_df_for_gsheet = yearly_payroll_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})


# In[ ]:




