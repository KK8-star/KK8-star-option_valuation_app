import pathlib, ast, sys

print("=" * 60)
print("?1?????????")
files = [
    "app.py",
    "src/ui/pages/case_list.py",
    "src/ui/pages/case_detail.py",
    "src/data/database.py",
    "src/data/models.py",
    "data/valuations.db",
]
for f in files:
    p = pathlib.Path(f)
    exists = "? ??" if p.exists() else "? ??"
    size   = f"({p.stat().st_size} bytes)" if p.exists() else ""
    print(f"  {exists}  {f} {size}")

print()
print("?2?app.py ????????")
with open("app.py", encoding="utf-8") as f:
    app_src = f.read()

import re
# PAGES dict ???
matches = re.findall(r'"([^"]+)"\s*:\s*(\w+)', app_src)
for k, v in matches:
    marker = " ? ?????" if "detail" in v.lower() else ""
    print(f"  [{k}] -> {v}{marker}")

print()
print("?3?case_list.py ???????")
with open("src/ui/pages/case_list.py", encoding="utf-8") as f:
    cl_src = f.read()

# current_page ???????????????
nav_keys = re.findall(r'current_page"\]\s*=\s*"([^"]+)"', cl_src)
print(f"  case_list.py ??????????: {nav_keys}")

# BOM??
raw = pathlib.Path("src/ui/pages/case_list.py").read_bytes()
print(f"  BOM: {'?? ?' if raw[:3] == b'\xef\xbb\xbf' else '?? ?'}")

print()
print("?4?case_detail.py ?????")
with open("src/ui/pages/case_detail.py", encoding="utf-8") as f:
    cd_src = f.read()
print(f"  ???????: {len(cd_src)} ??")
print(f"  selected_case_id ??: {'?? ?' if 'selected_case_id' in cd_src else '?? ?'}")
print(f"  show() ??: {'?? ?' if 'def show(' in cd_src else '?? ?'}")
print(f"  render() ??: {'?? ?' if 'def render(' in cd_src else '?? ?'}")

# ??????
try:
    ast.parse(cd_src)
    print(f"  ??: OK ?")
except SyntaxError as e:
    print(f"  ????? ?: {e}")

print()
print("?5?DB??")
if pathlib.Path("data/valuations.db").exists():
    import sqlite3
    con = sqlite3.connect("data/valuations.db")
    tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"  ????: {[t[0] for t in tables]}")
    for t in tables:
        cnt = con.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
        print(f"    {t[0]}: {cnt} ?")
    con.close()
else:
    print("  DB??? ?")

print()
print("?6?app.py ???????????")
# current_page ?????????????
lines = app_src.splitlines()
for i, line in enumerate(lines):
    if "current_page" in line or "case_detail" in line:
        print(f"  L{i+1:3d}: {line}")

print("=" * 60)
