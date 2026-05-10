# src/ui/pages/case_detail.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from src.services.valuation_service import (
    ValuationService, ValuationParams, ComparableTickerRow)

svc = ValuationService()

# ── ボラティリティ取得ヘルパー ───────────────────────────────────
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

# ── メイン ───────────────────────────────────────────────────────
def show(case_id: int):
    case = svc.get_case(case_id)
    if case is None:
        st.error("ケースが見つかりません")
        return

    # 編集モードフラグ
    edit_key = f"edit_mode_{case_id}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    # ── ヘッダー ────────────────────────────────────────────────
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.title(f"📋 {case['case_name']}")
    with col_btn:
        if not st.session_state[edit_key]:
            if st.button("✏️ 編集・再評価", use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()
        else:
            if st.button("❌ キャンセル", use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()

    created = case['created_at'].strftime("%Y-%m-%d %H:%M") if case.get('created_at') else "-"
    updated = case['updated_at'].strftime("%Y-%m-%d %H:%M") if case.get('updated_at') else "-"
    st.caption(f"作成: {created}　最終更新: {updated}")
    st.divider()

    # ════════════════════════════════════════════════
    #  閲覧モード
    # ════════════════════════════════════════════════
    if not st.session_state[edit_key]:
        _show_view(case, case_id)

    # ════════════════════════════════════════════════
    #  編集モード
    # ════════════════════════════════════════════════
    else:
        _show_edit(case, case_id, edit_key)


# ── 閲覧モード ───────────────────────────────────────────────────
def _show_view(case: dict, case_id: int):
    # パラメータ
    st.subheader("📥 入力パラメータ")
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.metric("株価 (S)",       f"¥{case['stock_price']:,.2f}")
        st.metric("行使価格 (K)",    f"¥{case['strike_price']:,.2f}")
        st.metric("リスクフリー率",  f"{case['risk_free_rate']*100:.2f}%")
        st.metric("ボラティリティ",  f"{case['volatility']*100:.2f}%")
    with p_col2:
        st.metric("満期までの期間",  f"{case['time_to_expiry']:.4f} 年")
        st.metric("オプション種別",  case['option_type'].upper())
        st.metric("配当利回り",      f"{(case['dividend_yield'] or 0)*100:.2f}%")
        st.metric("二項モデルステップ数", str(case['binomial_steps']))

    # 比較企業
    comps = svc.get_comparable_tickers(case_id)
    if comps:
        st.divider()
        st.subheader("🏢 比較対象企業 ボラティリティ")
        rows = [{"ティッカー":   c["ticker"],
                 "企業名":       c.get("company_label") or "-",
                 "ボラティリティ": f"{c['volatility']*100:.2f}%" if c.get("volatility") else "-",
                 "取得期間":     c.get("vol_period") or "-",
                 "ステータス":   "✅" if c.get("fetch_ok") else f"❌ {c.get('error_msg','')}"}
                for c in comps]
        st.dataframe(pd.DataFrame(rows), use_container_width=True,
                     hide_index=True)
        valid_vols = [c["volatility"] for c in comps
                      if c.get("fetch_ok") and c.get("volatility")]
        if valid_vols:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("平均", f"{np.mean(valid_vols)*100:.2f}%")
            c2.metric("最大", f"{np.max(valid_vols)*100:.2f}%")
            c3.metric("最小", f"{np.min(valid_vols)*100:.2f}%")
            c4.metric("社数", len(valid_vols))

    # 評価結果
    st.divider()
    st.subheader("📊 評価結果")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Black-Scholes",  f"¥{case['bs_price']:,.4f}")
    r2.metric("二項モデル",      f"¥{case['binomial_price']:,.4f}")
    r3.metric("モンテカルロ",    f"¥{case['mc_price']:,.4f}")
    r4.metric("加重平均",        f"¥{case['weighted_price']:,.4f}",
              delta="最終評価額")

    st.divider()
    st.subheader("📐 Greeks")
    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Delta", f"{case['delta']:.4f}")
    g2.metric("Gamma", f"{case['gamma']:.6f}")
    g3.metric("Theta", f"{case['theta']:.4f}")
    g4.metric("Vega",  f"{case['vega']:.4f}")
    g5.metric("Rho",   f"{case['rho']:.4f}")

    # 削除
    st.divider()
    with st.expander("⚠️ 危険ゾーン"):
        if st.button("🗑️ このケースを削除", type="primary"):
            svc.delete_case(case_id)
            st.success("削除しました")
            st.session_state["page"] = "case_list"
            st.rerun()


# ── 編集モード ───────────────────────────────────────────────────
def _show_edit(case: dict, case_id: int, edit_key: str):
    st.subheader("✏️ パラメータ編集")

    comp_key = f"edit_comps_{case_id}"

    # ── 比較企業セクション ──────────────────────────────────────
    st.markdown("##### 🏢 比較対象企業（ボラティリティ取得）")
    existing = svc.get_comparable_tickers(case_id)  # list[dict]
    default_tickers = ", ".join(c["ticker"] for c in existing)

    ticker_input = st.text_input(
        "ティッカー（カンマ区切り）",
        value=default_tickers,
        key=f"edit_ticker_input_{case_id}",
        placeholder="例: 7203.T, 7267.T, AAPL"
    )

    if st.button("🔄 ティッカー取得", key=f"fetch_btn_{case_id}"):
        tickers = [t.strip() for t in ticker_input.split(",") if t.strip()]
        if tickers:
            rows: list[ComparableTickerRow] = []
            prog = st.progress(0)
            for i, t in enumerate(tickers):
                rows.append(_fetch_vol(t))
                prog.progress((i+1)/len(tickers))
            prog.empty()
            st.session_state[comp_key] = rows
        else:
            st.session_state[comp_key] = []

    # 比較企業の表示と平均ボラティリティ
    avg_vol_from_comp = None
    if comp_key in st.session_state and st.session_state[comp_key]:
        comps: list[ComparableTickerRow] = st.session_state[comp_key]
        rows_disp = [{"ティッカー": c.ticker,
                      "企業名":    c.company_label or "-",
                      "ボラティリティ": f"{c.volatility*100:.2f}%" if c.volatility else "-",
                      "ステータス": "✅" if c.fetch_ok else f"❌ {c.error_msg}"}
                     for c in comps]
        st.dataframe(pd.DataFrame(rows_disp), use_container_width=True,
                     hide_index=True)
        valid = [c.volatility for c in comps if c.fetch_ok and c.volatility]
        if valid:
            avg_vol_from_comp = float(np.mean(valid))
            st.info(f"📊 比較企業 平均ボラティリティ: **{avg_vol_from_comp*100:.2f}%**")

    elif comp_key not in st.session_state and existing:
        # 初回表示時は既存データ(dict)を表示
        rows_disp = [{"ティッカー": c["ticker"],
                      "企業名":    c.get("company_label") or "-",
                      "ボラティリティ": f"{c['volatility']*100:.2f}%" if c.get("volatility") else "-",
                      "ステータス": "✅" if c.get("fetch_ok") else f"❌ {c.get('error_msg','')}"}
                     for c in existing]
        st.dataframe(pd.DataFrame(rows_disp), use_container_width=True,
                     hide_index=True)
        valid = [c["volatility"] for c in existing
                 if c.get("fetch_ok") and c.get("volatility")]
        if valid:
            avg_vol_from_comp = float(np.mean(valid))

    st.divider()

    # ── パラメータ入力フォーム ──────────────────────────────────
    default_vol = avg_vol_from_comp if avg_vol_from_comp else case["volatility"]

    with st.form(key=f"edit_form_{case_id}"):
        st.markdown("##### 📥 評価パラメータ")
        col1, col2 = st.columns(2)
        with col1:
            case_name    = st.text_input("ケース名",
                               value=case["case_name"])
            stock_price  = st.number_input("株価 (S)",
                               value=float(case["stock_price"]),
                               min_value=0.01, step=100.0)
            strike_price = st.number_input("行使価格 (K)",
                               value=float(case["strike_price"]),
                               min_value=0.01, step=100.0)
            risk_free    = st.number_input("リスクフリー率",
                               value=float(case["risk_free_rate"])*100,
                               min_value=0.0, max_value=20.0,
                               step=0.1, format="%.2f")
        with col2:
            volatility   = st.number_input("ボラティリティ (%)",
                               value=float(default_vol)*100,
                               min_value=0.1, max_value=300.0,
                               step=1.0, format="%.2f")
            time_to_exp  = st.number_input("満期までの期間 (年)",
                               value=float(case["time_to_expiry"]),
                               min_value=0.01, max_value=10.0,
                               step=0.25, format="%.4f")
            option_type  = st.selectbox("オプション種別", ["call", "put"],
                               index=0 if case["option_type"] == "call" else 1)
            div_yield    = st.number_input("配当利回り (%)",
                               value=float(case["dividend_yield"] or 0)*100,
                               min_value=0.0, max_value=20.0,
                               step=0.1, format="%.2f")

        with st.expander("⚙️ 高度な設定"):
            bin_steps = st.number_input("二項モデル ステップ数",
                            value=int(case["binomial_steps"]),
                            min_value=10, max_value=1000, step=10)
            mc_sims   = st.number_input("モンテカルロ 試行回数",
                            value=int(case["mc_simulations"]),
                            min_value=1000, max_value=100000, step=1000)

        submitted = st.form_submit_button("🔄 再評価・保存", type="primary",
                                          use_container_width=True)

    if submitted:
        params = ValuationParams(
            case_name      = case_name,
            stock_price    = stock_price,
            strike_price   = strike_price,
            risk_free_rate = risk_free / 100,
            volatility     = volatility / 100,
            time_to_expiry = time_to_exp,
            option_type    = option_type,
            dividend_yield = div_yield / 100,
            binomial_steps = int(bin_steps),
            mc_simulations = int(mc_sims),
        )
        result = svc.calculate(params)

        # 比較企業データ（再取得済み ComparableTickerRow or 既存 dict → 変換）
        comp_data: list[ComparableTickerRow] | None = st.session_state.get(comp_key, None)
        if comp_data is None:
            comp_data = [ComparableTickerRow(
                ticker        = c["ticker"],
                company_label = c.get("company_label"),
                volatility    = c.get("volatility"),
                vol_period    = c.get("vol_period"),
                fetch_ok      = bool(c.get("fetch_ok")),
                error_msg     = c.get("error_msg") or "",
            ) for c in existing]

        svc.update(case_id, params, result, comp_data if comp_data else None)

        # セッション状態をクリア
        if comp_key in st.session_state:
            del st.session_state[comp_key]
        st.session_state[edit_key] = False

        st.success("✅ 再評価・保存が完了しました")
        st.rerun()


# app.py / case_list.py からの呼び出し互換
def render(case_id: int | None = None) -> None:
    # 引数がなければ session_state から取得
    if case_id is None:
        case_id = st.session_state.get("selected_case_id")

    if case_id is None:
        st.warning("⚠️ 案件が選択されていません。")
        st.info("「📋 評価一覧」から案件を選択してください。")
        if st.button("📋 評価一覧へ"):
            st.session_state["current_page"] = "📋 評価一覧"
            st.rerun()
        return

    show(case_id)

