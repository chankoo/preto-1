proposal_list = (
    ["basic_proposal"]
    + [f"proposal_0{i}" for i in range(1, 10)]
    + [f"proposal_{i}" for i in range(10, 21)]
)
title_list = [
    "기본 현황판: 인원 변동 현황",
    "승진 소요 기간",
    "승진 경로",
    "연령 분포 현황",
    "근속연수 분포 현황",
    "퇴사율 변화 추이",
    "연도별 잔존율",
    "첫 직무별 재직기간",
    "인력 유지 현황",
    "직무 이동률 추이",
    "초봉 관계 분석",
    "초과근무 분포 현황",
    "출근 문화 분석",
    "초과근무 시간 분포",
    "지각률 분포",
    "부서 변경 전후 초과근무 패턴",
    "평균 주말근무 일수",
    "요일별 업무 강도",
    "연차-병가 사용 패턴",
    "퇴사 전 휴가 패턴",
    "부서별 휴가 유형",
]
name_dictionary = {
    proposal: title for proposal, title in zip(proposal_list, title_list)
}
name_dictionary
