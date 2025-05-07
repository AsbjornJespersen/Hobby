import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import requests
import io

st.set_page_config(layout="wide")
st.title("📈 AsbBuffets Portfolio")
st.subheader("📊 Tracking Nasdaq-100")
st.markdown("""
I built this tool to manually track and replicate the Nasdaq-100 index by buying individual stocks.  
That way, I avoid paying annual management fees to an ETF provider — but still follow the same investment strategy.
""")

# ---- Fetch Nasdaq-100 Weights ----
url = "https://www.slickcharts.com/nasdaq100"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
tables = pd.read_html(response.text)
nasdaq_df = tables[0][['Symbol', 'Company', 'Portfolio%']]
nasdaq_df.columns = ['Ticker', 'Company', 'Nasdaq100 Weight (%)']
nasdaq_df.set_index('Ticker', inplace=True)
nasdaq_df['Nasdaq100 Weight (%)'] = (
    nasdaq_df['Nasdaq100 Weight (%)']
    .astype(str).str.replace('%', '', regex=False)
    .str.replace(',', '', regex=False).astype(float)
)

# ---- User Input via Sliders for Top 20 Stocks ----
st.sidebar.header("Adjust Your Holdings (Top 20)")
top20 = nasdaq_df.head(20)
default_portfolio = {
    'AAPL': 11, 'MSFT': 5, 'NVDA': 17, 'CSCO': 23,
    'AMZN': 7, 'GOOGL': 8, 'TMUS': 5, 'AVGO': 6,
    'META': 2, 'NFLX': 1, 'BRK-B': 2, 'COST': 1,
}

if "portfolio_submitted" not in st.session_state:
    st.session_state.portfolio_submitted = True

with st.sidebar.form("portfolio_form"):
    portfolio = {}
    submitted = st.form_submit_button("Update Portfolio")
    for ticker in top20.index:
        default = default_portfolio.get(ticker, 0)
        shares = st.slider(f"{ticker} ({top20.loc[ticker, 'Company']})", 0, 50, default)
        if shares > 0:
            portfolio[ticker] = shares
    if submitted:
        st.session_state.portfolio_submitted = True

if not st.session_state.portfolio_submitted:
    st.stop()

# ---- Fetch Current Prices ----
tickers = list(portfolio.keys())
data = yf.download(tickers, period='1d', auto_adjust=True)
prices = data['Close'].iloc[-1] if isinstance(data.columns, pd.MultiIndex) else data.iloc[-1]

# ---- Calculate Portfolio Weights ----
df = pd.DataFrame({'Shares': pd.Series(portfolio), 'Price': prices})
df['Value'] = df['Shares'] * df['Price']
df['Weight (%)'] = 100 * df['Value'] / df['Value'].sum()

# ---- Merge and Compare ----
comparison = df.merge(nasdaq_df[['Nasdaq100 Weight (%)']], left_index=True, right_index=True, how='outer').fillna(0)
comparison['Difference (%)'] = comparison['Weight (%)'] - comparison['Nasdaq100 Weight (%)']
comparison = comparison.sort_values('Nasdaq100 Weight (%)', ascending=False)

# ---- Portfolio Value ----
total_usd = df['Value'].sum()
fx_data = yf.download('USDDKK=X', period='1d', interval='1m')['Close'].dropna()
fx_rate = float(fx_data.iloc[0])
total_dkk = total_usd * fx_rate

st.markdown(f"""
<div style='background-color:#e6ffed;padding:20px;border-radius:10px;text-align:center'>
    <h2 style='color:#008000;'>💰 Portfolio Value</h2>
    <h1 style='color:#008000;'>${total_usd:,.2f} USD</h1>
    <h1 style='color:#008000;'>{total_dkk:,.2f} DKK</h1>
    <p style='color:gray'>Exchange Rate: {fx_rate:.2f} DKK/USD</p>
</div>
""", unsafe_allow_html=True)

# ---- Portfolio Performance Summary ----
performance_periods = {
    "1 Day": "1d",
    "1 Month": "1mo",
    "1 Year": "1y",
    "10 Years": "10y"
}

# ---- Bar Chart ----
st.write("### Nasdaq-100 Portfolio Tracker")
fig, ax = plt.subplots(figsize=(18, 6))
ax.bar(comparison.index, comparison['Nasdaq100 Weight (%)'], color='gray', label='Nasdaq-100')
ax.bar(comparison.index, comparison['Weight (%)'], alpha=0.7, label='Your Portfolio')
plt.xticks(rotation=90)
plt.ylabel('Weight (%)')
plt.title('Your Portfolio vs. Nasdaq-100 Allocation')
plt.legend()
st.pyplot(fig)

# ---- Suggest stock to buy with $1250 ----
purchase_amount = 1250
total_usd = df['Value'].sum()
suggestions = []

for ticker, row in comparison.iterrows():
    current_value = row['Value']
    target_weight = row['Nasdaq100 Weight (%)']
    new_value = current_value + purchase_amount
    new_total = total_usd + purchase_amount
    new_weight = 100 * new_value / new_total
    new_diff = abs(new_weight - target_weight)
    suggestions.append((ticker, new_diff, target_weight))

suggestions.sort(key=lambda x: x[1])
best_ticker, projected_gap, target_weight = suggestions[0]
price = df.loc[best_ticker, 'Price'] if best_ticker in df.index else yf.Ticker(best_ticker).info['regularMarketPrice']
shares_to_buy = purchase_amount / price

st.markdown(f"""
<div style="background-color:#e8f5ff;padding:20px;border-radius:10px">
    <h3 style='color:#0066cc;'>💡 Suggested Purchase</h3>
    <p style='font-size:20px;'>Buy <b>{shares_to_buy:.2f} shares</b> of <b>{best_ticker}</b> for ${purchase_amount}</p>
    <p style='color:gray;'>This would reduce your gap to the Nasdaq-100 target weight of <b>{target_weight:.2f}%</b> with a projected deviation of <b>{projected_gap:.2f}%</b>.</p>
</div>
""", unsafe_allow_html=True)

performance_changes = []

#for label, period in performance_periods.items():
#    hist = yf.download(tickers, period=period, interval="1d", auto_adjust=True)['Close']
#    if isinstance(hist.columns, pd.MultiIndex):
#        hist = hist[tickers]
#    portfolio_value = hist.dot(pd.Series(portfolio))
#    start_value = portfolio_value.iloc[0]
#    end_value = portfolio_value.iloc[-1]
#    pct_change = ((end_value - start_value) / start_value) * 100
#    color = "green" if pct_change >= 0 else "red"
#    performance_changes.append((label, pct_change, color))
#st.markdown("### 📈 Performance Snapshot")
#st.markdown("<div style='display: flex; gap: 40px;'>", unsafe_allow_html=True)
#for label, change, color in performance_changes:
#    st.markdown(f"""
#    <div style='text-align: center;'>
#        <h4>{label}</h4>
#        <h2 style='color:{color};'>{change:+.2f}%</h2>
#    </div>
#    """, unsafe_allow_html=True)
#st.markdown("</div>", unsafe_allow_html=True)