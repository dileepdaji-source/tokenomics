import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="$SVPERIOR: Tokenomics Simulator", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .sidebar .sidebar-content { background: #262730; }
    h1, h2, h3 { 
        color: #F59E0B !important; 
        font-family: 'Helvetica', 'Arial', sans-serif !important;
    }
    body, .stApp, p, div, span, label, .stMarkdown, .stDataFrame, .stMetric {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    }
    .metric-container {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    /* Slider styling */
    [data-baseweb="slider"] [role="slider"] {
        background-color: #D92A1C !important;
    }
    [data-baseweb="slider"] [data-testid="stSliderTrack"] > div {
        background-color: #D92A1C !important;
    }
    .stSlider [data-baseweb="slider"] > div > div {
        background-color: #D92A1C !important;
    }
    /* Sidebar collapse button styling */
    [data-testid="collapsedControl"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.image("https://www.svperior.com/wp-content/uploads/2025/07/Svperior-Logomark.png", width=150)
st.sidebar.header("Simulation Parameters")

st.sidebar.subheader("1. Protocol Growth")
initial_aum = st.sidebar.number_input("New AUM Added Per Month ($M)", value=10, step=50)
monthly_growth = st.sidebar.slider("Monthly AUM Growth Rate (%)", 0, 20, 1)

st.sidebar.subheader("2. Token Mechanics")
initial_supply = st.sidebar.number_input("Initial Token Supply", value=100000000, step=1000000, format="%d")
fee_bps = st.sidebar.slider("Protocol Fee (Basis Points)", 5, 150, 25)
burn_pct = st.sidebar.slider("Burn Rate (%)", 0, 100, 50)
initial_price = st.sidebar.number_input("Starting Token Price ($)", value=0.50, step=0.10)

st.sidebar.subheader("3. Market Depth")
liquidity_depth = st.sidebar.number_input(
    "Buy Pressure for 1% Move ($)", 
    value=500000, 
    step=50000, 
    format="%d",
    help="On Uniswap (DeFi) or a mid-tier exchange (like Bybit...), the 'Liquidity Pool' usually holds about $5M - $10M worth of tokens. Mathematically, in a pool of that size, a $50k - $250k buy order is usually enough to shift the price by ~1%."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Your Portfolio")
user_tokens = st.sidebar.number_input("Tokens You Own", value=1000000, step=100000, format="%d")

# --- SIMULATION LOGIC ---
def run_simulation():
    months = 24
    current_supply = initial_supply
    current_price = initial_price
    
    # Convert inputs
    fee_rate = fee_bps / 10000
    
    data = []
    
    # Track total AUM
    total_aum = 0
    # Current Monthly New AUM
    monthly_new_aum = initial_aum * 1_000_000 
    
    for i in range(1, months + 1):
        # Add new AUM to total
        total_aum += monthly_new_aum
        
        # 1. Revenue (based on new AUM only)
        revenue_usd = monthly_new_aum * fee_rate
        
        # 2. Tokens Bought & Burned
        tokens_bought = revenue_usd / current_price
        tokens_burned = tokens_bought * (burn_pct / 100)
        
        # Circuit Breaker: If supply is critically low, reduce burn to microscopic amounts
        CRITICAL_SUPPLY_THRESHOLD = 1_000_000  # 1M tokens
        if current_supply < CRITICAL_SUPPLY_THRESHOLD:
            # As supply approaches zero, price goes to infinity, so burn becomes microscopic
            supply_factor = current_supply / CRITICAL_SUPPLY_THRESHOLD
            tokens_burned = tokens_burned * supply_factor * 0.01  # Reduce burn by 99%+ when critical
        
        # 3. Price Impact Logic
        current_mcap = current_supply * current_price
        # Dynamic depth grows with market cap to prevent infinite price explosions
        # Base liquidity + 1% of market cap as available depth
        dynamic_depth = liquidity_depth + (current_mcap * 0.01)
        
        price_move_pct = revenue_usd / dynamic_depth
        current_price = current_price * (1 + price_move_pct)
        
        # 4. Update Supply with guardrails
        current_supply -= tokens_burned
        current_supply = max(0, current_supply)  # Supply can never go negative
        
        # 5. Growth for next month
        monthly_new_aum = monthly_new_aum * (1 + (monthly_growth / 100))
        
        # 6. Portfolio Value
        portfolio_value = user_tokens * current_price
        
        # 7. Total Token Value (Market Cap)
        total_token_value = current_supply * current_price
        
        data.append({
            "Month": i,
            "Total AUM ($)": total_aum,
            "New AUM ($)": monthly_new_aum,
            "Revenue ($)": revenue_usd,
            "Token Price ($)": current_price,
            "Supply": current_supply,
            "TTV ($)": total_token_value,
            "Tokens Burned": tokens_burned,
            "Market Depth ($)": dynamic_depth,
            "Your Portfolio Value ($)": portfolio_value
        })
        
    return pd.DataFrame(data)

df = run_simulation()

# --- DASHBOARD LAYOUT ---

st.title("$SVPERIOR: Tokenomics Simulator")

# Top Level Metrics
final_price = df.iloc[-1]['Token Price ($)']
start_port_value = user_tokens * initial_price
final_port_value = user_tokens * final_price
roi_pct = ((final_port_value - start_port_value) / start_port_value) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Target Token Price", f"${final_price:,.2f}")
col2.metric("Ending Supply", f"{df.iloc[-1]['Supply']:,.0f}")
col3.metric("Your Portfolio Start", f"${start_port_value:,.0f}")
col4.metric("Your Portfolio End", f"${final_port_value:,.0f}", f"+{roi_pct:,.0f}%")

st.markdown("---")

# Charts - 3 columns
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Token Price")
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(
        x=df['Month'], 
        y=df['Token Price ($)'], 
        line=dict(color='#00FF94', width=3),
        name="Price"
    ))
    fig_price.update_layout(
        yaxis=dict(title="Price ($)", gridcolor='#333'),
        xaxis=dict(title="Month", gridcolor='#333'),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    st.plotly_chart(fig_price, use_container_width=True)

with c2:
    st.subheader("Token Supply")
    fig_supply = go.Figure()
    fig_supply.add_trace(go.Scatter(
        x=df['Month'], 
        y=df['Supply'], 
        line=dict(color='#D92A1C', width=3),
        name="Supply"
    ))
    fig_supply.update_layout(
        yaxis=dict(title="Supply", gridcolor='#333'),
        xaxis=dict(title="Month", gridcolor='#333'),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    st.plotly_chart(fig_supply, use_container_width=True)

with c3:
    st.subheader("Your Portfolio Value")
    fig_port = go.Figure()
    fig_port.add_trace(go.Scatter(
        x=df['Month'], 
        y=df['Your Portfolio Value ($)'],
        fill='tozeroy',
        line=dict(color='#1E90FF', width=3),
        name="Portfolio Value"
    ))
    fig_port.update_layout(
        yaxis=dict(title="Value ($)", gridcolor='#333'),
        xaxis=dict(title="Month", gridcolor='#333'),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    st.plotly_chart(fig_port, use_container_width=True)

# Data Table
st.dataframe(df.style.format({
    "Total AUM ($)": "${:,.0f}",
    "New AUM ($)": "${:,.0f}",
    "Revenue ($)": "${:,.0f}",
    "Token Price ($)": "${:,.2f}",
    "Supply": "{:,.0f}",
    "TTV ($)": "${:,.0f}",
    "Tokens Burned": "{:,.0f}",
    "Market Depth ($)": "${:,.0f}",
    "Your Portfolio Value ($)": "${:,.0f}"
}))

st.subheader("Total Assets Under Management")
fig_aum = go.Figure()
fig_aum.add_trace(go.Scatter(
    x=df['Month'], 
    y=df['Total AUM ($)'],
    fill='tozeroy',
    line=dict(color='#F59E0B', width=3),
    name="Total AUM"
))
fig_aum.update_layout(
    yaxis=dict(title="Total AUM ($)", gridcolor='#333'),
    xaxis=dict(title="Month", gridcolor='#333'),
    margin=dict(l=0, r=0, t=0, b=0),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    showlegend=False
)
st.plotly_chart(fig_aum, use_container_width=True)

st.subheader("Required Liquidity for 1% Move")
st.area_chart(df.set_index('Month')[['Market Depth ($)']])
