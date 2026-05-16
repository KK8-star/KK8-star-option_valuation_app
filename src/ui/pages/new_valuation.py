# src/ui/pages/new_valuation.py
from __future__ import annotations
import streamlit as st
import numpy as np
import pandas as pd
from src.ui.components.result_display import render_calculation_detail
from src.services.valuation_service import (
    ValuationService,
    ValuationParams,
    ValuationResult,
    ComparableTickerRow,
)

svc = ValuationService()


def _fetch_vol(ticker: str, period: str) -> ComparableTickerRow:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return ComparableTickerRow(
                ticker=ticker, fetch_ok=False,
                error_msg="データなし", vol_period=period,
            )
        log_ret = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
        vol = float(log_ret.std() * np.sqrt(252))
        try:
            info  = yf.Ticker(ticker).info
            label = info.get("shortName") or info.get("longName") or ticker
        except Exception:
            label = ticker
        return ComparableTickerRow(
            ticker=ticker, company_label=label,
            volatility=vol, vol_period=period, fetch_ok=True,
        )
    except Exception as e:
        return ComparableTickerRow(
            ticker=ticker, fetch_ok=False,
            error_msg=str(e), vol_period=period,
        )


def render() -> None:
    st.title("新規評価ケース作成")

    # ── 基本パラメータ ────────────────────────────────────────────
    with st.expander("評価パラメータ", expanded=True):
        case_name = st.text_input("ケース名", value="新規ケース")

        col1, col2 = st.columns(2)
        with col1:
            stock_price    = st.number_input("株価 (S)",        value=100.0,  min_value=0.01)
            strike_price   = st.number_input("行使価格 (K)",    value=100.0,  min_value=0.01)
            risk_free_rate = st.number_input("無リスク金利",    value=0.02,   min_value=0.0,   format="%.4f")
        with col2:
            volatility     = st.number_input("ボラティリティ", value=0.20,   min_value=0.001, format="%.4f")
            time_to_expiry = st.number_input("残存期間 (年)",   value=1.0,    min_value=0.01)
            dividend_yield = st.number_input("配当利回り",      value=0.0,    min_value=0.0,   format="%.4f")

        col3, col4, col5 = st.columns(3)
        with col3:
            option_type    = st.selectbox("オプション種類", ["call", "put"])
        with col4:
            binomial_steps = st.number_input("二項ステップ数",        value=100,   min_value=10,   step=10)
        with col5:
            mc_simulations = st.number_input("MCシミュレーション数", value=10000, min_value=1000, step=1000)

    # ── 類似会社ボラティリティ ────────────────────────────────────
    with st.expander("類似会社ボラティリティ（任意）"):
        ticker_input = st.text_input(
            "ティッカー（カンマ区切り）",
            placeholder="例: 7203.T, 6758.T",
        )
        vol_period = st.selectbox("取得期間", ["1y", "2y", "3y", "6mo"], index=0)

        if ticker_input.strip() and st.button("ボラティリティ取得"):
            tickers = [t.strip() for t in ticker_input.split(",") if t.strip()]
            with st.spinner("取得中..."):
                rows = [_fetch_vol(tk, vol_period) for tk in tickers]
            st.session_state["comparable_rows"] = rows

        if "comparable_rows" in st.session_state:
            rows: list[ComparableTickerRow] = st.session_state["comparable_rows"]
            df = pd.DataFrame([
                {
                    "ティッカー":         r.ticker,
                    "会社名":             r.company_label,
                    "ボラティリティ":     f"{r.volatility:.2%}" if r.fetch_ok else "—",
                    "ステータス":         "✓" if r.fetch_ok else f"✗ {r.error_msg}",
                }
                for r in rows
            ])
            st.dataframe(df, use_container_width=True)

    # ── 計算・保存 ────────────────────────────────────────────────
    if st.button("計算・保存", type="primary"):
        comparables: list[ComparableTickerRow] = st.session_state.get("comparable_rows", [])

        params = ValuationParams(
            case_name      = case_name,
            stock_price    = float(stock_price),
            strike_price   = float(strike_price),
            risk_free_rate = float(risk_free_rate),
            volatility     = float(volatility),
            time_to_expiry = float(time_to_expiry),
            option_type    = option_type,
            dividend_yield = float(dividend_yield),
            binomial_steps = int(binomial_steps),
            mc_simulations = int(mc_simulations),
        )

        with st.spinner("計算中..."):
            result: ValuationResult = svc.calculate(params)
            case_id = svc.save(params, result, comparables or None)

        st.success(f"保存完了 (case_id = {case_id})")

        # 結果表示
        st.subheader("評価結果")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("BS価格",   f"{result.bs_price:.4f}")
        c2.metric("二項価格", f"{result.binomial_price:.4f}")
        c3.metric("MC価格",   f"{result.mc_price:.4f}")
        c4.metric("加重平均", f"{result.weighted_price:.4f}")

        st.subheader("Greeks")
        g1, g2, g3, g4, g5 = st.columns(5)
        g1.metric("Delta", f"{result.delta:.4f}")
        g2.metric("Gamma", f"{result.gamma:.4f}")
        g3.metric("Theta", f"{result.theta:.4f}")
        g4.metric("Vega",  f"{result.vega:.4f}")
        g5.metric("Rho",   f"{result.rho:.4f}")
        render_calculation_detail(vars(params), result)

        # comparable_rows をリセット
        st.session_state.pop("comparable_rows", None)
