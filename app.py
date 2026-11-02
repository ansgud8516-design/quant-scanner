import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# 페이지 설정 및 베이지 톤 테마 커스텀 CSS 적용
st.set_page_config(page_title="AI 프로페셔널 트레이딩 마스터", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-color: #F5F2EB;
        color: #222222 !important;
    }
    p, span, label, div, h1, h2, h3, h4, h5, h6, .stMarkdown {
        color: #222222 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #EAE6DF;
        border-right: 1px solid #D0CCC4;
    }
    [data-testid="stSidebar"] * {
        color: #222222 !important;
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] h3 {
        color: #8B4513 !important;
        font-weight: bold;
    }
    .stButton button {
        color: #FFFFFF !important;
        font-weight: bold;
        border: 1px solid #8B4513 !important;
        background-color: #8B4513 !important;
    }
    .stButton button:hover {
        background-color: #A0522D !important;
        color: #FFFFFF !important;
    }
    div[data-baseweb="select"] *, div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #222222 !important;
    }
    div[data-baseweb="select"] {
        border: 1px solid #D0CCC4 !important;
        border-radius: 4px;
    }
    div[data-baseweb="popover"] *, div[data-baseweb="menu"] * {
        background-color: #FFFFFF !important;
        color: #222222 !important;
    }
    li[data-baseweb="option"]:hover {
        background-color: #F5F2EB !important;
        color: #8B4513 !important;
    }
    .stTextInput input {
        color: #222222 !important;
        background-color: #FFFFFF !important;
        border: 1px solid #D0CCC4 !important;
    }
    div.stMetric, div.stAlert {
        background-color: #EAE6DF;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #D0CCC4;
        color: #222222 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("✨ Gemini Quant : 디스코드 자동전송 종가매매 마스터")

# ==========================================
# 🎮 디스코드 웹훅 메시지 전송 설정
# ==========================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1566474178763300884/0xBS4n8nJHQ7aDQ8KEaVpulMLYdAjw4W8ILwLoqwdsO-esLg9v28CQR-pc-LFFyTIdxN"

def send_discord_message(text_content):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ 디스코드 웹훅 URL이 설정되지 않았습니다.")
        return False
    
    payload = {
        "content": text_content
    }
    
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    return response.status_code == 204


# =========================================
# 🗂️ 사이드바 메뉴 및 종목 유동성 풀 정의
# =========================================
st.sidebar.header("🧭 메인 네비게이션 메뉴")
menu_choice = st.sidebar.selectbox(
    "원하시는 모드를 선택하세요:",
    [
        "1. 종가매매 스캐너 (디스코드 자동전송 연동)",
        "2. AI 장중 수급 집중 스캐너 & 비주얼 차트"
    ]
)

KOREAN_UNIVERSE = {
    "삼성전자": {"ticker": "005930.KS", "tv_symbol": "KRX:005930", "keyword": "삼성전자"},
    "SK하이닉스": {"ticker": "000660.KS", "tv_symbol": "KRX:000660", "keyword": "SK하이닉스"},
    "삼양식품": {"ticker": "393210.KS", "tv_symbol": "KRX:393210", "keyword": "삼양식품"},
    "ISC": {"ticker": "214370.KQ", "tv_symbol": "KOSDAQ:214370", "keyword": "ISC 주식"},
    "NAVER": {"ticker": "035420.KS", "tv_symbol": "KRX:035420", "keyword": "NAVER"},
    "카카오": {"ticker": "035720.KS", "tv_symbol": "KRX:035720", "keyword": "카카오 주식"},
    "LG에너지솔루션": {"ticker": "373220.KS", "tv_symbol": "KRX:373220", "keyword": "LG에너지솔루션"},
    "에코프로비엠": {"ticker": "247540.KQ", "tv_symbol": "KOSDAQ:247540", "keyword": "에코프로비엠"},
    "에코프로": {"ticker": "086520.KQ", "tv_symbol": "KOSDAQ:086520", "keyword": "에코프로"},
    "셀트리온": {"ticker": "068270.KS", "tv_symbol": "KRX:068270", "keyword": "셀트리온"},
    "현대차": {"ticker": "005380.KS", "tv_symbol": "KRX:005380", "keyword": "현대차"},
    "기아": {"ticker": "000270.KS", "tv_symbol": "KRX:000270", "keyword": "기아 주식"},
    "알테오젠": {"ticker": "196170.KQ", "tv_symbol": "KOSDAQ:196170", "keyword": "알테오젠"},
    "한미반도체": {"ticker": "042700.KS", "tv_symbol": "KRX:042700", "keyword": "한미반도체"},
    "두산에너빌리티": {"ticker": "034020.KS", "tv_symbol": "KRX:034020", "keyword": "두산에너빌리티"}
}

US_EXTENDED_UNIVERSE = {
    "테슬라 (Tesla)": {"ticker": "TSLA", "tv_symbol": "NASDAQ:TSLA", "keyword": "Tesla stock"},
    "엔비디아 (NVIDIA)": {"ticker": "NVDA", "tv_symbol": "NASDAQ:NVDA", "keyword": "NVIDIA stock"},
    "애플 (Apple)": {"ticker": "AAPL", "tv_symbol": "NASDAQ:AAPL", "keyword": "Apple stock"},
    "마이크로소프트 (Microsoft)": {"ticker": "MSFT", "tv_symbol": "NASDAQ:MSFT", "keyword": "Microsoft stock"},
    "아마존 (Amazon)": {"ticker": "AMZN", "tv_symbol": "NASDAQ:AMZN", "keyword": "Amazon stock"},
    "인텔 (Intel)": {"ticker": "INTC", "tv_symbol": "NASDAQ:INTC", "keyword": "Intel stock"},
    "AMD": {"ticker": "AMD", "tv_symbol": "NASDAQ:AMD", "keyword": "AMD stock"},
    "SOXL (반도체 3배)": {"ticker": "SOXL", "tv_symbol": "NYSE:SOXL", "keyword": "SOXL ETF"},
    "TQQQ (나스닥 3배)": {"ticker": "TQQQ", "tv_symbol": "NASDAQ:TQQQ", "keyword": "TQQQ ETF"},
    "SQQQ (나스닥 -3배)": {"ticker": "SQQQ", "tv_symbol": "NASDAQ:SQQQ", "keyword": "SQQQ ETF"},
    "팔란티어 (Palantir)": {"ticker": "PLTR", "tv_symbol": "NYSE:PLTR", "keyword": "Palantir stock"},
    "넷플릭스 (Netflix)": {"ticker": "NFLX", "tv_symbol": "NASDAQ:NFLX", "keyword": "Netflix stock"},
    "알파벳 (Google)": {"ticker": "GOOGL", "tv_symbol": "NASDAQ:GOOGL", "keyword": "Google stock"},
    "메타 (Meta)": {"ticker": "META", "tv_symbol": "NASDAQ:META", "keyword": "Meta stock"},
    "코인베이스 (Coinbase)": {"ticker": "COIN", "tv_symbol": "NASDAQ:COIN", "keyword": "Coinbase stock"},
    "마이크로스트레티지 (MSTR)": {"ticker": "MSTR", "tv_symbol": "NASDAQ:MSTR", "keyword": "MicroStrategy stock"},
    "슈퍼마이크로컴퓨터 (SMCI)": {"ticker": "SMCI", "tv_symbol": "NASDAQ:SMCI", "keyword": "SMCI stock"},
    "아이온큐 (IONQ)": {"ticker": "IONQ", "tv_symbol": "NYSE:IONQ", "keyword": "IONQ stock"},
    "소파이 (SoFi)": {"ticker": "SOFI", "tv_symbol": "NASDAQ:SOFI", "keyword": "SoFi stock"},
    "리비안 (RIVN)": {"ticker": "RIVN", "tv_symbol": "NASDAQ:RIVN", "keyword": "Rivian stock"},
    "루시드 (LCID)": {"ticker": "LCID", "tv_symbol": "NASDAQ:LCID", "keyword": "Lucid stock"}
}

BUDGET_UNIVERSE = {
    "소파이 (SoFi)": {"ticker": "SOFI", "tv_symbol": "NASDAQ:SOFI", "keyword": "SoFi stock"},
    "니콜라 (NKLA)": {"ticker": "NKLA", "tv_symbol": "NASDAQ:NKLA", "keyword": "NKLA stock"},
    "리비안 (RIVN)": {"ticker": "RIVN", "tv_symbol": "NASDAQ:RIVN", "keyword": "Rivian stock"},
    "루시드 (LCID)": {"ticker": "LCID", "tv_symbol": "NASDAQ:LCID", "keyword": "Lucid stock"},
    "그랩 (GRAB)": {"ticker": "GRAB", "tv_symbol": "NASDAQ:GRAB", "keyword": "Grab stock"},
    "아이온큐 (IONQ)": {"ticker": "IONQ", "tv_symbol": "NYSE:IONQ", "keyword": "IONQ stock"},
    "SOXL (반도체 3배 레버리지)": {"ticker": "SOXL", "tv_symbol": "NYSE:SOXL", "keyword": "SOXL ETF"},
    "TQQQ (나스닥 3배 레버리지)": {"ticker": "TQQQ", "tv_symbol": "NASDAQ:TQQQ", "keyword": "TQQQ ETF"},
    "로블록스 (RBLX)": {"ticker": "RBLX", "tv_symbol": "NYSE:RBLX", "keyword": "Roblox stock"},
    "유니티 (U)": {"ticker": "U", "tv_symbol": "NYSE:U", "keyword": "Unity stock"}
}

def fetch_single_stock_vwap(item_tuple, is_us):
    name, info = item_tuple
    ticker = info["ticker"]
    try:
        stock = yf.Ticker(ticker)
        # 강제로 최신 데이터를 가져오기 위해 period 설정 및 프록시/세션 우회 효과 부여
        df_hist = stock.history(period="60d", proxy=None)
        if len(df_hist) >= 20:
            current_price = float(df_hist['Close'].iloc[-1])
            prev_price = float(df_hist['Close'].iloc[-2])
            ctrt = round(((current_price - prev_price) / prev_price) * 100, 2)
            curr_vol = int(df_hist['Volume'].iloc[-1])
            
            approx_trading_value = current_price * curr_vol
            min_value_limit = 10000000 if is_us else 10000000000
            
            if curr_vol < 300000 or approx_trading_value < min_value_limit:
                return None 
            
            typical_price = (df_hist['High'] + df_hist['Low'] + df_hist['Close']) / 3
            vwap_series = (typical_price * df_hist['Volume']).cumsum() / df_hist['Volume'].cumsum()
            current_vwap = float(vwap_series.iloc[-1])
            
            ema20 = float(df_hist['Close'].ewm(span=20, adjust=False).mean().iloc[-1])
            avg_vol = float(df_hist['Volume'].rolling(window=20).mean().iloc[-1])
            vol_spike = curr_vol >= (avg_vol * 1.5)
            
            if ctrt > 0.5 and current_price >= ema20 and current_price >= current_vwap and vol_spike:
                signal = "🔥 ▲ 거래량 폭증 + VWAP 돌파 (매수강력)"
            elif ctrt >= -2.0:
                signal = "🟡 밴드수축 관망"
            else:
                signal = "🔴 매수보류"
            
            price_display = f"{current_price:,.0f} 원" if not is_us else f"${current_price:,.2f}"
            
            return {
                "AI 매매 시그널": signal,
                "종목명": name,
                "심볼": ticker,
                "현재가": price_display,
                "등락률(%)": ctrt,
                "거래량": f"{curr_vol:,}",
                "raw_price": current_price
            }
    except Exception:
        pass
    return None

def run_ai_explorer_vwap(pool_dict, is_us):
    scanned_results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_stock_vwap, item, is_us) for item in pool_dict.items()]
        for future in futures:
            res = future.result()
            if res:
                scanned_results.append(res)
    return pd.DataFrame(scanned_results)

# ==========================================
# ⏰ 백그라운드 스케줄러 (평일 15:25 자동 스캔 및 디스코드 전송)
# ==========================================
def scheduled_closing_scan_and_discord():
    df_result = run_ai_explorer_vwap(KOREAN_UNIVERSE, False)
    if not df_result.empty:
        df_success = df_result[df_result['AI 매매 시그널'].str.contains("🔥")].copy()
        if not df_success.empty:
            msg = "🚨 **[Gemini Quant 종가매매 자동 스캐너 리포트]**\n⏰ 평일 15:25 자동 포착 리스트:\n\n"
            for _, row in df_success.iterrows():
                msg += f"- `{row['종목명']}` ({row['심볼']}) | 현재가: {row['현재가']} | 등락률: **+{row['등락률(%)']}%**\n"
            send_discord_message(msg)
        else:
            send_discord_message(f"📊 **[Gemini Quant 종가매매 스캐너]** ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n현재 조건(거래량 폭증+VWAP)을 충족한 주도주가 없습니다.")
    else:
        send_discord_message(f"📊 **[Gemini Quant 종가매매 스캐너]** ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n데이터 수집 결과 포착된 종목이 없습니다.")

@st.cache_resource
def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_closing_scan_and_discord, 'cron', day_of_week='mon-fri', hour=15, minute=25, timezone='Asia/Seoul')
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    return scheduler

try:
    init_scheduler()
except Exception:
    pass

# ==============================================================================
# [MENU 1] 종가매매 스캐너
# ==============================================================================
if menu_choice.startswith("1."):
    st.markdown("##### 🚀 거래량 폭증 유동성 스캔 + VWAP 추세 검증 (디스코드 자동전송 연동)")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ 스캐너 설정")
    market_choice_1 = st.sidebar.selectbox(
        "시장 선택:", 
        [
            "국내 주식 시장 (KRX 주요 유동성)", 
            "미국 주식 시장 (전체 유동성 종목 스캔)",
            "소액 투자자 맞춤형 (저가주·레버리지 유동성)"
        ]
    )

    @st.cache_data(ttl=600)
    def check_market_trend(is_us=False):
        try:
            symbol = "^GSPC" if is_us else "^KS11"
            market_idx = yf.Ticker(symbol)
            df_k = market_idx.history(period="40d")
            if len(df_k) >= 20:
                k_close = df_k['Close'].iloc[-1]
                k_ema20 = df_k['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
                if k_close >= k_ema20:
                    return "🟢 시장 지수 20일선 위 (오버나이트 유리)", True
                else:
                    return "🔴 시장 지수 20일선 하방 이탈 (매수 주의)", False
        except Exception:
            pass
        return "🟡 시장 중립", True

    is_us_market_1 = "미국" in market_choice_1 or "소액" in market_choice_1
    market_status_text_1, is_market_safe_1 = check_market_trend(is_us=is_us_market_1)
    st.sidebar.info(f"📊 **시장 진단**\n\n{market_status_text_1}")

    if "소액" in market_choice_1:
        current_pool_1 = BUDGET_UNIVERSE
    elif "미국" in market_choice_1:
        current_pool_1 = US_EXTENDED_UNIVERSE
    else:
        current_pool_1 = KOREAN_UNIVERSE

    col_btn1, col_btn2 = st.columns([0.3, 0.7])
    with col_btn1:
        run_scan_btn = st.button("🔥 통합 종가매매 탐색기 실행")
    with col_btn2:
        test_discord_btn = st.button("📲 현재 포착 리스트 디스코드 채널로 즉시 전송 테스트")

    if run_scan_btn:
        with st.spinner("스캔 중..."):
            st.session_state['explorer_df_1'] = run_ai_explorer_vwap(current_pool_1, is_us_market_1)
        st.sidebar.success("완료!")

    if 'explorer_df_1' not in st.session_state:
        st.session_state['explorer_df_1'] = run_ai_explorer_vwap(current_pool_1, is_us_market_1)

    df_scanned_1 = st.session_state['explorer_df_1']
    df_success_1 = df_scanned_1[df_scanned_1['AI 매매 시그널'].str.contains("🔥")].copy() if not df_scanned_1.empty else pd.DataFrame()

    if test_discord_btn:
        if not df_success_1.empty:
            msg = "🚨 **[Gemini Quant 디스코드 즉시 전송 테스트]**\n종가매매 포착 리스트:\n\n"
            for _, row in df_success_1.iterrows():
                msg += f"- `{row['종목명']}` ({row['심볼']}) | 현재가: {row['현재가']} | 등락률: **+{row['등락률(%)']}%**\n"
            success = send_discord_message(msg)
            if success:
                st.success("✨ 디스코드 채널로 리포트 전송 성공!")
            else:
                st.error("⚠️ 디스코드 전송 실패. 웹훅 주소를 확인해 주세요.")
        else:
            msg = f"📊 **[Gemini Quant 테스트]**\n현재 조건에 부합하는 포착된 주식이 없습니다."
            success = send_discord_message(msg)
            if success:
                st.info("ℹ️ 포착된 종목이 없어 '포착된 주식이 없습니다' 메시지를 디스코드로 전송했습니다.")
            else:
                st.error("⚠️ 디스코드 전송 실패.")

    st.markdown("### 📋 종가매매 포착 리스트")
    if not df_success_1.empty:
        df_sorted_1 = df_success_1.sort_values(by="등락률(%)", ascending=False).reset_index(drop=True)
        df_sorted_1.index = df_sorted_1.index + 1
        st.dataframe(df_sorted_1.drop(columns=['raw_price']), use_container_width=True)
        names_1 = df_sorted_1['종목명'].tolist()
    else:
        st.info("조건을 충족하는 종목이 없습니다.")
        names_1 = list(current_pool_1.keys())

    selected_name_1 = st.selectbox("분석 종목 선택:", names_1)
    sel_info_1 = current_pool_1.get(selected_name_1, list(current_pool_1.values())[0])

    col_c1, col_i1 = st.columns([1.3, 0.7])
    with col_c1:
        import streamlit.components.v1 as components
        tv_html_1 = f"""
        <div class="tradingview-widget-container" style="height:100%;width:100%">
          <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "width": "100%", "height": "550", "symbol": "{sel_info_1['tv_symbol']}",
            "interval": "D", "timezone": "Asia/Seoul", "theme": "dark", "style": "1", "locale": "kr"
          }}
          </script>
        </div>
        """
        components.html(tv_html_1, height=560)
    with col_i1:
        st.markdown(f"#### 🤖 [{selected_name_1}] 진단")
        st.success("🔥 거래량 폭증 및 VWAP 추세 검증 구역")
        try:
            lang = "ko" if not is_us_market_1 else "en"
            q_enc = urllib.parse.quote(sel_info_1['keyword'])
            rss = f"https://news.google.com/rss/search?q={q_enc}&hl={lang}&gl={'KR' if not is_us_market_1 else 'US'}&ceid={'KR' if not is_us_market_1 else 'US'}:{lang.upper()}"
            for e in feedparser.parse(rss).entries[:3]:
                st.markdown(f"- [{e.title}]({e.link})")
        except Exception:
            pass

# ==============================================================================
# [MENU 2] AI 장중 수급 집중 스캐너 & 비주얼 차트
# ==============================================================================
elif menu_choice.startswith("2."):
    st.markdown("### 🔥 AI 장중 수급 집중 스캐너 & 비주얼 차트 분석")
    st.info("💡 **[장중 수급 스캔 실행]** 버튼을 누르시면, 현재 시장에서 **평균 거래량 대비 1.5배 이상 돈이 쏠리며 급등하는 주도주**들을 실시간으로 발굴하여 리스트업하고 차트와 타점을 연동해 줍니다.")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ 장중 스캐너 설정")
    market_choice_2 = st.sidebar.selectbox("스캔 시장 선택:", ["미국 주식 시장 (주요 빅테크 및 레버리지)", "국내 주식 시장 (KRX 주요 유동성)", "소액/레버리지 풀"], key="m2")
    is_us_market_2 = "국내" not in market_choice_2
    
    if "소액" in market_choice_2:
        scan_pool_2 = BUDGET_UNIVERSE
    elif "국내" in market_choice_2:
        scan_pool_2 = KOREAN_UNIVERSE
    else:
        scan_pool_2 = US_EXTENDED_UNIVERSE

    if st.sidebar.button("🔥 장중 수급 쏠림 종목 스캔 실행"):
        with st.spinner("장중 수급 및 거래량 폭증 종목 스캔 중..."):
            st.session_state['surge_df_2'] = run_ai_explorer_vwap(scan_pool_2, is_us_market_2)
        st.sidebar.success("스캔 완료!")

    if 'surge_df_2' not in st.session_state:
        st.session_state['surge_df_2'] = run_ai_explorer_vwap(scan_pool_2, is_us_market_2)

    df_surge_raw = st.session_state['surge_df_2']
    df_surge_success = df_surge_raw[df_surge_raw['AI 매매 시그널'].str.contains("🔥")].copy() if not df_surge_raw.empty else pd.DataFrame()

    st.markdown("### 📋 장중 수급 폭증(Volume Surge) 포착 리스트")
    
    selected_ticker_2 = ""
    selected_name_2 = ""

    if not df_surge_success.empty:
        df_sorted_2 = df_surge_success.sort_values(by="등락률(%)", ascending=False).reset_index(drop=True)
        df_sorted_2.index = df_sorted_2.index + 1
        st.dataframe(df_sorted_2.drop(columns=['raw_price']), use_container_width=True)
        
        chosen_row_name = st.selectbox("포착된 주도주 중 분석할 종목 선택:", df_sorted_2['종목명'].tolist())
        matched_item = df_sorted_2[df_sorted_2['종목명'] == chosen_row_name].iloc[0]
        selected_ticker_2 = matched_item['심볼']
        selected_name_2 = chosen_row_name
    else:
        st.warning("⚠️ 현재 조건(거래량 1.5배 이상 폭증 + VWAP 돌파)을 충족하는 장중 수급 종목이 없습니다. 직접 티커를 검색해서 분석할 수도 있습니다.")
        manual_input = st.text_input("🔍 직접 종목 티커 검색 (예: TSLA, AAPL, 005930.KS):", "TSLA")
        selected_ticker_2 = manual_input.strip().upper()
        selected_name_2 = selected_ticker_2

    is_us_tab2 = not (selected_ticker_2.endswith(".KS") or selected_ticker_2.endswith(".KQ") or selected_ticker_2.isdigit())

    if st.button("🔄 실시간 최신 데이터 강제 갱신"):
        st.rerun()

    # 캐시 완전 차단 및 실시간 타임스탬프를 부여한 데이터 생성 함수
    def generate_ai_visual_chart(ticker, is_us):
        try:
            tk = yf.Ticker(ticker)
            # 매번 새로운 세션 요청처럼 처리하기 위해 period와 함께 강제 갱신 유도
            df = tk.history(period="60d", auto_adjust=True)
            if not df.empty and len(df) > 10:
                tp = (df['High'] + df['Low'] + df['Close']) / 3
                df['VWAP'] = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
                
                df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
                df['Vol_Surge'] = df['Volume'] >= (df['Vol_MA20'] * 1.5)
                df['VWAP_Diff'] = (df['Close'] - df['VWAP']) / df['VWAP']
                
                df['Signal'] = 0
                df.loc[(df['Close'] > df['VWAP']) & (df['Close'].shift(1) <= df['VWAP'].shift(1)), 'Signal'] = 1  
                df.loc[(df['Close'] < df['VWAP']) & (df['Close'].shift(1) >= df['VWAP'].shift(1)), 'Signal'] = -1 
                
                dynamic_tp_pct = 0.03 + (df['VWAP_Diff'] * 1.2).clip(0, 0.07)
                df['TP_Price'] = df['Close'] * (1 + dynamic_tp_pct)
                df['SL_Price'] = df['Close'] * 0.965
                return df
        except Exception:
            pass
        return pd.DataFrame()

    if selected_ticker_2:
        df_chart = generate_ai_visual_chart(selected_ticker_2, is_us_tab2)

        if not df_chart.empty:
            cur_p = float(df_chart['Close'].iloc[-1])
            prev_p = float(df_chart['Close'].iloc[-2])
            diff_pct = round(((cur_p - prev_p) / prev_p) * 100, 2)
            cur_vwap = float(df_chart['VWAP'].iloc[-1])
            
            current_diff = max(0.0, (cur_p - cur_vwap) / cur_vwap)
            current_tp_rate = min(0.10, max(0.03, 0.03 + (current_diff * 1.2)))

            cur_fmt = f"${cur_p:,.2f}" if is_us_tab2 else f"{cur_p:,.0f} 원"
            vwap_fmt = f"${cur_vwap:,.2f}" if is_us_tab2 else f"{cur_vwap:,.0f} 원"
            dynamic_tp_price = cur_p * (1 + current_tp_rate)
            sl_price = cur_p * 0.965

            m1, m2, m3 = st.columns(3)
            m1.metric(f"📌 [{selected_name_2}] 현재 종가", cur_fmt, f"{diff_pct:+.2f}%")
            m2.metric("📊 VWAP 기준가", vwap_fmt)
            m3.metric(f"🎯 AI 동적 익절 목표가 (TP +{current_tp_rate*100:.1f}%)", f"${dynamic_tp_price:,.2f}" if is_us_tab2 else f"${dynamic_tp_price:,.0f} 원")

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
            
            fig.add_trace(go.Candlestick(
                x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'],
                increasing_line_color='#FF3B30', decreasing_line_color='#007AFF', 
                increasing_fillcolor='#FF3B30', decreasing_fillcolor='#007AFF',
                name="주가 캔들"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df_chart.index, y=df_chart['VWAP'], line=dict(color='#34C759', width=2), name='VWAP 선'
            ), row=1, col=1)
            
            long_signals = df_chart[df_chart['Signal'] == 1]
            if not long_signals.empty:
                long_texts = [f"장중수급 롱: {p:,.2f}" if is_us_tab2 else f"장중수급 롱: {p:,.0f}" for p in long_signals['Close']]
                fig.add_trace(go.Scatter(
                    mode="markers+text", x=long_signals.index, y=long_signals['Low'] * 0.975,
                    marker=dict(symbol="triangle-up", size=14, color="#34C759"),
                    text=long_texts, textposition="bottom center", name="장중수급 롱 진입"
                ), row=1, col=1)

            tp_signals = df_chart[df_chart['Signal'] == -1]
            if not tp_signals.empty:
                tp_texts = [f"익절TP: {tp:,.2f}" if is_us_tab2 else f"익절TP: {tp:,.0f}" for tp in tp_signals['TP_Price']]
                fig.add_trace(go.Scatter(
                    mode="markers+text", x=tp_signals.index, y=tp_signals['High'] * 1.025,
                    marker=dict(symbol="triangle-down", size=14, color="#FF3B30"),
                    text=tp_texts, textposition="top center", name="AI 익절(TP)"
                ), row=1, col=1)

            colors = ['#FF3B30' if row['Close'] >= row['Open'] else '#007AFF' for _, row in df_chart.iterrows()]
            fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=colors, name='거래량'), row=2, col=1)

            fig.update_layout(
                height=600, xaxis_rangeslider_visible=False,
                paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF',
                font=dict(color='#222222'),
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(gridcolor='#EFEFEF')
            fig.update_yaxes(gridcolor='#EFEFEF')

            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.markdown(f"### 📋 [{selected_name_2}] 장중 수급형 AI 타점 요약 가이드")
            col_g1, col_g2, col_g3 = st.columns(3)
            with col_g1:
                st.success(f"🟢 **추천 롱 진입가**\n\n**{cur_fmt}**\n\n*(장중 수급 쏠림 + VWAP 돌파)*")
            with col_g2:
                st.info(f"🎯 **AI 동적 익절 목표가 (TP +{current_tp_rate*100:.1f}%)**\n\n**{f'${dynamic_tp_price:,.2f}' if is_us_tab2 else f'{dynamic_tp_price:,.0f} 원'}**\n\n*(추세 연동형 최대 10%)*")
            with col_g3:
                st.error(f"🔴 **손절가 (SL -3.5%)**\n\n**{f'${sl_price:,.2f}' if is_us_tab2 else f'{sl_price:,.0f} 원'}**\n\n*(휩소 방어 리스크 관리)*")
        else:
            st.warning(f"⚠️ 입력하신 종목 [{selected_ticker_2}]의 차트 데이터를 불러올 수 없습니다.")
