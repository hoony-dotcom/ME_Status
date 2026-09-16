import os
import glob
import re
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# 1. 페이지 설정
st.set_page_config(page_title="의료장비 현황 대시보드", page_icon="🏥", layout="wide")

# 운영체제별 한글 폰트 자동 설정 및 마이너스 기호 깨짐 방지
def set_korean_font():
    font_list = [f.name for f in fm.fontManager.ttflist]
    candidates = ['NanumGothic', 'Malgun Gothic', 'AppleGothic', 'Nanum Barun Gothic', 'DejaVu Sans']
    
    selected_font = 'DejaVu Sans'
    for font in candidates:
        if font in font_list:
            selected_font = font
            break
            
    plt.rcParams['font.family'] = selected_font
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

# 2. 폴더 내에서 가장 최신의 '의료기기 현황조회' 엑셀 파일 자동 탐색 함수
def get_latest_excel_file():
    pattern = '의료기기 현황조회*.xlsx'
    files = glob.glob(pattern)
    
    if not files:
        return '의료기기 현황조회_20260901091435400.xlsx'
    
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

file_path = get_latest_excel_file()

# 3. 파일명에서 기준일 추출 함수 (언더바 뒤 8자리)
def get_base_date(filename):
    try:
        base_name = os.path.basename(filename)
        match = re.search(r'_(\d{8})', base_name)
        if match:
            date_str = match.group(1)
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:]
            return f"{year}년 {month}월 {day}일"
    except Exception:
        pass
    return "날짜 정보 없음"

base_date_display = get_base_date(file_path)

# 4. 데이터 로드 및 전처리 함수
@st.cache_data
def load_data(path):
    df = pd.read_excel(path, sheet_name=0)
    
    # 사용부서가 공란(빈 칸, NaN 등)인 데이터 제외
    df['사용부서_str'] = df['사용\n부서'].astype(str).str.strip()
    df = df[df['사용\n부서'].notna() & (df['사용부서_str'] != '') & (df['사용부서_str'].str.lower() != 'nan')].copy()
    
    # 사용부서가 '88'인 경우 '매각완료'로 이름 변경
    df.loc[df['사용부서_str'] == '88', '사용\n부서'] = '매각완료'
    
    # 등급분류 공란 처리 및 문자열 변환
    df['등급\n분류'] = df['등급\n분류'].fillna('해당무').astype(str).str.strip()
    df.loc[df['등급\n분류'] == '', '등급\n분류'] = '해당무'
    
    return df

raw_df = load_data(file_path)

# 5. 사이드바 필터 설정
st.sidebar.header("⚙️ 대시보드 필터 설정")
st.sidebar.info(f"📂 **사용 중인 파일**:\n`{os.path.basename(file_path)}`")

# 기본 선택은 '매각완료 제외' (체크 해제 상태)
include_sold = st.sidebar.checkbox("매각완료 장비 포함하기", value=False, help="체크하면 매각완료(부서코드 88) 장비가 포함되어 조회됩니다.")

# 필터 적용
if include_sold:
    df = raw_df.copy()
    filter_status_text = "매각완료 장비 포함"
else:
    df = raw_df[raw_df['사용\n부서'] != '매각완료'].copy()
    filter_status_text = "매각완료 장비 제외 (기본값)"

# 6. 상단 타이틀 및 관련 링크 영역 (의용공학팀 연결앱)
st.title("🔗 의용공학팀 연결앱")
st.markdown("병원 의료장비 관리 및 관련 계획 실적 연동 페이지입니다.")

# 외부 링크 버튼 배치
st.markdown(
    """
    <a href="https://buly.kr/DEbvdwF" target="_blank">
        <button style="background-color:#4CAF50; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer; font-size:16px; font-weight:bold;">
            📈 의료장비 투자집행 계획 실적 바로가기
        </button>
    </a>
    """,
    unsafe_allow_html=True
)

st.markdown("")
st.subheader("🏥 병원 의료장비 현황 대시보드")
st.markdown(f"**📅 기준일:** {base_date_display} &nbsp;&nbsp;|&nbsp;&nbsp; **현재 필터:** {filter_status_text}")
st.markdown("---")

# 7. 상단 KPI 요약 메트릭 (금액 천원 단위 환산)
total_cost_thousand = df['취득가'].sum() / 1_000

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="조회 장비 대수", value=f"{len(df):,} 대")
with col2:
    st.metric(label="총 취득가액", value=f"{total_cost_thousand:,.1f} 천원")
with col3:
    high_risk_count = len(df[df['등급\n분류'].astype(str).str.contains('3|4')])
    st.metric(label="고위험 장비 (3/4등급)", value=f"{high_risk_count:,} 대")
with col4:
    d_status_count = len(df[df['자산\n상태'] == 'D'])
    st.metric(label="노후/불용 검토 (D등급)", value=f"{d_status_count:,} 대")

st.markdown("---")

# 8. 메인 그래프 영역 (3단 컬럼 배치)
col1, col2, col3 = st.columns(3)

# [1단] 자산 상태별 현황
with col1:
    st.subheader("📊 자산 상태별 현황")
    status_counts = df['자산\n상태'].value_counts()
    
    fig1, ax1 = plt.subplots(figsize=(5, 4))
    
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return f'{pct:.1f}%\n({val:,}대)'
        return my_autopct

    ax1.pie(
        status_counts, 
        labels=status_counts.index, 
        autopct=make_autopct(status_counts.values), 
        startangle=90, 
        colors=sns.color_palette('pastel')
    )
    ax1.axis('equal')
    st.pyplot(fig1)
    
    status_desc_map = {
        'A': '무상보증기간 이내에 있거나 수리이력이 거의 없는 장비',
        'B': '보증기간이 지났으나, 단순수리 또는 부품을 교체하여 외관 및 기능에 이상이 없는 장비',
        'C': '노후되거나 고장시 수리가 불가할 수 있으나 사용에 지장이 없는 장비',
        'D': '수리가 불가능하거나, 수리하는 것이 비경제적인 장비로 폐기 진행중'
    }
    
    with st.container():
        st.markdown("**📋 자산 상태 상세 기준**")
        for status in sorted(status_counts.index):
            desc = status_desc_map.get(status, '기타')
            st.markdown(f"- **`{status}`등급**: {desc}")

# [2단] 식약처/위험 등급별 현황
with col2:
    st.subheader("📊 위험 등급별 현황")
    grade_counts = df['등급\n분류'].value_counts()
    
    def grade_sort_key(grade_str):
        s = str(grade_str).strip()
        if '해당무' in s or s == '':
            return 0
        match = re.search(r'([1-4])', s)
        if match:
            return int(match.group(1))
        return 99

    sorted_grades = sorted(grade_counts.index, key=grade_sort_key)
    grade_counts = grade_counts.reindex(sorted_grades).dropna()
    
    fig2, ax2 = plt.subplots(figsize=(5, 4))
    sns.barplot(x=grade_counts.index, y=grade_counts.values, ax=ax2, palette='viridis')
    ax2.set_ylabel("대수")
    ax2.set_xlabel("등급")
    plt.xticks(rotation=45)
    st.pyplot(fig2)
    
    grade_df = pd.DataFrame({
        '등급분류': grade_counts.index,
        '대수': [f"{val:,} 대" for val in grade_counts.values]
    })
    
    with st.container():
        st.markdown("**📋 위험 등급 상세 보기**")
        st.dataframe(grade_df, hide_index=True)

# [3단] 장비 보유 상위 부서 TOP 10 현황
with col3:
    st.subheader("📊 부서별 장비 보유 TOP 10")
    dept_counts = df['사용\n부서'].value_counts().head(10)
    
    fig3, ax3 = plt.subplots(figsize=(5, 4))
    sns.barplot(y=dept_counts.index, x=dept_counts.values, ax=ax3, palette='mako', orient='h')
    ax3.set_xlabel("장비 대수")
    ax3.set_ylabel("부서명")
    st.pyplot(fig3)
    
    dept_df = pd.DataFrame({
        '사용부서': dept_counts.index,
        '대수': [f"{val:,} 대" for val in dept_counts.values]
    })
    
    with st.container():
        st.markdown("**📋 부서별 상세 보기**")
        st.dataframe(dept_df, hide_index=True)

# 9. 하단 장비 상세 데이터 목록 (기본 노출 및 검색 기능)
st.markdown("---")
st.subheader("🔍 장비 상세 데이터 목록")
search_query = st.text_input("검색어 입력 (장비명, 모델명, 부서명 등):", "")

# 검색어가 있으면 필터링, 없으면 전체 표시
if search_query:
    display_target_df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)].copy()
    st.write(f"검색 결과: {len(display_target_df):,} 대")
else:
    display_target_df = df.copy()
    st.write(f"전체 목록: {len(display_target_df):,} 대")

# 취득가 천원 단위 변환 및 천 단위 콤마 포맷팅 적용
display_df = display_target_df[['관리번호', '장비명/구성품명', '사용\n부서', '자산\n상태', '등급\n분류', '취득가']].copy()
display_df['취득가(천원)'] = (display_df['취득가'] / 1_000).round(1).apply(lambda x: f"{x:,.1f}")
display_df = display_df.drop(columns=['취득가'])

st.dataframe(display_df, hide_index=True)