from src.data.database import get_session
from src.data.models import ValuationCase
from sqlalchemy import select, text

with get_session() as s:
    result = s.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).all()
    print("=== テーブル一覧 ===")
    for r in result:
        print(f"  {r[0]}")

    result2 = s.execute(text("PRAGMA table_info(valuation_cases)")).all()
    print("=== valuation_cases カラム ===")
    for r in result2:
        print(f"  {r}")

    rows = s.execute(select(ValuationCase)).all()
    print(f"=== 全レコード数(削除含む): {len(rows)} ===")
    for r in rows:
        vc = r[0]
        print(f"  id={vc.id} case={vc.case_name} company={vc.company_name} is_deleted={vc.is_deleted}")