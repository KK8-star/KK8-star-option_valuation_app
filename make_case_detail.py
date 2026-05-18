import pathlib

content = """\
import streamlit as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf
import time
import random
import pandas as pd
from dataclasses import dataclass
from typing import Optional
from scipy.stats import norm

@dataclass
class ComparableTickerRow:
    ticker: str
    name: str
    volatility: Optional[float]
    current_price: Optional[float]
    error: Optional[str]

def _fetch_vol(ticker: str, period: str = "1y") -> ComparableTickerRow:
    wait_times = [5, 15, 30]
    for attempt, wait in enumerate(wait_times):
        try:
            pre_delay = 2.0 + random.uniform(0.5, 2.0)
            time.sleep(pre_delay)
            t_obj = yf.Ticker(ticker)
            info = {}
            try:
                time.sleep(1.5)
                info = t_obj.info or {}
            except Exception:
                info = {}
            hist = t_obj.history(period=period)
            if hist.empty:
                return ComparableTickerRow(
                    ticker=ticker,
                    name=info.get("shortName", ticker),
                    volatility=None,
                    current_price=None,
                    error="No price data"
                )
            closes = hist["Close"].dropna()
            log_returns = np.log(closes / closes.shift(1)).dropna()
            annual_vol = float(log_returns.std() * np.sqrt(252))
            current_price = float(closes.iloc[-1])
            name = info.get("shortName", ticker)
            return ComparableTickerRow(
                ticker=ticker,
                name=name,
                volatility=annual_vol,
                current_price=current_price,
                error=None
            )
        except Exception as e:
            err_msg = str(e).lower()
            is_rate_limit = any(x in err_msg for x in ["too many requests", "429", "rate limit", "throttl"])
            if attempt < len(wait_times) - 1:
                if is_rate_limit:
                    actual_wait = wait + random.uniform(0, 5)
                    st.warning(f"Rate limited [{ticker}]. Waiting {actual_wait:.0f}s (attempt {attempt+1}/{len(wait_times)})...")
                    time.sleep(actual_wait)
                else:
                    time.sleep(3)
                continue
            error_type = "Rate limited" if is_rate_limit else str(e)[:50]
            return ComparableTickerRow(
                ticker=ticker,
                name=ticker,
                volatility=None,
                current_price=None,
                error=error_type
            )
    return ComparableTickerRow(ticker=ticker, name=ticker, volatility=None, current_price=None, error="Max retries exceeded")

def fetch_comparables(tickers: list, period: str = "1y") -> list:
    results = []
    total = len(tickers)
    st.info(f"Fetching {total} ticker(s). Requests spaced 4-8s apart.")
    progress = st.progress(0)
    status = st.empty()
    for i, ticker in enumerate(tickers):
        status.text(f"Fetching {ticker} ({i+1}/{total})...")
        if i > 0:
            inter_delay = 4.0 + random.uniform(0, 4)
            time.sleep(inter_delay)
        row = _fetch_vol(ticker, period)
        results.append(row)
        progress.progress((i + 1) / total)
    status.text("Fetch complete.")
    return results

def bs_price(S, K, T, r, sigma, option_type="call"):
    if T <= 0:
        return max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == "call":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def bs_greeks(S, K, T, r, sigma, option_type="call"):
    if T <= 0:
        return {"delta": float("nan"), "gamma": float("nan"), "theta": float("nan"), "vega": float("nan"), "rho": float("nan")}
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    pdf_d1 = norm.pdf(d1)
    gamma = pdf_d1 / (S * sigma * np.sqrt(T))
    vega = S * pdf_d1 * np.sqrt(T) / 100
    if option_type == "call":
        delta = norm.cdf(d1)
        theta = (-(S * pdf_d1 * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        delta = norm.cdf(d1) - 1
        theta = (-(S * pdf_d1 * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}

def binomial_price(S, K, T, r, sigma, option_type="call", steps=5):
    dt = T / steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp(r * dt) - d) / (u - d)
    prices = np.zeros((steps + 1, steps + 1))
    for i in range(steps + 1):
        for j in range(i + 1):
            prices[j, i] = S * (u ** (i - j)) * (d ** j)
    values = np.zeros((steps + 1, steps + 1))
    for j in range(steps + 1):
        if option_type == "call":
            values[j, steps] = max(prices[j, steps] - K, 0)
        else:
            values[j, steps] = max(K - prices[j, steps], 0)
    for i in range(steps - 1, -1, -1):
        for j in range(i + 1):
            values[j, i] = np.exp(-r * dt) * (p * values[j, i + 1] + (1 - p) * values[j + 1, i + 1])
    return prices, values

def monte_carlo_price(S, K, T, r, sigma, option_type="call", n_sim=10000):
    np.random.seed(42)
    Z = np.random.standard_normal(n_sim)
    ST = S * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)
    if option_type == "call":
        payoffs = np.maximum(ST - K, 0)
    else:
        payoffs = np.maximum(K - ST, 0)
    price = np.exp(-r * T) * np.mean(payoffs)
    return price, ST, payoffs

def show(case: dict):
    st.title(f"Case Detail: {case.get('name', 'Unnamed')}")
    with st.expander("Parameters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            S = st.number_input("Stock Price (S)", value=float(case.get("stock_price", 100)), min_value=0.01)
            K = st.number_input("Strike Price (K)", value=float(case.get("strike_price", 100)), min_value=0.01)
        with col2:
            T = st.number_input("Time to Expiry (T, years)", value=float(case.get("time_to_expiry", 1.0)), min_value=0.01)
            r = st.number_input("Risk-free Rate (r)", value=float(case.get("risk_free_rate", 0.05)), min_value=0.0, max_value=1.0, step=0.001, format="%.3f")
        with col3:
            sigma = st.number_input("Volatility (sigma)", value=float(case.get("volatility", 0.2)), min_value=0.001, max_value=5.0, step=0.01, format="%.3f")
            option_type = st.selectbox("Option Type", ["call", "put"], index=0 if case.get("option_type", "call") == "call" else 1)
    tab1, tab2, tab3 = st.tabs(["Black-Scholes", "Binomial Model", "Monte Carlo"])
    with tab1:
        st.subheader("Black-Scholes Price")
        price_bs = bs_price(S, K, T, r, sigma, option_type)
        st.metric("Option Price", f"{price_bs:.4f}")
        st.latex(r"C = S \\cdot N(d_1) - K e^{-rT} \\cdot N(d_2)")
        st.latex(r"d_1 = \\frac{\\ln(S/K) + (r + \\frac{\\sigma^2}{2})T}{\\sigma\\sqrt{T}}, \\quad d_2 = d_1 - \\sigma\\sqrt{T}")
        st.subheader("Greeks")
        greeks = bs_greeks(S, K, T, r, sigma, option_type)
        g1, g2, g3, g4, g5 = st.columns(5)
        g1.metric("Delta", f"{greeks['delta']:.4f}")
        g2.metric("Gamma", f"{greeks['gamma']:.4f}")
        g3.metric("Theta", f"{greeks['theta']:.4f}")
        g4.metric("Vega", f"{greeks['vega']:.4f}")
        g5.metric("Rho", f"{greeks['rho']:.4f}")
    with tab2:
        st.subheader("Binomial Model (5-step)")
        prices, values = binomial_price(S, K, T, r, sigma, option_type, steps=5)
        st.write("**Stock Price Tree**")
        price_df = pd.DataFrame(prices, index=[f"d^{i}" for i in range(6)], columns=[f"Step {i}" for i in range(6)])
        st.dataframe(price_df.style.format("{:.2f}"))
        st.write("**Option Value Tree**")
        value_df = pd.DataFrame(values, index=[f"d^{i}" for i in range(6)], columns=[f"Step {i}" for i in range(6)])
        st.dataframe(value_df.style.format("{:.4f}"))
        st.metric("Binomial Price", f"{values[0, 0]:.4f}")
    with tab3:
        st.subheader("Monte Carlo Simulation")
        n_sim = st.slider("Simulations", 1000, 50000, 10000, 1000)
        price_mc, ST, payoffs = monte_carlo_price(S, K, T, r, sigma, option_type, n_sim)
        st.metric("Monte Carlo Price", f"{price_mc:.4f}")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        ax1.hist(ST, bins=50, color="steelblue", alpha=0.7, edgecolor="white")
        ax1.axvline(K, color="red", linestyle="--", label=f"K={K}")
        ax1.set_title("Terminal Stock Price Distribution")
        ax1.set_xlabel("Price")
        ax1.set_ylabel("Frequency")
        ax1.legend()
        ax2.hist(payoffs, bins=50, color="green", alpha=0.7, edgecolor="white")
        ax2.axvline(float(np.mean(payoffs)), color="orange", linestyle="--", label=f"Mean={np.mean(payoffs):.2f}")
        ax2.set_title("Payoff Distribution")
        ax2.set_xlabel("Payoff")
        ax2.set_ylabel("Frequency")
        ax2.legend()
        st.pyplot(fig)
        plt.close(fig)
    st.divider()
    st.subheader("Comparable Company Volatility")
    ticker_input = st.text_input("Enter ticker symbols (comma-separated)", placeholder="Example: 7203.T, 9984.T, AAPL, MSFT")
    period_sel = st.selectbox("Historical Period", ["6mo", "1y", "2y"], index=1)
    col_fetch, col_clear = st.columns([1, 1])
    with col_fetch:
        fetch_btn = st.button("Fetch Volatility", type="primary")
    with col_clear:
        clear_btn = st.button("Clear Results")
    if clear_btn:
        st.session_state.pop("comparable_results", None)
        st.rerun()
    if fetch_btn and ticker_input.strip():
        tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
        with st.spinner("Fetching data..."):
            results = fetch_comparables(tickers, period_sel)
        st.session_state["comparable_results"] = results
    if "comparable_results" in st.session_state:
        results = st.session_state["comparable_results"]
        rows = []
        for r_row in results:
            rows.append({
                "Ticker": r_row.ticker,
                "Name": r_row.name,
                "Volatility": f"{r_row.volatility:.1%}" if r_row.volatility else "N/A",
                "Current Price": f"{r_row.current_price:.2f}" if r_row.current_price else "N/A",
                "Status": "OK" if not r_row.error else f"ERROR: {r_row.error}"
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        vols = [r_row.volatility for r_row in results if r_row.volatility]
        if vols:
            st.subheader("Summary Statistics")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Mean Vol", f"{np.mean(vols):.1%}")
            s2.metric("Median Vol", f"{np.median(vols):.1%}")
            s3.metric("Min Vol", f"{np.min(vols):.1%}")
            s4.metric("Max Vol", f"{np.max(vols):.1%}")
"""

import pathlib
out = pathlib.Path("src/ui/pages/case_detail.py")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(content, encoding="utf-8")
print(f"Written: {out}  ({out.stat().st_size} bytes)")
