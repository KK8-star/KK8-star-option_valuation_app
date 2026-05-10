import sqlite3, pathlib

db_path = pathlib.Path('data/valuations.db')
if not db_path.exists():
    print('DB未作成')
else:
    con = sqlite3.connect(db_path)
    
    # テーブル一覧
    tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print('=== テーブル一覧 ===')
    for t in tables:
        print(f'  {t[0]}')
    
    # cases テーブルの内容
    print()
    print('=== cases テーブル ===')
    try:
        rows = con.execute('SELECT * FROM cases LIMIT 5').fetchall()
        cols = [d[0] for d in con.execute('SELECT * FROM cases LIMIT 1').description or []]
        print(f'  カラム: {cols}')
        print(f'  件数: {len(rows)}')
        for r in rows:
            print(f'  {r}')
    except Exception as e:
        print(f'  ERROR: {e}')
    
    # valuation_results テーブルの内容
    print()
    print('=== valuation_results テーブル ===')
    try:
        rows = con.execute('SELECT * FROM valuation_results LIMIT 5').fetchall()
        print(f'  件数: {len(rows)}')
        for r in rows:
            print(f'  {r}')
    except Exception as e:
        print(f'  ERROR: {e}')
    
    con.close()
