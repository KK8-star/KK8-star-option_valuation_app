from src.data.database import get_session
from src.data.models import ValuationCase
from sqlalchemy import select, func, or_

print("=" * 50)
print("テスト1: 最新10件取得（キーワードなし）")
print("=" * 50)
with get_session() as s:
    rows = s.execute(
        select(ValuationCase)
        .where(ValuationCase.is_deleted == 0)
        .order_by(ValuationCase.created_at.desc())
        .limit(10)
    ).all()
    print(f"件数: {len(rows)}")
    for r in rows:
        vc = r[0]
        print(f"  [{vc.id}] {vc.case_name} / {vc.company_name} / is_deleted={vc.is_deleted}")

print()
print("=" * 50)
print("テスト2: 「テスト」で検索")
print("=" * 50)
with get_session() as s:
    keyword = "テスト"
    pat = f"%{keyword}%"
    rows = s.execute(
        select(ValuationCase)
        .where(ValuationCase.is_deleted == 0)
        .where(or_(
            func.lower(ValuationCase.case_name).like(func.lower(pat)),
            func.lower(ValuationCase.company_name).like(func.lower(pat)),
        ))
        .order_by(ValuationCase.created_at.desc())
    ).all()
    print(f"件数: {len(rows)}")
    for r in rows:
        vc = r[0]
        print(f"  [{vc.id}] {vc.case_name} / {vc.company_name}")

print()
print("=" * 50)
print("テスト3: 「スタートアップ」で検索")
print("=" * 50)
with get_session() as s:
    keyword = "スタートアップ"
    pat = f"%{keyword}%"
    rows = s.execute(
        select(ValuationCase)
        .where(ValuationCase.is_deleted == 0)
        .where(or_(
            func.lower(ValuationCase.case_name).like(func.lower(pat)),
            func.lower(ValuationCase.company_name).like(func.lower(pat)),
        ))
        .order_by(ValuationCase.created_at.desc())
    ).all()
    print(f"件数: {len(rows)}")
    for r in rows:
        vc = r[0]
        print(f"  [{vc.id}] {vc.case_name} / {vc.company_name}")

print()
print("=" * 50)
print("テスト4: 「global」で大文字小文字無視検索")
print("=" * 50)
with get_session() as s:
    keyword = "global"
    pat = f"%{keyword}%"
    rows = s.execute(
        select(ValuationCase)
        .where(ValuationCase.is_deleted == 0)
        .where(or_(
            func.lower(ValuationCase.case_name).like(func.lower(pat)),
            func.lower(ValuationCase.company_name).like(func.lower(pat)),
        ))
        .order_by(ValuationCase.created_at.desc())
    ).all()
    print(f"件数: {len(rows)}")
    for r in rows:
        vc = r[0]
        print(f"  [{vc.id}] {vc.case_name} / {vc.company_name}")

print()
print("全テスト完了")