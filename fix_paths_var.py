with open('src/ui/pages/case_detail.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 139行目(0-indexedで138)の paths を S_paths に修正
old_line = '        final_prices = paths[:, -1]\n'
new_line = '        final_prices = S_paths[:, -1]\n'

if lines[138] == old_line:
    lines[138] = new_line
    with open('src/ui/pages/case_detail.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('SUCCESS: paths -> S_paths に修正しました')
else:
    print(f'ERROR: 対象行が一致しません')
    print(f'実際の内容: {repr(lines[138])}')
