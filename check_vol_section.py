import pathlib

c = pathlib.Path('src/ui/pages/new_valuation.py').read_text(encoding='utf-8')

# ボラティリティ関連行を抽出
lines = c.split('\n')
for i, line in enumerate(lines):
    if any(kw in line for kw in ['volat', 'ticker', 'Ticker', 'ティッカー', 'yfinance', 'vol_source', 'vol_method', 'vol_period', 'hist']):
        print(f"{i+1:4d}: {line}")
