"""
src/ui/pages/home.py - ホームページ
"""
from __future__ import annotations

import streamlit as st
from sqlalchemy import func, select

from src.data.database import get_session
from src.data.models import ValuationCase, ComparableTicker


def render() -> None:
    st.title("🏠 非上場会社向けオプション評価システム")


    try:
        with get_session() as session:
            # 評価ケース総数
            total_cases: int = session.scalar(
                select(func.count(ValuationCase.id))
            ) or 0

            # 比較ティッカー総数
            total_tickers: int = session.scalar(
                select(func.count(ComparableTicker.id))
            ) or 0

            # 最新5件
            recent_rows = session.execute(
                select(
                    ValuationCase.id,
                    ValuationCase.case_name,
                    ValuationCase.created_at,
                )
                .order_by(ValuationCase.created_at.desc())
                .limit(5)
            ).all()

            recent_data = [
                {
                    "id": r.id,
                    "case_name": r.case_name,
                    "created_at": r.created_at,
                }
                for r in recent_rows
            ]
    except Exception as e:
        st.error(f"データベース接続エラー: {e}")
        return

    # メトリクス
    col1, col2, col3 = st.columns(3)
    col1.metric("📁 評価ケース数", total_cases)
    col2.metric("📊 比較ティッカー数", total_tickers)
    col3.metric("✅ アクティブ", total_cases)

    st.divider()

    # クイックアクション
    st.subheader("クイックアクション")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 新規評価を開始", use_container_width=True, type="primary"):
            st.session_state["current_page"] = "📊 新規評価"
            st.rerun()
    with c2:
        if st.button("📋 評価一覧を見る", use_container_width=True):
            st.session_state["current_page"] = "📋 評価一覧"
            st.rerun()

    st.divider()

    # 最近の評価ケース
    st.subheader("最近の評価ケース（最新5件）")

    if not recent_data:
        st.info("まだ評価ケースがありません。「新規評価」から開始してください。")
        return

    for item in recent_data:
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([3, 3, 1])
            col_a.markdown(f"**{item['case_name']}**")
            col_b.caption(
                f"作成日: {item['created_at'].strftime('%Y-%m-%d %H:%M')}"
                if item["created_at"] else "作成日: -"
            )
            with col_c:
                if st.button("詳細", key=f"home_detail_{item['id']}"):
                    st.session_state["current_page"] = "📋 評価一覧"
                    st.session_state["selected_case_id"] = item["id"]
                    st.rerun()
