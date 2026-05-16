with open('src/ui/pages/case_detail.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

results = []
for i, line in enumerate(lines, 1):
    if any(kw in line for kw in ['ax1', 'ax2', 'fig', 'plt', 'bar', 'plot']):
        results.append(f'{i}: {line.rstrip()}')

with open('graph_check.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print('Done: graph_check.txt に保存しました')
