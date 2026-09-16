import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# 1. 페이지 설정
st.set_page_config(page_title="의료장비 현황 대시보드", page_icon="🏥", layout="wide")

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 2. 데이터 로드 및 전처리 함수
@st.cache_data
def load_data():
    file_path = '의료기기 현황조회_20260901091435400.xlsx'
    df = pd.read_excel(file_path, sheet_name=0)
    
    # 사용부서가 '88'인 데이터 제외 (문자열 변환 및 공백 제거 후 비교)
    df['사용부서_str'] = df['사용\n부서'].astype(str).str.strip()
    df_filtered = df[df['사용부서_str'] != '88'].copy()
    
    return df_filtered

df = load_data()

# 3. 대시보드 제목
st.title("🏥 병원 의료장비 현황 대시보드")
st.markdown("엑셀 데이터 기반 (사용부서 '88' 제외) 자산 상태별, 위험 등급별 현황 모니터링 시스템입니다.")
st.markdown("---")

# 4. 상단 KPI 요약 메트릭
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="조회 장비 대수 (88부서 제외)", value=f"{len(df):,} 건")
with col2:
    total_cost = df['취득가'].sum()
    st.metric(label="총 취득가액", value=f"{total_cost:,.0f} 원")
with col3:
    high_risk_count = len(df[df['등급\n분류'].astype(str).str.contains('3|4')])
    st.metric(label="고위험 장비 (3/4등급)", value=f"{high_risk_count:,} 건")
with col4:
    d_status_count = len(df[df['자산\n상태'] == 'D'])
    st.metric(label="노후/불용 검토 (D등급)", value=f"{d_status_count:,} 건")

st.markdown("---")

# 5. 메인 그래프 영역 (자산 등급별 / 위험 등급별)
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
    # 컬럼 순서 재배치 (자산상태, 설명, 건수)
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

# 6. 하단 추가 필터 및 검색 기능
st.markdown("---")
st.subheader("🔍 장비 상세 데이터 검색")
search_query = st.text_input("장비명, 모델명 또는 부서명을 입력하세요:")
if search_query:
    filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
    st.write(f"검색 결과: {len(filtered_df)}건")
    st.dataframe(filtered_df[['관리번호', '장비명/구성품명', '사용\n부서', '자산\n상태', '등급\n분류', '취득가']])
else:
    st.info("검색어를 입력하면 조건에 맞는 의료장비 목록을 실시간으로 확인할 수 있습니다.")