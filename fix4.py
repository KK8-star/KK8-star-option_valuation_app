import sys
sys.stdout.reconfigure(encoding='utf-8')

lines = open('src/ui/pages/case_detail.py', encoding='utf-8').readlines()

fixes = {
    75:  '# 計算プロセス表示関数\n',
    77:  '    """Black-Scholes / 二項モデル / モンテカルロの計算過程を表示"""\n',
    91:  '        ["📊 Black-Scholes", "🌳 二項モデル", "🎲 モンテカルロ"]\n',
    94:  '    # タブ1: Black-Scholes\n',
    96:  '        st.markdown("#### Black-Scholes モデル 計算過程")\n',
    100: '        st.markdown("**📌 入力パラメータ**")\n',
    102: '        c1.metric("S (株価)", f"{S:,.2f}")\n',
    103: '        c2.metric("K (行使価格)", f"{K:,.2f}")\n',
    104: '        c3.metric("r (無リスク金利)", f"{r*100:.2f}%")\n',
    105: '        c4.metric("σ (ボラティリティ)", f"{v*100:.2f}%")\n',
    106: '        c5.metric("T (満期年数)", f"{T:.4f}年")\n',
    108: '        st.markdown("**d1, d2 の計算**")\n',
    161: '        st.markdown("**📌 モデルパラメータ**")\n',
    163: '        p1.metric("ステップ数 N", N)\n',
    164: '        p2.metric("Δt (1期間)", f"{dt:.6f}年")\n',
    165: '        p3.metric("u (上昇率)", f"{u:.6f}")\n',
    166: '        p4.metric("d (下落率)", f"{d:.6f}")\n',
    167: '        p5.metric("p (リスク中立確率)", f"{p:.6f}")\n',
    173: '            f"u  = e^({v}×√{dt:.6f}) = {u:.6f}\\n"\n',
    177: '            f"p  = (e^(({r}-{q})×{dt:.6f}) - {d:.6f}) / ({u:.6f} - {d:.6f})\\n"\n',
    183: '        st.markdown("**📌 価格ツリー（最初の5ステップ）**")\n',
    196: '        st.info(f"実際の{N}ステップ完全計算結果: {N+1}ノード")\n',
    197: '        st.metric("二項モデル価格", f"¥{case[\'binomial_price\']:,.4f}")\n',
    199: '    # タブ3: モンテカルロ\n',
    201: '        st.markdown("#### モンテカルロ シミュレーション 計算過程")\n',
    203: '        st.markdown("**📌 GBMによる株価パス生成式**")\n',
    210: '            f"ドリフト項 = ({r} - {q} - {v}²/2) × {T}\\n"\n',
    214: '            f"拡散項    = {v} × √{T} × Z  (Z ~ N(0,1))\\n"\n',
    216: '            f"シミュレーション数: {M:,}回",\n',
    220: '        st.markdown("**📌 ペイオフ計算**")\n',
    228: '        st.markdown("**📌 割引計算**")\n',
    231: '            f"Price = e^(-{r}×{T}) × 平均ペイオフ\\n"\n',
    233: '            f"      = {math.exp(-r*T):.6f} × 平均ペイオフ\\n"\n',
    235: '            f"      ≈ ¥{case[\'mc_price\']:,.4f}",\n',
    239: '        st.success(f"モンテカルロ価格: ¥{case[\'mc_price\']:,.4f}  ({M:,}回シミュレーション)")\n',
    241: '        st.markdown("**📌 収束性について**")\n',
    243: '            f"標準誤差 ≈ σ_payoff / √M  \\n"\n',
    245: '            f"シミュレーション数 {M:,} 回  \\n"\n',
    247: '            f"数が多いほど価格は真の値に収束します"\n',
}

for idx, new_line in fixes.items():
    lines[idx - 1] = new_line

open('src/ui/pages/case_detail.py', 'w', encoding='utf-8').writelines(lines)
print('Done! Fixed', len(fixes), 'lines')
