import sqlite3
import os
import glob

# プロジェクト内の全DBファイルを検索
db_files = glob.glob("**/*.db", recursive=True) + glob.glob("**/*.sqlite", recursive=True) + glob.glob("**/*.sqlite3", recursive=True)
print(f"=== 発見したDBファイル ===")
for f in db_files:
    size = os.path.getsize(f)
    print(f"  {f} ({size} bytes)")

print()

# 各DBの valuation_cases テーブルを確認
for f in db_files:
    print(f"=== {f} の内容 ===")
    try:
        conn = sqlite3.connect(f)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"  テーブル: {tables}")
        if "valuation_cases" in tables:
            cur.execute("SELECT COUNT(*) FROM valuation_cases WHERE is_deleted=0")
            cnt = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM valuation_cases")
            total = cur.fetchone()[0]
            print(f"  件数: 有効={cnt}, 総数={total}")
            # 最新5件を表示
            cur.execute("SELECT id, case_name, created_at, is_deleted FROM valuation_cases ORDER BY created_at DESC LIMIT 5")
            rows = cur.fetchall()
            print(f"  最新5件:")
            for r in rows:
                print(f"    id={r[0]}, name={r[1]}, created={r[2]}, deleted={r[3]}")
        conn.close()
    except Exception as e:
        print(f"  ERROR: {e}")

print()
print("=== database.py のDB接続パスを確認 ===")
with open("src/data/database.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "sqlite" in line.lower() or "db" in line.lower() or "path" in line.lower() or "url" in line.lower():
            print(f"  L{i}: {line.rstrip()}")