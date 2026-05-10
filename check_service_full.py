import pathlib
c = pathlib.Path('src/services/valuation_service.py').read_text(encoding='utf-8')
for i, line in enumerate(c.split('\n'), 1):
    print(f"{i:4d}: {line}")
