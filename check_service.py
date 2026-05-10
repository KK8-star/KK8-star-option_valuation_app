import pathlib

c = pathlib.Path('src/services/valuation_service.py').read_text(encoding='utf-8')
lines = c.split('\n')

for i, line in enumerate(lines, start=1):
    print(f"{i:4d}: {line}")
