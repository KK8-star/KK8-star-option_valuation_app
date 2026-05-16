import sys
sys.stdout.reconfigure(encoding='utf-8')

lines = open('src/ui/pages/case_detail.py', encoding='utf-8').readlines()

fixes = {
    76:  '# 計算プロセス表示関数\n',
    78:  '    """Black-Scholes / 二項モデル / モンテカルロの計算過程を表示"""\n',
    92:  '        ["📊 Black-Scholes", "🌳 二項モデル", "🎲 モンテカルロ"]\n',
    95:  '    # タブ1: Black-Scholes\n',
    97:  '        st.markdown("#### Black-Scholes モデル 計算過程")\n',
    101: '        st.markdown("**📌 入力パラメータ**")\n',
    107: '        c5.metric("T (満期年数)", f"{T:.4f}年")\n',
    109: '        st.markdown("**d1, d2 の計算**")\n',
    162: '        st.markdown("**📌 モデルパラメータ**")\n',
    168: '        p5.metric("p (リスク中立確率)", f"{p:.6f}")\n',
    174: '            f"u  = e^({v}×√{dt:.6f}) = {u:.6f}\\n"\n',
    178: '            f"p  = (e^(({r}-{q})×{dt:.6f}) - {d:.6f}) / ({u:.6f} - {d:.6f})\\n"\n',
    184: '        st.markdown("**📌 価格ツリー（最初の5ステップ）**")\n',
    198: '        st.metric("二項モデル価格", f"¥{case[\'binomial_price\']:,.4f}")\n',
    200: '    # タブ3: モンテカルロ\n',
    202: '        st.markdown("#### モンテカルロ シミュレーション 計算過程")\n',
    204: '        st.markdown("**📌 GBMによる株価パス生成式**")\n',
    211: '            f"ドリフト項 = ({r} - {q} - {v}²/2) × {T}\\n"\n',
    215: '            f"拡散項    = {v} × √{T} × Z  (Z ~ N(0,1))\\n"\n',
    217: '            f"シミュレーション数: {M:,}回",\n',
    221: '        st.markdown("**📌 ペイオフ計算**")\n',
    229: '        st.markdown("**📌 割引計算**")\n',
    232: '            f"Price = e^(-{r}×{T}) × 平均ペイオフ\\n"\n',
    234: '            f"      = {math.exp(-r*T):.6f} × 平均ペイオフ\\n"\n',
    236: '            f"      ≈ ¥{case[\'mc_price\']:,.4f}",\n',
    240: '        st.success(f"モンテカルロ価格: ¥{case[\'mc_price\']:,.4f}  ({M:,}回シミュレーション)")\n',
    242: '        st.markdown("**📌 収束性について**")\n',
    244: '            f"標準誤差 ≈ σ_payoff / √M  \\n"\n',
    246: '            f"シミュレーション数 {M:,} 回  \\n"\n',
    248: '            f"数が多いほど価格は真の値に収束します"\n',
}

for idx, new_line in fixes.items():
    lines[idx - 1] = new_line

open('src/ui/pages/case_detail.py', 'w', encoding='utf-8').writelines(lines)
print(f'Done! Fixed {len(fixes)} lines')
