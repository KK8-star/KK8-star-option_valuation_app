import sqlite3, pathlib

db_path = pathlib.Path('data/valuations.db')
if not db_path.exists():
    print('DB未作成 — 計算を実行してください')
else:
    con = sqlite3.connect(db_path)
    rows = con.execute("""
        SELECT DISTINCT model_type, COUNT(*) as cnt
        FROM valuation_results
        GROUP BY model_type
        ORDER BY model_type
    """).fetchall()
    con.close()
    print(f"  {'model_type':<25} {'件数':>6}")
    print('  ' + '-' * 33)
    for mt, cnt in rows:
        ok = 'OK' if mt.endswith('_call') or mt.endswith('_put') else 'NG 旧形式'
        print(f"  {ok} {mt:<23} {cnt:>6}")
