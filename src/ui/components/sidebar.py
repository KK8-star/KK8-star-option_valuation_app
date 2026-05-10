"""サイドバーコンポーネント"""
import streamlit as st


def render_sidebar() -> dict:
    """
    サイドバーを描画し、選択されたページ情報を返す

    Returns:
        dict: {"page": ページ名}
    """
    with st.sidebar:
        st.title("📊 オプション評価")
        st.caption("非上場企業株式評価システム")
        st.divider()

        page = st.radio(
            "メニュー",
            options=[
                "🏠 ホーム",
                "🔢 新規評価",
                "📁 評価案件一覧",
                "📈 結果・グラフ",
                "⚙️ 設定",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        st.caption("v1.0.0 | Python 3.12")

    return {"page": page}
