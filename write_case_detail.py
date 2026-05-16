import pathlib

CONTENT = """\
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
                                       error_msg="データ不足")
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
        ["\\U0001f4ca Black-Scholes", "\\U0001f333 二項モデル", "\\U0001f3b2 モンテカルロ"]
    )

    with tab1:
        st.markdown("#### Black-Scholes モデル 計算過程")
        d1 = (math.log(S / K) + (r - q + 0.5 * v**2) * T) / (v * math.sqrt(T))
        d2 = d1 - v * math.sqrt(T)

        st.markdown("**入力パラメータ**")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("S (株価)", f"{S:,.2f}")
        c2.metric("K (行使価格)", f"{K:,.2f}")
        c3.metric("r (無リスク金利)", f"{r*100:.2f}%")
        c4.metric("σ (ボラティリティ)", f"{v*100:.2f}%")
        c5.metric("T (満期年数)", f"{T:.4f}年")

        st.markdown("**d1, d2 の計算**")
        st.latex(r"d_1 = \\frac{\\ln(S/K) + (r - q + \\frac{\\sigma^2}{2})T}{\\sigma\\sqrt{T}}")
        st.code(
            f"d1 = {d1:.6f}\\nd2 = {d2:.6f}",
            language="text"
        )

        st.markdown("**正規分布値と価格**")
        if opt == "call":
            price_bs = S * math.exp(-q*T) * norm.cdf(d1) - K * math.exp(-r*T) * norm.cdf(d2)
            st.latex(r"C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2)")
        else:
            price_bs = K * math.exp(-r*T) * norm.cdf(-d2) - S * math.exp(-q*T) * norm.cdf(-d1)
            st.latex(r"P = K e^{-rT} N(-d_2) - S e^{-qT} N(-d_1)")
        st.success(f"Black-Scholes価格: {price_bs:,.4f}")

    with tab2:
        st.markdown("#### 二項モデル（Cox-Ross-Rubinstein）")
        dt = T / N
        u  = math.exp(v * math.sqrt(dt))
        d  = 1 / u
        p  = (math.exp((r - q) * dt) - d) / (u - d)

        st.markdown("**モデルパラメータ**")
        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("ステップ数 N", N)
        p2.metric("Δt", f"{dt:.6f}年")
        p3.metric("u (上昇率)", f"{u:.6f}")
        p4.metric("d (下落率)", f"{d:.6f}")
        p5.metric("p (中立確率)", f"{p:.6f}")

        st.markdown("**価格ツリー（最初の5ステップ）**")
        steps_show = min(5, N)
        tree_data = {}
        for step in range(steps_show + 1):
            prices = [round(S * (u**(step-j)) * (d**j), 2) for j in range(step + 1)]
            tree_data[f"t={step}"] = prices + [""] * (steps_show - step)
        st.dataframe(pd.DataFrame(tree_data), use_container_width=True)
        st.metric("二項モデル価格", f"¥{float(case['binomial_price']):,.4f}")

    with tab3:
        st.markdown("#### モンテカルロ シミュレーション")
        st.latex(r"S_T = S_0 \\exp\\left[\\left(r - q - \\frac{\\sigma^2}{2}\\right)T + \\sigma\\sqrt{T}\\,Z\\right]")
        if opt == "call":
            st.latex(r"\\text{Payoff} = \\max(S_T - K,\\ 0)")
        else:
            st.latex(r"\\text{Payoff} = \\max(K - S_T,\\ 0)")
        st.latex(r"\\text{Price} = e^{-rT} \\times \\mathbb{E}[\\text{Payoff}]")
        st.success(f"モンテカルロ価格: ¥{float(case['mc_price']):,.4f}  ({M:,}回シミュレーション)")
        st.info(f"標準誤差 ≈ σ_payoff / √M　シミュレーション数: {M:,}回")


def _show_view(case: dict, case_id: int):
    st.subheader("入力パラメータ")
    c1, c2, c3 = st.columns(3)
    c1.metric("株価 S", f"¥{float(case['stock_price']):,.2f}")
    c2.metric("行使価格 K", f"¥{float(case['strike_price']):,.2f}")
    c3.metric("満期年数 T", f"{float(case['time_to_expiry']):.4f}年")
    c4, c5, c6 = st.columns(3)
    c4.metric("無リスク金利 r", f"{float(case['risk_free_rate'])*100:.2f}%")
    c5.metric("ボラティリティ σ", f"{float(case['volatility'])*100:.2f}%")
    c6.metric("配当利回り q", f"{float(case['dividend_yield'] or 0)*100:.2f}%")
    st.divider()

    st.subheader("評価結果")
    r1, r2, r3 = st.columns(3)
    r1.metric("Black-Scholes", f"¥{float(case['bs_price']):,.4f}")
    r2.metric("二項モデル", f"¥{float(case['binomial_price']):,.4f}")
    r3.metric("モンテカルロ", f"¥{float(case['mc_price']):,.4f}")
    st.divider()

    st.subheader("Greeks")
    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Delta", f"{float(case['delta']):.6f}")
    g2.metric("Gamma", f"{float(case['gamma']):.6f}")
    g3.metric("Theta", f"{float(case['theta']):.6f}")
    g4.metric("Vega",  f"{float(case['vega']):.6f}")
    g5.metric("Rho",   f"{float(case['rho']):.6f}")
    st.divider()

    st.subheader("計算過程")
    _show_calc_process(case)


def _show_edit(case: dict, case_id: int, edit_key: str):
    st.subheader("パラメータ編集・再評価")

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        with col1:
            case_name      = st.text_input("ケース名", value=case["case_name"])
            stock_price    = st.number_input("株価 S",    value=float(case["stock_price"]),    min_value=0.01, step=100.0)
            strike_price   = st.number_input("行使価格 K", value=float(case["strike_price"]),   min_value=0.01, step=100.0)
            time_to_expiry = st.number_input("満期年数 T", value=float(case["time_to_expiry"]), min_value=0.01, step=0.25)
        with col2:
            risk_free_rate = st.number_input("無リスク金利 r",   value=float(case["risk_free_rate"]),      min_value=0.0, step=0.001, format="%.4f")
            volatility     = st.number_input("ボラティリティ σ", value=float(case["volatility"]),           min_value=0.001, step=0.01, format="%.4f")
            dividend_yield = st.number_input("配当利回り q",      value=float(case["dividend_yield"] or 0), min_value=0.0, step=0.001, format="%.4f")
            option_type    = st.selectbox("オプション種別", ["call", "put"],
                                          index=0 if case["option_type"] == "call" else 1)
        col3, col4 = st.columns(2)
        with col3:
            binomial_steps  = st.number_input("二項ステップ数",       value=int(case["binomial_steps"]),  min_value=10,   max_value=1000,    step=10)
        with col4:
            mc_simulations  = st.number_input("モンテカルロ回数",     value=int(case["mc_simulations"]),  min_value=1000, max_value=1000000, step=1000)

        submitted = st.form_submit_button("再評価・保存", use_container_width=True)

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
        with st.spinner("再評価中..."):
            svc.update_case(case_id, params)
        st.success("更新・再評価が完了しました")
        st.session_state[edit_key] = False
        st.rerun()

    st.divider()
    st.subheader("類似上場企業 ボラティリティ参照")
    with st.expander("銘柄を追加して参照"):
        ticker_input = st.text_input("ティッカー (例: 7203.T, AAPL)", key="ticker_input")
        period = st.selectbox("期間", ["1y", "2y", "5y"], key="vol_period")
        if st.button("取得", key="fetch_btn"):
            if ticker_input.strip():
                with st.spinner(f"{ticker_input} のデータ取得中..."):
                    row = _fetch_vol(ticker_input.strip(), period)
                if row.fetch_ok:
                    st.success(f"{row.company_label}: σ = {row.volatility*100:.2f}%")
                else:
                    st.error(f"取得失敗: {row.error_msg}")


def show(case_id: int):
    case = svc.get_case(case_id)
    if case is None:
        st.error("ケースが見つかりません")
        return

    edit_key = f"edit_mode_{case_id}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.title(f"\\U0001f4cb {case['case_name']}")
    with col_btn:
        if not st.session_state[edit_key]:
            if st.button("編集・再評価", use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()
        else:
            if st.button("キャンセル", use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()

    created = case["created_at"].strftime("%Y-%m-%d %H:%M") if case.get("created_at") else "-"
    updated = case["updated_at"].strftime("%Y-%m-%d %H:%M") if case.get("updated_at") else "-"
    st.caption(f"作成: {created}　最終更新: {updated}")
    st.divider()

    if not st.session_state[edit_key]:
        _show_view(case, case_id)
    else:
        _show_edit(case, case_id, edit_key)
"""

pathlib.Path("src/ui/pages/case_detail.py").write_text(CONTENT, encoding="utf-8")
print("完了: src/ui/pages/case_detail.py を書き込みました")
