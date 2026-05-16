import sys
sys.stdout.reconfigure(encoding='utf-8')

lines = open('src/ui/pages/case_detail.py', encoding='utf-8').readlines()

# 123行目(インデックス122)の壊れた行を削除
# 152行目はインデックス151 -> 削除後は150になる
# まず123行目を削除
del lines[122]

# 削除後、152行目はインデックス150になる -> 修正
lines[150] = '        st.success(f"Black-Scholes価格: {price_bs:,.4f}")\n'

open('src/ui/pages/case_detail.py', 'w', encoding='utf-8').writelines(lines)
print('Done! Total lines:', len(lines))
