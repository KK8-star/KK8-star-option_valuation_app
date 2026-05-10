from pathlib import Path

path = Path('src/ui/case_detail.py')
content = path.read_text(encoding='utf-8')
print('=== 現在のMODEL_LABELS / model_type関連コード ===')

# MODEL_LABELSの前後を表示
idx = content.find('MODEL_LABEL')
if idx == -1:
    idx = content.find('model_type')
print(content[max(0,idx-100):idx+500])
print('...')
print(f'ファイル総行数: {len(content.splitlines())}')
