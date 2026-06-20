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
st.title("🏆
