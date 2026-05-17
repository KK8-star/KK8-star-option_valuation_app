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


def render_calculation_detail(params: dict, result) -> None:
    import pandas as pd
    import plotly.graph_objects as go
    import numpy as _np

    S     = params.get("stock_price", 0)
    K     = params.get("strike_price", 0)
    T     = params.get("time_to_expiry", 0)
    r     = params.get("risk_free_rate", 0)
    sigma = params.get("volatility", 0)
    q     = params.get("dividend_yield", 0.0)
    otype = params.get("option_type", "call")
    bs    = getattr(result, "bs_detail",  {}) or {}
    bn    = getattr(result, "bin_detail", {}) or {}
    mc    = getattr(result, "mc_detail",  {}) or {}

    with st.expander("計算プロセス詳細", expanded=False):
        tab_bs, tab_bin, tab_mc = st.tabs([
            "ブラック・ショールズ法",
            "二項モデル法",
            "モンテカルロ法",
        ])

        # ── TAB 1: Black-Scholes ──────────────────────────────
        with tab_bs:
            st.markdown("### Black-Scholes (Merton拡張) 計算プロセス")
            st.markdown("#### 入力パラメータ")
            c1, c2, c3 = st.columns(3)
            c1.metric("株価 S",          f"{S:,.0f}")
            c1.metric("権利行使価格 K",   f"{K:,.0f}")
            c2.metric("残存期間 T",       f"{T:.4f} 年")
            c2.metric("無リスク金利 r",   f"{r*100:.3f} %")
            c3.metric("ボラティリティ σ", f"{sigma*100:.2f} %")
            c3.metric("配当利回り q",     f"{q*100:.3f} %")
            st.divider()

            if bs:
                d1_val  = bs.get("d1", 0)
                d2_val  = bs.get("d2", 0)
                log_SK  = bs.get("log_SK", 0)
                sig_sT  = bs.get("sigma_sqrtT", 0)
                eqT     = bs.get("exp_qT", 1)
                erT     = bs.get("exp_rT", 1)
                Nd1     = bs.get("Nd1",  0)
                Nd2     = bs.get("Nd2",  0)
                Nnd1    = bs.get("Nnd1", 0)
                Nnd2    = bs.get("Nnd2", 0)
                nd1     = bs.get("nd1",  0)

                st.markdown("#### d1・d2 の計算")
                st.latex(
                    r"d_1 = \frac{\ln(S/K) + (r - q + \frac{1}{2}\sigma^2) \cdot T}{\sigma\sqrt{T}}"
                )
                numerator = log_SK + (r - q + 0.5 * sigma ** 2) * T
                st.code(
                    f"ln(S/K)   = ln({S:.2f}/{K:.2f}) = {log_SK:.6f}\n"
                    f"sigmaRootT = {sigma:.4f} x sqrt({T:.4f}) = {sig_sT:.6f}\n"
                    f"numerator  = {log_SK:.6f} + ({r:.4f}-{q:.4f}+0.5x{sigma:.4f}^2)x{T:.4f} = {numerator:.6f}\n"
                    f"d1         = {numerator:.6f} / {sig_sT:.6f} = {d1_val:.6f}\n"
                    f"d2         = d1 - sigmaRootT = {d1_val:.6f} - {sig_sT:.6f} = {d2_val:.6f}",
                    language="text"
                )
                st.divider()

                st.markdown("#### 標準正規分布 累積確率")
                st.dataframe(pd.DataFrame({
                    "変数":       ["d1", "d2", "-d1", "-d2", "n(d1)密度"],
                    "数値":       [f"{d1_val:.6f}", f"{d2_val:.6f}",
                                   f"{-d1_val:.6f}", f"{-d2_val:.6f}", "—"],
                    "分布値":     [f"N(d1)={Nd1:.6f}", f"N(d2)={Nd2:.6f}",
                                   f"N(-d1)={Nnd1:.6f}", f"N(-d2)={Nnd2:.6f}",
                                   f"n(d1)={nd1:.6f}"],
                }), use_container_width=True, hide_index=True)
                st.divider()

                st.markdown("#### オプション価格の展開")
                if otype == "call":
                    st.latex(r"C = S \cdot e^{-qT} \cdot N(d_1) - K \cdot e^{-rT} \cdot N(d_2)")
                    t1 = S * eqT * Nd1
                    t2 = K * erT * Nd2
                    st.code(
                        f"term1 = {S:.2f} x {eqT:.6f} x {Nd1:.6f} = {t1:.4f}\n"
                        f"term2 = {K:.2f} x {erT:.6f} x {Nd2:.6f} = {t2:.4f}\n"
                        f"Call  = {t1:.4f} - {t2:.4f} = {t1-t2:.4f}",
                        language="text"
                    )
                else:
                    st.latex(r"P = K \cdot e^{-rT} \cdot N(-d_2) - S \cdot e^{-qT} \cdot N(-d_1)")
                    t1 = K * erT * Nnd2
                    t2 = S * eqT * Nnd1
                    st.code(
                        f"term1 = {K:.2f} x {erT:.6f} x {Nnd2:.6f} = {t1:.4f}\n"
                        f"term2 = {S:.2f} x {eqT:.6f} x {Nnd1:.6f} = {t2:.4f}\n"
                        f"Put   = {t1:.4f} - {t2:.4f} = {t1-t2:.4f}",
                        language="text"
                    )
                st.divider()

                st.markdown("#### Greeks（感応度指標）")
                g1, g2, g3 = st.columns(3)
                g1.metric("Delta", f"{bs.get('delta',0):.6f}")
                g1.metric("Gamma", f"{bs.get('gamma',0):.8f}")
                g2.metric("Vega",  f"{bs.get('vega',0):.6f}")
                g2.metric("Theta", f"{bs.get('theta',0):.6f}")
                g3.metric("Rho",   f"{bs.get('rho',0):.6f}")
            else:
                st.info("計算詳細データがありません（T=0 または sigma=0）")

        # ── TAB 2: 二項モデル ─────────────────────────────────
        with tab_bin:
            st.markdown("### Cox-Ross-Rubinstein (CRR) 二項モデル 計算プロセス")

            if bn:
                dt   = bn.get("dt", 0)
                u    = bn.get("u", 0)
                d    = bn.get("d", 0)
                p_up = bn.get("p_up", 0)
                p_dn = bn.get("p_down", 0)
                disc = bn.get("discount", 0)
                N    = bn.get("steps", 0)

                st.markdown("#### ツリーパラメータ")
                b1, b2, b3 = st.columns(3)
                b1.metric("ステップ数 N",    f"{N}")
                b1.metric("dt (1ステップ)",  f"{dt:.6f} 年")
                b2.metric("上昇率 u",         f"{u:.6f}")
                b2.metric("下落率 d",         f"{d:.6f}")
                b3.metric("上昇確率 p",       f"{p_up:.6f}")
                b3.metric("割引因子",         f"{disc:.6f}")
                st.divider()

                st.markdown("#### パラメータ計算式")
                st.latex(r"\Delta t = T/N,\quad u = e^{\sigma\sqrt{\Delta t}},\quad d = 1/u")
                st.latex(r"p = \frac{e^{(r-q)\Delta t} - d}{u - d}")
                st.code(
                    f"dt  = {T:.4f} / {N} = {dt:.6f}\n"
                    f"u   = exp({sigma:.4f} x sqrt({dt:.6f})) = {u:.6f}\n"
                    f"d   = 1/{u:.6f} = {d:.6f}\n"
                    f"p   = (exp(({r:.4f}-{q:.4f})x{dt:.6f}) - {d:.6f}) / ({u:.6f}-{d:.6f}) = {p_up:.6f}\n"
                    f"1-p = {p_dn:.6f}\n"
                    f"disc= exp(-{r:.4f}x{dt:.6f}) = {disc:.6f}",
                    language="text"
                )
                st.divider()

                st.markdown("#### 満期時の株価・ペイオフ（サンプル）")
                t_prices  = bn.get("terminal_prices_sample", [])
                t_payoffs = bn.get("terminal_payoffs_sample", [])
                rows = []
                for i, (pr, pf) in enumerate(zip(t_prices, t_payoffs)):
                    if pr == "...":
                        rows.append({"ノード": "...", "末端株価": "...", "ペイオフ": "..."})
                    else:
                        rows.append({
                            "ノード":   str(i if i < 5 else f"N-{9-i}"),
                            "末端株価": f"{pr:,.2f}",
                            "ペイオフ": f"{pf:,.4f}",
                        })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                c1, c2, c3 = st.columns(3)
                c1.metric("最高末端株価", f"{bn.get('max_terminal_price',0):,.0f}")
                c2.metric("最低末端株価", f"{bn.get('min_terminal_price',0):,.0f}")
                c3.metric("ITMノード数",  f"{bn.get('n_itm',0)} / {N+1}")
                st.divider()

                st.markdown("#### バックワードインダクション（後退法）")
                st.latex(r"V_i = e^{-r\Delta t}[p \cdot V_{i+1}^{up} + (1-p) \cdot V_{i+1}^{down}]")
                bs_price  = getattr(result, "bs_price", 0) or 0
                bin_price = getattr(result, "binomial_price", 0) or 0
                st.info(
                    f"ステップ {N} -> 0 の方向に後退計算を {N} 回繰り返します。\n"
                    f"二項モデル価格: {bin_price:,.4f}"
                )
            else:
                st.info("計算詳細データがありません（T=0 または sigma=0）")

        # ── TAB 3: モンテカルロ ───────────────────────────────
        with tab_mc:
            st.markdown("### モンテカルロ・シミュレーション 計算プロセス")

            if mc:
                n_sim   = mc.get("n_simulations", 0)
                mean_ST = mc.get("mean_ST", 0)
                std_ST  = mc.get("std_ST", 0)
                min_ST  = mc.get("min_ST", 0)
                max_ST  = mc.get("max_ST", 0)
                n_itm   = mc.get("n_itm", 0)
                itm_r   = mc.get("itm_ratio", 0)
                m_pay   = mc.get("mean_payoff", 0)
                s_pay   = mc.get("std_payoff", 0)
                disc_f  = mc.get("discount_factor", 1)
                std_err = mc.get("std_error", 0)
                ci_lo   = mc.get("ci95_lower", 0)
                ci_hi   = mc.get("ci95_upper", 0)

                st.markdown("#### シミュレーション設定")
                st.latex(
                    r"S_T = S \cdot e^{(r-q-\frac{1}{2}\sigma^2)T + \sigma\sqrt{T} \cdot Z},\quad Z \sim N(0,1)"
                )
                m1, m2, m3 = st.columns(3)
                m1.metric("シミュレーション回数", f"{n_sim:,}")
                m2.metric("割引因子 e^(-rT)",      f"{disc_f:.6f}")
                m3.metric("ドリフト (r-q-0.5sigma^2)T",
                          f"{(r - q - 0.5*sigma**2)*T:.6f}")
                st.divider()

                st.markdown("#### シミュレーション結果統計")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**末端株価 S_T**")
                    st.dataframe(pd.DataFrame({
                        "統計量": ["平均", "標準偏差", "最小値", "最大値"],
                        "値":     [f"{mean_ST:,.2f}", f"{std_ST:,.2f}",
                                   f"{min_ST:,.2f}", f"{max_ST:,.2f}"],
                    }), use_container_width=True, hide_index=True)
                with col_b:
                    st.markdown("**ペイオフ統計**")
                    st.dataframe(pd.DataFrame({
                        "統計量": ["ITM回数", "ITM割合", "平均ペイオフ", "SD"],
                        "値":     [f"{n_itm:,}", f"{itm_r*100:.2f}%",
                                   f"{m_pay:,.4f}", f"{s_pay:,.4f}"],
                    }), use_container_width=True, hide_index=True)
                st.divider()

                st.markdown("#### オプション価格の算出")
                st.latex(
                    r"\hat{C} = e^{-rT} \cdot \frac{1}{N}\sum_{i=1}^{N}\max(S_T^{(i)}-K,\,0)"
                )
                mc_price = getattr(result, "mc_price", 0) or 0
                st.code(
                    f"割引因子         = e^(-{r:.4f}x{T:.4f}) = {disc_f:.6f}\n"
                    f"平均ペイオフ     = {m_pay:.6f}\n"
                    f"MC価格推定値     = {disc_f:.6f} x {m_pay:.6f} = {disc_f*m_pay:.4f}\n"
                    f"標準誤差 SE      = {s_pay:.4f} / sqrt({n_sim}) = {std_err:.6f}\n"
                    f"95%信頼区間      = [{ci_lo:.4f}, {ci_hi:.4f}]",
                    language="text"
                )
                st.divider()

                # ヒストグラム
                ST_hist = mc.get("ST_hist", [])
                if ST_hist:
                    st.markdown("#### 末端株価 S_T 分布")
                    arr = _np.array(ST_hist, dtype=float)
                    counts, edges = _np.histogram(arr, bins=60)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=edges[:-1].tolist(), y=counts.tolist(),
                        marker_color="steelblue", opacity=0.75, name="S_T"
                    ))
                    fig.add_vline(x=float(K), line_dash="dash",
                                  line_color="red",
                                  annotation_text=f"K={K:,.0f}",
                                  annotation_position="top left",
                                  annotation_yshift=0)
                    fig.add_vline(x=float(mean_ST), line_dash="dot",
                                  line_color="green",
                                  annotation_text=f"mean={mean_ST:,.0f}",
                                  annotation_position="top right",
                                  annotation_yshift=-20)
                    fig.update_layout(
                        title="末端株価分布", xaxis_title="S_T",
                        yaxis_title="頻度", height=350,
                        template="plotly_white"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                pay_hist = mc.get("payoff_hist", [])
                if pay_hist:
                    st.markdown("#### ペイオフ分布（ITM部分）")
                    arr_p   = _np.array(pay_hist, dtype=float)
                    itm_arr = arr_p[arr_p > 0]
                    if len(itm_arr) > 0:
                        counts2, edges2 = _np.histogram(itm_arr, bins=50)
                        fig2 = go.Figure()
                        fig2.add_trace(go.Bar(
                            x=edges2[:-1].tolist(), y=counts2.tolist(),
                            marker_color="darkorange", opacity=0.75, name="ペイオフ"
                        ))
                        fig2.add_vline(
                            x=float(_np.mean(itm_arr)), line_dash="dash",
                            line_color="red",
                            annotation_text=f"平均={_np.mean(itm_arr):,.0f}",
                            annotation_position="top right",
                            annotation_yshift=0
                        )
                        fig2.update_layout(
                            title="ITMペイオフ分布", xaxis_title="ペイオフ",
                            yaxis_title="頻度", height=320,
                            template="plotly_white"
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.warning("ITMシナリオ0件（ディープOTM）")

                st.divider()
                st.markdown("#### 推定精度サマリー")
                st.info(
                    f"推定価格: {disc_f*m_pay:,.4f}  |  "
                    f"標準誤差: +/-{std_err:.4f}  |  "
                    f"95%信頼区間: [{ci_lo:.4f} - {ci_hi:.4f}]  |  "
                    f"区間幅: {ci_hi-ci_lo:.4f}  (n={n_sim:,})"
                )
            else:
                st.info("計算詳細データがありません（T=0 または sigma=0）")



