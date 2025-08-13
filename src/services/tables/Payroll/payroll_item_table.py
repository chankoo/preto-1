#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd

# ==============================================================================
# --- 1. 급여 항목 관리(Payroll Item Table) ---
# ==============================================================================

# --- 1. 각 급여 항목의 속성 정의 ---
payroll_items_base_data = [
    {'PAYROLL_ITEM_NAME': '기본급', 'PAYMENT_TYPE': '1개월', 'PAYROLL_ITEM_CATEGORY': '기본급여', 'TAX_YN': 'Y'},
    {'PAYROLL_ITEM_NAME': '식대', 'PAYMENT_TYPE': '1개월', 'PAYROLL_ITEM_CATEGORY': '정기수당', 'TAX_YN': 'N'},
    {'PAYROLL_ITEM_NAME': '시간외근로수당', 'PAYMENT_TYPE': '1개월', 'PAYROLL_ITEM_CATEGORY': '정기수당', 'TAX_YN': 'Y'},
    {'PAYROLL_ITEM_NAME': '직책수당', 'PAYMENT_TYPE': '1개월', 'PAYROLL_ITEM_CATEGORY': '정기수당', 'TAX_YN': 'Y'},
    {'PAYROLL_ITEM_NAME': '연구수당', 'PAYMENT_TYPE': '1개월', 'PAYROLL_ITEM_CATEGORY': '정기수당', 'TAX_YN': 'N'},
    {'PAYROLL_ITEM_NAME': '육아수당', 'PAYMENT_TYPE': '1개월', 'PAYROLL_ITEM_CATEGORY': '정기수당', 'TAX_YN': 'N'},
    {'PAYROLL_ITEM_NAME': '기타수당', 'PAYMENT_TYPE': '1개월', 'PAYROLL_ITEM_CATEGORY': '정기수당', 'TAX_YN': 'Y'},
    {'PAYROLL_ITEM_NAME': '고정상여', 'PAYMENT_TYPE': '2개월', 'PAYROLL_ITEM_CATEGORY': '기본급여', 'TAX_YN': 'Y'},
    {'PAYROLL_ITEM_NAME': '인센티브', 'PAYMENT_TYPE': '변동', 'PAYROLL_ITEM_CATEGORY': '변동급여', 'TAX_YN': 'Y'},
    {'PAYROLL_ITEM_NAME': '기타성과급', 'PAYMENT_TYPE': '변동', 'PAYROLL_ITEM_CATEGORY': '변동급여', 'TAX_YN': 'Y'}
]

# --- 2. 초기 DataFrame 생성 ---
payroll_item_records = []
for i, item_data in enumerate(payroll_items_base_data, start=1):
    record = {
        'PAYROLL_ITEM_ID': f'PI{i:03d}',
        'PAYROLL_ITEM_NAME': item_data['PAYROLL_ITEM_NAME'],
        'PAYMENT_TYPE': item_data['PAYMENT_TYPE'],
        'PAYROLL_ITEM_CATEGORY': item_data['PAYROLL_ITEM_CATEGORY'],
        'TAX_YN': item_data['TAX_YN']
    }
    payroll_item_records.append(record)

# --- 3. 원본/Google Sheets용 DataFrame 분리 ---
payroll_item_df = pd.DataFrame(payroll_item_records)
final_column_order = [
    'PAYROLL_ITEM_ID', 'PAYROLL_ITEM_NAME', 'PAYMENT_TYPE', 
    'PAYROLL_ITEM_CATEGORY', 'TAX_YN'
]
payroll_item_df = payroll_item_df[final_column_order]

payroll_item_df_for_gsheet = payroll_item_df.copy()
for col in payroll_item_df_for_gsheet.columns:
    payroll_item_df_for_gsheet[col] = payroll_item_df_for_gsheet[col].astype(str)
payroll_item_df_for_gsheet = payroll_item_df_for_gsheet.replace({'None': '', 'nan': '', 'NaT': ''})

