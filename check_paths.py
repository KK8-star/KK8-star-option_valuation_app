with open('src/ui/pages/case_detail.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

results = []
for i, line in enumerate(lines, 1):
    if any(kw in line for kw in ['paths', 'S0', 'sigma', 'monte', 'simulation', 'np.', 'simulate', 'disc_payoffs', 'payoff']):
        results.append(f'{i}: {line.rstrip()}')

with open('paths_check.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print('Done')
