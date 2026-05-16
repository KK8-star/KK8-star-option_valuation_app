with open('src/ui/pages/case_detail.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt'''

new_code = '''        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        # Windows日本語フォント設定
        jp_fonts = ["MS Gothic", "Yu Gothic", "Meiryo", "IPAexGothic", "DejaVu Sans"]
        available = [f.name for f in fm.fontManager.ttflist]
        for font in jp_fonts:
            if font in available:
                plt.rcParams["font.family"] = font
                break'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('src/ui/pages/case_detail.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: 日本語フォント設定を追加しました")
else:
    print("ERROR: 対象コードが見つかりません")
