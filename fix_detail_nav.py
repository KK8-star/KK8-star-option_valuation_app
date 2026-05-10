import re

# ── 1. case_list.py: 詳細ボタンの遷移先を修正 ──────────────────
path = "src/ui/pages/case_list.py"
content = open(path, encoding="utf-8").read()

# 実際のファイルに存在する文字列で置換
old = '                    st.session_state["current_page"] = "📊 新規評価"'
new = '                    st.session_state["current_page"] = "📋 評価詳細"'

if old in content:
    content = content.replace(old, new)
    open(path, "w", encoding="utf-8").write(content)
    print("✅ case_list.py 修正完了")
else:
    print("❌ case_list.py: 対象文字列なし")
    for i, line in enumerate(content.split("\n"), 1):
        if "current_page" in line:
            print(f"  {i}: {repr(line)}")

# ── 2. app.py: case_detail を import して PAGES に追加 ──────────
path2 = "app.py"
content2 = open(path2, encoding="utf-8").read()

# import 行を追加
old_import = "from src.ui.pages import home, new_valuation, case_list"
new_import  = "from src.ui.pages import home, new_valuation, case_list, case_detail"

if new_import in content2:
    print("⚠️  app.py: import 既に追加済み")
elif old_import in content2:
    content2 = content2.replace(old_import, new_import)
    print("✅ app.py: import 追加完了")
else:
    print("❌ app.py: import 行が見つかりません")

# PAGES 辞書に評価詳細を追加
old_pages = '''\
PAGES = {
    "🏠 ホーム":     home,
    "📊 新規評価":   new_valuation,
    "📋 評価一覧":   case_list,
    "⚙️ 設定":       None,
}'''

new_pages = '''\
PAGES = {
    "🏠 ホーム":     home,
    "📊 新規評価":   new_valuation,
    "📋 評価一覧":   case_list,
    "📋 評価詳細":   case_detail,
    "⚙️ 設定":       None,
}'''

if new_pages in content2:
    print("⚠️  app.py: PAGES 既に修正済み")
elif old_pages in content2:
    content2 = content2.replace(old_pages, new_pages)
    print("✅ app.py: PAGES 修正完了")
else:
    print("❌ app.py: PAGES 辞書が見つかりません")
    for i, line in enumerate(content2.split("\n"), 1):
        if "PAGES" in line or "新規評価" in line:
            print(f"  {i}: {repr(line)}")

open(path2, "w", encoding="utf-8").write(content2)
print("✅ app.py 書き込み完了")

# ── 3. サイドバーに評価詳細を表示しない: PAGE_KEYS を分ける ────
# app.py を再読み込みして確認
content3 = open(path2, encoding="utf-8").read()

# サイドバーは「評価詳細」を除いたキーだけ表示する
old_nav = "PAGE_KEYS = list(PAGES.keys())"
new_nav  = '''\
PAGE_KEYS     = list(PAGES.keys())
SIDEBAR_KEYS  = [k for k in PAGE_KEYS if k != "📋 評価詳細"]'''

if new_nav in content3:
    print("⚠️  app.py: SIDEBAR_KEYS 既に追加済み")
elif old_nav in content3:
    content3 = content3.replace(old_nav, new_nav)
    print("✅ app.py: SIDEBAR_KEYS 追加完了")
else:
    print("❌ app.py: PAGE_KEYS 行が見つかりません")

# st.radio の PAGE_KEYS を SIDEBAR_KEYS に変更
old_radio = "    sel = st.radio(\n        \"メニュー\",\n        PAGE_KEYS,"
new_radio  = "    sel = st.radio(\n        \"メニュー\",\n        SIDEBAR_KEYS,"
if new_radio in content3:
    print("⚠️  app.py: radio 既に修正済み")
elif old_radio in content3:
    content3 = content3.replace(old_radio, new_radio)
    print("✅ app.py: radio 修正完了")
else:
    print("❌ app.py: radio 箇所が見つかりません")
    for i, line in enumerate(content3.split("\n"), 1):
        if "st.radio" in line or "PAGE_KEYS" in line:
            print(f"  {i}: {repr(line)}")

# _radio_index の参照先を SIDEBAR_KEYS に変更
old_idx = "_radio_index = PAGE_KEYS.index(st.session_state[\"current_page\"])"
new_idx  = "_radio_index = SIDEBAR_KEYS.index(st.session_state[\"current_page\"]) if st.session_state[\"current_page\"] in SIDEBAR_KEYS else 0"
if new_idx in content3:
    print("⚠️  app.py: _radio_index 既に修正済み")
elif old_idx in content3:
    content3 = content3.replace(old_idx, new_idx)
    print("✅ app.py: _radio_index 修正完了")
else:
    print("❌ app.py: _radio_index 行が見つかりません")

open(path2, "w", encoding="utf-8").write(content3)
print("\n✅ 全修正完了")
