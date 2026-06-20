import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 페이지 기본 설정 및 레이아웃 구성
st.set_page_config(page_title="축구 팀 랭킹 시스템", layout="wide")

@st.cache_data
def load_initial_data():
    """초기 파일 로드 함수 (결측치 제외 및 타입 변환 적용)"""
    try:
        df = pd.read_csv("results.csv")
        # 스코어 데이터에 NA나 빈 값이 있으면 제외
        df = df.dropna(subset=['home_score', 'away_score'])
        df['home_score'] = df['home_score'].astype(int)
        df['away_score'] = df['away_score'].astype(int)
        return df[['date', 'home_team', 'away_team', 'home_score', 'away_score']]
    except FileNotFoundError:
        # 파일이 없을 경우를 대비한 빈 데이터프레임 구조 생성
        return pd.DataFrame(columns=['date', 'home_team', 'away_team', 'home_score', 'away_score'])

# 세션 상태(Session State)를 통해 데이터 누적 유지
if 'match_data' not in st.session_state:
    st.session_state.match_data = load_initial_data()

# 2. 랭킹 계산 함수 (승점제 규칙 적용)
def calculate_ranking(df):
    stats = {}
    
    for _, row in df.iterrows():
        home, away = row['home_team'], row['away_team']
        h_score, a_score = int(row['home_score']), int(row['away_score'])
        
        # 팀 스탯 사전 초기화
        for team in [home, away]:
            if team not in stats:
                stats[team] = {'경기수': 0, '승': 0, '무': 0, '패': 0, '득점': 0, '실점': 0, '골득실': 0, '승점': 0}
        
        stats[home]['경기수'] += 1
        stats[away]['경기수'] += 1
        stats[home]['득점'] += h_score
        stats[home]['실점'] += a_score
        stats[away]['득점'] += a_score
        stats[away]['실점'] += h_score
        
        # 승(3점), 무(1점), 패(0점) 계산
        if h_score > a_score:
            stats[home]['승'] += 1
            stats[home]['승점'] += 3
            stats[away]['패'] += 1
        elif h_score < a_score:
            stats[away]['승'] += 1
            stats[away]['승점'] += 3
            stats[home]['패'] += 1
        else:
            stats[home]['무'] += 1
            stats[home]['승점'] += 1
            stats[away]['무'] += 1
            stats[away]['승점'] += 1

    # 데이터프레임 변환 후 순위 정렬
    ranking_df = pd.DataFrame.from_dict(stats, orient='index')
    if not ranking_df.empty:
        ranking_df['골득실'] = ranking_df['득점'] - ranking_df['실점']
        # 정렬 기준: 승점 -> 골득실 -> 다득점
        ranking_df = ranking_df.sort_values(by=['승점', '골득실', '득점'], ascending=False)
        ranking_df.insert(0, '순위', range(1, len(ranking_df) + 1))
    
    return ranking_df

# 3. 메인 웹 UI 화면 구성
st.title("🏆 실시간 축구 팀 랭킹 시스템")
st.write("경기 결과를 바탕으로 승점, 골득실, 다득점을 계산하여 실시간 순위표를 업데이트합니다.")

# 세 가지 기능을 탭으로 분리
tab1, tab2, tab3 = st.tabs(["📊 실시간 랭킹", "➕ 경기 결과 입력", "📜 전체 경기 기록"])

# --- [탭 1] 실시간 랭킹 확인 ---
with tab1:
    st.header("현재 팀 순위표")
    ranking_res = calculate_ranking(st.session_state.match_data)
    
    if not ranking_res.empty:
        st.dataframe(ranking_res, use_container_width=True)
    else:
        st.info("등록된 경기 데이터가 없습니다. 먼저 경기를 입력하거나 csv 파일을 확인해 주세요.")

# --- [탭 2] 경기 결과 입력 ---
with tab2:
    st.header("새로운 경기 결과 등록")
    
    # 데이터 내의 모든 유니크한 팀 목록 추출
    all_teams = sorted(list(set(st.session_state.match_data['home_team'].unique()) | set(st.session_state.match_data['away_team'].unique())))
    
    # 폼 생성
    with st.form("match_input_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            match_date = st.date_input("경기 날짜", datetime.today(), key="form_date")
        with col2:
            home_team = st.selectbox("홈 팀 선택", all_teams, key="form_home_team")
        with col3:
            default_away_idx = 1 if len(all_teams) > 1 else 0
            away_team = st.selectbox("원정 팀 선택", all_teams, index=default_away_idx, key="form_away_team")
            
        col4, col5 = st.columns(2)
        with col4:
            home_score = st.number_input(f"[{home_team}] 득점", min_value=0, step=1, value=0, key="form_home_score")
        with col5:
            away_score = st.number_input(f"[{away_team}] 득점", min_value=0, step=1, value=0, key="form_away_score")
            
        submit_btn = st.form_submit_button("⚽ 경기 결과 저장 및 반영")
        
        # 버튼을 눌렀을 때의 데이터 처리 로직
        if submit_btn:
            if home_team == away_team:
                st.error("⚠️ 홈 팀과 원정 팀은 서로 다른 팀이어야 합니다. 다시 선택해 주세요.")
            else:
                # 새 경기 데이터를 DataFrame 형태로 준비
                new_match = pd.DataFrame([{
                    'date': match_date.strftime('%Y-%m-%d'),
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': int(home_score),
                    'away_score': int(away_score)
                }])
                
                # 기존 데이터에 신규 데이터 병합(누적)
                st.session_state.match_data = pd.concat([st.session_state.match_data, new_match], ignore_index=True)
                st.success(f"성공적으로 반영되었습니다! ({home_team} {home_score} : {away_score} {away_team})")
                
                # 앱을 다시 실행(rerun)시켜 상단 랭킹 탭에 즉시 반영되도록 처리
                st.rerun()

# --- [탭 3] 전체 경기 기록 히스토리 확인 ---
with tab3:
    st.header("전체 경기 내역 목록")
    st.write(f"현재까지 기록된 총 경기 수: **{len(st.session_state.match_data)}**개")
    
    if not st.session_state.match_data.empty:
        st.dataframe(st.session_state.match_data.iloc[::-1], use_container_width=True)
    else:
        st.info("기록된 데이터가 없습니다.")
