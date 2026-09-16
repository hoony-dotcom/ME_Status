import os
import glob
import re
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# 1. 페이지 설정
st.set_page_config(page_title="의료장비 현황 대시보드", page_icon="🏥", layout="wide")

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 2. 폴더 내에서 가장 최신의 '의료기기 현황조회' 엑셀 파일 자동 탐색 함수
def get_latest_excel_file():
    # '의료기기 현황조회'로 시작하는 엑셀 파일들 검색
    pattern = '의료기기 현황조회*.xlsx'
    files = glob.glob(pattern)
    
    if not files:
        # 파일이 없을 경우 기본값 반환
        return '의료기기 현황조회_20260901091435400.xlsx'
    
    # 파일 수정 일시(mtime)가 가장 최신인 파일을 선택
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
    
    # 사용부서가 '88'인 경우 '매각완료'로 이름 변경
    df['사용부서_str'] = df['사용\n부서'].astype(str).str.strip()
    df.loc[df['사용부서_str'] == '88', '사용\n부서'] = '매각완료'
    
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

# 6. 대시보드 제목 및 기준일 표시
st.title("🏥 병원 의료장비 현황 대시보드")
st.markdown(f"**📅 기준일:** {base_date_display} &nbsp;&nbsp;|&nbsp;&nbsp; **현재 필터:** {filter_status_text}")
st.markdown("---")

# 7. 상단 KPI 요약 메트릭 (금액 천원 단위 환산)
total_cost_thousand = df['취득가'].sum() / 1_000

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="조회 장비 대수", value=f"{len(df):,} 건")
with col2:
    st.metric(label="총 취득가액", value=f"{total_cost_thousand:,.1f} 천원")
with col3:
    high_risk_count = len(df[df['등급\n분류'].astype(str).str.contains('3|4')])
    st.metric(label="고위험 장비 (3/4등급)", value=f"{high_risk_count:,} 건")
with col4:
    d_status_count = len(df[df['자산\n상태'] == 'D'])
    st.metric(label="노후/불용 검토 (D등급)", value=f"{d_status_count:,} 건")

st.markdown("---")

# 8. 메인 그래프 영역 (자산 등급별 / 위험 등급별)
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 자산 상태별 현황 (Asset Status)")
    status_counts = df['자산\n상태'].value_counts()
    
    fig1, ax1 = plt.subplots(figsize=(7, 5))
    ax1.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('pastel'))
    ax1.axis('equal')
    st.pyplot(fig1)
    
    # 자산 상태 상세 데이터에 설명 열 추가
    status_desc_map = {
        'A': '정상운영 / 사용중',
        'B': '하자보증 / 신규도입',
        'C': '예비 / 대기중',
        'D': '노후 / 불용검토 / 폐기대상'
    }
    
    status_df = pd.DataFrame({
        '자산상태': status_counts.index,
        '건수': status_counts.values
    })
    status_df['설명'] = status_df['자산상태'].map(status_desc_map).fillna('기타')
    status_df = status_df[['자산상태', '설명', '건수']]

    with st.expander("자산 상태별 상세 데이터 보기"):
        st.dataframe(status_df, hide_index=True)

with col_right:
    st.subheader("📊 식약처/위험 등급별 현황 (Risk Grade)")
    grade_counts = df['등급\n분류'].value_counts()
    
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    sns.barplot(x=grade_counts.index, y=grade_counts.values, ax=ax2, palette='viridis')
    ax2.set_ylabel("장비 대수")
    ax2.set_xlabel("등급 분류")
    plt.xticks(rotation=45)
    st.pyplot(fig2)
    
    grade_df = pd.DataFrame({
        '등급분류': grade_counts.index,
        '건수': grade_counts.values
    })
    
    with st.expander("위험 등급별 상세 데이터 보기"):
        st.dataframe(grade_df, hide_index=True)

# 9. 하단 장비 상세 데이터 목록 (기본 노출 및 검색 기능)
st.markdown("---")
st.subheader("🔍 장비 상세 데이터 목록")
search_query = st.text_input("검색어 입력 (장비명, 모델명, 부서명 등):", "")

# 검색어가 있으면 필터링, 없으면 전체 표시
if search_query:
    display_target_df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)].copy()
    st.write(f"검색 결과: {len(display_target_df)}건")
else:
    display_target_df = df.copy()
    st.write(f"전체 목록: {len(display_target_df)}건")

# 취득가 천원 단위 변환 표시
display_df = display_target_df[['관리번호', '장비명/구성품명', '사용\n부서', '자산\n상태', '등급\n분류', '취득가']].copy()
display_df['취득가(천원)'] = (display_df['취득가'] / 1_000).round(1)
display_df = display_df.drop(columns=['취득가'])

st.dataframe(display_df, hide_index=True)