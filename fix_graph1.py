with open('src/ui/pages/case_detail.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''        fig1, ax1 = plt.subplots(figsize=(8, 3))
        for path in S_paths:
            ax1.plot(path, alpha=0.15, linewidth=0.7, color="steelblue")
        ax1.axhline(K, color="red", linestyle="--", linewidth=1.2, label=f"行使価格 K={K:,.0f}")
        ax1.set_xlabel("ステップ")
        ax1.set_ylabel("株価")
        ax1.set_title(f"シミュレーションパス（{n_paths}本サンプル）")
        ax1.legend(fontsize=8)
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)'''

new_code = '''        # 各時点の平均・標準偏差を計算
        mean_path = np.mean(S_paths, axis=0)
        std_path  = np.std(S_paths,  axis=0)
        time_steps = np.arange(S_paths.shape[1])

        fig1, ax1 = plt.subplots(figsize=(10, 4))

        # ±2σ帯（薄い水色）
        ax1.bar(
            time_steps,
            4 * std_path,
            bottom=mean_path - 2 * std_path,
            color="lightblue",
            alpha=0.35,
            width=0.85,
            label="平均 ± 2σ"
        )
        # ±1σ帯（濃い青）
        ax1.bar(
            time_steps,
            2 * std_path,
            bottom=mean_path - std_path,
            color="steelblue",
            alpha=0.55,
            width=0.85,
            label="平均 ± 1σ"
        )
        # 平均株価ライン
        ax1.plot(
            time_steps, mean_path,
            color="navy", linewidth=2.0,
            label="平均株価"
        )
        # 行使価格ライン
        ax1.axhline(
            K, color="red", linestyle="--",
            linewidth=1.5, label=f"行使価格 K={K:,.0f}"
        )
        ax1.set_xlabel("時間ステップ（月次）")
        ax1.set_ylabel("株価（円）")
        ax1.set_title("株価の広がりイメージ（標準偏差ベース）")
        ax1.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x:,.0f}")
        )
        ax1.legend(fontsize=8, loc="upper left")
        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('src/ui/pages/case_detail.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: グラフ1を標準偏差棒グラフに修正しました")
else:
    print("ERROR: 対象コードが見つかりません")
