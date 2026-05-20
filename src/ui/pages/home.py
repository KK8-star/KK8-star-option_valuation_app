# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
from pathlib import Path
from src.data.database import DatabaseManager
from src.data.models import ValuationCase


def show() -> None:

    # ── ロゴ（ページ上部中央） ─────────────────────────────────────────
    logo_path = Path("assets/logo.png")
    if logo_path.exists():
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.image(str(logo_path), use_container_width=True)
        st.markdown("")          # 余白
    # ─────────────────────────────────────────────────────────────────

    st.title("ホーム")
    st.markdown("### 直近の評価結果（最新3件）")

    # DBから直接取得
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

            if not cases:
                st.info("まだ計算済みのケースがありません。ケース一覧からケースを作成・計算してください。")
            else:
                for c in cases:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 2])
                        with col1:
                            st.markdown(f"**{c.case_name}**")
                            st.caption(
                                f"作成日時: {c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else '不明'}"
                            )
                        with col2:
                            st.metric("BS価格", f"{c.bs_price:.4f}")
                        with col3:
                            if c.mc_price is not None:
                                st.caption(f"MC価格: {c.mc_price:.4f}")
                            if st.button("詳細を見る", key=f"home_detail_{c.id}"):
                                st.session_state["detail_case_id"] = c.id
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
