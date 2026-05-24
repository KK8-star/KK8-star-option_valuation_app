# -*- coding: utf-8 -*-
# src/ui/pages/home.py
from __future__ import annotations

import streamlit as st
from pathlib import Path
from src.data.database import DatabaseManager
from src.data.models import ValuationCase


def show() -> None:
    logo_path = Path("assets/logo.png")
    if logo_path.exists():
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.image(str(logo_path), use_container_width=True)
        st.markdown("")

    st.title("ホーム")
    st.markdown("### 直近の評価結果（最新3件）")

    try:
        db = DatabaseManager()
        with db.get_session() as session:
            cases = (
                session.query(ValuationCase)
                .filter(ValuationCase.bs_price.isnot(None))
                .order_by(ValuationCase.created_at.desc())
                .limit(3)
                .all()
            )
            cases_data = []
            for c in cases:
                cases_data.append({
                    "id":             c.id,
                    "case_name":      c.case_name,
                    "created_at":     c.created_at,
                    "bs_price":       c.bs_price,
                    "binomial_price": c.binomial_price,
                    "mc_price":       c.mc_price,
                    "weighted_price": c.weighted_price,
                    "option_type":    c.option_type,
                })

        if not cases_data:
            st.info("まだ計算済みのケースがありません。新規評価からケースを作成してください。")
        else:
            for c in cases_data:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                    with col1:
                        st.markdown(f"**{c['case_name']}**")
                        created = c["created_at"]
                        st.caption(
                            f"作成日時: {created.strftime('%Y-%m-%d %H:%M') if created else '不明'}"
                        )
                        st.caption(f"種類: {c.get('option_type', '')}")
                    with col2:
                        bs = c["bs_price"]
                        st.metric("BS価格", f"{bs:.4f}" if bs is not None else "N/A")
                    with col3:
                        binom = c["binomial_price"]
                        st.metric("二項価格", f"{binom:.4f}" if binom is not None else "N/A")
                    with col4:
                        mc = c["mc_price"]
                        st.metric("MC価格", f"{mc:.4f}" if mc is not None else "N/A")
                    with col5:
                        if st.button("詳細", key=f"home_detail_{c['id']}", type="primary"):
                            st.session_state["detail_case_id"] = c["id"]
                            st.session_state["current_page"] = "case_detail"
                            st.rerun()
                    st.divider()

    except Exception as e:
        st.error(f"データ取得エラー: {e}")

    st.markdown("---")
    st.markdown("### クイックスタート")
    if st.button("新しいケースを作成する", type="primary"):
        st.session_state["current_page"] = "new_valuation"
        st.rerun()


def render() -> None:
    show()
