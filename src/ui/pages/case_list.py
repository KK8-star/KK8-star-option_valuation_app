"""
src/ui/pages/case_list.py - 評価ケース一覧ページ
"""
from __future__ import annotations

import streamlit as st
from sqlalchemy import func, select

from src.data.database import get_session
from src.data.models import ValuationCase, ComparableTicker


def _search_cases(keyword: str) -> list[dict]:
    """キーワードで評価ケースを検索"""
    with get_session() as session:
        stmt = (
            select(ValuationCase)
            .order_by(ValuationCase.created_at.desc())
        )
        if keyword:
            stmt = stmt.where(
                ValuationCase.case_name.ilike(f"%{keyword}%")
            )
        rows = session.scalars(stmt).all()
        return [
            {
                "id":         vc.id,
                "case_name":  vc.case_name,
                "created_at": vc.created_at,
                "updated_at": vc.updated_at,
            }
            for vc in rows
        ]


def _delete_case(case_id: int) -> None:
    """ケースを物理削除"""
    with get_session() as session:
        vc = session.get(ValuationCase, case_id)
        if vc:
            session.delete(vc)
            session.commit()


def render() -> None:
    st.title("?? ケース一覧")

    # 検索バー
    keyword = st.text_input("?? ケース名で検索", placeholder="例: ABC社")

    try:
        cases = _search_cases(keyword)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return

    # サマリーメトリクス
    try:
        with get_session() as session:
            total_cases: int = session.scalar(
                select(func.count(ValuationCase.id))
            ) or 0
            total_tickers: int = session.scalar(
                select(func.count(ComparableTicker.id))
            ) or 0
    except Exception:
        total_cases = len(cases)
        total_tickers = 0

    col1, col2 = st.columns(2)
    col1.metric("?? 総ケース数", total_cases)
    col2.metric("?? 比較ティッカー数", total_tickers)

    st.divider()

    if not cases:
        st.info("評価ケースが見つかりません。")
        return

    # selected_case_id が session_state にある場合は詳細へ
    if "selected_case_id" in st.session_state:
        selected_id = st.session_state.pop("selected_case_id")
        st.session_state["detail_case_id"] = selected_id

    # 詳細表示中
    if "detail_case_id" in st.session_state:
        from src.ui.pages import case_detail
        case_detail.render(st.session_state["detail_case_id"])
        if st.button("← 一覧に戻る"):
            del st.session_state["detail_case_id"]
            st.rerun()
        return

    # 一覧表示
    for case in cases:
        with st.container(border=True):
            col_a, col_b, col_c, col_d = st.columns([4, 2, 1, 1])

            col_a.markdown(f"**{case['case_name']}**")

            created = case["created_at"]
            updated = case["updated_at"]
            col_b.caption(
                f"作成: {created.strftime('%Y-%m-%d') if created else '-'}  \n"
                f"更新: {updated.strftime('%Y-%m-%d') if updated else '-'}"
            )

            with col_c:
                if st.button("詳細", key=f"list_detail_{case['id']}"):
                    st.session_state["detail_case_id"] = case["id"]
                    st.rerun()

            with col_d:
                if st.button("???", key=f"list_del_{case['id']}",
                             help="このケースを削除"):
                    _delete_case(case["id"])
                    st.success("削除しました")
                    st.rerun()
