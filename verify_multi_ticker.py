import pathlib

c = pathlib.Path('src/ui/pages/new_valuation.py').read_text(encoding='utf-8')
lines = c.split('\n')

for i, line in enumerate(lines[63:95], start=64):
    print(f"{i+1:4d}: {line}")
