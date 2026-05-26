# src/ui/pages/case_detail.py
from __future__ import annotations

import traceback
import streamlit as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.services.valuation_service import ValuationService, ValuationParams


# ─────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────
def _get_service() -> ValuationService:
    return ValuationService()


def _fetch_case(case_id: int) -> dict | None:
    return _get_service().get_case(case_id)


def _build_params(p: dict, case_name: str = "") -> ValuationParams:
    return ValuationParams(
        case_name      = case_name or p.get("case_name", ""),
        stock_price    = float(p.get("stock_price",    100)),
        strike_price   = float(p.get("strike_price",   100)),
        risk_free_rate = float(p.get("risk_free_rate", 0.02)),
        volatility     = float(p.get("volatility",     0.30)),
        time_to_expiry = float(p.get("time_to_expiry", 1.0)),
        option_type    = p.get("option_type", "call"),
        dividend_yield = float(p.get("dividend_yield", 0.0)),
        binomial_steps = int(p.get("binomial_steps",   100)),
        mc_simulations = int(p.get("mc_simulations",   10000)),
    )


def _plot_mc_histogram(payoffs: list, price: float) -> None:
    arr = np.array(payoffs, dtype=float)
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.hist(arr, bins=60, color="#4C8BF5", edgecolor="white", alpha=0.85)
    ax.axvline(price, color="red", linewidth=1.8, linestyle="--",
               label=f"MC Price: {price:.2f}")
    ax.set_xlabel("Payoff")
    ax.set_ylabel("Frequency")
    ax.set_title("Monte Carlo Payoff Distribution")
    ax.legend()
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _fmt(v) -> str:
    if isinstance(v, float): return f"{v:.6f}"
    if isinstance(v, int):   return f"{v:,}"
    if isinstance(v, list):
        preview = [f"{x:.4f}" if isinstance(x, float) else str(x) for x in v[:4]]
        return "[" + ", ".join(preview) + (" …" if len(v) > 4 else "") + "]"
    return str(v)


def _show_scalars(d: dict, skip: tuple = ("ST_hist", "payoff_hist")) -> None:
    items = [(k, v) for k, v in d.items()
             if k not in skip and not isinstance(v, list)]
    if not items:
        st.info("表示できるデータがありません。")
        return
    cols = st.columns(3)
    for idx, (k, v) in enumerate(items):
        cols[idx % 3].metric(k, _fmt(v))


def _show_list_items(d: dict, skip: tuple = ("ST_hist", "payoff_hist")) -> None:
    for k, v in d.items():
        if k not in skip and isinstance(v, list):
            with st.expander(f"└ {k}（{len(v)} 件）", expanded=False):
                st.write(v)


# ─────────────────────────────────────────
# session_state 初期化ヘルパー
# ─────────────────────────────────────────
def _init_edit_state(case: dict, case_id: int) -> None:
    """
    編集用session_stateを初期化する。
    case_idが変わった場合のみリセット（ページ遷移対応）。
    """
    if st.session_state.get("_edit_case_id") != case_id:
        st.session_state["_edit_case_id"]     = case_id
        st.session_state["edit_case_name"]    = case.get("case_name", "")
        st.session_state["edit_stock_price"]  = float(case.get("stock_price",    100))
        st.session_state["edit_strike"]       = float(case.get("strike_price",   100))
        st.session_state["edit_rate"]         = float(case.get("risk_free_rate", 0.02))
        st.session_state["edit_div"]          = float(case.get("dividend_yield", 0.0))
        st.session_state["edit_vol"]          = float(case.get("volatility",     0.30))
        st.session_state["edit_tte"]          = float(case.get("time_to_expiry", 1.0))
        st.session_state["edit_opt_type"]     = case.get("option_type", "call")
        st.session_state["edit_bin_steps"]    = int(case.get("binomial_steps",   100))
        st.session_state["edit_mc_sims"]      = int(case.get("mc_simulations",   10000))
        # 計算結果もリセット
        st.session_state["edit_result"]       = None
        st.session_state["edit_result_dirty"] = True  # 再計算が必要


def _read_edit_state() -> dict:
    """session_stateから現在の編集値をdictで返す"""
    return dict(
        case_name      = st.session_state.get("edit_case_name",   ""),
        stock_price    = st.session_state.get("edit_stock_price", 100.0),
        strike_price   = st.session_state.get("edit_strike",      100.0),
        risk_free_rate = st.session_state.get("edit_rate",        0.02),
        volatility     = st.session_state.get("edit_vol",         0.30),
        time_to_expiry = st.session_state.get("edit_tte",         1.0),
        option_type    = st.session_state.get("edit_opt_type",    "call"),
        dividend_yield = st.session_state.get("edit_div",         0.0),
        binomial_steps = st.session_state.get("edit_bin_steps",   100),
        mc_simulations = st.session_state.get("edit_mc_sims",     10000),
    )


# ─────────────────────────────────────────
# show()
# ─────────────────────────────────────────
def show() -> None:
    case_id = st.session_state.get("detail_case_id")
    if not case_id:
        st.warning("ケースが選択されていません。")
        if st.button("← ホームに戻る"):
            st.session_state["current_page"] = "home"
            st.rerun()
        return

    case = _fetch_case(case_id)
    if not case:
        st.error(f"ケース ID={case_id} が見つかりません。")
        return

    # ── session_state を初期化（ケース切り替え時にリセット）
    _init_edit_state(case, case_id)

    st.title(f"?? {case.get('case_name', 'ケース詳細')}")

    tab_edit, tab_result, tab_mc = st.tabs(
        ["?? パラメータ編集 & 再計算", "?? 評価結果", "?? MCヒストグラム"]
    )

    # ????????????????????????????????????????
    # タブ 1: パラメータ編集 & 再計算
    # ????????????????????????????????????????
    with tab_edit:

        # ── パラメータ入力フォーム ──────────────────
        st.subheader("パラメータ編集")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state["edit_case_name"] = st.text_input(
                "ケース名",
                value=st.session_state["edit_case_name"],
                key="_w_case_name")
            st.session_state["edit_stock_price"] = st.number_input(
                "株価 (S)",
                value=st.session_state["edit_stock_price"],
                step=1.0, key="_w_stock_price")
            st.session_state["edit_strike"] = st.number_input(
                "行使価格 (K)",
                value=st.session_state["edit_strike"],
                step=1.0, key="_w_strike")
            st.session_state["edit_rate"] = st.number_input(
                "無リスク金利",
                value=st.session_state["edit_rate"],
                step=0.001, format="%.3f", key="_w_rate")
            st.session_state["edit_div"] = st.number_input(
                "配当利回り",
                value=st.session_state["edit_div"],
                step=0.001, format="%.3f", key="_w_div")
        with col2:
            # ── ボラティリティ（類似会社から反映可能）────
            vol_val = st.session_state["edit_vol"]
            new_vol = st.number_input(
                "ボラティリティ",
                value=vol_val,
                step=0.01, format="%.3f", key="_w_vol")
            st.session_state["edit_vol"] = new_vol

            st.session_state["edit_tte"] = st.number_input(
                "残存年数 (T)",
                value=st.session_state["edit_tte"],
                step=0.1, format="%.2f", key="_w_tte")

            opt_options = ["call", "put"]
            opt_idx = 0 if st.session_state["edit_opt_type"] == "call" else 1
            selected = st.selectbox(
                "オプション種類", opt_options,
                index=opt_idx, key="_w_opt_type")
            st.session_state["edit_opt_type"] = selected

            st.session_state["edit_bin_steps"] = int(st.number_input(
                "二項ステップ数",
                value=st.session_state["edit_bin_steps"],
                step=10, min_value=10, key="_w_bin_steps"))
            st.session_state["edit_mc_sims"] = int(st.number_input(
                "MC シミュレーション数",
                value=st.session_state["edit_mc_sims"],
                step=1000, min_value=1000, key="_w_mc_sims"))

        # ── 類似会社ボラティリティ参照 ────────────────
        _show_comparable_vol_selector(case_id)

        st.divider()

        # ── アクションボタン（フォーム外） ────────────
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

        with btn_col1:
            calc_btn = st.button("?? 再計算", type="primary", use_container_width=True)
        with btn_col2:
            save_btn = st.button("?? 保存", use_container_width=True)
        with btn_col3:
            new_name_input = st.text_input("別名保存ケース名", value="",
                                            key="_w_new_name",
                                            label_visibility="collapsed",
                                            placeholder="新しいケース名")
            saveas_btn = st.button("?? 別名保存", use_container_width=True)
        with btn_col4:
            del_btn = st.button("??? 削除", type="secondary", use_container_width=True)

        edited = _read_edit_state()
        svc    = _get_service()

        # ── 再計算 ────────────────────────────────────
        if calc_btn:
            with st.spinner("計算中..."):
                try:
                    params = _build_params(edited)
                    result = svc.calculate(params)
                    st.session_state["edit_result"]       = result
                    st.session_state["edit_result_dirty"] = False
                    st.success("? 再計算完了。「?? 評価結果」タブで確認できます。")
                except Exception as e:
                    st.error(f"計算エラー: {e}")
                    st.code(traceback.format_exc())

        # ── 保存 ──────────────────────────────────────
        if save_btn:
            try:
                params = _build_params(edited)
                svc.update_case(case_id, params)
                st.success("? 保存しました。")
                st.session_state["edit_result_dirty"] = True
            except Exception as e:
                st.error(f"保存エラー: {e}")
                st.code(traceback.format_exc())

        # ── 別名保存 ──────────────────────────────────
        if saveas_btn:
            name = new_name_input.strip() or f"{edited['case_name']}_copy"
            try:
                params = _build_params(edited, name)
                result = svc.calculate(params)
                svc.save(p=params, r=result)
                st.success(f"? 「{name}」として保存しました。")
            except Exception as e:
                st.error(f"別名保存エラー: {e}")
                st.code(traceback.format_exc())

        # ── 削除 ──────────────────────────────────────
        if del_btn:
            try:
                svc.delete_case(case_id)
                st.success("??? 削除しました。")
                st.session_state["current_page"]    = "home"
                st.session_state["detail_case_id"]  = None
                st.rerun()
            except Exception as e:
                st.error(f"削除エラー: {e}")
                st.code(traceback.format_exc())

        # ── 現在のパラメータで計算結果をプレビュー ────
        result = st.session_state.get("edit_result")
        if result:
            st.divider()
            st.subheader("最新計算結果プレビュー")
            if st.session_state.get("edit_result_dirty"):
                st.warning("?? パラメータが変更されています。再計算してください。")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("BS 価格",      f"\{result.bs_price:,.2f}")
            m2.metric("二項式価格",   f"\{result.binomial_price:,.2f}")
            m3.metric("MC 価格",      f"\{result.mc_price:,.2f}")
            m4.metric("加重平均価格", f"\{result.weighted_price:,.2f}")
        else:
            st.info("?? 「?? 再計算」ボタンを押すと評価結果が表示されます。")

    # ????????????????????????????????????????
    # タブ 2: 評価結果
    # ????????????????????????????????????????
    with tab_result:
        result = st.session_state.get("edit_result")

        if result is None:
            st.info("タブ1で「?? 再計算」を実行してください。")
        else:
            if st.session_state.get("edit_result_dirty"):
                st.warning("?? パラメータが変更されています。タブ1で再計算してください。")

            # 価格サマリー
            st.subheader("?? 価格サマリー")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("BS 価格",      f"\{result.bs_price:,.2f}")
            m2.metric("二項式価格",   f"\{result.binomial_price:,.2f}")
            m3.metric("MC 価格",      f"\{result.mc_price:,.2f}")
            m4.metric("加重平均価格", f"\{result.weighted_price:,.2f}")

            st.divider()

            # Greeks
            st.subheader("?? Greeks (BS)")
            g1, g2, g3, g4, g5 = st.columns(5)
            g1.metric("Delta", f"{result.delta:.4f}")
            g2.metric("Gamma", f"{result.gamma:.6f}")
            g3.metric("Theta", f"{result.theta:.4f}")
            g4.metric("Vega",  f"{result.vega:.4f}")
            g5.metric("Rho",   f"{result.rho:.4f}")

            st.divider()

            # 詳細
            with st.expander("?? ブラック・ショールズ 計算詳細", expanded=False):
                _show_scalars(result.bs_detail or {})

            with st.expander("?? 二項モデル 計算詳細", expanded=False):
                d_bin = result.bin_detail or {}
                _show_scalars(d_bin) if d_bin else st.info("データなし")
                _show_list_items(d_bin)

            with st.expander("?? モンテカルロ 計算詳細", expanded=False):
                d_mc = result.mc_detail or {}
                if d_mc:
                    _show_scalars(d_mc, skip=("ST_hist", "payoff_hist"))
                    payoffs = d_mc.get("payoff_hist", [])
                    if payoffs:
                        st.markdown("**ペイオフ分布プレビュー**")
                        _plot_mc_histogram(payoffs, result.mc_price)
                else:
                    st.info("データなし")

    # ????????????????????????????????????????
    # タブ 3: MC ヒストグラム
    # ????????????????????????????????????????
    with tab_mc:
        st.subheader("?? モンテカルロ シミュレーション（フル実行）")

        if st.button("? シミュレーション実行", type="primary"):
            with st.spinner("計算中..."):
                try:
                    edited  = _read_edit_state()
                    params  = _build_params(edited)
                    res     = _get_service().calculate(params)
                    mc      = res.mc_detail or {}
                    payoffs = mc.get("payoff_hist", [])

                    if payoffs:
                        _plot_mc_histogram(payoffs, res.mc_price)
                    else:
                        st.warning("ペイオフデータが取得できませんでした。")

                    r1c1, r1c2, r1c3 = st.columns(3)
                    r1c1.metric("MC 価格",     f"\{res.mc_price:,.2f}")
                    r1c2.metric("95% CI 下限", f"\{mc.get('ci95_lower', 0):,.2f}")
                    r1c3.metric("95% CI 上限", f"\{mc.get('ci95_upper', 0):,.2f}")

                    r2c1, r2c2, r2c3 = st.columns(3)
                    r2c1.metric("ITM 比率",        f"{mc.get('itm_ratio', 0):.1%}")
                    r2c2.metric("標準誤差",         f"{mc.get('std_error', 0):.4f}")
                    r2c3.metric("シミュレーション数", f"{mc.get('n_simulations', 0):,}")

                except Exception as e:
                    st.error(f"? MC エラー: {e}")
                    st.code(traceback.format_exc())

    # ── 戻るボタン ────────────────────────────────
    st.divider()
    if st.button("← ホームに戻る"):
        st.session_state["current_page"]   = "home"
        st.session_state["detail_case_id"] = None
        st.rerun()


# ─────────────────────────────────────────
# 類似会社ボラティリティ選択UI
# ─────────────────────────────────────────
def _show_comparable_vol_selector(case_id: int) -> None:
    """
    類似会社一覧を表示し、選択したボラティリティを
    edit_vol に反映してページを再描画する。
    """
    svc = _get_service()
    try:
        tickers = svc.get_comparable_tickers(case_id)
    except Exception:
        tickers = []

    if not tickers:
        return

    st.markdown("---")
    st.markdown("**?? 類似会社ボラティリティ参照**")

    rows = []
    for t in tickers:
        vol = t.get("volatility") or t.get("vol")
        if vol is not None:
            rows.append({
                "ticker":     t.get("ticker", ""),
                "company":    t.get("company_label") or t.get("ticker", ""),
                "volatility": float(vol),
            })

    if not rows:
        st.caption("ボラティリティデータがある類似会社がありません。")
        return

    cols = st.columns([2, 2, 2, 1])
    cols[0].markdown("**ティッカー**")
    cols[1].markdown("**会社名**")
    cols[2].markdown("**ボラティリティ**")
    cols[3].markdown("**適用**")

    for row in rows:
        c0, c1, c2, c3 = st.columns([2, 2, 2, 1])
        c0.write(row["ticker"])
        c1.write(row["company"])
        c2.write(f"{row['volatility']:.1%}")
        btn_key = f"apply_vol_{row['ticker']}_{case_id}"
        if c3.button("↑ 適用", key=btn_key):
            # ★ ここが核心：session_stateを直接書き換えてrerun
            st.session_state["edit_vol"] = row["volatility"]
            st.rerun()


def render() -> None:
    show()
