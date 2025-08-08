import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta

def find_next_quarter_start(current_date):
    """주어진 날짜 이후의 가장 가까운 분기 시작일을 찾습니다."""
    if current_date.month < 4:
        return datetime.date(current_date.year, 4, 1)
    elif current_date.month < 7:
        return datetime.date(current_date.year, 7, 1)
    elif current_date.month < 10:
        return datetime.date(current_date.year, 10, 1)
    else:
        return datetime.date(current_date.year + 1, 1, 1)

def find_parents(dep_id, dept_level_map, parent_map_dept, dept_name_map):
    """부서 ID를 바탕으로 Division과 Office 이름을 찾는 함수"""
    path = {'DIVISION_NAME': None, 'OFFICE_NAME': None}
    level = dept_level_map.get(dep_id)
    if not level:
        if dep_id == 'DEP001':
            path['DIVISION_NAME'] = 'HQ 직속'
            path['OFFICE_NAME'] = 'HQ 직속'
        return pd.Series(path)

    current_id = dep_id
    if level == 4: # Team
        office_id = parent_map_dept.get(current_id)
        path['OFFICE_NAME'] = dept_name_map.get(office_id)
        if office_id:
            path['DIVISION_NAME'] = dept_name_map.get(parent_map_dept.get(office_id))
    elif level == 3: # Office
        path['OFFICE_NAME'] = dept_name_map.get(current_id)
        path['DIVISION_NAME'] = dept_name_map.get(parent_map_dept.get(current_id))
    elif level == 2: # Division
        path['DIVISION_NAME'] = dept_name_map.get(current_id)

    if path['DIVISION_NAME'] and not path['OFFICE_NAME']:
        path['OFFICE_NAME'] = f"{path['DIVISION_NAME']} (직속)"

    return pd.Series(path)

def get_level1_ancestor(job_id, df_indexed, p_map):
    """직무 ID의 최상위(L1) 조상 JOB_ID를 찾는 함수"""
    if pd.isna(job_id): return None
    try:
        current_level = df_indexed.loc[job_id, 'JOB_LEVEL']
        current_id = job_id
        depth = 0
        while current_level != 1 and pd.notna(p_map.get(current_id)) and depth < 5:
            current_id = p_map.get(current_id)
            current_level = df_indexed.loc[current_id, 'JOB_LEVEL']
            depth += 1
        return current_id if current_level == 1 else None
    except KeyError:
        return None

def find_division_name_for_dept(dep_id, dept_level_map, parent_map_dept, dept_name_map):
    """부서 ID에서 Division 이름만 찾아주는 간소화된 함수 (find_parents 호출)"""
    return find_parents(dep_id, dept_level_map, parent_map_dept, dept_name_map)['DIVISION_NAME']

def calculate_age(personal_id, base_date=datetime.datetime.now()):
    """주민등록번호 앞자리로 기준일자 기준 나이를 계산하는 함수"""
    try:
        birth_yy = int(str(personal_id)[:2])
        gender_code = str(personal_id)[7]
        birth_year = (1900 + birth_yy) if gender_code in ['1', '2', '5', '6'] else (2000 + birth_yy)
        return base_date.year - birth_year
    except:
        return np.nan

def get_period_dates(eval_time_str):
    """'YYYY-상반기' 문자열을 시작일과 종료일로 변환하는 함수"""
    year, period = eval_time_str.split('-')
    year = int(year)
    if period == '상반기':
        return datetime.date(year, 1, 1), datetime.date(year, 6, 30)
    else: # 하반기
        return datetime.date(year, 7, 1), datetime.date(year, 12, 31)

def calculate_night_minutes(start_dt, end_dt):
    """야간 근무 시간을 분 단위로 계산하는 함수"""
    if pd.isna(start_dt) or pd.isna(end_dt): return 0
    total_night_minutes = 0
    current_day = start_dt.normalize()
    night_start1, night_end1 = current_day + pd.Timedelta(hours=22), current_day + pd.Timedelta(days=1, hours=6)
    overlap_start, overlap_end = max(start_dt, night_start1), min(end_dt, night_end1)
    if overlap_end > overlap_start:
        total_night_minutes += (overlap_end - overlap_start).total_seconds() / 60
    if start_dt.hour < 6:
        night_start2, night_end2 = current_day, current_day + pd.Timedelta(hours=6)
        overlap_start2, overlap_end2 = max(start_dt, night_start2), min(end_dt, night_end2)
        if overlap_end2 > overlap_start2:
            total_night_minutes += (overlap_end2 - overlap_start2).total_seconds() / 60
    return round(total_night_minutes)