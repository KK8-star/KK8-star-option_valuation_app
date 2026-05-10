import pathlib

c = pathlib.Path('src/ui/pages/new_valuation.py').read_text(encoding='utf-8')
lines = c.split('\n')

checks = [
    ('ティッカー入力欄',    'ticker_symbol'),
    ('yfinance import',     'import yfinance'),
    ('自動計算ロジック',    'log_ret.std()'),
    ('auto_vol反映',        'auto_vol'),
    ('vol_source残存',      'vol_source'),
    ('vol_data_raw',        'vol_data_raw'),
]

for label, kw in checks:
    print(('OK' if kw in c else 'NG') + ' ' + label)

print()
# 該当行を表示
for i, line in enumerate(lines):
    if any(kw in line for kw in ['ticker_symbol', 'auto_vol', 'yfinance', 'vol_source']):
        print(f"{i+1:4d}: {line}")
