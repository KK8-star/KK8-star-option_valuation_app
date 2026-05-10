content = open('app.py', encoding='utf-8').read()

# PAGES辞書の部分を抽出
start = content.find('PAGES')
chunk = content[start:start+300]
print("=== PAGES block ===")
print(repr(chunk))

print()

# home.pyのcurrent_page設定値を16進数で確認
content2 = open('src/ui/pages/home.py', encoding='utf-8').read()
print("=== home.py current_page hex dump ===")
for line in content2.split('\n'):
    if 'current_page' in line and '=' in line:
        stripped = line.strip()
        print(repr(stripped))
        # 文字列値の部分を抽出して16進数表示
        if '"' in stripped:
            parts = stripped.split('"')
            for i, p in enumerate(parts):
                if p and i % 2 == 1:
                    print("  value:", repr(p), "hex:", [hex(ord(c)) for c in p])
