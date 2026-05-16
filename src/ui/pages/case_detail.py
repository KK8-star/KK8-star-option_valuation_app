# src/ui/pages/case_detail.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import math
import numpy as np
import yfinance as yf
from scipy.stats import norm
from src.services.valuation_service import (
    ValuationService, ValuationParams, ComparableTickerRow)

svc = ValuationService()


def _fetch_vol(ticker: str, period: str = "1y") -> ComparableTickerRow:
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty or len(hist) < 5:
            return ComparableTickerRow(ticker=ticker, fetch_ok=False,
                                       error_msg="Insufficient data")
        ret = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
        vol = float(ret.std() * np.sqrt(252))
        info = yf.Ticker(ticker).info
        label = info.get("longName") or info.get("shortName") or ticker
        return ComparableTickerRow(ticker=ticker, company_label=label,
                                   volatility=vol, vol_period=period,
                                   fetch_ok=True)
    except Exception as e:
        return ComparableTickerRow(ticker=ticker, fetch_ok=False,
                                   error_msg=str(e))


def _show_calc_process(case: dict):
    S   = float(case["stock_price"])
    K   = float(case["strike_price"])
    r   = float(case["risk_free_rate"])
    v   = float(case["volatility"])
    T   = float(case["time_to_expiry"])
    q   = float(case["dividend_yield"] or 0)
    opt = case["option_type"].lower()
    N   = int(case["binomial_steps"])
    M   = int(case["mc_simulations"])

    tab1, tab2, tab3 = st.tabs(
        ["\U0001f4ca Black-Scholes", "\U0001f333 Binomial Model", "\U0001f3b2 Monte Carlo"]
    )

    with tab1:
        st.markdown("#### Black-Scholes Model - Calculation Process")
        d1 = (math.log(S / K) + (r - q + 0.5 * v**2) * T) / (v * math.sqrt(T))
        d2 = d1 - v * math.sqrt(T)

        st.markdown("**Input Parameters**")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("S (Stock Price)", f"{S:,.2f}")
        c2.metric("K (Strike)", f"{K:,.2f}")
        c3.metric("r (Risk-Free Rate)", f"{r*100:.2f}%")
        c4.metric("sigma (Volatility)", f"{v*100:.2f}%")
        c5.metric("T (Years to Expiry)", f"{T:.4f} yr")

        st.markdown("**d1, d2 Calculation**")
        st.latex(r"d_1 = \frac{\ln(S/K) + (r - q + \frac{\sigma^2}{2})T}{\sigma\sqrt{T}}")
        st.code(
            f"d1 = {d1:.6f}\nd2 = {d2:.6f}",
            language="text"
        )

        st.markdown("**Normal Distribution Values and Price**")
        if opt == "call":
            price_bs = S * math.exp(-q*T) * norm.cdf(d1) - K * math.exp(-r*T) * norm.cdf(d2)
            st.latex(r"C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2)")
        else:
            price_bs = K * math.exp(-r*T) * norm.cdf(-d2) - S * math.exp(-q*T) * norm.cdf(-d1)
            st.latex(r"P = K e^{-rT} N(-d_2) - S e^{-qT} N(-d_1)")
        st.success(f"Black-Scholes Price: {price_bs:,.4f}")

    with tab2:
        st.markdown("#### Binomial Model（Cox-Ross-Rubinstein）")
        dt = T / N
        u  = math.exp(v * math.sqrt(dt))
        d  = 1 / u
        p  = (math.exp((r - q) * dt) - d) / (u - d)

        st.markdown("**Model Parameters**")
        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("Steps N", N)
        p2.metric("Delta_t", f"{dt:.6f} yr")
        p3.metric("u (Up Factor)", f"{u:.6f}")
        p4.metric("d (Down Factor)", f"{d:.6f}")
        p5.metric("p (Risk-Neutral Prob)", f"{p:.6f}")

        st.markdown("**Price Tree (First 5 Steps)**")
        steps_show = min(5, N)
        tree_data = {}
        for step in range(steps_show + 1):
            prices = [round(S * (u**(step-j)) * (d**j), 2) for j in range(step + 1)]
            tree_data[f"t={step}"] = prices + [""] * (steps_show - step)
        st.dataframe(pd.DataFrame(tree_data), use_container_width=True)
        st.metric("Binomial Model Price", f"¥{float(case['binomial_price']):,.4f}")

    with tab3:
        st.markdown("#### Monte Carlo Simulation")
        st.latex(r"S_T = S_0 \exp\left[\left(r - q - \frac{\sigma^2}{2}\right)T + \sigma\sqrt{T}\,Z\right]")
        if opt == "call":
            st.latex(r"\text{Payoff} = \max(S_T - K,\ 0)")
        else:
            st.latex(r"\text{Payoff} = \max(K - S_T,\ 0)")
        st.latex(r"\text{Price} = e^{-rT} \times \mathbb{E}[\text{Payoff}]")
        st.success(f"Monte Carlo Price: ¥{float(case['mc_price']):,.4f}  ({M:,} simulations)")
        st.info(f"Std Error approx sigma_payoff / sqrt(M)  Simulations: {M:,}")

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        rng = np.random.default_rng(42)
        n_paths = min(200, M)
        n_steps = 50
        dt_mc = T / n_steps
        Z_paths = rng.standard_normal((n_paths, n_steps))
        log_ret = (r - q - 0.5 * v**2) * dt_mc + v * np.sqrt(dt_mc) * Z_paths
        S_paths = S * np.exp(np.cumsum(log_ret, axis=1))
        S_paths = np.hstack([np.full((n_paths, 1), S), S_paths])

        # Calculate mean and std at each time step
        mean_path = np.mean(S_paths, axis=0)
        std_path  = np.std(S_paths,  axis=0)
        time_steps = np.arange(S_paths.shape[1])

        # Graph 1: Histogram of final stock prices
        final_prices = S_paths[:, -1]
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.hist(final_prices, bins=80, color="steelblue", edgecolor="white", alpha=0.8, density=True)
        ax1.axvline(final_prices.mean(), color="green", linestyle="--", linewidth=2, label=f"Mean Price: {final_prices.mean():,.0f} JPY")
        ax1.axvline(K, color="red", linestyle="--", linewidth=2, label=f"Strike: {K:,.0f} JPY")
        ax1.set_xlabel("Stock Price (JPY)")
        ax1.set_ylabel("Probability Density")
        ax1.set_title("Stock Price Distribution at Maturity")
        ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax1.legend(fontsize=9, loc="upper right")
        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)

        Z_all = rng.standard_normal(M)
        S_T = S * np.exp((r - q - 0.5 * v**2) * T + v * np.sqrt(T) * Z_all)
        if opt == "call":
            payoffs = np.maximum(S_T - K, 0)
        else:
            payoffs = np.maximum(K - S_T, 0)
        disc_payoffs = np.exp(-r * T) * payoffs

        fig2, ax2 = plt.subplots(figsize=(8, 3))
        ax2.hist(disc_payoffs, bins=60, color="steelblue", edgecolor="white", alpha=0.8)
        ax2.axvline(disc_payoffs.mean(), color="red", linestyle="--",
                    linewidth=1.5, label=f"Mean = {disc_payoffs.mean():,.2f}")
        ax2.set_xlabel("Discounted Payoff")
        ax2.set_ylabel("Frequency")
        ax2.set_title("Payoff Distribution")
        ax2.legend(fontsize=8)
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)


def _show_view(case: dict, case_id: int):
    st.subheader("Input Parameters")
    c1, c2, c3 = st.columns(3)
    c1.metric("Stock Price S", f"¥{float(case['stock_price']):,.2f}")
    c2.metric("Strike K", f"¥{float(case['strike_price']):,.2f}")
    c3.metric("Time to Expiry T", f"{float(case['time_to_expiry']):.4f} yr")
    c4, c5, c6 = st.columns(3)
    c4.metric("Risk-Free Rate r", f"{float(case['risk_free_rate'])*100:.2f}%")
    c5.metric("Volatility sigma", f"{float(case['volatility'])*100:.2f}%")
    c6.metric("Dividend Yield q", f"{float(case['dividend_yield'] or 0)*100:.2f}%")
    st.divider()

    st.subheader("Valuation Results")
    r1, r2, r3 = st.columns(3)
    r1.metric("Black-Scholes", f"¥{float(case['bs_price']):,.4f}")
    r2.metric("Binomial Model", f"¥{float(case['binomial_price']):,.4f}")
    r3.metric("Monte Carlo", f"¥{float(case['mc_price']):,.4f}")
    st.divider()

    st.subheader("Greeks")
    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Delta", f"{float(case['delta']):.6f}")
    g2.metric("Gamma", f"{float(case['gamma']):.6f}")
    g3.metric("Theta", f"{float(case['theta']):.6f}")
    g4.metric("Vega",  f"{float(case['vega']):.6f}")
    g5.metric("Rho",   f"{float(case['rho']):.6f}")
    st.divider()

    st.subheader("Calculation Process")
    _show_calc_process(case)


def _show_edit(case: dict, case_id: int, edit_key: str):
    st.subheader("Edit Parameters / Re-evaluate")

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        with col1:
            case_name      = st.text_input("Case Name", value=case["case_name"])
            stock_price    = st.number_input("Stock Price S",    value=float(case["stock_price"]),    min_value=0.01, step=100.0)
            strike_price   = st.number_input("Strike K", value=float(case["strike_price"]),   min_value=0.01, step=100.0)
            time_to_expiry = st.number_input("Time to Expiry T", value=float(case["time_to_expiry"]), min_value=0.01, step=0.25)
        with col2:
            risk_free_rate = st.number_input("Risk-Free Rate r",   value=float(case["risk_free_rate"]),      min_value=0.0, step=0.001, format="%.4f")
            volatility     = st.number_input("Volatility sigma", value=float(case["volatility"]),           min_value=0.001, step=0.01, format="%.4f")
            dividend_yield = st.number_input("Dividend Yield q",      value=float(case["dividend_yield"] or 0), min_value=0.0, step=0.001, format="%.4f")
            option_type    = st.selectbox("Option Type", ["call", "put"],
                                          index=0 if case["option_type"] == "call" else 1)
        col3, col4 = st.columns(2)
        with col3:
            binomial_steps  = st.number_input("Binomial Steps",       value=int(case["binomial_steps"]),  min_value=10,   max_value=1000,    step=10)
        with col4:
            mc_simulations  = st.number_input("MC Simulations",     value=int(case["mc_simulations"]),  min_value=1000, max_value=1000000, step=1000)

        submitted = st.form_submit_button("Re-evaluate & Save", use_container_width=True)

    if submitted:
        params = ValuationParams(
            case_name=case_name,
            stock_price=stock_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            dividend_yield=dividend_yield,
            option_type=option_type,
            binomial_steps=int(binomial_steps),
            mc_simulations=int(mc_simulations),
        )
        with st.spinner("Re-evaluating..."):
            svc.update_case(case_id, params)
        st.success("Update and re-evaluation complete")
        st.session_state[edit_key] = False
        st.rerun()

    st.divider()
    st.subheader("Reference: Listed Comparable Volatility Estimation")
    with st.expander("Add ticker to estimate volatility"):
        ticker_input = st.text_input("Ticker (e.g. 7203.T, AAPL)", key="ticker_input")
        period = st.selectbox("Period", ["1y", "2y", "5y"], key="vol_period")
        if st.button("Fetch", key="fetch_btn"):
            if ticker_input.strip():
                with st.spinner(f"{ticker_input} - Fetching data...")
                    row = _fetch_vol(ticker_input.strip(), period)
                if row.fetch_ok:
                    st.success(f"{row.company_label}: σ = {row.volatility*100:.2f}%")
                else:
                    st.error(f"Fetch error: {row.error_msg}")


def show(case_id: int):
    case = svc.get_case(case_id)
    if case is None:
        st.error("Case not found")
        return

    edit_key = f"edit_mode_{case_id}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.title(f"\U0001f4cb {case['case_name']}")
    with col_btn:
        if not st.session_state[edit_key]:
            if st.button("Edit / Re-evaluate", use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()
        else:
            if st.button("Cancel", use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()

    created = case["created_at"].strftime("%Y-%m-%d %H:%M") if case.get("created_at") else "-"
    updated = case["updated_at"].strftime("%Y-%m-%d %H:%M") if case.get("updated_at") else "-"
    st.caption(f"Created: {created}　Last Updated: {updated}")
    st.divider()

    if not st.session_state[edit_key]:
        _show_view(case, case_id)
    else:
        _show_edit(case, case_id, edit_key)


# Entry point called from app.py / case_list.py
def render(case_id: int | None = None):
    if case_id is None:
        case_id = st.session_state.get('detail_case_id')
    show(case_id)
