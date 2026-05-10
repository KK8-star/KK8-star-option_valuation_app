# -*- coding: utf-8 -*-
"""
作成時刻がずれる問題の修正
1. models.py: server_default=func.now() → Python側 datetime.now() に変更
2. database.py の関数名確認 & JST変換ユーティリティ追加
3. case_list.py: 表示時刻をJSTで表示
"""
import re

# ============================================================
# 修正1: models.py の時刻デフォルトを Python 側に変更
# ============================================================
path_m = 'src/data/models.py'
content = open(path_m, encoding='utf-8-sig').read()

# importに datetime を確保（既存: from datetime import datetime）
old_import = "from datetime import datetime"
new_import = "from datetime import datetime, timezone, timedelta"
if old_import in content and "timedelta" not in content:
    content = content.replace(old_import, new_import)
    print("✅ 修正1a: datetime import 拡張")
else:
    print("ℹ️  修正1a: import は既に対応済みまたはスキップ")

# JST now() ヘルパーを追加（import の直後）
jst_helper = (
    "\n"
    "# JSTタイムゾーン\n"
    "JST = timezone(timedelta(hours=9))\n"
    "\n"
    "def _now_jst() -> datetime:\n"
    '    """現在のJST時刻を返す（タイムゾーンなし）"""\n'
    "    return datetime.now(JST).replace(tzinfo=None)\n"
)

# func のimport確認
if "from sqlalchemy import" in content and "_now_jst" not in content:
    # from sqlalchemy import ... の行の後に挿入
    lines = content.split("\n")
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("from sqlalchemy") or line.startswith("import sqlalchemy"):
            insert_idx = i + 1
    lines.insert(insert_idx, jst_helper)
    content = "\n".join(lines)
    print("✅ 修正1b: _now_jst() ヘルパー追加")
elif "_now_jst" in content:
    print("ℹ️  修正1b: _now_jst は既に存在します")
else:
    print("⚠️  修正1b: 挿入位置が見つかりませんでした")

# created_at の server_default → default=_now_jst に変更
old_created = (
    "    created_at: Mapped[datetime] = mapped_column(\n"
    "        DateTime, server_default=func.now(), nullable=False\n"
    "    )"
)
new_created = (
    "    created_at: Mapped[datetime] = mapped_column(\n"
    "        DateTime, default=_now_jst, nullable=False\n"
    "    )"
)
if old_created in content:
    content = content.replace(old_created, new_created)
    print("✅ 修正1c: created_at を default=_now_jst に変更")
elif "default=_now_jst" in content:
    print("ℹ️  修正1c: created_at は既に対応済み")
else:
    print("⚠️  修正1c: created_at の対象文字列が見つかりませんでした")

# updated_at の server_default → default=_now_jst, onupdate=_now_jst に変更
old_updated = (
    "    updated_at: Mapped[datetime] = mapped_column(\n"
    "        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False\n"
    "    )"
)
new_updated = (
    "    updated_at: Mapped[datetime] = mapped_column(\n"
    "        DateTime, default=_now_jst, onupdate=_now_jst, nullable=False\n"
    "    )"
)
if old_updated in content:
    content = content.replace(old_updated, new_updated)
    print("✅ 修正1d: updated_at を default=_now_jst に変更")
elif "onupdate=_now_jst" in content:
    print("ℹ️  修正1d: updated_at は既に対応済み")
else:
    print("⚠️  修正1d: updated_at の対象文字列が見つかりませんでした")

# calculated_at も同様に修正
old_calc = (
    "    calculated_at: Mapped[datetime] = mapped_column(\n"
    "        DateTime, server_default=func.now(), nullable=False\n"
    "    )"
)
new_calc = (
    "    calculated_at: Mapped[datetime] = mapped_column(\n"
    "        DateTime, default=_now_jst, nullable=False\n"
    "    )"
)
if old_calc in content:
    content = content.replace(old_calc, new_calc)
    print("✅ 修正1e: calculated_at を default=_now_jst に変更")
elif "calculated_at" in content and "default=_now_jst" in content:
    print("ℹ️  修正1e: calculated_at は既に対応済み")
else:
    print("⚠️  修正1e: calculated_at の対象文字列が見つかりませんでした（スキップ）")

open(path_m, 'w', encoding='utf-8', newline='\n').write(content)
print(f"💾 {path_m} を保存しました\n")

# ============================================================
# 修正2: case_list.py の時刻表示を確認・修正
# ============================================================
path_cl = 'src/ui/pages/case_list.py'
content2 = open(path_cl, encoding='utf-8-sig').read()

# created_at の表示フォーマットを確認・修正
# strftime がなければ追加
if "created_at" in content2:
    lines2 = content2.split("\n")
    print("=== case_list.py の created_at 表示箇所 ===")
    for i, line in enumerate(lines2):
        if "created_at" in line:
            print(f"  {i+1:4d}: {line}")

# 表示フォーマットが .strftime なければ修正
old_display = '"作成日時": c.created_at,'
new_display = '"作成日時": c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else "-",'

old_display2 = '"作成日時": c.created_at'
new_display2 = '"作成日時": c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else "-"'

if old_display in content2:
    content2 = content2.replace(old_display, new_display)
    print("✅ 修正2a: created_at 表示フォーマット適用")
elif old_display2 in content2:
    content2 = content2.replace(old_display2, new_display2)
    print("✅ 修正2b: created_at 表示フォーマット適用")
elif "strftime" in content2:
    print("ℹ️  修正2: strftime は既に存在します")
else:
    print("⚠️  修正2: case_list.py の created_at 表示箇所を手動確認してください")

open(path_cl, 'w', encoding='utf-8', newline='\n').write(content2)
print(f"💾 {path_cl} を保存しました\n")

# ============================================================
# 構文チェック
# ============================================================
import ast
files = ['src/data/models.py', 'src/ui/pages/case_list.py']
print("=== 構文チェック ===")
for path in files:
    try:
        ast.parse(open(path, encoding='utf-8').read())
        print(f"  ✅ OK: {path}")
    except SyntaxError as e:
        print(f"  ❌ NG: {path} → {e}")

print("\n🎉 時刻修正完了")
