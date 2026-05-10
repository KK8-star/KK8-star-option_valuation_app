"""評価結果表示コンポーネント"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import numpy as np


def render_result_metrics(result: object) -> None:
    """メインの評価結果メトリクスを表示"""
    st.subheader("📊 評価結果")

    # オプション価格（大きく表示）
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="オプション価格",
            value=f"¥{result.option_price:,.0f}",
            help="算出されたオプション公正価値",
        )
    with col2:
        st.metric(
            label="デルタ (Δ)",
            value=f"{result.delta:.4f}",
            help="株価1円変動に対するオプション価格変動",
        )
    with col3:
        st.metric(
            label="ガンマ (Γ)",
            value=f"{result.gamma:.6f}",
            help="デルタの変化率",
        )
    with col4:
        st.metric(
            label="ベガ (ν)",
            value=f"{result.vega:.4f}",
            help="ボラティリティ1%変動に対する価格変動",
        )

    # セカンダリメトリクス
    col5, col6, col7 = st.columns(3)
    with col5:
        theta_val = result.theta if result.theta is not None else 0.0
        st.metric(
            label="シータ (Θ)",
            value=f"{theta_val:.4f}",
            help="1日経過によるオプション価格変動",
        )
    with col6:
        rho_val = result.rho if result.rho is not None else 0.0
        st.metric(
            label="ロー (ρ)",
            value=f"{rho_val:.4f}",
            help="金利1%変動に対する価格変動",
        )
    with col7:
        model_name = {
            "black_scholes": "BS法",
            "binomial": "二項法",
        }.get(result.model_type, result.model_type)
        st.metric(label="評価モデル", value=model_name)


def render_sensitivity_chart(
    base_result: object,
    model_class: type,
    params: dict,
) -> None:
    """感度分析グラフを描画"""
    st.subheader("📈 感度分析")

    tab1, tab2, tab3 = st.tabs(["株価感度", "ボラティリティ感度", "残存期間感度"])

    S0      = params["stock_price"]
    K       = params["strike_price"]
    T       = params["time_to_expiry"]
    r       = params["risk_free_rate"]
    sigma   = params["volatility"]
    is_call = params["is_call"]

    # ─── Tab1: 株価感度 ──────────────────────────────
    with tab1:
        s_range = np.linspace(S0 * 0.5, S0 * 1.5, 60)
        prices  = []
        deltas  = []
        for s in s_range:
            m = model_class(S=s, K=K, T=T, r=r, sigma=sigma)
            prices.append(m.price(is_call=is_call))
            deltas.append(m.delta(is_call=is_call))

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=s_range, y=prices,
            name="オプション価格",
            line=dict(color="#1f77b4", width=2),
        ))
        fig.add_vline(
            x=S0, line_dash="dash", line_color="red",
            annotation_text=f"現在株価 ¥{S0:,.0f}",
        )
        fig.add_vline(
            x=K, line_dash="dot", line_color="orange",
            annotation_text=f"行使価格 ¥{K:,.0f}",
        )
        fig.update_layout(
            title="株価 vs オプション価格",
            xaxis_title="株価 (円)",
            yaxis_title="オプション価格 (円)",
            height=380,
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ─── Tab2: ボラティリティ感度 ─────────────────────
    with tab2:
        vol_range  = np.linspace(0.10, 1.50, 60)
        vol_prices = [
            model_class(S=S0, K=K, T=T, r=r, sigma=v).price(is_call=is_call)
            for v in vol_range
        ]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=vol_range * 100, y=vol_prices,
            name="オプション価格",
            line=dict(color="#2ca02c", width=2),
        ))
        fig2.add_vline(
            x=sigma * 100, line_dash="dash", line_color="red",
            annotation_text=f"現在σ={sigma*100:.0f}%",
        )
        fig2.update_layout(
            title="ボラティリティ vs オプション価格",
            xaxis_title="ボラティリティ (%)",
            yaxis_title="オプション価格 (円)",
            height=380,
            template="plotly_white",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ─── Tab3: 残存期間感度 ───────────────────────────
    with tab3:
        t_range  = np.linspace(0.25, max(T * 1.5, 5.0), 60)
        t_prices = [
            model_class(S=S0, K=K, T=t, r=r, sigma=sigma).price(is_call=is_call)
            for t in t_range
        ]

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=t_range, y=t_prices,
            name="オプション価格",
            line=dict(color="#ff7f0e", width=2),
        ))
        fig3.add_vline(
            x=T, line_dash="dash", line_color="red",
            annotation_text=f"残存 {T:.1f}年",
        )
        fig3.update_layout(
            title="残存期間 vs オプション価格",
            xaxis_title="残存期間 (年)",
            yaxis_title="オプション価格 (円)",
            height=380,
            template="plotly_white",
        )
        st.plotly_chart(fig3, use_container_width=True)
