import pathlib

additions = """

    # ------------------------------------------------------------------ #
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
            conn.commit()
"""

path = pathlib.Path('src/services/valuation_service.py')
original = path.read_text(encoding='utf-8')

# クラス末尾（最終行）に追加
if 'def list_cases' in original:
    print('SKIP: already patched')
else:
    # 最後の改行の前に挿入
    patched = original.rstrip() + "\n" + additions + "\n"
    path.write_text(patched, encoding='utf-8')
    print('PATCHED')

# 検証
c = path.read_text(encoding='utf-8')
for label, kw in [
    ('list_cases',  'def list_cases'),
    ('get_case',    'def get_case'),
    ('get_params',  'def get_params'),
    ('get_results', 'def get_results'),
    ('delete_case', 'def delete_case'),
]:
    print(('OK' if kw in c else 'NG') + ' ' + label)
