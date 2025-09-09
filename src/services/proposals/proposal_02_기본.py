#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

# --- 1. 데이터 임포트 ---
from services.tables.HR_Core.position_info_table import position_info_df
from services.tables.HR_Core.position_table import position_df
from services.tables.HR_Core.department_info_table import department_info_df
from services.tables.HR_Core.job_info_table import job_info_df
from services.tables.HR_Core.job_table import job_df, job_df_indexed, parent_map_job
from services.tables.HR_Core.department_table import division_order, dept_level_map, parent_map_dept, dept_name_map
from services.helpers.utils import find_division_name_for_dept, get_level1_ancestor

def create_figure():
    """
    제안 2: 차세대 리더 승진 경로 분석 그래프를 생성합니다.
    """
    pos_info = position_info_df.copy()
    pos_info = pd.merge(pos_info, position_df[['POSITION_ID', 'POSITION_NAME']].drop_duplicates(), on='POSITION_ID')
    dept_info = department_info_df.copy()
    job_info = job_info_df.copy()

    dept_info_sorted = dept_info.sort_values(['EMP_ID', 'DEP_APP_START_DATE'])
    job_info_sorted = job_info.sort_values(['EMP_ID', 'JOB_APP_START_DATE'])
    job_l1_map = job_df[job_df['JOB_LEVEL'] == 1].set_index('JOB_ID')['JOB_NAME'].to_dict()

    def get_promotion_path_div_and_job(employee_id, promotion_to):
        emp_pos_history = pos_info[pos_info['EMP_ID'] == employee_id].sort_values('GRADE_START_DATE')
        promo_event_df = emp_pos_history[emp_pos_history['POSITION_NAME'] == promotion_to]
        if promo_event_df.empty: return None
        promo_event = promo_event_df.iloc[0]

        prev_pos_name = 'Staff' if promotion_to == 'Manager' else 'Manager'
        prev_pos_events = emp_pos_history[(emp_pos_history['POSITION_NAME'] == prev_pos_name) & (emp_pos_history['GRADE_START_DATE'] < promo_event['GRADE_START_DATE'])]
        if prev_pos_events.empty: return None

        prev_pos_event_date = prev_pos_events.iloc[-1]['GRADE_START_DATE']
        promo_event_date = promo_event['GRADE_START_DATE']

        emp_dept_history = dept_info_sorted[dept_info_sorted['EMP_ID'] == employee_id]
        emp_job_history = job_info_sorted[job_info_sorted['EMP_ID'] == employee_id]

        dept_before_df = emp_dept_history[emp_dept_history['DEP_APP_START_DATE'] <= prev_pos_event_date]
        dept_after_df = emp_dept_history[emp_dept_history['DEP_APP_START_DATE'] <= promo_event_date]
        job_before_df = emp_job_history[emp_job_history['JOB_APP_START_DATE'] <= prev_pos_event_date]
        job_after_df = emp_job_history[emp_job_history['JOB_APP_START_DATE'] <= promo_event_date]

        if any(df.empty for df in [dept_before_df, dept_after_df, job_before_df, job_after_df]): return None

        dept_before, dept_after = dept_before_df.iloc[-1], dept_after_df.iloc[-1]
        job_before, job_after = job_before_df.iloc[-1], job_after_df.iloc[-1]

        # --- 수정된 부분 2: 함수 호출 시 필요한 인수들을 모두 전달 ---
        div_before = find_division_name_for_dept(dept_before['DEP_ID'], dept_level_map, parent_map_dept, dept_name_map)
        div_after = find_division_name_for_dept(dept_after['DEP_ID'], dept_level_map, parent_map_dept, dept_name_map)
        # --- 수정 완료 ---
        job_l1_before = job_l1_map.get(get_level1_ancestor(job_before['JOB_ID'], job_df_indexed, parent_map_job))
        job_l1_after = job_l1_map.get(get_level1_ancestor(job_after['JOB_ID'], job_df_indexed, parent_map_job))

        if all([div_before, div_after, job_l1_before, job_l1_after]):
            return {
                "from_div": f"{div_before} ({prev_pos_name})", "to_div": f"{div_after} ({promotion_to})",
                "from_job": f"{job_l1_before} ({prev_pos_name})", "to_job": f"{job_l1_after} ({promotion_to})",
            }
        return None

    all_transitions = []
    manager_ids = pos_info[pos_info['POSITION_NAME'] == 'Manager']['EMP_ID'].unique()
    director_ids = pos_info[pos_info['POSITION_NAME'] == 'Director']['EMP_ID'].unique()

    for emp_id in manager_ids:
        path = get_promotion_path_div_and_job(emp_id, 'Manager')
        if path: all_transitions.append(path)
    for emp_id in director_ids:
        path = get_promotion_path_div_and_job(emp_id, 'Director')
        if path: all_transitions.append(path)

    if not all_transitions:
        return go.Figure().update_layout(title_text="분석할 승진 경로 데이터가 없습니다.")

    transitions_df = pd.DataFrame(all_transitions)

    sankey_div = transitions_df.groupby(['from_div', 'to_div']).size().reset_index(name='value')
    all_div_nodes_unsorted = pd.concat([sankey_div['from_div'], sankey_div['to_div']]).unique()
    div_map = {f"{div} ({pos})": i for i, div in enumerate(division_order) for pos in ['Staff', 'Manager', 'Director']}
    labels_div = sorted(all_div_nodes_unsorted, key=lambda x: div_map.get(x, 99))
    indices_div = {label: i for i, label in enumerate(labels_div)}

    sankey_job = transitions_df.groupby(['from_job', 'to_job']).size().reset_index(name='value')
    labels_job = sorted(pd.concat([sankey_job['from_job'], sankey_job['to_job']]).unique())
    indices_job = {label: i for i, label in enumerate(labels_job)}

    fig = go.Figure()
    fig.add_trace(go.Sankey(
        node=dict(pad=15, thickness=20, label=labels_div),
        link=dict(source=sankey_div['from_div'].map(indices_div), target=sankey_div['to_div'].map(indices_div), value=sankey_div['value']),
        visible=True
    ))
    fig.add_trace(go.Sankey(
        node=dict(pad=15, thickness=20, label=labels_job),
        link=dict(source=sankey_job['from_job'].map(indices_job), target=sankey_job['to_job'].map(indices_job), value=sankey_job['value']),
        visible=False
    ))

    fig.update_layout(
        updatemenus=[dict(
            buttons=[
                dict(label='Division Level', method='update', args=[{'visible': [True, False]}]),
                dict(label='Job Level', method='update', args=[{'visible': [False, True]}])
            ],
            direction="down", pad={"r": 10, "t": 10},
            showactive=True, x=0.01, xanchor="left", y=1.1, yanchor="top"
        )],
        title_text="핵심 인재 승진 경로 분석",
        font_size=12, height=800
    )

    return fig

pio.renderers.default = 'vscode'
fig = create_figure()
fig.show()


# In[ ]:




