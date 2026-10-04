import streamlit as st
import yfinance as yf
import pandas as pd
import io
import zipfile
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(
    page_title="Yahoo Finance Equity Data Downloader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📈 Yahoo Finance Equity Data Downloader</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Fetch, preview, and download OHLC stock data with rounded 2 decimal precision (Single & Batch Modes).</div>', unsafe_allow_html=True)

def format_symbol(symbol: str, append_ns: bool) -> str:
    """
    Appends '.NS' suffix for Indian NSE equity symbols if enabled and no extension exists.
    Supports symbols containing hyphens (e.g. BAJAJ-AUTO -> BAJAJ-AUTO.NS).
    """
    sym = symbol.strip().upper()
    if not sym:
        return sym

    # Do not append if symbol is an index (starts with ^) or FX currency pair (ends with =X)
    if sym.startswith('^') or sym.endswith('=X'):
        return sym

    # Do not append if it already has an exchange dot extension (e.g. .NS, .BO, .L, .DE, .PA, .T)
    if '.' in sym:
        return sym

    # Do not append for crypto pairs ending with -USD, -EUR, -BTC, etc.
    crypto_suffixes = ['-USD', '-EUR', '-GBP', '-INR', '-BTC', '-ETH', '-USDT']
    if any(sym.endswith(suffix) for suffix in crypto_suffixes):
        return sym

    if append_ns:
        return f"{sym}.NS"

    return sym

def get_currency_symbol(symbol: str, ticker: yf.Ticker) -> str:
    """
    Determine appropriate currency prefix for metric display.
    Returns empty string for index symbols (starting with '^') since index values are points.
    """
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

# Sidebar Inputs
st.sidebar.header("⚙️ Configuration")

input_mode = st.sidebar.radio(
    "Select Input Mode",
    ["Single Stock Symbol", "Batch CSV Upload"],
    help="Choose whether to download data for a single symbol or upload a CSV containing multiple stock symbols."
)

default_start = datetime.today() - timedelta(days=365)
default_end = datetime.today()

col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    start_date = st.date_input("Start Date", value=default_start)
with col_s2:
    end_date = st.date_input("End Date", value=default_end)

include_volume = st.sidebar.checkbox("Include Volume Column", value=True)

auto_append_ns = st.sidebar.checkbox(
    "Auto-append '.NS' to Indian symbols",
    value=True,
    help="Automatically appends '.NS' suffix for Indian NSE equity symbols (e.g. BAJAJ-AUTO -> BAJAJ-AUTO.NS, RELIANCE -> RELIANCE.NS)."
)

st.sidebar.markdown("---")

if input_mode == "Single Stock Symbol":
    st.sidebar.subheader("🔍 Search Parameter")
    symbol_input = st.sidebar.text_input(
        "Stock Symbol",
        value="BAJAJ-AUTO",
        help="Enter ticker symbol (e.g. BAJAJ-AUTO, RELIANCE, TCS, AAPL, ^NSEI)"
    ).strip().upper()

    st.sidebar.markdown("### 💡 Quick Examples")
    st.sidebar.markdown("""
    - **Indian Stocks (NSE):** `BAJAJ-AUTO`, `RELIANCE`, `TCS`, `INFY`
    - **Indian Indices:** `^NSEI` (Nifty 50), `^BSESN` (Sensex)
    - **US Stocks / Indices:** `AAPL`, `MSFT`, `^GSPC` (S&P 500)
    - **Crypto / FX:** `BTC-USD`, `EURUSD=X`
    """)

    if not symbol_input:
        st.warning("⚠️ Please enter a stock symbol in the sidebar.")
    elif start_date > end_date:
        st.error("❌ Error: Start Date cannot be after End Date.")
    else:
        formatted_symbol = format_symbol(symbol_input, auto_append_ns)

        with st.spinner(f"Fetching data for **{formatted_symbol}**..."):
            try:
                ticker = yf.Ticker(formatted_symbol)
                fetch_end = end_date + timedelta(days=1)
                df = ticker.history(start=start_date, end=fetch_end)

                if df.empty:
                    st.error(f"❌ No data found for symbol **{formatted_symbol}** between {start_date} and {end_date}. Please verify the symbol and date range.")
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

                    curr_symbol = get_currency_symbol(formatted_symbol, ticker)
                    fmt_val = lambda val: f"{curr_symbol}{val:,.2f}" if curr_symbol else f"{val:,.2f}"

                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    latest_close = df_filtered['Close'].iloc[-1]
                    prev_close = df_filtered['Close'].iloc[-2] if len(df_filtered) > 1 else latest_close
                    change = latest_close - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

                    high_val = df_filtered['High'].max()
                    low_val = df_filtered['Low'].min()

                    m_col1.metric("Latest Close", fmt_val(latest_close), f"{change:+.2f} ({change_pct:+.2f}%)")
                    m_col2.metric("Period High", fmt_val(high_val))
                    m_col3.metric("Period Low", fmt_val(low_val))
                    m_col4.metric("Total Trading Days", len(df_filtered))

                    tab1, tab2 = st.tabs(["📊 Price Chart", "📋 Data Table"])

                    with tab1:
                        st.subheader(f"{formatted_symbol} Price Trend")
                        st.line_chart(df_filtered[['Open', 'High', 'Low', 'Close']])

                    with tab2:
                        st.subheader(f"OHLC Data Preview ({len(df_filtered)} rows)")
                        st.dataframe(df_filtered, width="stretch")

                    csv_data = df_filtered.to_csv(index=True)
                    file_name = f"{formatted_symbol}_OHLC_{start_date}_to_{end_date}.csv"

                    st.markdown("---")
                    st.download_button(
                        label=f"📥 Download {formatted_symbol} OHLC CSV",
                        data=csv_data,
                        file_name=file_name,
                        mime="text/csv",
                        width="stretch"
                    )

            except Exception as e:
                st.error(f"❌ An error occurred while fetching data: {str(e)}")

else:
    st.sidebar.subheader("📁 Upload CSV File")
    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV with 'Symbol' column",
        type=["csv"],
        help="Upload a CSV file containing a 'Symbol' column listing ticker symbols."
    )

    # Provide sample CSV download
    sample_csv = "Symbol\nBAJAJ-AUTO\nRELIANCE\nTCS\nINFY\n^NSEI\nAAPL\n"
    st.sidebar.download_button(
        label="📄 Download Sample CSV Template",
        data=sample_csv,
        file_name="stock_symbols_sample.csv",
        mime="text/csv"
    )

    if start_date > end_date:
        st.error("❌ Error: Start Date cannot be after End Date.")
    elif uploaded_file is None:
        st.info("ℹ️ Please upload a CSV file in the sidebar to start batch processing. The CSV must contain a **'Symbol'** column.")
    else:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
            
            # Case-insensitive column matching for 'Symbol'
            symbol_col = None
            for col in uploaded_df.columns:
                if str(col).strip().lower() == 'symbol':
                    symbol_col = col
                    break

            if symbol_col is None:
                st.error(f"❌ Validation Failed: The uploaded CSV file does not contain a **'Symbol'** column. Found columns: `{list(uploaded_df.columns)}`")
            else:
                raw_symbols = uploaded_df[symbol_col].dropna().astype(str).str.strip().str.upper().unique().tolist()
                raw_symbols = [s for s in raw_symbols if s]

                if not raw_symbols:
                    st.error("❌ Validation Failed: The 'Symbol' column in the uploaded CSV is empty or contains no valid stock symbols.")
                else:
                    symbols_list = [format_symbol(s, auto_append_ns) for s in raw_symbols]
                    st.success(f"✅ CSV Validated Successfully! Found **{len(symbols_list)}** unique stock symbol(s): `{', '.join(symbols_list)}`")

                    fetch_button = st.button("🚀 Fetch Batch OHLC Data", width="stretch")

                    if fetch_button or 'batch_zip' in st.session_state:
                        if fetch_button:
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
                                            results_summary.append({"Symbol": sym, "Rows": 0, "Status": "❌ No Data Found"})
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

                                            csv_content = df_filtered.to_csv(index=True)
                                            file_in_zip = f"{sym}_OHLC_{start_date}_to_{end_date}.csv"
                                            zip_file.writestr(file_in_zip, csv_content)

                                            results_summary.append({"Symbol": sym, "Rows": len(df_filtered), "Status": "✅ Success"})
                                    except Exception as ex:
                                        results_summary.append({"Symbol": sym, "Rows": 0, "Status": f"❌ Error ({str(ex)})"})

                                    progress_bar.progress((idx + 1) / len(symbols_list))

                            status_text.text("Processing complete!")
                            zip_buffer.seek(0)
                            
                            st.session_state['batch_zip'] = zip_buffer.getvalue()
                            st.session_state['summary_df'] = pd.DataFrame(results_summary)

                        if 'batch_zip' in st.session_state:
                            summary_df = st.session_state['summary_df']
                            success_count = (summary_df['Status'] == "✅ Success").sum()

                            st.subheader("📊 Batch Processing Summary")
                            m_b1, m_b2, m_b3 = st.columns(3)
                            m_b1.metric("Total Symbols Requested", len(symbols_list))
                            m_b2.metric("Successfully Fetched", success_count)
                            m_b3.metric("Failed / No Data", len(symbols_list) - success_count)

                            st.dataframe(summary_df, width="stretch")

                            zip_filename = f"Stock_OHLC_Batch_{start_date}_to_{end_date}.zip"
                            st.markdown("---")
                            st.download_button(
                                label=f"📦 Download Zipped CSVs for All Symbols ({len(symbols_list)} files)",
                                data=st.session_state['batch_zip'],
                                file_name=zip_filename,
                                mime="application/zip",
                                width="stretch"
                            )

        except Exception as e:
            st.error(f"❌ Error reading CSV file: {str(e)}")
