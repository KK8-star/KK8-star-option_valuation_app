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


def _fetch_vol(ticker: str, period: str = "1y") -> "ComparableTickerRow":
    try:
        t_obj = yf.Ticker(ticker)
        hist = t_obj.history(period=period)
        if hist is None or hist.empty or len(hist) < 5:
            return ComparableTickerRow(
                ticker=ticker, fetch_ok=False,
                error_msg="Insufficient data (fewer than 5 trading days)")
        close = hist["Close"].dropna()
        if len(close) < 2:
            return ComparableTickerRow(
                ticker=ticker, fetch_ok=False,
                error_msg="Insufficient close price data")
        log_ret = np.log(close / close.shift(1)).dropna()
        if len(log_ret) < 2:
            return ComparableTickerRow(
                ticker=ticker, fetch_ok=False,
                error_msg="Cannot compute returns (too few data points)")
        vol = float(log_ret.std(ddof=1) * np.sqrt(252))
        label = ticker
        try:
            info = t_obj.info
            label = info.get("longName") or info.get("shortName") or ticker
        except Exception:
            label = ticker
        return ComparableTickerRow(
            ticker=ticker, company_label=label,
            volatility=vol, vol_period=period, fetch_ok=True)
    except Exception as e:
        return ComparableTickerRow(
            ticker=ticker, fetch_ok=False, error_msg=str(e))


def _parse_tickers(raw: str) -> list:
    import re
    parts = re.split(r"[,\s\n]+", raw.strip())
    return [p.strip().upper() for p in parts if p.strip()]


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

    tab1, tab2, tab3 = st.tabs([
        "Black-Scholes",
        "Binomial Model",
        "Monte Carlo"])

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
        st.code(f"d1 = {d1:.6f}\nd2 = {d2:.6f}", language="text")
        st.markdown("**Normal Distribution Values and Option Price**")
        if opt == "call":
            price_bs = (S * math.exp(-q*T) * norm.cdf(d1)
                        - K * math.exp(-r*T) * norm.cdf(d2))
            st.latex(r"C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2)")
        else:
            price_bs = (K * math.exp(-r*T) * norm.cdf(-d2)
                        - S * math.exp(-q*T) * norm.cdf(-d1))
            st.latex(r"P = K e^{-rT} N(-d_2) - S e^{-qT} N(-d_1)")
        st.success(f"Black-Scholes Price: {price_bs:,.4f} JPY")

    with tab2:
        st.markdown("#### Binomial Model (Cox-Ross-Rubinstein)")
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
        st.markdown("**Price Tree (first 5 steps)**")
        steps_show = min(5, N)
        tree_data = {}
        for step in range(steps_show + 1):
            prices = [round(S * (u**(step-j)) * (d**j), 2)
                      for j in range(step + 1)]
            tree_data[f"t={step}"] = prices + [""] * (steps_show - step)
        st.dataframe(pd.DataFrame(tree_data), use_container_width=True)
        bp = float(case["binomial_price"])
        st.metric("Binomial Model Price", f"Y{bp:,.4f}")

    with tab3:
        st.markdown("#### Monte Carlo Simulation")
        st.latex(r"S_T = S_0 \exp\left[\left(r - q - \frac{\sigma^2}{2}\right)T + \sigma\sqrt{T}\,Z\right]")
        if opt == "call":
            st.latex(r"\text{Payoff} = \max(S_T - K,\ 0)")
        else:
            st.latex(r"\text{Payoff} = \max(K - S_T,\ 0)")
        st.latex(r"\text{Price} = e^{-rT} \times \mathbb{E}[\text{Payoff}]")
        mc_p = float(case["mc_price"])
        st.success(f"Monte Carlo Price: Y{mc_p:,.4f}  (Simulations: {M:,})")

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        rng = np.random.default_rng(42)
        n_paths = min(200, M)
        n_steps_mc = 50
        dt_mc = T / n_steps_mc
        Z_paths = rng.standard_normal((n_paths, n_steps_mc))
        log_ret_mc = ((r - q - 0.5 * v**2) * dt_mc
                      + v * np.sqrt(dt_mc) * Z_paths)
        S_paths = S * np.exp(np.cumsum(log_ret_mc, axis=1))
        S_paths = np.hstack([np.full((n_paths, 1), S), S_paths])

        final_prices = S_paths[:, -1]
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.hist(final_prices, bins=80, color="steelblue",
                 edgecolor="white", alpha=0.8, density=True)
        mean_val = final_prices.mean()
        ax1.axvline(mean_val, color="green", linestyle="--", linewidth=2,
                    label=f"Mean: {mean_val:,.0f} JPY")
        ax1.axvline(K, color="red", linestyle="--", linewidth=2,
                    label=f"Strike: {K:,.0f} JPY")
        ax1.set_xlabel("Stock Price (JPY)")
        ax1.set_ylabel("Probability Density")
        ax1.set_title("Stock Price Distribution at Maturity")
        ax1.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax1.legend(loc="upper right", fontsize=8)
        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)

        Z_all = rng.standard_normal(M)
        S_T = S * np.exp(
            (r - q - 0.5 * v**2) * T + v * np.sqrt(T) * Z_all)
        if opt == "call":
            payoffs = np.maximum(S_T - K, 0)
        else:
            payoffs = np.maximum(K - S_T, 0)
        disc_payoffs = np.exp(-r * T) * payoffs

        fig2, ax2 = plt.subplots(figsize=(8, 3))
        ax2.hist(disc_payoffs, bins=60, color="steelblue",
                 edgecolor="white", alpha=0.8)
        ax2.axvline(disc_payoffs.mean(), color="red", linestyle="--",
                    linewidth=1.5,
                    label=f"Mean = {disc_payoffs.mean():,.2f}")
        ax2.set_xlabel("Discounted Payoff")
        ax2.set_ylabel("Frequency")
        ax2.set_title("Payoff Distribution")
        ax2.legend(fontsize=8)
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)


def _show_comparable_section():
    st.divider()
    st.subheader("Reference: Listed Comparable Volatility Estimation")
    with st.expander("Fetch volatility from comparable companies",
                     expanded=False):
        st.markdown(
            "Enter one or more tickers separated by commas or spaces.  \n"
            "Example: `7203.T, 9984.T, AAPL, MSFT`")
        col_a, col_b = st.columns([3, 1])
        with col_a:
            ticker_raw = st.text_input(
                "Ticker(s)",
                placeholder="e.g. 7203.T, 9984.T, AAPL",
                key="comp_ticker_input")
        with col_b:
            period = st.selectbox(
                "Period", options=["1y", "2y", "5y"],
                key="comp_vol_period")
        fetch_clicked = st.button(
            "Fetch Volatility", key="comp_fetch_btn",
            use_container_width=True)

        if "comp_results" not in st.session_state:
            st.session_state["comp_results"] = []

        if fetch_clicked and ticker_raw.strip():
            tickers = _parse_tickers(ticker_raw)
            if not tickers:
                st.warning("No valid tickers found.")
            else:
                results = []
                progress = st.progress(0, text="Fetching...")
                for i, tk in enumerate(tickers):
                    progress.progress(
                        (i + 1) / len(tickers),
                        text=f"Fetching {tk} ({i+1}/{len(tickers)})...")
                    results.append(_fetch_vol(tk, period))
                progress.empty()
                st.session_state["comp_results"] = results

        if st.session_state["comp_results"]:
            rows = st.session_state["comp_results"]
            table_data = []
            for row in rows:
                if row.fetch_ok:
                    table_data.append({
                        "Ticker":     row.ticker,
                        "Company":    row.company_label or row.ticker,
                        "Volatility": f"{row.volatility * 100:.2f}%",
                        "Period":     row.vol_period,
                        "Status":     "OK",
                    })
                else:
                    table_data.append({
                        "Ticker":     row.ticker,
                        "Company":    "-",
                        "Volatility": "-",
                        "Period":     "-",
                        "Status":     f"ERROR: {row.error_msg}",
                    })
            st.dataframe(pd.DataFrame(table_data),
                         use_container_width=True, hide_index=True)
            success_rows = [r for r in rows if r.fetch_ok]
            if success_rows:
                vols = [r.volatility for r in success_rows]
                st.markdown("**Summary Statistics**")
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Mean sigma",   f"{np.mean(vols)*100:.2f}%")
                s2.metric("Median sigma", f"{np.median(vols)*100:.2f}%")
                s3.metric("Min sigma",    f"{np.min(vols)*100:.2f}%")
                s4.metric("Max sigma",    f"{np.max(vols)*100:.2f}%")
                if len(success_rows) >= 2:
                    st.metric("Std Dev sigma",
                              f"{np.std(vols, ddof=1)*100:.2f}%")
            if st.button("Clear Results", key="comp_clear_btn"):
                st.session_state["comp_results"] = []
                st.rerun()


def _show_view(case: dict, case_id: int):
    st.subheader("Input Parameters")
    c1, c2, c3 = st.columns(3)
    sp = float(case["stock_price"])
    sk = float(case["strike_price"])
    te = float(case["time_to_expiry"])
    c1.metric("Stock Price S", f"Y{sp:,.2f}")
    c2.metric("Strike K", f"Y{sk:,.2f}")
    c3.metric("Time to Expiry T", f"{te:.4f} yr")
    c4, c5, c6 = st.columns(3)
    rr = float(case["risk_free_rate"])
    vo = float(case["volatility"])
    dy = float(case["dividend_yield"] or 0)
    c4.metric("Risk-Free Rate r",  f"{rr*100:.2f}%")
    c5.metric("Volatility sigma",  f"{vo*100:.2f}%")
    c6.metric("Dividend Yield q",  f"{dy*100:.2f}%")
    st.divider()
    st.subheader("Valuation Results")
    r1, r2, r3 = st.columns(3)
    bs = float(case["bs_price"])
    bn = float(case["binomial_price"])
    mc = float(case["mc_price"])
    r1.metric("Black-Scholes",  f"Y{bs:,.4f}")
    r2.metric("Binomial Model", f"Y{bn:,.4f}")
    r3.metric("Monte Carlo",    f"Y{mc:,.4f}")
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
            case_name      = st.text_input(
                "Case Name", value=case["case_name"])
            stock_price    = st.number_input(
                "Stock Price S", value=float(case["stock_price"]),
                min_value=0.01, step=100.0)
            strike_price   = st.number_input(
                "Strike K", value=float(case["strike_price"]),
                min_value=0.01, step=100.0)
            time_to_expiry = st.number_input(
                "Time to Expiry T", value=float(case["time_to_expiry"]),
                min_value=0.01, step=0.25)
        with col2:
            risk_free_rate = st.number_input(
                "Risk-Free Rate r", value=float(case["risk_free_rate"]),
                min_value=0.0, step=0.001, format="%.4f")
            volatility     = st.number_input(
                "Volatility sigma", value=float(case["volatility"]),
                min_value=0.001, step=0.01, format="%.4f")
            dividend_yield = st.number_input(
                "Dividend Yield q",
                value=float(case["dividend_yield"] or 0),
                min_value=0.0, step=0.001, format="%.4f")
            option_type    = st.selectbox(
                "Option Type", ["call", "put"],
                index=0 if case["option_type"] == "call" else 1)
        col3, col4 = st.columns(2)
        with col3:
            binomial_steps = st.number_input(
                "Binomial Steps", value=int(case["binomial_steps"]),
                min_value=10, max_value=1000, step=10)
        with col4:
            mc_simulations = st.number_input(
                "MC Simulations", value=int(case["mc_simulations"]),
                min_value=1000, max_value=1000000, step=1000)
        submitted = st.form_submit_button(
            "Re-evaluate & Save", use_container_width=True)

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
        st.success("Updated and re-evaluated successfully.")
        st.session_state[edit_key] = False
        st.rerun()

    _show_comparable_section()


def show(case_id: int):
    case = svc.get_case(case_id)
    if case is None:
        st.error("Case not found.")
        return
    edit_key = f"edit_mode_{case_id}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.title(f"Case: {case['case_name']}")
    with col_btn:
        if not st.session_state[edit_key]:
            if st.button("Edit / Re-evaluate", use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()
        else:
            if st.button("Cancel", use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()
    created = (case["created_at"].strftime("%Y-%m-%d %H:%M")
               if case.get("created_at") else "-")
    updated = (case["updated_at"].strftime("%Y-%m-%d %H:%M")
               if case.get("updated_at") else "-")
    st.caption(f"Created: {created}  Last Updated: {updated}")
    st.divider()
    if not st.session_state[edit_key]:
        _show_view(case, case_id)
    else:
        _show_edit(case, case_id, edit_key)


def render(case_id=None):
    if case_id is None:
        case_id = st.session_state.get("detail_case_id")
    show(case_id)
