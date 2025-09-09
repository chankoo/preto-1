#!/usr/bin/env python
# coding: utf-8

# In[4]:


import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import random

# --- 1. 사전 준비 ---
from services.tables.HR_Core.basic_info_table import emp_df
from services.tables.HR_Core.department_table import department_df, parent_map_dept, dept_level_map, dept_name_map, division_order
from services.helpers.utils import find_parents, find_next_quarter_start, calculate_age

random.seed(42)
np.random.seed(42)
today = datetime.datetime.now().date()
today_ts = pd.to_datetime(today)

# --- 2. 1단계: 모든 직원의 기본 부서 배치 이력 생성 ---
base_assignment_records = []
assignable_departments_df = department_df[
    (department_df['DEP_USE_YN'] == 'Y') &
    (department_df['DEP_LEVEL'] >= 3) # 팀/오피스 레벨에만 배정
].copy()

# --- 수정된 부분: Division의 모든 하위 부서를 찾는 범용 함수 ---
def get_all_descendants(dep_id, parent_map_df):
    children = parent_map_df[parent_map_df['UP_DEP_ID'] == dep_id]['DEP_ID'].tolist()
    all_descendants = list(children)
    for child_id in children:
        all_descendants.extend(get_all_descendants(child_id, parent_map_df))
    return all_descendants

parent_map_df_for_func = department_df[['DEP_ID', 'UP_DEP_ID']]
# --- 수정 완료 ---

if not assignable_departments_df.empty:
    for _, emp_row in emp_df.iterrows():
        emp_id, in_date, out_date = emp_row['EMP_ID'], emp_row['IN_DATE'].date(), emp_row['OUT_DATE'].date() if pd.notna(emp_row['OUT_DATE']) else None

        current_start_date = in_date
        num_assignments = random.randint(1, 5)
        last_dept_id = None

        for i in range(num_assignments):
            if (out_date and current_start_date > out_date) or (current_start_date > today): break

            candidate_depts = assignable_departments_df

            # --- 수정된 부분: 첫 부서 배정 로직 수정 ---
            if i == 0: # 첫 부서 배정 시
                # 4개 Division 중 하나를 무작위로 선택
                chosen_division_name = random.choice(division_order)
                division_id = department_df[department_df['DEP_NAME'] == chosen_division_name]['DEP_ID'].iloc[0]

                # 해당 Division의 모든 하위 부서(팀/오피스)를 후보로 설정
                descendant_ids = get_all_descendants(division_id, parent_map_df_for_func)
                if descendant_ids:
                    candidate_depts = department_df[department_df['DEP_ID'].isin(descendant_ids)]
            # --- 수정 완료 ---
            elif last_dept_id and random.random() < 0.70: # 두 번째 이후 배정 시 70% 확률 적용
                last_dept_info = find_parents(last_dept_id, dept_level_map, parent_map_dept, dept_name_map)
                if last_dept_info['DIVISION_NAME']:
                    division_id_series = department_df.loc[department_df['DEP_NAME'] == last_dept_info['DIVISION_NAME'], 'DEP_ID']
                    if not division_id_series.empty:
                        division_id = division_id_series.iloc[0]
                        all_member_ids = get_all_descendants(division_id, parent_map_df_for_func)
                        if all_member_ids:
                            div_members_df = department_df[department_df['DEP_ID'].isin(all_member_ids)]
                            if not div_members_df.empty:
                                candidate_depts = div_members_df

            dept_row = candidate_depts.sample(n=1).iloc[0]

            end_date = out_date if i == num_assignments - 1 else find_next_quarter_start(current_start_date + timedelta(days=random.randint(365, 2 * 365))) - timedelta(days=1)
            if out_date and end_date > out_date: end_date = out_date
            if end_date and end_date > today: end_date = today

            base_assignment_records.append({'EMP_ID': emp_id, 'DEP_ID': dept_row['DEP_ID'], 'DEP_APP_START_DATE': current_start_date, 'DEP_APP_END_DATE': end_date})

            last_dept_id = dept_row['DEP_ID']
            if end_date is None or end_date >= (out_date or today): break
            current_start_date = end_date + timedelta(days=1)

base_assignments_df = pd.DataFrame(base_assignment_records)
# (이하 코드는 이전과 동일합니다)
base_assignments_df['DEP_APP_START_DATE'] = pd.to_datetime(base_assignments_df['DEP_APP_START_DATE'])
base_assignments_df['DEP_APP_END_DATE'] = pd.to_datetime(base_assignments_df['DEP_APP_END_DATE'])

# --- 3. 2단계: 부서장 선출 및 기록 단편화 ---
fragmented_records = []
emp_ages = emp_df.set_index('EMP_ID')['PERSONAL_ID'].apply(lambda pid: calculate_age(pid)).to_dict()
all_event_dates = sorted(pd.to_datetime(pd.concat([base_assignments_df['DEP_APP_START_DATE'], base_assignments_df['DEP_APP_END_DATE'].dropna()]).unique()))

for i in range(len(all_event_dates)):
    period_start = all_event_dates[i]
    period_end = all_event_dates[i+1] - timedelta(days=1) if i + 1 < len(all_event_dates) else today_ts
    if period_start > period_end: continue
    active_assignments = base_assignments_df[(base_assignments_df['DEP_APP_START_DATE'] <= period_start) & (base_assignments_df['DEP_APP_END_DATE'].isnull() | (base_assignments_df['DEP_APP_END_DATE'] >= period_end))]
    for dep_id in active_assignments['DEP_ID'].unique():
        members_in_dept = active_assignments[active_assignments['DEP_ID'] == dep_id]
        member_ids = members_in_dept['EMP_ID'].tolist()
        if not member_ids: continue
        member_ages_df = pd.DataFrame([{'EMP_ID': mid, 'AGE': emp_ages.get(mid, 25)} for mid in member_ids])
        head_id = member_ages_df.sort_values(by=['AGE', 'EMP_ID'], ascending=[False, True])['EMP_ID'].iloc[0]
        for emp_id in member_ids:
            fragmented_records.append({'EMP_ID': emp_id, 'DEP_ID': dep_id, 'TITLE_INFO': 'Head' if emp_id == head_id else 'Member', 'PERIOD_START': period_start, 'PERIOD_END': period_end})

# --- 4. 3단계: 연속된 기록 병합 ---
fragmented_df = pd.DataFrame(fragmented_records)
if not fragmented_df.empty:
    fragmented_df = fragmented_df.sort_values(['EMP_ID', 'DEP_ID', 'TITLE_INFO', 'PERIOD_START'])
    group_ids = (fragmented_df[['EMP_ID', 'DEP_ID', 'TITLE_INFO']] != fragmented_df[['EMP_ID', 'DEP_ID', 'TITLE_INFO']].shift()).any(axis=1).cumsum()
    department_info_df = fragmented_df.groupby(group_ids).agg(
        EMP_ID=('EMP_ID', 'first'), DEP_ID=('DEP_ID', 'first'), TITLE_INFO=('TITLE_INFO', 'first'),
        DEP_APP_START_DATE=('PERIOD_START', 'min'), DEP_APP_END_DATE=('PERIOD_END', 'max')
    ).reset_index(drop=True)
else:
    department_info_df = pd.DataFrame()

# --- 5. 최종 데이터 정리 ---
if not department_info_df.empty:
    department_info_df = pd.merge(department_info_df, department_df[['DEP_ID', 'DEPT_TYPE', 'DEP_REL_START_DATE']], on='DEP_ID', how='left')
    department_info_df['MAIN_DEP'] = 'Y'
    department_info_df['DEP_DURATION'] = (department_info_df['DEP_APP_END_DATE'] - department_info_df['DEP_APP_START_DATE']).dt.days
    final_cols = ['EMP_ID', 'DEP_ID', 'DEPT_TYPE', 'DEP_REL_START_DATE', 'DEP_APP_START_DATE', 'DEP_APP_END_DATE', 'MAIN_DEP', 'TITLE_INFO', 'DEP_DURATION']
    department_info_df = department_info_df.reindex(columns=final_cols)
    emp_last_record_idx = department_info_df.groupby('EMP_ID')['DEP_APP_START_DATE'].idxmax()
    current_emp_ids = emp_df[emp_df['CURRENT_EMP_YN'] == 'Y']['EMP_ID']
    idx_to_update = emp_last_record_idx[emp_last_record_idx.index.isin(current_emp_ids)]
    department_info_df.loc[idx_to_update, 'DEP_APP_END_DATE'] = None
    department_info_df = department_info_df.sort_values(by=['EMP_ID', 'DEP_APP_START_DATE']).reset_index(drop=True)

# --- 6. Google Sheets용 복사본 생성 ---
department_info_df_for_gsheet = department_info_df.copy()
if not department_info_df_for_gsheet.empty:
    date_cols = ['DEP_REL_START_DATE', 'DEP_APP_START_DATE', 'DEP_APP_END_DATE']
    for col in date_cols:
        department_info_df_for_gsheet[col] = department_info_df_for_gsheet[col].dt.strftime('%Y-%m-%d')
    for col in department_info_df_for_gsheet.columns:
        department_info_df_for_gsheet[col] = department_info_df_for_gsheet[col].astype(str)
    department_info_df_for_gsheet = department_info_df_for_gsheet.replace({'None':'', 'NaT':'', 'nan':''})


# In[ ]:




