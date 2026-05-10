"""評価パラメータ入力フォームコンポーネント"""
from __future__ import annotations
import streamlit as st


def render_input_form() -> dict | None:
    """
    オプション評価パラメータ入力フォームを描画する

    Returns:
        dict | None: 入力値の辞書。送信されていない場合は None
    """
    st.subheader("📋 評価パラメータ入力")

    with st.form("valuation_form"):
        # ─── 案件基本情報 ────────────────────────────
        st.markdown("#### 案件基本情報")
        col1, col2 = st.columns(2)
        with col1:
            case_name = st.text_input(
                "案件名 *",
                placeholder="例: A社 ストックオプション評価",
                help="案件を識別する名称を入力してください",
            )
            company = st.text_input(
                "対象会社名 *",
                placeholder="例: 株式会社〇〇",
            )
        with col2:
            industry = st.selectbox(
                "業種",
                options=[
                    "technology", "biotech", "fintech",
                    "saas", "ecommerce", "manufacturing",
                    "real_estate", "other",
                ],
                format_func=lambda x: {
                    "technology": "テクノロジー",
                    "biotech": "バイオテック",
                    "fintech": "フィンテック",
                    "saas": "SaaS",
                    "ecommerce": "Eコマース",
                    "manufacturing": "製造業",
                    "real_estate": "不動産",
                    "other": "その他",
                }.get(x, x),
            )
            stage = st.selectbox(
                "ステージ",
                options=[
                    "seed", "pre_series_a", "series_a",
                    "series_b", "series_c", "pre_ipo",
                ],
                format_func=lambda x: {
                    "seed": "シード",
                    "pre_series_a": "プレシリーズA",
                    "series_a": "シリーズA",
                    "series_b": "シリーズB",
                    "series_c": "シリーズC",
                    "pre_ipo": "プレIPO",
                }.get(x, x),
            )

        st.divider()

        # ─── オプションパラメータ ─────────────────────
        st.markdown("#### オプションパラメータ")
        col3, col4, col5 = st.columns(3)
        with col3:
            stock_price = st.number_input(
                "株価 (S) [円]",
                min_value=1.0,
                max_value=1_000_000_000.0,
                value=1_000_000.0,
                step=10_000.0,
                format="%,.0f",
                help="現在の株式価値（1株あたり）",
            )
            strike_price = st.number_input(
                "行使価格 (K) [円]",
                min_value=1.0,
                max_value=1_000_000_000.0,
                value=1_200_000.0,
                step=10_000.0,
                format="%,.0f",
                help="オプション行使価格",
            )
        with col4:
            time_to_expiry = st.number_input(
                "残存期間 (T) [年]",
                min_value=0.1,
                max_value=10.0,
                value=3.0,
                step=0.5,
                format="%.1f",
                help="オプションの残存年数",
            )
            risk_free_rate = st.number_input(
                "無リスク金利 (r) [%]",
                min_value=0.0,
                max_value=20.0,
                value=0.5,
                step=0.1,
                format="%.2f",
                help="日本国債利回り等を参考に設定",
            )
        with col5:
            volatility = st.number_input(
                "ボラティリティ (σ) [%]",
                min_value=1.0,
                max_value=300.0,
                value=60.0,
                step=5.0,
                format="%.1f",
                help="年率ボラティリティ（類似上場企業またはVC法で推定）",
            )
            option_type = st.selectbox(
                "オプション種別",
                options=["call", "put"],
                format_func=lambda x: "コールオプション" if x == "call" else "プットオプション",
            )

        st.divider()

        # ─── モデル設定 ──────────────────────────────
        st.markdown("#### モデル設定")
        col6, col7 = st.columns(2)
        with col6:
            model_type = st.selectbox(
                "評価モデル",
                options=["black_scholes", "binomial"],
                format_func=lambda x: {
                    "black_scholes": "ブラック・ショールズ法",
                    "binomial": "二項ツリー法（CRR）",
                }.get(x, x),
            )
        with col7:
            if model_type == "binomial":
                american = st.checkbox("アメリカン型（早期行使可能）", value=False)
                n_steps = st.slider("ステップ数", min_value=50, max_value=500, value=200, step=50)
            else:
                american = False
                n_steps = 200

        st.divider()

        # ─── 送信ボタン ──────────────────────────────
        submitted = st.form_submit_button(
            "🔢 評価を実行",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        # バリデーション
        errors = []
        if not case_name.strip():
            errors.append("案件名を入力してください")
        if not company.strip():
            errors.append("対象会社名を入力してください")

        if errors:
            for err in errors:
                st.error(f"❌ {err}")
            return None

        return {
            "case_name": case_name.strip(),
            "company": company.strip(),
            "industry": industry,
            "stage": stage,
            "stock_price": stock_price,
            "strike_price": strike_price,
            "time_to_expiry": time_to_expiry,
            "risk_free_rate": risk_free_rate / 100.0,   # % → 小数
            "volatility": volatility / 100.0,           # % → 小数
            "is_call": option_type == "call",
            "model_type": model_type,
            "american": american,
            "n_steps": n_steps,
        }

    return None
