import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import io
import zipfile
import os
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(
    page_title="Yahoo Finance Equity Downloader & Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Server Storage Directory
DATA_DIR = os.path.join(os.getcwd(), "saved_data")
os.makedirs(DATA_DIR, exist_ok=True)

# Custom CSS for styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #e2e8f0;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📈 Yahoo Finance Equity Downloader & Screener</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Fetch OHLC stock data, save locally on server, and perform advanced multi-condition technical screening.</div>', unsafe_allow_html=True)

# Preset Indices / Stock Lists
PRESET_LISTS = {
    "NIFTY 50": [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BHARTIARTL", "SBIN", "ITC", 
        "LTIM", "HINDUNILVR", "LT", "HCLTECH", "KOTAKBANK", "AXISBANK", "SUNPHARMA", "TITAN", 
        "MARUTI", "ULTRACEMCO", "ASIANPAINT", "NTPC", "TATAMOTORS", "POWERGRID", "TATASTEEL", 
        "M&M", "BAJFINANCE", "ADANIENT", "COALINDIA", "ONGC", "INDUSINDBK", "GRASIM", 
        "TECHM", "HDFCLIFE", "HINDALCO", "DRREDDY", "CIPLA", "SBILIFE", "EICHERMOT", 
        "BPCL", "TATACONSUM", "BRITANNIA", "ADANIPORTS", "DIVISLAB", "APOLLOHOSP", "SHRIRAMFIN", 
        "HEROMOTOCO", "BEL", "TRENT", "WIPRO", "NESTLEIND", "BAJAJ-AUTO"
    ],
    "SENSEX": [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BHARTIARTL", "SBIN", "ITC", 
        "HINDUNILVR", "LT", "HCLTECH", "KOTAKBANK", "AXISBANK", "SUNPHARMA", "TITAN", 
        "MARUTI", "ULTRACEMCO", "ASIANPAINT", "NTPC", "TATAMOTORS", "POWERGRID", "TATASTEEL", 
        "M&M", "BAJFINANCE", "INDUSINDBK", "TECHM", "JSWSTEEL", "ADANIPORTS", "NESTLEIND", "BAJAJ-AUTO"
    ],
    "NSE 500 (Sample Major 30)": [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BHARTIARTL", "SBIN", "ITC", 
        "LTIM", "HINDUNILVR", "LT", "HCLTECH", "KOTAKBANK", "AXISBANK", "SUNPHARMA", "TITAN", 
        "MARUTI", "ULTRACEMCO", "ASIANPAINT", "NTPC", "TATAMOTORS", "POWERGRID", "TATASTEEL", 
        "M&M", "BAJFINANCE", "ADANIENT", "COALINDIA", "ONGC", "INDUSINDBK", "GRASIM"
    ],
    "US TECH TOP 10": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "AMD", "NFLX"
    ]
}

TIMEFRAME_MAP = {
    "1D (default)": {"period": "1y", "interval": "1d"},
    "1W": {"period": "2y", "interval": "1wk"},
    "1M": {"period": "5y", "interval": "1mo"},
    "3M": {"period": "5y", "interval": "1mo"},
    "6M": {"period": "5y", "interval": "1mo"},
    "1Y": {"period": "10y", "interval": "1mo"},
    "4H": {"period": "60d", "interval": "60m"},
    "1H": {"period": "60d", "interval": "60m"},
    "30M": {"period": "1mo", "interval": "30m"},
    "15M": {"period": "1mo", "interval": "15m"},
    "5M": {"period": "1mo", "interval": "5m"},
    "1M_INTRA": {"period": "7d", "interval": "1m"}
}

def format_symbol(symbol: str, append_ns: bool) -> str:
    sym = symbol.strip().upper()
    if not sym:
        return sym
    if sym.startswith('^') or sym.endswith('=X'):
        return sym
    if '.' in sym:
        return sym
    crypto_suffixes = ['-USD', '-EUR', '-GBP', '-INR', '-BTC', '-ETH', '-USDT']
    if any(sym.endswith(suffix) for suffix in crypto_suffixes):
        return sym
    if append_ns:
        return f"{sym}.NS"
    return sym

def get_currency_symbol(symbol: str, ticker: yf.Ticker) -> str:
    if symbol.startswith('^'):
        return ""
    curr = None
    try:
        if hasattr(ticker, 'fast_info'):
            curr = getattr(ticker.fast_info, 'currency', None)
        if not curr and hasattr(ticker, 'info'):
            curr = ticker.info.get('currency')
    except Exception:
        pass
    if curr:
        curr_str = str(curr).upper()
        if curr_str == 'INR':
            return "₹"
        elif curr_str == 'USD':
            return "$"
        elif curr_str == 'EUR':
            return "€"
        elif curr_str in ['GBP', 'GBp']:
            return "£"
        elif curr_str == 'JPY':
            return "¥"
        elif curr_str == 'CAD':
            return "CA$"
        elif curr_str == 'AUD':
            return "A$"
        else:
            return f"{curr_str} "
    if symbol.endswith('.NS') or symbol.endswith('.BO'):
        return "₹"
    elif symbol.endswith('.L'):
        return "£"
    elif any(symbol.endswith(ext) for ext in ['.DE', '.PA', '.AS', '.MI', '.MC']):
        return "€"
    elif symbol.endswith('.T'):
        return "¥"
    return "$"

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False

# Indicator Calculations
def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculates Simple Moving Average using TA-Lib if available, falling back to pandas."""
    if HAS_TALIB:
        try:
            vals = series.values.astype(float)
            res = talib.SMA(vals, timeperiod=period)
            return pd.Series(res, index=series.index)
        except Exception:
            pass
    return series.rolling(window=period).mean()

def calculate_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculates Average True Range using TA-Lib if available, falling back to pandas."""
    if HAS_TALIB:
        try:
            high = df['High'].values.astype(float)
            low = df['Low'].values.astype(float)
            close = df['Close'].values.astype(float)
            res = talib.ATR(high, low, close, timeperiod=period)
            return pd.Series(res, index=df.index)
        except Exception:
            pass
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    ha_df = df.copy()
    ha_df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4.0

    ha_open = np.zeros(len(df))
    if len(df) > 0:
        ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2.0
        for i in range(1, len(df)):
            ha_open[i] = (ha_open[i-1] + ha_df['HA_Close'].iloc[i-1]) / 2.0
    ha_df['HA_Open'] = ha_open

    ha_df['HA_High'] = ha_df[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    ha_df['HA_Low'] = ha_df[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    return ha_df

def calculate_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
    df_st = df.copy()
    high = df_st['High']
    low = df_st['Low']
    close = df_st['Close']

    atr = calculate_atr(df_st, period)

    hl2 = (high + low) / 2.0
    basic_upperband = hl2 + (multiplier * atr)
    basic_lowerband = hl2 - (multiplier * atr)

    n = len(df_st)
    upperband = np.zeros(n)
    lowerband = np.zeros(n)
    in_uptrend = np.ones(n, dtype=bool)

    if n < period or atr.isnull().all():
        df_st['SuperTrend'] = np.nan
        df_st['ST_Trend'] = "N/A"
        return df_st

    # Find first index where ATR is valid
    first_valid_idx = period - 1

    for i in range(n):
        if i <= first_valid_idx:
            upperband[i] = basic_upperband.iloc[first_valid_idx] if pd.notna(basic_upperband.iloc[first_valid_idx]) else 0
            lowerband[i] = basic_lowerband.iloc[first_valid_idx] if pd.notna(basic_lowerband.iloc[first_valid_idx]) else 0
            in_uptrend[i] = True
        else:
            prev_ub = upperband[i-1]
            prev_lb = lowerband[i-1]
            curr_close = close.iloc[i]
            prev_close = close.iloc[i-1]

            curr_bub = basic_upperband.iloc[i]
            curr_blb = basic_lowerband.iloc[i]

            if curr_bub < prev_ub or prev_close > prev_ub:
                upperband[i] = curr_bub
            else:
                upperband[i] = prev_ub

            if curr_blb > prev_lb or prev_close < prev_lb:
                lowerband[i] = curr_blb
            else:
                lowerband[i] = prev_lb

            if curr_close > upperband[i-1]:
                in_uptrend[i] = True
            elif curr_close < lowerband[i-1]:
                in_uptrend[i] = False
            else:
                in_uptrend[i] = in_uptrend[i-1]

    st_val = np.where(in_uptrend, lowerband, upperband)
    st_val[:first_valid_idx] = np.nan

    df_st['SuperTrend'] = st_val
    df_st['ST_Trend'] = np.where(
        np.isnan(st_val),
        "N/A",
        np.where(in_uptrend, "🟢 Bullish (BUY)", "🔴 Bearish (SELL)")
    )
    return df_st

# Function to Save CSV files to Streamlit server
def save_data_to_server(symbol: str, df: pd.DataFrame):
    filename = f"{symbol}_OHLC.csv"
    filepath = os.path.join(DATA_DIR, filename)
    df.to_csv(filepath, index=True)
    return filepath

# Navigation Tabs
main_tab1, main_tab2 = st.tabs(["📥 Equity Data Downloader", "🔍 Stock Screener"])

# Sidebar Common Configurations
st.sidebar.header("⚙️ Configuration")
auto_append_ns = st.sidebar.checkbox(
    "Auto-append '.NS' to Indian symbols",
    value=True,
    help="Appends '.NS' for Indian NSE symbols if missing."
)
include_volume = st.sidebar.checkbox("Include Volume Column", value=True)

# --- TAB 1: DATA DOWNLOADER ---
with main_tab1:
    input_mode = st.radio(
        "Select Input Mode",
        ["Single Stock Symbol", "Batch CSV Upload"],
        horizontal=True
    )

    col_s1, col_s2 = st.columns(2)
    default_start = datetime.today() - timedelta(days=365)
    default_end = datetime.today()

    with col_s1:
        start_date = st.date_input("Start Date", value=default_start, key="dl_start")
    with col_s2:
        end_date = st.date_input("End Date", value=default_end, key="dl_end")

    if input_mode == "Single Stock Symbol":
        symbol_input = st.text_input(
            "Stock Symbol",
            value="BAJAJ-AUTO",
            help="Enter ticker symbol (e.g. BAJAJ-AUTO, RELIANCE, TCS, AAPL, ^NSEI)"
        ).strip().upper()

        if not symbol_input:
            st.warning("⚠️ Please enter a stock symbol.")
        elif start_date > end_date:
            st.error("❌ Error: Start Date cannot be after End Date.")
        else:
            formatted_symbol = format_symbol(symbol_input, auto_append_ns)

            if st.button("🚀 Download Single Stock Data"):
                with st.spinner(f"Fetching data for **{formatted_symbol}**..."):
                    try:
                        ticker = yf.Ticker(formatted_symbol)
                        fetch_end = end_date + timedelta(days=1)
                        df = ticker.history(start=start_date, end=fetch_end)

                        if df.empty:
                            st.error(f"❌ No data found for symbol **{formatted_symbol}**.")
                        else:
                            df.index = pd.to_datetime(df.index)
                            df.index = df.index.strftime('%Y-%m-%d')
                            df.index.name = 'Date'

                            ohlc_cols = ['Open', 'High', 'Low', 'Close']
                            available_cols = [c for c in ohlc_cols if c in df.columns]
                            if include_volume and 'Volume' in df.columns:
                                available_cols.append('Volume')

                            df_filtered = df[available_cols].copy()
                            for col in [c for c in ohlc_cols if c in df_filtered.columns]:
                                df_filtered[col] = df_filtered[col].round(2)

                            saved_path = save_data_to_server(formatted_symbol, df_filtered)
                            st.success(f"✅ Data for **{formatted_symbol}** fetched and saved on server: `{saved_path}`")

                            curr_symbol = get_currency_symbol(formatted_symbol, ticker)
                            fmt_val = lambda val: f"{curr_symbol}{val:,.2f}" if curr_symbol else f"{val:,.2f}"

                            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                            latest_close = df_filtered['Close'].iloc[-1]
                            prev_close = df_filtered['Close'].iloc[-2] if len(df_filtered) > 1 else latest_close
                            change = latest_close - prev_close
                            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

                            m_col1.metric("Latest Close", fmt_val(latest_close), f"{change:+.2f} ({change_pct:+.2f}%)")
                            m_col2.metric("Period High", fmt_val(df_filtered['High'].max()))
                            m_col3.metric("Period Low", fmt_val(df_filtered['Low'].min()))
                            m_col4.metric("Total Days", len(df_filtered))

                            st.dataframe(df_filtered, width="stretch")

                            csv_data = df_filtered.to_csv(index=True)
                            st.download_button(
                                label=f"📥 Download {formatted_symbol} CSV",
                                data=csv_data,
                                file_name=f"{formatted_symbol}_OHLC_{start_date}_to_{end_date}.csv",
                                mime="text/csv"
                            )
                    except Exception as e:
                        st.error(f"❌ Error fetching data: {str(e)}")

    else: # Batch CSV Upload
        uploaded_file = st.file_uploader(
            "Upload CSV with 'Symbol' column",
            type=["csv"],
            help="CSV containing a 'Symbol' column listing ticker symbols."
        )

        sample_csv = "Symbol\nBAJAJ-AUTO\nRELIANCE\nTCS\nINFY\n^NSEI\nAAPL\n"
        st.download_button(
            label="📄 Download Sample CSV Template",
            data=sample_csv,
            file_name="stock_symbols_sample.csv",
            mime="text/csv"
        )

        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                symbol_col = next((c for c in uploaded_df.columns if str(c).strip().lower() == 'symbol'), None)

                if symbol_col is None:
                    st.error(f"❌ Missing 'Symbol' column. Found columns: `{list(uploaded_df.columns)}`")
                else:
                    raw_symbols = uploaded_df[symbol_col].dropna().astype(str).str.strip().str.upper().unique().tolist()
                    symbols_list = [format_symbol(s, auto_append_ns) for s in raw_symbols if s]

                    st.success(f"✅ Found **{len(symbols_list)}** valid stock symbol(s): `{', '.join(symbols_list)}`")

                    if st.button("🚀 Fetch Batch OHLC Data"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        zip_buffer = io.BytesIO()
                        results_summary = []
                        fetch_end = end_date + timedelta(days=1)

                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for idx, sym in enumerate(symbols_list):
                                status_text.text(f"Fetching [{idx+1}/{len(symbols_list)}]: {sym}...")
                                try:
                                    ticker = yf.Ticker(sym)
                                    df = ticker.history(start=start_date, end=fetch_end)

                                    if df.empty:
                                        results_summary.append({"Symbol": sym, "Rows": 0, "Status": "❌ No Data"})
                                    else:
                                        df.index = pd.to_datetime(df.index)
                                        df.index = df.index.strftime('%Y-%m-%d')
                                        df.index.name = 'Date'

                                        ohlc_cols = ['Open', 'High', 'Low', 'Close']
                                        available_cols = [c for c in ohlc_cols if c in df.columns]
                                        if include_volume and 'Volume' in df.columns:
                                            available_cols.append('Volume')

                                        df_filtered = df[available_cols].copy()
                                        for col in [c for c in ohlc_cols if c in df_filtered.columns]:
                                            df_filtered[col] = df_filtered[col].round(2)

                                        save_data_to_server(sym, df_filtered)
                                        csv_content = df_filtered.to_csv(index=True)
                                        zip_file.writestr(f"{sym}_OHLC.csv", csv_content)

                                        results_summary.append({"Symbol": sym, "Rows": len(df_filtered), "Status": "✅ Success & Saved"})
                                except Exception as ex:
                                    results_summary.append({"Symbol": sym, "Rows": 0, "Status": f"❌ Error ({str(ex)})"})

                                progress_bar.progress((idx + 1) / len(symbols_list))

                        status_text.text("Processing complete! Data stored on server.")
                        zip_buffer.seek(0)
                        summary_df = pd.DataFrame(results_summary)
                        st.dataframe(summary_df, width="stretch")

                        st.download_button(
                            label=f"📦 Download Zipped CSVs ({len(symbols_list)} files)",
                            data=zip_buffer.getvalue(),
                            file_name=f"Stock_OHLC_Batch_{start_date}_to_{end_date}.zip",
                            mime="application/zip"
                        )
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")


# --- TAB 2: STOCK SCREENER ---
with main_tab2:
    st.subheader("📊 Technical Stock Screener")
    st.markdown("Filter stocks based on Moving Averages, Super-Trend, and Candle Patterns using custom logic (AND/OR).")

    # Data Source Selection for Screener
    data_source = st.radio(
        "Select Stock Data Source for Screener",
        ["Bulk CSV Upload", "Preset Market Indices (NIFTY 50, SENSEX, etc.)", "Server Stored Data"],
        help="Choose uploaded CSV, select preset index data, or use data previously saved on the server."
    )

    screener_stock_data = {} # Dict of {symbol: df}

    if data_source == "Bulk CSV Upload":
        uploaded_screener_file = st.file_uploader(
            "Upload Bulk CSV file with 'Symbol' column",
            type=["csv"],
            key="screener_csv_uploader"
        )
        if uploaded_screener_file is not None:
            try:
                up_df = pd.read_csv(uploaded_screener_file)
                sym_col = next((c for c in up_df.columns if str(c).strip().lower() == 'symbol'), None)
                if sym_col:
                    symbols = up_df[sym_col].dropna().astype(str).str.strip().str.upper().unique().tolist()
                    symbols = [format_symbol(s, auto_append_ns) for s in symbols if s]
                    st.info(f"Loaded **{len(symbols)}** symbols from uploaded CSV: `{', '.join(symbols)}`")

                    if st.button("📥 Download & Cache Stock Data for Screener"):
                        progress = st.progress(0)
                        st_text = st.empty()
                        end_d = datetime.today()
                        start_d = end_d - timedelta(days=365)
                        fetch_end = end_d + timedelta(days=1)

                        for idx, sym in enumerate(symbols):
                            st_text.text(f"Fetching [{idx+1}/{len(symbols)}]: {sym}...")
                            try:
                                tk = yf.Ticker(sym)
                                d_hist = tk.history(start=start_d, end=fetch_end)
                                if not d_hist.empty:
                                    d_hist.index = pd.to_datetime(d_hist.index).strftime('%Y-%m-%d')
                                    d_hist.index.name = 'Date'
                                    save_data_to_server(sym, d_hist)
                                    screener_stock_data[sym] = d_hist
                            except Exception:
                                pass
                            progress.progress((idx + 1) / len(symbols))
                        st.session_state['screener_stock_data'] = screener_stock_data
                        st.success(f"✅ Successfully downloaded & saved {len(screener_stock_data)} stock dataset(s) on server!")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    elif data_source == "Preset Market Indices (NIFTY 50, SENSEX, etc.)":
        selected_preset = st.selectbox("Choose Stock Market Index", list(PRESET_LISTS.keys()))
        symbols_preset = PRESET_LISTS[selected_preset]
        symbols_preset_fmt = [format_symbol(s, auto_append_ns) for s in symbols_preset]
        st.write(f"Constituent Symbols ({len(symbols_preset_fmt)}): `{', '.join(symbols_preset_fmt)}`")

        if st.button(f"📥 Download {selected_preset} Data & Save to Server"):
            progress = st.progress(0)
            st_text = st.empty()
            end_d = datetime.today()
            start_d = end_d - timedelta(days=365)
            fetch_end = end_d + timedelta(days=1)

            for idx, sym in enumerate(symbols_preset_fmt):
                st_text.text(f"Fetching [{idx+1}/{len(symbols_preset_fmt)}]: {sym}...")
                try:
                    tk = yf.Ticker(sym)
                    d_hist = tk.history(start=start_d, end=fetch_end)
                    if not d_hist.empty:
                        d_hist.index = pd.to_datetime(d_hist.index).strftime('%Y-%m-%d')
                        d_hist.index.name = 'Date'
                        save_data_to_server(sym, d_hist)
                        screener_stock_data[sym] = d_hist
                except Exception:
                    pass
                progress.progress((idx + 1) / len(symbols_preset_fmt))
            st.session_state['screener_stock_data'] = screener_stock_data
            st.success(f"✅ Successfully downloaded & saved {len(screener_stock_data)} stocks on server for backtesting!")

    else: # Server Stored Data
        saved_files = [f for f in os.listdir(DATA_DIR) if f.endswith('_OHLC.csv')]
        if saved_files:
            st.info(f"📁 Found **{len(saved_files)}** stock dataset(s) saved on server.")
            if st.button("🔄 Load Server Saved Stock Data"):
                for sf in saved_files:
                    sym = sf.replace('_OHLC.csv', '')
                    fp = os.path.join(DATA_DIR, sf)
                    df_load = pd.read_csv(fp, index_col=0)
                    screener_stock_data[sym] = df_load
                st.session_state['screener_stock_data'] = screener_stock_data
                st.success(f"✅ Loaded {len(screener_stock_data)} saved stock datasets into screener!")
        else:
            st.warning("⚠️ No saved stock files found on server. Please download data using Bulk CSV Upload or Market Indices first.")

    # Retrieve cached data if available
    if 'screener_stock_data' in st.session_state and st.session_state['screener_stock_data']:
        screener_stock_data = st.session_state['screener_stock_data']

    st.markdown("---")
    st.subheader("⚙️ Screener Indicator Inputs & Criteria")

    c1, c2 = st.columns(2)
    with c1:
        timeframe = st.selectbox(
            "1. Time Frame",
            ["1D (default)", "1Y", "6M", "3M", "1M", "1W", "4H", "1H", "30M", "15M", "5M", "1M_INTRA"],
            index=0
        )
    with c2:
        candle_type = st.selectbox(
            "4. Candle Type",
            ["Normal (default)", "Heikin Ashi"],
            index=0
        )

    st.markdown("##### 2. Moving Average Criteria")
    col_ma1, col_ma2, col_ma3 = st.columns(3)
    with col_ma1:
        ma_enable = st.checkbox("Enable MA Filter", value=True)
    with col_ma2:
        ma_period = st.number_input("MA Period", min_value=1, value=50, step=1, help="Type desired MA period e.g. 20, 50, 100, 200")
    with col_ma3:
        ma_op = st.selectbox("MA Operator (Price vs MA)", ["> Greater Than", "< Less Than", "== Equal To"])

    st.markdown("##### 3. Super Trend Criteria")
    col_st1, col_st2, col_st3, col_st4 = st.columns(4)
    with col_st1:
        st_enable = st.checkbox("Enable Super Trend Filter", value=False)
    with col_st2:
        st_period = st.number_input("ST ATR Period", min_value=1, value=7, step=1, help="Type desired ATR period e.g. 7, 10, 14, 21")
    with col_st3:
        st_mult = st.number_input("ST Multiplier", min_value=0.1, value=3.0, step=0.5, help="Type desired ST multiplier e.g. 1.0, 2.0, 3.0")
    with col_st4:
        st_op = st.selectbox("ST Operator (Price vs SuperTrend)", ["> Greater Than", "< Less Than", "== Equal To"])

    st.markdown("##### 5. Filter Execution Logic")
    logic_op = st.radio("Combine Enabled Conditions Using:", ["AND (All match)", "OR (Any match)"], horizontal=True)

    if st.button("🔍 Run Stock Screener", width="stretch"):
        if not screener_stock_data:
            st.error("❌ No stock data loaded! Please load stock data from Bulk CSV, Market Indices, or Server Storage above.")
        else:
            filtered_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            symbols_to_screen = list(screener_stock_data.keys())

            ma_period_int = int(ma_period)
            st_period_int = int(st_period)

            for idx, sym in enumerate(symbols_to_screen):
                status_text.text(f"Screening [{idx+1}/{len(symbols_to_screen)}]: {sym}...")
                df_stock = screener_stock_data[sym].copy()

                if len(df_stock) < 5:
                    continue

                # Ensure numeric types
                for col in ['Open', 'High', 'Low', 'Close']:
                    if col in df_stock.columns:
                        df_stock[col] = pd.to_numeric(df_stock[col], errors='coerce')

                # Candle Type Calculation
                if candle_type == "Heikin Ashi":
                    df_calc = calculate_heikin_ashi(df_stock)
                    close_series = df_calc['HA_Close']
                    open_series = df_calc['HA_Open']
                else:
                    df_calc = df_stock.copy()
                    close_series = df_calc['Close']
                    open_series = df_calc['Open']

                latest_close = close_series.iloc[-1]
                latest_open = open_series.iloc[-1]

                # MA Calculation & Trend Determination
                df_calc['MA'] = calculate_sma(close_series, ma_period_int)
                latest_ma = df_calc['MA'].iloc[-1]
                if pd.isna(latest_ma):
                    ma_trend = "N/A"
                elif abs(latest_close - latest_ma) / latest_ma < 0.001:
                    ma_trend = "🟠 Neutral (Price ≈ MA)"
                elif latest_close > latest_ma:
                    ma_trend = "🟢 Bullish (Price > MA)"
                else:
                    ma_trend = "🔴 Bearish (Price < MA)"

                # SuperTrend Calculation
                df_st = calculate_supertrend(df_calc, period=st_period_int, multiplier=st_mult)
                latest_st = df_st['SuperTrend'].iloc[-1]
                st_trend = df_st['ST_Trend'].iloc[-1]

                cond_ma_pass = True
                if ma_enable:
                    if pd.isna(latest_ma):
                        cond_ma_pass = False
                    elif ">" in ma_op:
                        cond_ma_pass = latest_close > latest_ma
                    elif "<" in ma_op:
                        cond_ma_pass = latest_close < latest_ma
                    else: # ==
                        cond_ma_pass = abs(latest_close - latest_ma) / latest_ma < 0.001

                cond_st_pass = True
                if st_enable:
                    if pd.isna(latest_st) or np.isnan(latest_st):
                        cond_st_pass = False
                    elif ">" in st_op:
                        cond_st_pass = latest_close > latest_st
                    elif "<" in st_op:
                        cond_st_pass = latest_close < latest_st
                    else: # ==
                        cond_st_pass = abs(latest_close - latest_st) / latest_st < 0.001

                # Combine active conditions
                active_conditions = []
                if ma_enable:
                    active_conditions.append(cond_ma_pass)
                if st_enable:
                    active_conditions.append(cond_st_pass)

                if not active_conditions:
                    is_match = True
                elif "AND" in logic_op:
                    is_match = all(active_conditions)
                else: # OR
                    is_match = any(active_conditions)

                if is_match:
                    filtered_results.append({
                        "Symbol": sym,
                        "Time Frame": timeframe,
                        "Latest Close": round(latest_close, 2),
                        f"MA ({ma_period_int})": round(latest_ma, 2) if pd.notna(latest_ma) else None,
                        "MA Trend": ma_trend,
                        f"SuperTrend ({st_period_int}, {st_mult})": round(float(latest_st), 2) if (pd.notna(latest_st) and not np.isnan(latest_st)) else None,
                        "ST Trend": st_trend,
                        "Candle Type": candle_type,
                        "Candle Pattern": "🟢 Bullish" if latest_close >= latest_open else "🔴 Bearish"
                    })

                progress_bar.progress((idx + 1) / len(symbols_to_screen))

            status_text.text("Screening Complete!")
            res_df = pd.DataFrame(filtered_results)

            st.markdown("### 🏆 Filtered Screener Results")
            st.metric("Total Stocks Matching Criteria", len(res_df))

            if not res_df.empty:
                st.dataframe(res_df, width="stretch")
                csv_screen = res_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Screener Results CSV",
                    data=csv_screen,
                    file_name="screener_filtered_stocks.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ No stocks matched the specified screening criteria.")
