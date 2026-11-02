import streamlit as st
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor
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
        return False
    payload = {"content": text_content}
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
        "2. AI 장중 수급 집중 스캐너 & 실시간 트레이딩뷰 차트"
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
        df_hist = stock.history(period="60d", auto_adjust=True)
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
# [MENU 2] AI 장중 수급 집중 스캐너 & 실시간 트레이딩뷰 차트 (자유 검색 및 직관적 타이밍 배지 포함)
# ==============================================================================
elif menu_choice.startswith("2."):
    st.markdown("### 🔥 AI 장중 수급 집중 스캐너 & 실시간 트레이딩뷰 차트")
    st.info("💡 **[장중 수급 스캔 실행]** 버튼을 누르거나, 아래 **[직접 티커 검색]** 창에 원하시는 주식 심볼(예: TSLA, AAPL, 005930.KS)을 입력하시면 즉시 실시간 차트와 명확한 매매 타이밍을 제공해 줍니다.")

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

    st.markdown("### 📋 장중 수급 폭증(Volume Surge) 포착 리스트 및 자유 검색")
    
    selected_ticker_2 = ""
    selected_name_2 = ""
    selected_tv_symbol_2 = "NASDAQ:TSLA"

    # 유저가 원하는 주식을 언제든 직접 검색할 수 있는 입력창을 최우선 배치
    manual_input = st.text_input("🔍 원하시는 종목 직접 검색 (예: TSLA, AAPL, NVDA, 005930.KS):", "TSLA", key="manual_t2")
    
    if manual_input:
        selected_ticker_2 = manual_input.strip().upper()
        selected_name_2 = selected_ticker_2
        
        # 트레이딩뷰 심볼 자동 매핑 로직
        if selected_ticker_2.endswith(".KS"):
            code = selected_ticker_2.split(".")[0]
            selected_tv_symbol_2 = f"KRX:{code}"
        elif selected_ticker_2.endswith(".KQ"):
            code = selected_ticker_2.split(".")[0]
            selected_tv_symbol_2 = f"KOSDAQ:{code}"
        elif selected_ticker_2.isdigit() and len(selected_ticker_2) == 6:
            selected_tv_symbol_2 = f"KRX:{selected_ticker_2}"
            selected_ticker_2 = f"{selected_ticker_2}.KS"
        else:
            # 미국 주식 주요 거래소 판별
            if selected_ticker_2 in ["SOXL", "PLTR", "IONQ", "RBLX", "U", "SPY", "QQQ"]:
                selected_tv_symbol_2 = f"NYSE:{selected_ticker_2}"
            else:
                selected_tv_symbol_2 = f"NASDAQ:{selected_ticker_2}"
    else:
        if not df_surge_success.empty:
            df_sorted_2 = df_surge_success.sort_values(by="등락률(%)", ascending=False).reset_index(drop=True)
            df_sorted_2.index = df_sorted_2.index + 1
            st.dataframe(df_sorted_2.drop(columns=['raw_price']), use_container_width=True)
            
            chosen_row_name = st.selectbox("포착된 주도주 중 분석할 종목 선택:", df_sorted_2['종목명'].tolist(), key="sel_name_2")
            matched_item = df_sorted_2[df_sorted_2['종목명'] == chosen_row_name].iloc[0]
            selected_ticker_2 = matched_item['심볼']
            selected_name_2 = chosen_row_name
            
            full_pool = {**KOREAN_UNIVERSE, **US_EXTENDED_UNIVERSE, **BUDGET_UNIVERSE}
            for k, v in full_pool.items():
                if v["ticker"] == selected_ticker_2:
                    selected_tv_symbol_2 = v["tv_symbol"]
                    break

    is_us_tab2 = not (selected_ticker_2.endswith(".KS") or selected_ticker_2.endswith(".KQ") or selected_ticker_2.isdigit())

    # 실시간 트레이딩뷰 위젯 렌더링
    import streamlit.components.v1 as components
    tv_html_2 = f"""
    <div class="tradingview-widget-container" style="height:100%;width:100%">
      <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {{
        "width": "100%", "height": "550", "symbol": "{selected_tv_symbol_2}",
        "interval": "15", "timezone": "Asia/Seoul", "theme": "dark", "style": "1", "locale": "kr"
      }}
      </script>
    </div>
    """
    components.html(tv_html_2, height=560)

    # 실시간 타이밍 분석 및 시각적 가이드 생성
    def get_realtime_timing_guide(ticker, is_us):
        try:
            tk = yf.Ticker(ticker)
            df = tk.history(period="15d", auto_adjust=True)
            if not df.empty and len(df) >= 5:
                cur_p = float(df['Close'].iloc[-1])
                prev_p = float(df['Close'].iloc[-2])
                diff_pct = round(((cur_p - prev_p) / prev_p) * 100, 2)
                
                typical_price = (df['High'] + df['Low'] + df['Close']) / 3
                vwap = float((typical_price * df['Volume']).cumsum().iloc[-1] / df['Volume'].cumsum().iloc[-1])
                ema5 = float(df['Close'].ewm(span=5, adjust=False).mean().iloc[-1])
                
                # 명확한 타이밍 배지 판별
                if cur_p >= vwap and cur_p >= ema5:
                    badge = "🚀 [적극 매수(롱) 타이밍]"
                    desc = "현재 주가가 핵심 VWAP 선과 단기 이평선(EMA5) 위에 안착해 있습니다. **지금이 강한 수급 유입 구간입니다!**"
                elif cur_p >= vwap * 0.99:
                    badge = "⏳ [눌림목 관망 타이밍]"
                    desc = "VWAP 지지선 부근에서 횡보 중입니다. 급등 전 분할 매수나 반등 타이밍을 노려보세요."
                else:
                    badge = "⚠️ [하방 이탈 / 매수 보류]"
                    desc = "주가가 VWAP 아래로 처져 있습니다. 추세가 회복될 때까지 관망을 권장합니다."

                tp_price = cur_p * 1.045
                sl_price = cur_p * 0.970
                
                cur_fmt = f"${cur_p:,.2f}" if is_us else f"{cur_p:,.0f} 원"
                tp_fmt = f"${tp_price:,.2f}" if is_us else f"{tp_price:,.0f} 원"
                sl_fmt = f"${sl_price:,.2f}" if is_us else f"{sl_price:,.0f} 원"
                vwap_fmt = f"${vwap:,.2f}" if is_us else f"{vwap:,.0f} 원"
                
                return badge, desc, cur_fmt, diff_pct, tp_fmt, sl_fmt, vwap_fmt
        except Exception:
            pass
        return "⚠️ 데이터 조회 중", "입력하신 티커를 확인해 주세요.", "N/A", 0.0, "N/A", "N/A", "N/A"

    badge, desc, cur_fmt, diff_pct, tp_fmt, sl_fmt, vwap_fmt = get_realtime_timing_guide(selected_ticker_2, is_us_tab2)

    st.markdown("---")
    st.markdown(f"### 🎯 [{selected_name_2}] AI 실시간 매매 타이밍 & 타점 가이드")
    
    # 직관적인 배지 형태로 타이밍 제시
    if "🚀" in badge:
        st.success(f"**{badge}**\n\n{desc}")
    elif "⏳" in badge:
        st.info(f"**{badge}**\n\n{desc}")
    else:
        st.error(f"**{badge}**\n\n{desc}")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.success(f"🟢 **추천 롱 진입 기준가**\n\n**{cur_fmt}**\n\n*(등락률 {diff_pct:+.2f}%)*")
    with m2:
        st.metric("📊 기준 VWAP 선", vwap_fmt)
    with m3:
        st.info(f"🎯 **AI 익절 목표가 (TP +4.5%)**\n\n**{tp_fmt}**")
    with m4:
        st.error(f"🔴 **손절가 (SL -3.0%)**\n\n**{sl_fmt}**")
