with open('src/ui/pages/case_detail.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

old_block = '''        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.bar(
'''

# 138行目から180行目を特定して置換
new_block = '''        # グラフ1: 最終株価の分布ヒストグラム
        final_prices = paths[:, -1]
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.hist(final_prices, bins=80, color="steelblue", edgecolor="white", alpha=0.8, density=True)
        ax1.axvline(final_prices.mean(), color="green", linestyle="--", linewidth=2, label=f"平均株価: {final_prices.mean():,.0f}円")
        ax1.axvline(K, color="red", linestyle="--", linewidth=2, label=f"行使価格: {K:,.0f}円")
        ax1.set_xlabel("株価（円）")
        ax1.set_ylabel("起こりやすさ（確率密度）")
        ax1.set_title("満期時点の株価分布")
        ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax1.legend(fontsize=9, loc="upper right")
        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)
'''

with open('src/ui/pages/case_detail.py', 'r', encoding='utf-8') as f:
    content = f.readlines()

# 138-180行目を置換（0-indexedで137-179）
new_content = content[:137] + [new_block] + content[180:]

with open('src/ui/pages/case_detail.py', 'w', encoding='utf-8') as f:
    f.writelines(new_content)

print('SUCCESS: グラフ1を株価ヒストグラムに変更しました')
