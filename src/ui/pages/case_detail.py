# -*- coding: utf-8 -*-
# src/ui/pages/case_detail.py
from __future__ import annotations
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
from src.services.valuation_service import ValuationService, ValuationParams

_svc = ValuationService()


def _fmt(v, fmt=".4f"):
    """None セーフなフォーマッタ"""
    if v is None:
        return "N/A"
    try:
        return format(float(v), fmt)
    except (TypeError, ValueError):
        return str(v)


def _sensitivity_chart(case: dict) -> go.Figure:
    """株価 vs BS価格の感応度チャート"""
    S0    = float(case["stock_price"])
    K     = float(case["strike_price"])
    r     = float(case["risk_free_rate"])
    sigma = float(case["volatility"])
    T     = float(case["time_to_expiry"])
    q     = float(case.get("dividend_yield") or 0.0)
    otype = case.get("option_type", "call")

    s_range = np.linspace(S0 * 0.5, S0 * 1.5, 60)
    prices  = []
    for s in s_range:
        p = ValuationParams(
            case_name="tmp", stock_price=s, strike_price=K,
            risk_free_rate=r, volatility=sigma, time_to_expiry=T,
            option_type=otype, dividend_yield=q,
            binomial_steps=50, mc_simulations=1000,
        )
        res = _svc.calculate(p)
        prices.append(res.bs_price)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=s_range, y=prices,
        mode="lines", name="BS価格",
        line=dict(color="#1f77b4", width=2),
    ))
    fig.add_vline(x=S0, line_dash="dash", line_color="red",
                  annotation_text=f"現在株価 {S0:.1f}")
    fig.add_vline(x=K,  line_dash="dot",  line_color="gray",
                  annotation_text=f"行使価格 {K:.1f}")
    fig.update_layout(
        title="株価感応度 (BS価格)",
        xaxis_title="株価 (S)",
        yaxis_title="オプション価格",
        height=380,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _show_bs_detail(detail: dict) -> None:
    """BS計算プロセス詳細の表示"""
    st.markdown("#### 📐 Black-Scholes 計算プロセス")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**中間変数**")
        st.latex(r"d_1 = \frac{\ln(S/K) + (r - q + \frac{\sigma^2}{2})T}{\sigma\sqrt{T}}")
        st.code(
            f"ln(S/K)      = {_fmt(detail.get('log_SK'))}\n"
            f"σ√T          = {_fmt(detail.get('sigma_sqrtT'))}\n"
            f"d₁           = {_fmt(detail.get('d1'))}\n"
            f"d₂           = {_fmt(detail.get('d2'))}",
            language=None,
        )
    with col2:
        st.markdown("**正規分布値**")
        st.code(
            f"N(d₁)        = {_fmt(detail.get('Nd1'))}\n"
            f"N(d₂)        = {_fmt(detail.get('Nd2'))}\n"
            f"N(-d₁)       = {_fmt(detail.get('Nnd1'))}\n"
            f"N(-d₂)       = {_fmt(detail.get('Nnd2'))}\n"
            f"n(d₁)        = {_fmt(detail.get('nd1'))}",
            language=None,
        )
    with col3:
        st.markdown("**割引因子**")
        st.code(
            f"e^(-qT)      = {_fmt(detail.get('exp_qT'))}\n"
            f"e^(-rT)      = {_fmt(detail.get('exp_rT'))}",
            language=None,
        )

    st.markdown("**Greeks（BSモデル）**")
    gc1, gc2, gc3, gc4, gc5 = st.columns(5)
    gc1.metric("Delta", _fmt(detail.get("delta")))
    gc2.metric("Gamma", _fmt(detail.get("gamma")))
    gc3.metric("Theta", _fmt(detail.get("theta")))
    gc4.metric("Vega",  _fmt(detail.get("vega")))
    gc5.metric("Rho",   _fmt(detail.get("rho")))


def _show_binomial_detail(detail: dict) -> None:
    """二項モデル計算プロセス詳細の表示"""
    st.markdown("#### 🌳 二項モデル 計算プロセス")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**ツリーパラメータ**")
        st.code(
            f"ステップ数 N  = {detail.get('steps', 'N/A')}\n"
            f"dt           = {_fmt(detail.get('dt'))}\n"
            f"上昇率 u     = {_fmt(detail.get('u'))}\n"
            f"下落率 d     = {_fmt(detail.get('d'))}\n"
            f"上昇確率 p↑  = {_fmt(detail.get('p_up'))}\n"
            f"下落確率 p↓  = {_fmt(detail.get('p_down'))}\n"
            f"割引因子     = {_fmt(detail.get('discount'))}",
            language=None,
        )
    with col2:
        st.markdown("**最終ノード（サンプル）**")
        prices  = detail.get("terminal_prices_sample", [])
        payoffs = detail.get("terminal_payoffs_sample", [])
        if prices:
            rows = []
            for pr, pa in zip(prices, payoffs):
                if pr == "...":
                    rows.append({"株価": "...", "ペイオフ": "..."})
                else:
                    rows.append({
                        "株価":    f"{float(pr):.2f}",
                        "ペイオフ": f"{float(pa):.2f}",
                    })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    col3, col4, col5 = st.columns(3)
    col3.metric("最大株価（満期）", _fmt(detail.get("max_terminal_price"), ".2f"))
    col4.metric("最小株価（満期）", _fmt(detail.get("min_terminal_price"), ".2f"))
    col5.metric("ITMノード数",     str(detail.get("n_itm", "N/A")))


def _show_mc_detail(detail: dict) -> None:
    """モンテカルロ計算プロセス詳細の表示"""
    st.markdown("#### 🎲 モンテカルロ 計算プロセス")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**シミュレーション統計**")
        st.code(
            f"シミュレーション数 = {detail.get('n_simulations', 'N/A')}\n"
            f"ST 平均           = {_fmt(detail.get('mean_ST'), '.4f')}\n"
            f"ST 標準偏差       = {_fmt(detail.get('std_ST'), '.4f')}\n"
            f"ST 最小           = {_fmt(detail.get('min_ST'), '.4f')}\n"
            f"ST 最大           = {_fmt(detail.get('max_ST'), '.4f')}\n"
            f"ITM本数           = {detail.get('n_itm', 'N/A')}\n"
            f"ITM比率           = {_fmt(detail.get('itm_ratio'), '.4f')}",
            language=None,
        )
    with col2:
        st.markdown("**価格推定**")
        st.code(
            f"平均ペイオフ       = {_fmt(detail.get('mean_payoff'), '.4f')}\n"
            f"標準偏差           = {_fmt(detail.get('std_payoff'), '.4f')}\n"
            f"標準誤差 (SE)      = {_fmt(detail.get('std_error'), '.6f')}\n"
            f"割引因子           = {_fmt(detail.get('discount_factor'))}\n"
            f"95%CI 下限         = {_fmt(detail.get('ci95_lower'), '.4f')}\n"
            f"95%CI 上限         = {_fmt(detail.get('ci95_upper'), '.4f')}",
            language=None,
        )

    # 株価分布ヒストグラム
    st_hist = detail.get("ST_hist")
    if st_hist:
        st.markdown("**最終株価分布（サンプル2000件）**")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=st_hist,
            nbinsx=50,
            marker_color="#1f77b4",
            opacity=0.7,
            name="最終株価",
        ))
        fig.add_vline(
            x=float(detail.get("mean_ST", 0)),
            line_dash="dash", line_color="red",
            annotation_text="平均",
        )
        fig.update_layout(
            title="モンテカルロ 最終株価分布",
            xaxis_title="最終株価 ST",
            yaxis_title="頻度",
            height=300,
            margin=dict(l=40, r=20, t=50, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════
# Ticker 編集 UI
# ════════════════════════════════════════════════════════
def _ticker_editor(case_id: int) -> None:
    """類似会社Tickerの追加・削除・再取得UI"""
    st.markdown("### 📡 類似会社Ticker（ボラティリティ参照）")

    comparables = _svc.get_comparable_tickers(case_id)

    if comparables:
        st.markdown("**現在登録済みのTicker**")
        for comp in comparables:
            col_tick, col_vol, col_status, col_del = st.columns([2, 2, 3, 1])
            with col_tick:
                st.write(f"`{comp['ticker']}`")
                if comp.get("company_label"):
                    st.caption(comp["company_label"])
            with col_vol:
                vol = comp.get("volatility")
                st.write(f"{vol:.4f}" if vol is not None else "未取得")
            with col_status:
                if comp.get("fetch_ok"):
                    st.success("✅ 取得成功", icon="✅")
                else:
                    st.error(f"❌ {comp.get('error_msg','取得失敗')}")
            with col_del:
                if st.button(
                    "🗑️",
                    key=f"del_ticker_{case_id}_{comp['ticker']}",
                    help=f"{comp['ticker']} を削除",
                ):
                    _svc.delete_comparable_ticker(case_id, comp["ticker"])
                    st.success(f"{comp['ticker']} を削除しました。")
                    st.rerun()
        st.divider()
    else:
        st.info("類似会社Tickerが登録されていません。")
        st.divider()

    st.markdown("**Tickerを追加する**")
    with st.form(key=f"add_ticker_form_{case_id}", clear_on_submit=True):
        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            new_ticker = st.text_input(
                "Tickerシンボル",
                placeholder="例: 7203.T",
                help="Yahoo Finance形式で入力（日本株は末尾に .T）",
            )
        with col_b:
            label = st.text_input("会社名（任意）", placeholder="例: トヨタ自動車")
        with col_c:
            period = st.selectbox("取得期間", ["1y", "2y", "3y", "6mo"], index=0)
        add_submitted = st.form_submit_button(
            "➕ 追加・取得", type="primary", use_container_width=True
        )

    if add_submitted:
        ticker_str = new_ticker.strip().upper()
        if not ticker_str:
            st.warning("Tickerシンボルを入力してください。")
        else:
            with st.spinner(f"{ticker_str} のデータを取得中..."):
                try:
                    result = _svc.add_comparable_ticker(
                        case_id=case_id,
                        ticker=ticker_str,
                        company_label=label.strip(),
                        vol_period=period,
                    )
                    if result.get("fetch_ok"):
                        st.success(
                            f"✅ {ticker_str} を追加しました。"
                            f"ボラティリティ: {result['volatility']:.4f}"
                        )
                    else:
                        st.error(f"❌ 取得失敗: {result.get('error_msg','不明なエラー')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"エラー: {e}")

    if comparables:
        st.divider()
        if st.button(
            "🔄 全Tickerを一括再取得",
            key=f"refetch_all_{case_id}",
            use_container_width=True,
        ):
            with st.spinner("全Tickerのデータを再取得中..."):
                try:
                    results = _svc.refetch_all_tickers(case_id)
                    ok  = sum(1 for r in results if r.get("fetch_ok"))
                    ng  = len(results) - ok
                    st.success(f"再取得完了: 成功 {ok} 件 / 失敗 {ng} 件")
                    st.rerun()
                except Exception as e:
                    st.error(f"エラー: {e}")


# ════════════════════════════════════════════════════════
# メイン show()
# ════════════════════════════════════════════════════════
def show() -> None:
    case_id = st.session_state.get("detail_case_id")
    if case_id is None:
        st.warning("ケースが選択されていません。")
        if st.button("← ケース一覧へ"):
            st.session_state["current_page"] = "case_list"
            st.rerun()
        return

    case = _svc.get_case(case_id)
    if case is None:
        st.error(f"ケース ID={case_id} が見つかりません。")
        if st.button("← ケース一覧へ"):
            st.session_state["current_page"] = "case_list"
            st.rerun()
        return

    # ── 詳細画面でパラメータから再計算（計算プロセス詳細を復元） ──
    cache_key = f"calc_result_{case_id}_{case.get('updated_at', '')}"
    if cache_key not in st.session_state:
        params = ValuationParams(
            case_name      = str(case["case_name"]),
            stock_price    = float(case["stock_price"]),
            strike_price   = float(case["strike_price"]),
            risk_free_rate = float(case["risk_free_rate"]),
            volatility     = float(case["volatility"]),
            time_to_expiry = float(case["time_to_expiry"]),
            option_type    = str(case.get("option_type", "call")),
            dividend_yield = float(case.get("dividend_yield") or 0.0),
            binomial_steps = int(case.get("binomial_steps") or 100),
            mc_simulations = int(case.get("mc_simulations") or 10000),
        )
        result = _svc.calculate(params)
        st.session_state[cache_key] = result

    result = st.session_state[cache_key]

    # ── ヘッダー ──────────────────────────────
    col_back, col_title = st.columns([1, 8])
    with col_back:
        if st.button("← 一覧"):
            st.session_state["current_page"] = "case_list"
            st.rerun()
    with col_title:
        st.title(f"📋 {case['case_name']}")

    created = case.get("created_at", "")
    updated = case.get("updated_at", "")
    st.caption(f"作成: {created}　最終更新: {updated}")

    # ── タブ構成 ──────────────────────────────
    tab_view, tab_edit, tab_chart = st.tabs(
        ["📊 結果・計算プロセス", "✏️ 編集・再計算", "📈 感応度分析"]
    )

    # ════════════════════════════════════════
    # TAB 1: 結果 ＋ 計算プロセス詳細
    # ════════════════════════════════════════
    with tab_view:

        # ── オプション価格 ────────────────────
        st.markdown("### 💰 オプション価格")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⭐ 加重平均価格", _fmt(case.get("weighted_price"), ".2f"))
        c2.metric("BS価格",         _fmt(case.get("bs_price"),        ".2f"))
        c3.metric("二項モデル価格", _fmt(case.get("binomial_price"),  ".2f"))
        c4.metric("MC価格",         _fmt(case.get("mc_price"),        ".2f"))
        st.caption("加重: BS×0.5 ＋ 二項×0.3 ＋ MC×0.2")

        # ── Greeks ───────────────────────────
        st.markdown("### 🔢 Greeks（BS基準）")
        g1, g2, g3, g4, g5 = st.columns(5)
        g1.metric("Delta", _fmt(case.get("delta")))
        g2.metric("Gamma", _fmt(case.get("gamma")))
        g3.metric("Theta", _fmt(case.get("theta")))
        g4.metric("Vega",  _fmt(case.get("vega")))
        g5.metric("Rho",   _fmt(case.get("rho")))

        # ── 計算パラメータ ────────────────────
        st.markdown("### ⚙️ 計算パラメータ")
        p1, p2 = st.columns(2)
        with p1:
            st.write(f"- 現在株価:     **{_fmt(case.get('stock_price'), '.2f')}**")
            st.write(f"- 行使価格:     **{_fmt(case.get('strike_price'), '.2f')}**")
            st.write(f"- 無リスク金利: **{_fmt(case.get('risk_free_rate'), '.4f')}**")
            st.write(f"- ボラティリティ: **{_fmt(case.get('volatility'), '.4f')}**")
        with p2:
            st.write(f"- 満期（年）:   **{_fmt(case.get('time_to_expiry'), '.4f')}**")
            st.write(f"- 配当利回り:   **{_fmt(case.get('dividend_yield'), '.4f')}**")
            st.write(f"- オプション種類: **{case.get('option_type', 'call')}**")
            st.write(f"- 二項ステップ: **{case.get('binomial_steps', 100)}**")
            st.write(f"- MC試行数:     **{case.get('mc_simulations', 10000):,}**")

        # ── 類似会社Ticker ────────────────────
        comparables = _svc.get_comparable_tickers(case_id)
        if comparables:
            st.markdown("### 📡 類似会社ボラティリティ")
            df = pd.DataFrame([{
                "ティッカー":     c["ticker"],
                "会社名":         c.get("company_label", ""),
                "ボラティリティ": f"{c.get('volatility', 0):.4f}",
                "期間":           c.get("vol_period", ""),
                "状態":           "✅" if c.get("fetch_ok") else f"❌ {c.get('error_msg','')}",
            } for c in comparables])
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

        # ════════════════════════════════════
        # 計算プロセス詳細（アコーディオン）
        # ════════════════════════════════════
        st.markdown("### 🔍 計算プロセス詳細")

        with st.expander("📐 Black-Scholes モデル（クリックで展開）", expanded=False):
            if result.bs_detail:
                _show_bs_detail(result.bs_detail)
            else:
                st.info("BS計算詳細がありません。")

        with st.expander("🌳 二項モデル（クリックで展開）", expanded=False):
            if result.bin_detail:
                _show_binomial_detail(result.bin_detail)
            else:
                st.info("二項モデル詳細がありません。")

        with st.expander("🎲 モンテカルロ シミュレーション（クリックで展開）", expanded=False):
            if result.mc_detail:
                _show_mc_detail(result.mc_detail)
            else:
                st.info("MC詳細がありません。")

    # ════════════════════════════════════════
    # TAB 2: 編集・再計算
    # ════════════════════════════════════════
    with tab_edit:
        st.markdown("### パラメータを変更して再計算")
        with st.form("edit_form"):
            case_name = st.text_input("ケース名", value=case["case_name"])
            col1, col2 = st.columns(2)
            with col1:
                S     = st.number_input("現在株価 (S)",   value=float(case["stock_price"]),    step=1.0)
                K     = st.number_input("行使価格 (K)",   value=float(case["strike_price"]),   step=1.0)
                T     = st.number_input("満期（年）(T)",  value=float(case["time_to_expiry"]), step=0.1,  format="%.4f")
                otype = st.selectbox(
                    "オプション種類", ["call", "put"],
                    index=0 if case.get("option_type", "call") == "call" else 1,
                )
            with col2:
                r     = st.number_input("無リスク金利 (r)",   value=float(case["risk_free_rate"]), step=0.001, format="%.4f")
                sigma = st.number_input("ボラティリティ (σ)", value=float(case["volatility"]),     step=0.01,  format="%.4f")
                q     = st.number_input("配当利回り (q)",
                                        value=float(case.get("dividend_yield") or 0.0),
                                        step=0.001, format="%.4f")
                steps = st.number_input("二項ステップ数", value=int(case.get("binomial_steps") or 100),
                                        min_value=10, max_value=1000, step=10)
                mc_n  = st.number_input("MCシミュレーション数",
                                        value=int(case.get("mc_simulations") or 10000),
                                        min_value=1000, max_value=100000, step=1000)
            submitted = st.form_submit_button("💾 保存して再計算", type="primary")

        if submitted:
            try:
                params = ValuationParams(
                    case_name=case_name, stock_price=S, strike_price=K,
                    risk_free_rate=r, volatility=sigma, time_to_expiry=T,
                    option_type=otype, dividend_yield=q,
                    binomial_steps=int(steps),
                    mc_simulations=int(mc_n),
                )
                _svc.update_case(case_id, params)
                # キャッシュ削除（再計算を促す）
                for key in list(st.session_state.keys()):
                    if key.startswith(f"calc_result_{case_id}_"):
                        del st.session_state[key]
                st.success("✅ 再計算・保存しました。「結果」タブで確認できます。")
                st.rerun()
            except Exception as e:
                st.error(f"エラー: {e}")

        st.divider()
        _ticker_editor(case_id)
        st.divider()

        # ── ケース削除 ────────────────────────
        st.markdown("### ⚠️ ケース削除")
        if st.button("🗑️ このケースを削除", type="secondary"):
            st.session_state["confirm_delete"] = True

        if st.session_state.get("confirm_delete"):
            st.warning(f"「{case['case_name']}」を削除しますか？この操作は元に戻せません。")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("はい、削除します", type="primary"):
                    _svc.delete_case(case_id)
                    # キャッシュ削除
                    for key in list(st.session_state.keys()):
                        if key.startswith(f"calc_result_{case_id}_"):
                            del st.session_state[key]
                    st.session_state.pop("detail_case_id", None)
                    st.session_state.pop("confirm_delete", None)
                    st.session_state["current_page"] = "case_list"
                    st.rerun()
            with col_no:
                if st.button("キャンセル"):
                    st.session_state.pop("confirm_delete", None)
                    st.rerun()

    # ════════════════════════════════════════
    # TAB 3: 感応度分析
    # ════════════════════════════════════════
    with tab_chart:
        st.markdown("### 株価 vs オプション価格（BS）")
        st.caption("現在のパラメータで株価を±50%変動させた場合の感応度")
        with st.spinner("チャート生成中..."):
            fig = _sensitivity_chart(case)
        st.plotly_chart(fig, use_container_width=True)


def render() -> None:
    show()
