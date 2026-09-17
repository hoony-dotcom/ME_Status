# 앱 이름: 병원 의료장비 현황 대시보드
import os
import glob
import re
from datetime import datetime
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# 1. 페이지 설정
st.set_page_config(
    page_title="의료장비 현황 대시보드", 
    page_icon="🏥", 
    layout="wide",
    initial_sidebar_state="auto"
)

# 한글 폰트 및 다크모드 대응 텍스트/축 색상 설정
def set_korean_font():
    font_list = [f.name for f in fm.fontManager.ttflist]
    candidates = [
        'NanumGothic', 'Nanum Barun Gothic', 'NanumSquare', 
        'Malgun Gothic', 'AppleGothic', 'Apple SD Gothic Neo', 'DejaVu Sans'
    ]
    
    selected_font = None
    for candidate in candidates:
        for f_name in font_list:
            if candidate.lower() in f_name.lower():
                selected_font = f_name
                break
        if selected_font:
            break
            
    if selected_font:
        plt.rcParams['font.family'] = selected_font
    else:
        plt.rcParams['font.family'] = 'sans-serif'
        
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['figure.facecolor'] = 'none'
    plt.rcParams['axes.facecolor'] = 'none'
    # 다크모드 시인성 확보를 위해 기본 텍스트 및 축 색상을 회색톤(또는 자동응답)으로 지정
    plt.rcParams['text.color'] = '#555555'
    plt.rcParams['axes.labelcolor'] = '#555555'
    plt.rcParams['xtick.color'] = '#555555'
    plt.rcParams['ytick.color'] = '#555555'

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

# 4. 데이터 로드 및 전처리 함수 (사용부서 88: 매각완료, 77: 노후불용 처리중)
@st.cache_data
def load_data(path):
    df = pd.read_excel(path, sheet_name=0)
    
    df['사용부서_str'] = df['사용\n부서'].astype(str).str.strip()
    df = df[df['사용\n부서'].notna() & (df['사용부서_str'] != '') & (df['사용부서_str'].str.lower() != 'nan')].copy()
    
    df.loc[df['사용부서_str'] == '88', '사용\n부서'] = '매각완료'
    df.loc[df['사용부서_str'] == '77', '사용\n부서'] = '노후불용 처리중'
    
    df['등급\n분류'] = df['등급\n분류'].fillna('해당무').astype(str).str.strip()
    df.loc[df['등급\n분류'] == '', '등급\n분류'] = '해당무'
    
    df['취득가'] = pd.to_numeric(df['취득가'], errors='coerce').fillna(0)
    
    def calculate_period_grade(date_val):
        try:
            if pd.isna(date_val) or str(date_val).strip() == '' or str(date_val).lower() == 'nat' or str(date_val).lower() == 'nan':
                return '납품대기'
            
            dt = pd.to_datetime(date_val)
            if pd.isna(dt):
                return '납품대기'
                
            today = datetime.today()
            years = (today - dt).days / 365.25
            
            if years < 0:
                return '납품대기'
            elif years < 3:
                return '가 (3년 이내)'
            elif years < 7:
                return '나 (3년~7년)'
            elif years < 15:
                return '다 (7년~15년)'
            else:
                return '라 (15년 이상)'
        except Exception:
            return '납품대기'

    if '취득일자' in df.columns:
        df['사용기간_등급'] = df['취득일자'].apply(calculate_period_grade)
    else:
        df['사용기간_등급'] = '납품대기'
    
    return df

raw_df = load_data(file_path)

# 5. 사이드바 설정
st.sidebar.markdown("### 📌 제작 및 문의")
st.sidebar.markdown("**인하대병원 의용공학팀**\n\n📧 [dhkoh@inhauh.com](mailto:dhkoh@inhauh.com)")
st.sidebar.markdown("---")

st.sidebar.header("⚙️ 대시보드 필터 설정")
st.sidebar.info(f"📂 **사용 중인 파일**:\n`{os.path.basename(file_path)}`")

include_sold = st.sidebar.checkbox("매각완료 장비 포함하기", value=False, help="체크하면 매각완료(부서코드 88) 장비가 포함되어 조회됩니다.")
include_obsolete = st.sidebar.checkbox("노후불용 처리중 장비 포함하기", value=True, help="체크 해제하면 노후불용 처리중(부서코드 77) 장비가 제외됩니다.")
include_delivery_wait = st.sidebar.checkbox("납품대기(취득일자 없음) 장비 포함하기", value=True, help="체크 해제하면 취득일자가 없어 '납품대기'로 분류된 장비가 제외됩니다.")

st.sidebar.markdown("---")
st.sidebar.subheader("🔗 의용공학팀 개발 앱")
st.sidebar.markdown("1. [의료장비 투자집행 계획 실적](https://buly.kr/DEbvdwF)")
st.sidebar.markdown("2. [의료장비 현황 바로가기](https://buly.kr/7mERs3u)")

df = raw_df.copy()

if not include_sold:
    df = df[df['사용\n부서'] != '매각완료'].copy()

if not include_obsolete:
    df = df[df['사용\n부서'] != '노후불용 처리중'].copy()

if not include_delivery_wait:
    df = df[df['사용기간_등급'] != '납품대기'].copy()

filter_status_desc = []
filter_status_desc.append("매각완료 포함" if include_sold else "매각완료 제외")
filter_status_desc.append("노후불용 포함" if include_obsolete else "노후불용 제외")
filter_status_desc.append("납품대기 포함" if include_delivery_wait else "납품대기 제외")
filter_status_text = " | ".join(filter_status_desc)

total_count_for_ratio = len(df) if len(df) > 0 else 1

# 전체 총 취득가 (천원 단위) 계산
total_cost_sum_grand = df['취득가'].sum() / 1_000
if total_cost_sum_grand <= 0:
    total_cost_sum_grand = 1.0

# 6. 상단 타이틀 및 기준일 표시
st.title("🏥 병원 의료장비 현황 대시보드")
st.markdown(f"**📅 기준일:** {base_date_display} &nbsp;&nbsp;|&nbsp;&nbsp; **현재 필터:** {filter_status_text}")
st.markdown("---")

# 7. 상단 KPI 요약 카드
total_cost_thousand = df['취득가'].sum() / 1_000
high_risk_count = len(df[df['등급\n분류'].astype(str).str.contains('3|4')])
d_status_count = len(df[df['자산\n상태'] == 'D'])

kpi_html = f"""
<style>
.kpi-container {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 20px;
}}
.kpi-card {{
    flex: 1;
    min-width: 160px;
    background-color: var(--secondary-background-color, #f8f9fa);
    border: 1px solid var(--border-color, #e9ecef);
    border-radius: 8px;
    padding: 14px 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}}
.kpi-label {{
    font-size: 13px;
    color: var(--text-color, #6c757d);
    font-weight: 600;
    margin-bottom: 6px;
    word-break: keep-all;
}}
.kpi-value {{
    font-size: 22px;
    color: var(--text-color, #212529);
    font-weight: bold;
    word-break: break-all;
    line-height: 1.3;
}}
@media (max-width: 768px) {{
    .kpi-card {{
        min-width: 100%;
    }}
    .kpi-value {{
        font-size: 20px;
    }}
}}
</style>

<div class="kpi-container">
    <div class="kpi-card">
        <div class="kpi-label">조회 장비 대수</div>
        <div class="kpi-value">{len(df):,} 대</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">총 취득가액</div>
        <div class="kpi-value">{total_cost_thousand:,.1f} 천원</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">고위험 장비 (3/4등급)</div>
        <div class="kpi-value">{high_risk_count:,} 대</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">노후/불용 검토 (D등급)</div>
        <div class="kpi-value">{d_status_count:,} 대</div>
    </div>
</div>
"""

st.markdown(kpi_html, unsafe_allow_html=True)
st.markdown("---")

# 8. 메인 그래프 영역 (1단: 자산 상태별 / 사용기간 기준 상태등급별)
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.subheader("📊 자산 상태별 현황")
    status_counts = df['자산\n상태'].value_counts()
    
    fig1, ax1 = plt.subplots(figsize=(6, 4.5))
    
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return f'{pct:.1f}%\n({val:,}대)'
        return my_autopct

    wedges, texts, autotexts = ax1.pie(
        status_counts, 
        labels=status_counts.index, 
        autopct=make_autopct(status_counts.values), 
        startangle=90, 
        colors=sns.color_palette('pastel')
    )
    
    # 파이차트 글자 색상 명시 (다크모드 대응)
    for t in texts + autotexts:
        t.set_fontsize(10)
        t.set_color('inherit') # 혹은 가시적인 색상 적용 가능
        
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

with row1_col2:
    st.subheader("📊 사용기간 기준 상태등급 현황")
    period_order = ['납품대기', '가 (3년 이내)', '나 (3년~7년)', '다 (7년~15년)', '라 (15년 이상)']
    period_counts = df['사용기간_등급'].value_counts().reindex(period_order).fillna(0)
    
    fig_period, ax_period = plt.subplots(figsize=(6, 4.5))
    barplot_obj = sns.barplot(x=period_counts.index, y=period_counts.values, ax=ax_period, palette='crest')
    
    for p in barplot_obj.patches:
        height = p.get_height()
        if height > 0:
            pct_val = (height / total_count_for_ratio) * 100
            ax_period.annotate(
                f'{int(height):,}대\n({pct_val:.1f}%)',
                (p.get_x() + p.get_width() / 2., height),
                ha='center', va='bottom',
                xytext=(0, 3),  
                textcoords='offset points',
                fontsize=9,
                fontweight='bold',
                color='#333333' if plt.rcParams.get('figure.facecolor') == 'none' else 'white'
            )
            
    ax_period.set_ylabel("대수")
    ax_period.set_xlabel("사용기간 등급")
    
    # 축 글자 가시성 확보를 위한 설정
    ax_period.tick_params(colors='#666666', labelsize=9)
    ax_period.xaxis.label.set_color('#666666')
    ax_period.yaxis.label.set_color('#666666')
    
    max_val = period_counts.max() if len(period_counts) > 0 else 1
    ax_period.set_ylim(0, max_val * 1.25)
    
    plt.xticks(rotation=25)
    st.pyplot(fig_period)
    
    with st.container():
        st.markdown("**📋 사용기간 등급 기준 안내**")
        st.markdown("- **납품대기**: 취득일자 정보가 없는 장비")
        st.markdown("- **가등급**: 취득일 기준 3년 이내")
        st.markdown("- **나등급**: 취득일 기준 3년 이상 ~ 7년 이내")
        st.markdown("- **다등급**: 취득일 기준 7년 이상 ~ 15년 이내")
        st.markdown("- **라등급**: 취득일 기준 15년 이상")

st.markdown("")

# 9. 메인 그래프 영역 (2단: 위험 등급별 / 부서별 장비 보유 TOP 10)
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
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
    
    fig2, ax2 = plt.subplots(figsize=(6, 4.5))
    barplot_grade2 = sns.barplot(x=grade_counts.index, y=grade_counts.values, ax=ax2, palette='viridis')
    
    for p in barplot_grade2.patches:
        height = p.get_height()
        if height > 0:
            pct_val = (height / total_count_for_ratio) * 100
            ax2.annotate(
                f'{int(height):,}대\n({pct_val:.1f}%)',
                (p.get_x() + p.get_width() / 2., height),
                ha='center', va='bottom',
                xytext=(0, 3),  
                textcoords='offset points',
                fontsize=9,
                fontweight='bold'
            )
            
    ax2.set_ylabel("대수")
    ax2.set_xlabel("등급")
    ax2.tick_params(colors='#666666', labelsize=9)
    ax2.xaxis.label.set_color('#666666')
    ax2.yaxis.label.set_color('#666666')
    
    max_grade2 = grade_counts.max() if len(grade_counts) > 0 else 1
    ax2.set_ylim(0, max_grade2 * 1.25)
    
    plt.xticks(rotation=45)
    st.pyplot(fig2)
    
    with st.container():
        st.markdown("💡 **팁:** 의료장비의 위험도 등급별 장비 분포 현황을 보여줍니다.")

with row2_col2:
    st.subheader("📊 부서별 장비 보유 TOP 10 (대수 기준)")
    dept_counts = df['사용\n부서'].value_counts().head(10)
    
    fig3, ax3 = plt.subplots(figsize=(6, 4.5))
    barplot_dept3 = sns.barplot(y=dept_counts.index, x=dept_counts.values, ax=ax3, palette='mako', orient='h')
    
    for p in barplot_dept3.patches:
        width = p.get_width()
        if width > 0:
            pct_val = (width / total_count_for_ratio) * 100
            ax3.annotate(
                f'{int(width):,}대 ({pct_val:.1f}%)',
                (width, p.get_y() + p.get_height() / 2.),
                ha='left', va='center',
                xytext=(5, 0),  
                textcoords='offset points',
                fontsize=9,
                fontweight='bold'
            )
            
    ax3.set_xlabel("장비 대수")
    ax3.set_ylabel("부서명")
    ax3.tick_params(colors='#666666', labelsize=9)
    ax3.xaxis.label.set_color('#666666')
    ax3.yaxis.label.set_color('#666666')
    
    max_dept3 = dept_counts.max() if len(dept_counts) > 0 else 1
    ax3.set_xlim(0, max_dept3 * 1.3)
    
    st.pyplot(fig3)
    
    with st.container():
        st.markdown("💡 **팁:** 부서별 장비 대수 상위 10개 부서의 현황을 보여줍니다.")

st.markdown("")

# 10. 메인 그래프 영역 (3단: 부서별 취득가 합계 TOP 10)
row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    st.subheader("📊 부서별 취득가 합계 TOP 10 (금액 기준)")
    dept_cost_sum = df.groupby('사용\n부서')['취득가'].sum().sort_values(ascending=False).head(10) / 1_000
    
    fig4, ax4 = plt.subplots(figsize=(6, 4.5))
    barplot_dept4 = sns.barplot(y=dept_cost_sum.index, x=dept_cost_sum.values, ax=ax4, palette='rocket', orient='h')
    
    for p in barplot_dept4.patches:
        width = p.get_width()
        if width > 0:
            pct_val = (width / total_cost_sum_grand) * 100
            ax4.annotate(
                f'{width:,.1f}천원 ({pct_val:.1f}%)',
                (width, p.get_y() + p.get_height() / 2.),
                ha='left', va='center',
                xytext=(5, 0),  
                textcoords='offset points',
                fontsize=8.5,
                fontweight='bold'
            )
            
    ax4.set_xlabel("취득가 합계 (천원)")
    ax4.set_ylabel("부서명")
    ax4.tick_params(colors='#666666', labelsize=9)
    ax4.xaxis.label.set_color('#666666')
    ax4.yaxis.label.set_color('#666666')
    
    max_dept4 = dept_cost_sum.max() if len(dept_cost_sum) > 0 else 1
    ax4.set_xlim(0, max_dept4 * 1.35)
    
    st.pyplot(fig4)
    
    with st.container():
        st.markdown("💡 **팁:** 부서별 장비 취득가 합계 상위 10개 부서의 현황을 보여줍니다.")

with row3_col2:
    st.info("💡 **팁:** 상단 사이드바의 필터 옵션을 활용하여 매각완료, 노후불용 및 납품대기 장비를 유연하게 포함하거나 제외해 보세요.")

# 11. 하단 장비 상세 데이터 목록 (기본 노출 및 검색 기능)
st.markdown("---")
st.subheader("🔍 장비 상세 데이터 목록")
search_query = st.text_input("검색어 입력 (장비명, 모델명, 부서명 등):", "")

if search_query:
    display_target_df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)].copy()
    st.write(f"검색 결과: {len(display_target_df):,} 대")
else:
    display_target_df = df.copy()
    st.write(f"전체 목록: {len(display_target_df):,} 대")

display_cols = ['관리번호', '장비명/구성품명', '사용\n부서', '의공담당', '취득일자', 'z산\n상태' if 'z산\n상태' in df.columns else '자산\n상태', '등급\n분류', '사용기간_등급', '취득가']
# 안전한 컬럼 매핑 조정
display_cols = ['관리번호', '장비명/구성품명', '사용\n부서', '의공담당', '취득일자', '자산\n상태', '등급\n분류', '사용기간_등급', '취득가']
existing_display_cols = [c for c in display_cols if c in display_target_df.columns]

display_df = display_target_df[existing_display_cols].copy()
display_df['취득가'] = 'hidden'

hide_dataframe_row_index = """
<style>
[data-testid="stElementToolbar"] {
    display: none;
}
</style>
"""
st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

st.dataframe(display_df, hide_index=True, use_container_width=True)