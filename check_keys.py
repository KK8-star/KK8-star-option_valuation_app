with open("src/ui/pages/case_list.py", encoding="utf-8") as f:
    src = f.read()

if "評価詳細" in src:
    print("OK: 評価詳細 キーあり")
else:
    print("NG: 評価詳細 キーなし")

if "current_page" in src:
    print("OK: current_page あり")
else:
    print("NG: current_page なし")

# app.py 側のキー確認
with open("app.py", encoding="utf-8") as f:
    app_src = f.read()

if "📋 評価詳細" in app_src:
    print("OK: app.py に 評価詳細 キーあり")
else:
    print("NG: app.py に 評価詳細 キーなし")
