from src.data.database import get_session
from src.data.models import ValuationCase
from datetime import datetime, timedelta

with get_session() as s:
    test_cases = [
        {"case_name": "テストケース01", "company_name": "サンプル株式会社A", "notes": "製造業・評価テスト"},
        {"case_name": "テストケース02", "company_name": "サンプル株式会社B", "notes": "IT業・評価テスト"},
        {"case_name": "テストケース03", "company_name": "テック株式会社",    "notes": "スタートアップ評価"},
        {"case_name": "評価ケース_2024Q1", "company_name": "フィンテック社",  "notes": "金融系オプション評価"},
        {"case_name": "評価ケース_2024Q2", "company_name": "バイオベンチャー", "notes": "医療系評価"},
        {"case_name": "ABC評価",          "company_name": "Global Tech Inc", "notes": "外資系企業評価"},
        {"case_name": "XYZ案件",          "company_name": "未来産業株式会社", "notes": "製造業大手"},
        {"case_name": "ストックオプション評価01", "company_name": "スタートアップX", "notes": "シリーズA"},
        {"case_name": "ストックオプション評価02", "company_name": "スタートアップY", "notes": "シリーズB"},
        {"case_name": "ストックオプション評価03", "company_name": "スタートアップZ", "notes": "シリーズC"},
    ]
    
    for i, data in enumerate(test_cases):
        vc = ValuationCase(
            case_name=data["case_name"],
            company_name=data["company_name"],
            notes=data["notes"],
            is_deleted=0,
        )
        s.add(vc)
    
    print(f"テストデータ {len(test_cases)} 件を投入完了")