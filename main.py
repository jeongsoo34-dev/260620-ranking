import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 페이지 기본 설정 및 데이터 로드
st.set_page_config(page_title="축구 팀 랭킹 시스템", layout="wide")

@st.cache_data
def load_initial_data():
    # 제공된 csv 파일 로드 (파일명이 다를 경우 수정 가능)
    try:
        df = pd.read_csv("results.csv")
        # 데이터가 너무 많을 경우 최근 데이터나 결측치가 없는 데이터만 기본으로 사용
        df = df.dropna(subset=['home_score', 'away_score'])
        df['home_score'] = df['home_score'].astype(int)
        df['away_score'] = df['away_score'].astype(int)
        return df[['date', 'home_team', 'away_team', 'home_score', 'away_score']]
    except FileNotFoundError:
        # 파일이 없을 경우 빈 데이터프레임 반환
        return pd.DataFrame(columns=['date', 'home_team', 'away_team', 'home_score', 'away_score'])

# 세션 상태(Session State)를 통해 앱이 리런되더라도 데이터가 유지되도록 설정
if 'match_data' not in st.session_state:
    st.session_state.match_data = load_initial_data()

# 2. 랭킹 산정 함수 정의 (승 3점, 무 1점, 패 0점 / 골득실 / 다득점 순)
def calculate_ranking(df):
    stats = {}
    
    for _, row in df.iterrows():
        home, away = row['home_team'], row['away_team']
        h_score, a_score = int(row['home_score']), int(row['away_score'])
        
        # 팀 존재 여부 확인 및 초기화
        for team in [home, away]:
            if team not in stats:
                stats[team] = {'경기수': 0, '승': 0, '무': 0, '패': 0, '득점': 0, '실점': 0, '골득실': 0, '승점': 0}
        
        # 경기수 및 득실점 기록
        stats[home]['경기수'] += 1
        stats[away]['경기수'] += 1
        stats[home]['득점'] += h_score
        stats[home]['실점'] += a_score
        stats[away]['득점'] += a_score
        stats[away]['실점'] += h_score
        
        # 승패에 따른 승점 부여
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

    # 데이터프레임 변환 후 골득실 계산
    ranking_df = pd.DataFrame.from_dict(stats, orient='index')
    if not ranking_df.empty:
        ranking_df['골득실'] = ranking_df['득점'] - ranking_df['실점']
        # 승점 -> 골득실 -> 다득점 순으로 정렬
        ranking_df = ranking_df.sort_values(by=['승점', '골득실', '득점'], ascending=False)
        ranking_df.insert(0, '순위', range(1, len(ranking_df) + 1))
    
    return ranking_df

# 3. UI 구성 (상단 타이틀 및 탭 분리)
st.title("🏆 실시간 축구 팀 랭킹 시스템")
st.write("경기 결과를 기반으로 승점(승 3, 무 1, 패 0) 및 골득실을 계산하여 순위를 매깁니다.")

tab1, tab2, tab3 = st.tabs(["📊 실시간 랭킹", "➕ 경기 결과 입력", "📜 전체 경기 기록"])

# --- 탭 1: 실시간 랭킹 ---
with tab1:
    st.header("현재 팀 순위표")
    ranking_res = calculate_ranking(st.session_state.match_data)
    
    if not ranking_res.empty:
        st.dataframe(ranking_res, use_container_width=True)
    else:
        st.info("등록된 경기 데이터가 없습니다.")

# --- 탭 2: 경기 결과 입력 ---
with tab2:
    st.header("새로운 경기 결과 등록")
    
    # 기존 데이터에 있는 팀 리스트 추출 (새로운 팀도 텍스트로 입력 가능하도록 구성 가능)
    all_teams = sorted(list(set(st.session_state.match_data['home_team'].unique()) | set(st.session_state.match_data['away_team'].unique())))
    
    with st.form("match_input_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            match_date = st.date_input("경기 날짜", datetime.today())
        with col2:
            home_team = st.selectbox("홈 팀 선택", all_teams)
        with col3:
            away_team = st.selectbox("원정 팀 선택", all_teams, index=min(1, len(all_teams)-1))
            
        col4, col5 = st.columns(2)
        with col4:
            home_score = st.number_input(f"[{home_team}] 득점", min_value=0, step=1, value=0)
        with col5:
            away_score = st.number_input(f"[{away_team}] 득점", min_value=0, step=1, value=0)
            
        submit_btn = st.form_submit_button("⚽ 경기 결과 저장 및 반영")
        
        if submit_btn:
            if home_team == away_team:
                st.error("홈 팀과 원정 팀은 서로 달라야 합니다.")
            else:
                # 새로운 경기 데이터를 데이터프레임 형태로 생성
                new_match = pd.DataFrame([{
                    'date': match_date.strftime('%Y-%m-%d'),
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': int(home_score),
                    'away_score': int(away_score)
                }])
                
                # 세션 데이터에 추가
                st.session_state.match_data = pd.concat([st.session_state.match_data, new_match], ignore_index=True)
                st.success(f"성공적으로 반영되었습니다! [{home_team} {home_score} : {away_score} {away_team}]")
                # 페이지 리런을 통해 탭1의 랭킹을 즉시 업데이트
                st.rerun()

# --- 탭 3: 전체 경기 기록 ---
with tab3:
    st.header("전체 경기 내역 목록")
    st.write(f"총 {len(st.session_state.match_data)}개의 경기 기록이 있습니다.")
    # 최신 경기가 위로 오도록 역순 출력
    st.dataframe(st.session_state.match_data.iloc[::-1], use_container_width=True)
