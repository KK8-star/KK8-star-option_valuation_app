from src.services.valuation_service import ValuationService
from src.data.database import get_db_manager
from src.data.models import ValuationResult
from sqlalchemy import select

svc = ValuationService()
result = svc.calculate(
    company_name='8件テスト3',
    stock_price=1000.0,
    strike_price=1000.0,
    risk_free_rate=0.005,
    volatility=0.30,
    T=1.0,
)
case_id = svc.save(result)
print(f'case_id = {case_id}')

db = get_db_manager()
with db.get_session() as s:
    rows = s.execute(
        select(ValuationResult.model_type, ValuationResult.option_value)
        .where(ValuationResult.case_id == case_id)
        .order_by(ValuationResult.id)
    ).all()
    print(f'保存件数: {len(rows)} 件 (期待値: 8件)')
    for mt, val in rows:
        print(f'  {mt:<20} = {val:.4f}')
