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

        tk_obj = yf.Ticker(ticker)
        hist = tk_obj.history(period=period)
        if hist is None or hist.empty:
            return {
                "ticker": ticker, "fetch_ok": False,
                "error_msg": "データなし", "vol_period": period,
                "volatility": 0.0, "company_label": ticker,
            }

        close   = hist["Close"].dropna()
        log_ret = np.log(close / close.shift(1)).dropna()
        if len(log_ret) < 20:
            return {
                "ticker": ticker, "fetch_ok": False,
                "error_msg": "データ不足（20営業日未満）", "vol_period": period,
                "volatility": 0.0, "company_label": ticker,
            }
        vol = float(log_ret.std(ddof=1) * np.sqrt(252))

        label = ticker
        try:
            info = tk_obj.info
            label = (
                info.get("longName") or
                info.get("shortName") or
                info.get("displayName") or
                info.get("name") or
                ticker
            )
            if not label or label.strip() == "":
                label = ticker
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
    return ComparableTickerRow(
        ticker        = d["ticker"],
        company_label = d["company_label"],
        volatility    = d["volatility"],
        vol_period    = d["vol_period"],
        fetch_ok      = d["fetch_ok"],
        error_msg     = d.get("error_msg", ""),
    )


def _calc_mean_volatility(rows: list[ComparableTickerRow]) -> float | None:
    vols = [r.volatility for r in rows if r.fetch_ok and r.volatility > 0]
    return float(np.mean(vols)) if vols else None


def _apply_vol(vol: float) -> None:
    """
    ボラティリティをsession_stateに反映する。
    vol_input keyが既に存在する場合はそちらも更新してrerun。
    """
    st.session_state["auto_vol"] = vol
    # number_inputのkeyが既に登録済みの場合、直接上書きしないと反映されない
    if "vol_input" in st.session_state:
        st.session_state["vol_input"] = vol
    st.rerun()


# ============================================================
# メインページ
# ============================================================
def show() -> None:
    st.title("新規評価ケース作成")

    # ----------------------------------------------------------
    # 類似会社ボラティリティ取得セクション
    # ----------------------------------------------------------
    with st.expander("📊 類似会社ボラティリティ（任意）", expanded=False):
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
                time.sleep(0.3)
            progress.empty()

            rows = [_dict_to_row(d) for d in rows_raw]
            st.session_state["comparable_rows"] = rows

            mean_vol = _calc_mean_volatility(rows)
            if mean_vol is not None:
                # ★ vol_inputキーも同時更新 → number_inputに即時反映
                st.session_state["auto_vol"] = mean_vol
                if "vol_input" in st.session_state:
                    st.session_state["vol_input"] = mean_vol
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
                    "ステータス":     "✅ OK" if r.fetch_ok else f"❌ {r.error_msg}",
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
                            _apply_vol(r.volatility)

            # 平均反映ボタン
            mean_vol = _calc_mean_volatility(ok_rows) if ok_rows else None
            if mean_vol is not None and len(ok_rows) > 1:
                if st.button(
                    f"平均値 ({mean_vol:.2%}) を反映",
                    key="apply_mean_vol",
                    use_container_width=True,
                ):
                    _apply_vol(mean_vol)

            if st.button("類似会社データをクリア", key="clear_comp"):
                st.session_state.pop("comparable_rows", None)
                st.session_state.pop("auto_vol", None)
                if "vol_input" in st.session_state:
                    st.session_state["vol_input"] = 0.20
                st.rerun()

    # ----------------------------------------------------------
    # 評価パラメータ
    # ----------------------------------------------------------
    # vol_input keyが既存ならそちらを使う（session_stateで管理）
    # 初期値は auto_vol → なければ 0.20
    if "vol_input" not in st.session_state:
        st.session_state["vol_input"] = st.session_state.get("auto_vol", 0.20)

    with st.expander("📋 評価パラメータ", expanded=True):
        case_name = st.text_input("ケース名 *", value="新規ケース", key="nv_case_name")

        if "auto_vol" in st.session_state:
            st.info(
                f"📌 類似会社ボラティリティ ({st.session_state['auto_vol']:.2%}) "
                "が反映されています。変更する場合は下欄を直接編集してください。"
            )

        col1, col2 = st.columns(2)
        with col1:
            stock_price    = st.number_input(
                "株価 (S)", value=100.0, min_value=0.01,
                key="nv_stock_price")
            strike_price   = st.number_input(
                "行使価格 (K)", value=100.0, min_value=0.01,
                key="nv_strike_price")
            risk_free_rate = st.number_input(
                "無リスク金利", value=0.02, min_value=0.0,
                format="%.4f", key="nv_risk_free_rate")
        with col2:
            # ★ keyを使ってsession_state経由で値を管理
            volatility = st.number_input(
                "ボラティリティ",
                min_value=0.001,
                max_value=5.0,
                format="%.4f",
                key="vol_input",          # session_state["vol_input"] と連動
                help="類似会社取得後は自動で更新されます",
            )
            time_to_expiry = st.number_input(
                "残存期間 (年)", value=1.0, min_value=0.01,
                key="nv_time_to_expiry")
            dividend_yield = st.number_input(
                "配当利回り", value=0.0, min_value=0.0,
                format="%.4f", key="nv_dividend_yield")

        col3, col4, col5 = st.columns(3)
        with col3:
            option_type = st.selectbox(
                "オプション種類", ["call", "put"], key="nv_option_type")
        with col4:
            binomial_steps = st.number_input(
                "二項ステップ数", value=100, min_value=10, step=10,
                key="nv_binomial_steps")
        with col5:
            mc_simulations = st.number_input(
                "MCシミュレーション数", value=10000, min_value=1000, step=1000,
                key="nv_mc_simulations")

    # ----------------------------------------------------------
    # 計算・保存
    # ----------------------------------------------------------
    st.markdown("---")
    if st.button("🚀 計算・保存", type="primary", use_container_width=True):

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

            st.success(f"✅ 保存完了 (case_id = {case_id})")

            # 結果表示
            st.subheader("📊 評価結果プレビュー")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("BS価格",   f"¥{result.bs_price:,.4f}")
            c2.metric("二項価格", f"¥{result.binomial_price:,.4f}")
            c3.metric("MC価格",   f"¥{result.mc_price:,.4f}")
            c4.metric("加重平均", f"¥{result.weighted_price:,.4f}")

            st.subheader("📐 Greeks")
            g1, g2, g3, g4, g5 = st.columns(5)
            g1.metric("Delta", f"{result.delta:.4f}")
            g2.metric("Gamma", f"{result.gamma:.6f}")
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
                if st.button("📂 詳細ページへ", use_container_width=True, key="goto_detail"):
                    st.session_state["detail_case_id"] = case_id
                    st.session_state["current_page"]   = "case_detail"
                    st.rerun()
            with col_b:
                if st.button("📋 ケース一覧へ", use_container_width=True, key="goto_list"):
                    st.session_state["current_page"] = "case_list"
                    st.rerun()

        except Exception as e:
            st.error(f"❌ エラーが発生しました: {e}")
            import traceback
            st.code(traceback.format_exc())


render = show
