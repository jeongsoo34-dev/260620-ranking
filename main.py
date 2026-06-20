import streamlit as st
import pandas as pd
from datetime import datetime

# [설정] 페이지 기본 레이아웃 구성
st.set_page_config(page_title="축구 팀 랭킹 시스템", layout="wide")

@st.cache_data
def load_initial_data():
    """results.csv 파일을 안전하게 로드하는 함수"""
    try:
        df = pd.read_csv("results.csv")
        # 결측치(빈 칸)가 있는 데이터는 미리 제거
        df = df.dropna(subset=['home_score', 'away_score'])
        df['home_score'] = df['home_score'].astype(int)
        df['away_score'] = df['away_score'].astype(int)
        return df[['date', 'home_team', 'away_team', 'home_score', 'away_score']]
    except FileNotFoundError:
        # 파일이 없을 때 에러가 나지 않도록 빈 데이터틀 제공
        return pd.DataFrame(columns=['date', 'home_team', 'away_team', 'home_score', 'away_score'])

# [세션 상태] 사용자가 새로 추가하는 데이터를 프로그램 메모리에 유지
if 'match_data' not in st.session_state:
    st.session_state.match_data = load_initial_data()

# [연산] 누적된 데이터를 바탕으로 랭킹(승점/골득실) 계산
def calculate_ranking(df):
    stats = {}
    for _, row in df.iterrows():
        home, away = row['home_team'], row['away_team']
        h_score, a_score = int(row['home_score']), int(row['away_score'])
        
        for team in [home, away]:
            if team not in stats:
                stats[team] = {'경기수': 0, '승': 0, '무': 0, '패': 0, '득점': 0, '실점': 0, '골득실': 0, '승점': 0}
        
        stats[home]['경기수'] += 1
        stats[away]['경기수'] += 1
        stats[home]['득점'] += h_score
        stats[home]['실점'] += a_score
        stats[away]['득점'] += a_score
        stats[away]['실점'] += h_score
        
        if h_score > a_score:
            stats[home]['승'] += 1; stats[home]['승점'] += 3; stats[away]['패'] += 1
        elif h_score < a_score:
            stats[away]['승'] += 1; stats[away]['승점'] += 3; stats[home]['패'] += 1
        else:
            stats[home]['무'] += 1; stats[home]['승점'] += 1; stats[away]['무'] += 1; stats[away]['승점'] += 1

    ranking_df = pd.DataFrame.from_dict(stats, orient='index')
    if not ranking_df.empty:
        ranking_df['골득실'] = ranking_df['득점'] - ranking_df['실점']
        ranking_df = ranking_df.sort_values(by=['승점', '골득실', '득점'], ascending=False)
        ranking_df.insert(0, '순위', range(1, len(ranking_df) + 1))
    return ranking_df

# --- 화면 UI 레이아웃 시작 ---
st.title("🏆 실시간 축구 팀 랭킹 시스템")
st.write("새로운 경기 결과를 입력하면 실시간으로 승점과 순위가 계산됩니다.")

tab1, tab2, tab3 = st.tabs(["📊 실시간 랭킹", "➕ 경기 결과 입력", "📜 전체 경기 기록"])

# [탭 1] 실시간 랭킹 확인
with tab1:
    st.header("현재 팀 순위표")
    ranking_res = calculate_ranking(st.session_state.match_data)
    if not ranking_res.empty:
        st.dataframe(ranking_res, use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

# [탭 2] 경기 결과 입력 (★ 버그 해결을 위해 완전히 개편된 부분)
with tab2:
    st.header("새로운 경기 결과 등록")
    st.write("팀과 날짜를 선택한 후, 아래 점수를 입력하고 등록 버튼을 눌러주세요.")
    
    # 1. 기존 데이터에서 고유한 팀 목록 가져오기
    all_teams = sorted(list(set(st.session_state.match_data['home_team'].unique()) | set(st.session_state.match_data['away_team'].unique())))
    
    # 2. 폼 바깥(일반 화면)에 팀 선택 상자 배치 (이렇게 해야 버그가 안 납니다!)
    col1, col2, col3 = st.columns(3)
    with col1:
        match_date = st.date_input("경기 날짜 선택", datetime.today(), key="select_date")
    with col2:
        home_team = st.selectbox("🏠 홈 팀 선택", all_teams, key="select_home_team")
    with col3:
        default_idx = 1 if len(all_teams) > 1 else 0
        away_team = st.selectbox("✈️ 원정 팀 선택", all_teams, index=default_idx, key="select_away_team")
        
    # 3. 점수 입력 및 최종 제출 버튼 배치
    st.markdown("---")
    col4, col5 = st.columns(2)
    with col4:
        home_score = st.number_input(f"[{home_team}] 팀의 득점", min_value=0, step=1, value=0, key="input_home_score")
    with col5:
        away_score = st.number_input(f"[{away_team}] 팀의 득점", min_value=0, step=1, value=0, key="input_away_score")
        
    # 4. 데이터 저장 버튼
    submit_btn = st.button("⚽ 경기 결과 저장 및 반영하기", type="primary", use_container_width=True)
    
    if submit_btn:
        if home_team == away_team:
            st.error("⚠️ 홈 팀과 원정 팀은 서로 다른 팀이어야 합니다. 다시 선택해 주세요.")
        else:
            # 새 데이터 생성 및 병합
            new_match = pd.DataFrame([{
                'date': match_date.strftime('%Y-%m-%d'),
                'home_team': home_team,
                'away_team': away_team,
                'home_score': int(home_score),
                'away_score': int(away_score)
            }])
            st.session_state.match_data = pd.concat([st.session_state.match_data, new_match], ignore_index=True)
            st.success(f"성공적으로 반영되었습니다! ({home_team} {home_score} : {away_score} {away_team})")
            # 즉시 새로고침하여 랭킹 반영
            st.rerun()

# [탭 3] 전체 경기 기록 히스토리 확인
with tab3:
    st.header("전체 경기 내역 목록")
    if not st.session_state.match_data.empty:
        st.dataframe(st.session_state.match_data.iloc[::-1], use_container_width=True)
    else:
        st.info("기록된 데이터가 없습니다.")
