import re

new_tab3 = '''    with tab3:
        st.markdown("#### モンテカルロ シミュレーション")
        st.latex(r"S_T = S_0 \\exp\\left[\\left(r - q - \\frac{\\sigma^2}{2}\\right)T + \\sigma\\sqrt{T}\\,Z\\right]")
        if opt == "call":
            st.latex(r"\\text{Payoff} = \\max(S_T - K,\\ 0)")
        else:
            st.latex(r"\\text{Payoff} = \\max(K - S_T,\\ 0)")
        st.latex(r"\\text{Price} = e^{-rT} \\times \\mathbb{E}[\\text{Payoff}]")
        st.success(f"モンテカルロ価格: ¥{float(case[\'mc_price\']):,.4f}  ({M:,}回シミュレーション)")
        st.info(f"標準誤差 ≈ σ_payoff / √M　シミュレーション数: {M:,}回")

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        rng = np.random.default_rng(42)
        n_paths = min(200, M)
        n_steps = 50
        dt_mc = T / n_steps
        Z_paths = rng.standard_normal((n_paths, n_steps))
        log_ret = (r - q - 0.5 * v**2) * dt_mc + v * np.sqrt(dt_mc) * Z_paths
        S_paths = S * np.exp(np.cumsum(log_ret, axis=1))
        S_paths = np.hstack([np.full((n_paths, 1), S), S_paths])

        fig1, ax1 = plt.subplots(figsize=(8, 3))
        for path in S_paths:
            ax1.plot(path, alpha=0.15, linewidth=0.7, color="steelblue")
        ax1.axhline(K, color="red", linestyle="--", linewidth=1.2, label=f"行使価格 K={K:,.0f}")
        ax1.set_xlabel("ステップ")
        ax1.set_ylabel("株価")
        ax1.set_title(f"シミュレーションパス（{n_paths}本サンプル）")
        ax1.legend(fontsize=8)
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)

        Z_all = rng.standard_normal(M)
        S_T = S * np.exp((r - q - 0.5 * v**2) * T + v * np.sqrt(T) * Z_all)
        if opt == "call":
            payoffs = np.maximum(S_T - K, 0)
        else:
            payoffs = np.maximum(K - S_T, 0)
        disc_payoffs = np.exp(-r * T) * payoffs

        fig2, ax2 = plt.subplots(figsize=(8, 3))
        ax2.hist(disc_payoffs, bins=60, color="steelblue", edgecolor="white", alpha=0.8)
        ax2.axvline(disc_payoffs.mean(), color="red", linestyle="--",
                    linewidth=1.5, label=f"平均 = {disc_payoffs.mean():,.2f}")
        ax2.set_xlabel("割引ペイオフ")
        ax2.set_ylabel("頻度")
        ax2.set_title("ペイオフ分布")
        ax2.legend(fontsize=8)
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)
'''

content = open('src/ui/pages/case_detail.py', encoding='utf-8').read()

# tab3ブロックをパターンで置換
pattern = r'    with tab3:.*?(?=\ndef |\Z)'
match = re.search(pattern, content, re.DOTALL)
if match:
    print(f"発見: {match.start()} - {match.end()}")
    content = content[:match.start()] + new_tab3 + '\n' + content[match.end():]
    open('src/ui/pages/case_detail.py', 'w', encoding='utf-8').write(content)
    print('置換成功')
else:
    print('パターンが見つかりません')
