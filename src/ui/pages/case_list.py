# -*- coding: utf-8 -*-
# src/ui/pages/case_list.py
from __future__ import annotations
import streamlit as st
import pandas as pd
from src.services.valuation_service import ValuationService

_svc = ValuationService()


def _open_detail(case_id: int) -> None:
    """詳細ページへ遷移するヘルパー"""
    st.session_state["detail_case_id"] = case_id
    st.session_state["current_page"]   = "case_detail"  # ✅ 修正
    st.rerun()


def show() -> None:
    st.title("📋 ケース一覧")

    # ── 全ケース取得（作成日時降順）────────────────────────────
    cases = _svc.get_all_cases()

    # ── ヘッダー行 ────────────────────────────────────────────
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.markdown(f"登録ケース数: **{len(cases)}** 件")
    with col_refresh:
        if st.button("🔄 更新", use_container_width=True):
            st.rerun()

    st.markdown("---")

    if not cases:
        st.info("ケースがありません。「➕ 新規評価」から作成してください。")
        return

    # ── ケース一覧テーブル ─────────────────────────────────────
    summary_rows = []
    for c in cases:
        weighted = c.get("weighted_price")
        bs       = c.get("bs_price")
        summary_rows.append({
            "ID":           c["id"],
            "ケース名":     c["case_name"],
            "加重平均価格": f"{weighted:.4f}" if weighted is not None else "未計算",
            "BS価格":       f"{bs:.4f}"       if bs       is not None else "未計算",
            "オプション種類": c.get("option_type", ""),
            "株価 S":       f"{c.get('stock_price', 0):.1f}",
            "行使価格 K":   f"{c.get('strike_price', 0):.1f}",
            "作成日時":     str(c.get("created_at", "")),
        })

    df = pd.DataFrame(summary_rows)
    st.dataframe(
        df.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    # ── 詳細ボタン（カード形式）───────────────────────────────
    st.markdown("### ケース詳細を開く")

    for c in cases:
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])

            with c1:
                st.markdown(f"**{c['case_name']}**")
                st.caption(f"作成: {c.get('created_at', '')}")

            with c2:
                wp = c.get("weighted_price")
                st.metric(
                    "加重平均価格",
                    f"{wp:.2f}" if wp is not None else "N/A",
                )

            with c3:
                bs = c.get("bs_price")
                st.metric(
                    "BS価格",
                    f"{bs:.2f}" if bs is not None else "N/A",
                )

            with c4:
                st.caption(f"種類: {c.get('option_type','')}")
                st.caption(f"S={c.get('stock_price',0):.1f}  K={c.get('strike_price',0):.1f}")

            with c5:
                if st.button(
                    "📂 詳細",
                    key=f"open_{c['id']}",
                    use_container_width=True,
                    type="primary",
                ):
                    _open_detail(c["id"])

            st.divider()


def render() -> None:
    show()
