# src/ui/pages/new_valuation.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import time
import numpy as np
import pandas as pd
import streamlit as st

from src.services.valuation_service import (
    ComparableTickerRow,
    ValuationParams,
    ValuationResult,
    ValuationService,
)
from src.ui.components.result_display import render_calculation_detail

svc = ValuationService()

# ============================================================
# yfinance キャッシュ付き取得（TTL=1時間）
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_vol_cached(ticker: str, period: str) -> dict:
    """
    yfinance でボラティリティと社名を取得してdictで返す。
    st.cache_data でキャッシュ → 同一ティッカーは1時間再取得しない。
    """
    try:
        import yfinance as yf

        # Tickerオブジェクトを1回だけ生成
        tk_obj = yf.Ticker(ticker)

        # 株価履歴取得
        hist = tk_obj.history(period=period)
        if hist is None or hist.empty:
            return {
                "ticker": ticker, "fetch_ok": False,
                "error_msg": "データなし", "vol_period": period,
                "volatility": 0.0, "company_label": ticker,
            }

        # ボラティリティ計算
        close   = hist["Close"].dropna()
        log_ret = np.log(close / close.shift(1)).dropna()
        if len(log_ret) < 20:
            return {
                "ticker": ticker, "fetch_ok": False,
                "error_msg": "データ不足（20営業日未満）", "vol_period": period,
                "volatility": 0.0, "company_label": ticker,
            }
        vol = float(log_ret.std(ddof=1) * np.sqrt(252))

        # 社名取得（失敗してもボラティリティは返す）
        label = ticker
        try:
            info  = tk_obj.info  # 同じオブジェクトを再利用
            label = info.get("shortName") or info.get("longName") or ticker
        except Exception:
            pass

        return {
            "ticker": ticker, "fetch_ok": True, "error_msg": "",
            "vol_period": period, "volatility": vol, "company_label": label,
        }

    except Exception as e:
        return {
            "ticker": ticker, "fetch_ok": False,
            "error_msg": str(e), "vol_period": period,
            "volatility": 0.0, "company_label": ticker,
        }


def _dict_to_row(d: dict) -> ComparableTickerRow:
    """キャッシュdictをComparableTickerRowに変換"""
    return ComparableTickerRow(
        ticker        = d["ticker"],
        company_label = d["company_label"],
        volatility    = d["volatility"],
        vol_period    = d["vol_period"],
        fetch_ok      = d["fetch_ok"],
        error_msg     = d.get("error_msg", ""),
    )


def _calc_mean_volatility(rows: list[ComparableTickerRow]) -> float | None:
    """成功したティッカーのボラティリティ平均を返す（1件もなければNone）"""
    vols = [r.volatility for r in rows if r.fetch_ok and r.volatility > 0]
    return float(np.mean(vols)) if vols else None


# ============================================================
# メインページ
# ============================================================
def show() -> None:
    st.title("新規評価ケース作成")

    # ----------------------------------------------------------
    # 類似会社ボラティリティ取得セクション（先に表示）
    # ----------------------------------------------------------
    with st.expander("類似会社ボラティリティ（任意）", expanded=False):
        ticker_input = st.text_input(
            "ティッカー（カンマ区切り）",
            placeholder="例: 7203.T, 6758.T, AAPL",
            key="ticker_input",
        )
        col_p, col_b = st.columns([2, 1])
        with col_p:
            vol_period = st.selectbox("取得期間", ["1y", "2y", "3y", "6mo"], index=0)
        with col_b:
            fetch_btn = st.button(
                "ボラティリティ取得",
                use_container_width=True,
                disabled=not ticker_input.strip(),
            )

        if fetch_btn and ticker_input.strip():
            tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
            rows_raw = []
            progress = st.progress(0, text="取得中...")
            for i, tk in enumerate(tickers):
                progress.progress((i + 1) / len(tickers), text=f"取得中: {tk}")
                d = _fetch_vol_cached(tk, vol_period)
                rows_raw.append(d)
                time.sleep(0.3)   # レート制限対策: ティッカー間0.3秒待機
            progress.empty()

            rows = [_dict_to_row(d) for d in rows_raw]
            st.session_state["comparable_rows"] = rows

            # 平均ボラティリティをセッションに保存 → パラメータ欄へ自動反映
            mean_vol = _calc_mean_volatility(rows)
            if mean_vol is not None:
                st.session_state["auto_vol"] = mean_vol
                st.success(
                    f"ボラティリティ取得完了 → 平均: **{mean_vol:.2%}** を"
                    "「ボラティリティ」欄に自動反映しました"
                )
            else:
                st.warning("全ティッカーの取得に失敗しました。手動で入力してください。")

        # 結果テーブル表示
        if "comparable_rows" in st.session_state:
            rows: list[ComparableTickerRow] = st.session_state["comparable_rows"]
            df = pd.DataFrame([
                {
                    "ティッカー":     r.ticker,
                    "会社名":         r.company_label,
                    "ボラティリティ": f"{r.volatility:.2%}" if r.fetch_ok else "---",
                    "期間":           r.vol_period,
                    "ステータス":     "OK" if r.fetch_ok else f"NG: {r.error_msg}",
                }
                for r in rows
            ])
            st.dataframe(df, use_container_width=True)

            # 個別選択ボタン
            ok_rows = [r for r in rows if r.fetch_ok]
            if ok_rows:
                st.markdown("**個別選択で反映:**")
                sel_cols = st.columns(min(len(ok_rows), 4))
                for i, r in enumerate(ok_rows):
                    with sel_cols[i % 4]:
                        if st.button(
                            f"{r.ticker}\n{r.volatility:.2%}",
                            key=f"sel_{r.ticker}",
                            use_container_width=True,
                        ):
                            st.session_state["auto_vol"] = r.volatility
                            st.rerun()

            if st.button("類似会社データをクリア", key="clear_comp"):
                st.session_state.pop("comparable_rows", None)
                st.session_state.pop("auto_vol", None)
                st.rerun()

    # ----------------------------------------------------------
    # 評価パラメータ
    # ----------------------------------------------------------
    # auto_vol が入っていれば自動反映
    default_vol = st.session_state.get("auto_vol", 0.20)

    with st.expander("評価パラメータ", expanded=True):
        case_name = st.text_input("ケース名 *", value="新規ケース")

        # auto_vol 反映インジケーター
        if "auto_vol" in st.session_state:
            st.info(
                f"類似会社ボラティリティ ({st.session_state['auto_vol']:.2%}) "
                "が自動反映されています。変更する場合は下欄を編集してください。"
            )

        col1, col2 = st.columns(2)
        with col1:
            stock_price    = st.number_input("株価 (S)",        value=100.0,       min_value=0.01)
            strike_price   = st.number_input("行使価格 (K)",    value=100.0,       min_value=0.01)
            risk_free_rate = st.number_input("無リスク金利",    value=0.02,        min_value=0.0,
                                             format="%.4f")
        with col2:
            volatility     = st.number_input(
                "ボラティリティ",
                value=float(default_vol),      # ← 自動反映ポイント
                min_value=0.001,
                max_value=5.0,
                format="%.4f",
                key="vol_input",
                help="類似会社取得後は自動で更新されます",
            )
            time_to_expiry = st.number_input("残存期間 (年)",   value=1.0,         min_value=0.01)
            dividend_yield = st.number_input("配当利回り",      value=0.0,         min_value=0.0,
                                             format="%.4f")

        col3, col4, col5 = st.columns(3)
        with col3:
            option_type    = st.selectbox("オプション種類", ["call", "put"])
        with col4:
            binomial_steps = st.number_input("二項ステップ数",        value=100,
                                             min_value=10,   step=10)
        with col5:
            mc_simulations = st.number_input("MCシミュレーション数", value=10000,
                                             min_value=1000, step=1000)

    # ----------------------------------------------------------
    # 計算・保存
    # ----------------------------------------------------------
    st.markdown("---")
    if st.button("計算・保存", type="primary", use_container_width=True):

        if not case_name.strip():
            st.error("ケース名は必須です。")
            return

        comparables: list[ComparableTickerRow] = st.session_state.get("comparable_rows", [])

        params = ValuationParams(
            case_name      = case_name.strip(),
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

        try:
            with st.spinner("計算中..."):
                result: ValuationResult = svc.calculate(params)
                case_id = svc.save(params, result, comparables or None)

            st.success(f"保存完了 (case_id = {case_id})")

            # 結果表示
            st.subheader("評価結果プレビュー")
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

            # セッションクリア
            st.session_state.pop("comparable_rows", None)
            st.session_state.pop("auto_vol", None)

            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("詳細ページへ", use_container_width=True):
                    st.session_state["detail_case_id"] = case_id
                    st.session_state["current_page"]   = "case_detail"
                    st.rerun()
            with col_b:
                if st.button("ケース一覧へ", use_container_width=True):
                    st.session_state["current_page"] = "case_list"
                    st.rerun()

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            raise


render = show
