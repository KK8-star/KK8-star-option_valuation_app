import re

with open('src/services/valuation_service.py', encoding='utf-8') as f:
    content = f.read()

print('=== 現在の_binomial関数 ===')
start = content.find('def _binomial')
end = content.find('\ndef _', start + 10)
print(content[start:end])
print()
print('=== 現在の_mc関数 ===')
start2 = content.find('def _mc')
end2 = content.find('\ndef _', start2 + 10)
if end2 == -1:
    end2 = content.find('\nclass ', start2)
print(content[start2:end2])
