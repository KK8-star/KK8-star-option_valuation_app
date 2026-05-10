import os

files = {
    "src/ui/pages/case_list.py": "show",
    "src/ui/pages/home.py": "show",
    "src/ui/pages/new_valuation.py": "show",
}

for filepath, func_name in files.items():
    if not os.path.exists(filepath):
        print(f"SKIP (存在しない): {filepath}")
        continue

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "def render(" in content:
        print(f"OK (既にrenderあり): {filepath}")
        continue

    if f"def {func_name}(" in content:
        # render = show のエイリアスを末尾に追加
        content = content.rstrip() + f"\n\n\ndef render():\n    {func_name}()\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"FIXED (render追加): {filepath}")
    else:
        # どんな関数が定義されているか調べる
        import ast
        try:
            tree = ast.parse(content)
            funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            print(f"WARNING: {filepath} に '{func_name}' が見つかりません。定義済み関数: {funcs}")
        except Exception as e:
            print(f"ERROR (parse失敗): {filepath} -> {e}")

print("\n=== 確認 ===")
for filepath in files:
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    import ast
    try:
        tree = ast.parse(content)
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        has_render = "render" in funcs
        print(f"{'OK' if has_render else 'NG'} {filepath}: 関数={funcs}")
    except Exception as e:
        print(f"ERROR {filepath}: {e}")