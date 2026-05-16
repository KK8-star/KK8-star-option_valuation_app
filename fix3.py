import sys
sys.stdout.reconfigure(encoding='utf-8')

lines = open('src/ui/pages/case_detail.py', encoding='utf-8').readlines()

# 153行目(インデックス152): コメント修正
lines[152] = '    # タブ2: 二項モデル（Cox-Ross-Rubinstein）\n'

# 155行目(インデックス154): tab2のmarkdown修正
lines[154] = '        st.markdown("#### 二項モデル（Cox-Ross-Rubinstein）")\n'

open('src/ui/pages/case_detail.py', 'w', encoding='utf-8').writelines(lines)
print('Done!')
