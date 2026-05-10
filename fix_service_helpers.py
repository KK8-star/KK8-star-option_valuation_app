import pathlib

path = pathlib.Path('src/services/valuation_service.py')
original = path.read_text(encoding='utf-8')

old_block = """    # ------------------------------------------------------------------ #
    #  READ / DELETE helpers                                               #
    # ------------------------------------------------------------------ #

    def list_cases(self) -> list[dict]:
        \"\"\"保存済み全ケースの概要リストを返す。\"\"\"
        with self._connect() as conn:
            rows = conn.execute(
                \"\"\"
                SELECT c.id, c.company_name, c.valuation_date, c.currency, c.industry
                FROM   ValuationCase c
                ORDER  BY c.id DESC
                \"\"\"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_case(self, case_id: int) -> dict | None:
        \"\"\"指定IDのケース基本情報を返す。\"\"\"
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ValuationCase WHERE id = ?", (case_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_params(self, case_id: int) -> dict | None:
        \"\"\"指定IDのパラメータ情報を返す。\"\"\"
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ValuationParameter WHERE case_id = ?", (case_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_results(self, case_id: int) -> dict | None:
        \"\"\"指定IDの評価結果を返す。\"\"\"
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ValuationResult WHERE case_id = ?", (case_id,)
            ).fetchone()
        return dict(row) if row else None

    def delete_case(self, case_id: int) -> None:
        \"\"\"指定IDのケースと関連データを全削除する。\"\"\"
        with self._connect() as conn:
            conn.execute("DELETE FROM ValuationParameter WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM ValuationResult    WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM ValuationCase      WHERE id      = ?", (case_id,))
            conn.commit()"""

new_block = """    # ------------------------------------------------------------------ #
    #  READ / DELETE helpers                                               #
    # ------------------------------------------------------------------ #

    def list_cases(self) -> list[dict]:
        \"\"\"保存済み全ケースの概要リストを返す。\"\"\"
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationCase
            db = get_db_manager()
            with db.get_session() as session:
                rows = session.query(ValuationCase).filter(
                    ValuationCase.is_deleted == 0
                ).order_by(ValuationCase.id.desc()).all()
                return [
                    {
                        'id': r.id,
                        'company_name': r.company_name,
                        'case_name': r.case_name,
                        'notes': r.notes,
                        'created_at': str(r.created_at) if hasattr(r, 'created_at') else '',
                    }
                    for r in rows
                ]
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    def get_case(self, case_id: int) -> dict | None:
        \"\"\"指定IDのケース基本情報を返す。\"\"\"
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationCase
            db = get_db_manager()
            with db.get_session() as session:
                row = session.query(ValuationCase).filter(ValuationCase.id == case_id).first()
                if row is None:
                    return None
                return {
                    'id': row.id,
                    'company_name': row.company_name,
                    'case_name': row.case_name,
                    'notes': row.notes,
                    'created_at': str(row.created_at) if hasattr(row, 'created_at') else '',
                }
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    def get_params(self, case_id: int) -> dict | None:
        \"\"\"指定IDのパラメータ情報を返す。\"\"\"
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationParameter
            db = get_db_manager()
            with db.get_session() as session:
                row = session.query(ValuationParameter).filter(
                    ValuationParameter.case_id == case_id
                ).first()
                if row is None:
                    return None
                return {c.name: getattr(row, c.name) for c in row.__table__.columns}
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    def get_results(self, case_id: int) -> list[dict]:
        \"\"\"指定IDの評価結果リストを返す。\"\"\"
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationResult as ORMResult
            db = get_db_manager()
            with db.get_session() as session:
                rows = session.query(ORMResult).filter(
                    ORMResult.case_id == case_id
                ).all()
                return [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    def delete_case(self, case_id: int) -> None:
        \"\"\"指定IDのケースと関連データを全削除する（論理削除）。\"\"\"
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationCase, ValuationParameter, ValuationResult as ORMResult
            db = get_db_manager()
            with db.get_session() as session:
                session.query(ORMResult).filter(ORMResult.case_id == case_id).delete()
                session.query(ValuationParameter).filter(ValuationParameter.case_id == case_id).delete()
                case = session.query(ValuationCase).filter(ValuationCase.id == case_id).first()
                if case:
                    case.is_deleted = 1
        except Exception:
            import traceback
            traceback.print_exc()"""

if old_block in original:
    patched = original.replace(old_block, new_block)
    path.write_text(patched, encoding='utf-8')
    print("PATCHED")
else:
    print("NG: 対象ブロックが見つかりません")
    for i, line in enumerate(old_block.split("\n")):
        if line not in original:
            print(f"  不一致行 {i+1}: [{line}]")
            break
