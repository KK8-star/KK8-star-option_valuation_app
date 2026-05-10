import pathlib

c = pathlib.Path('src/ui/pages/new_valuation.py').read_text(encoding='utf-8')
lines = c.split('\n')

# 40行目〜80行目を表示
for i, line in enumerate(lines[38:85], start=39):
    print(f"{i+1:4d}: {line}")
