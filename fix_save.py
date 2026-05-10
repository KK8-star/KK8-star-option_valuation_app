from pathlib import Path

path = Path('src/services/valuation_service.py')
content = path.read_text(encoding='utf-8')

# save()メソッドの開始位置
save_start = content.find('    def save(')
print(f'save() start pos: {save_start}')

# save()より前の部分だけ保持
before = content[:save_start]

# 新しいsave()メソッド
new_save = '''    def save(
        self,
        result: ValuationResult,
        option_type: str = "call",
    ) -> Optional[int]:
        """評価結果をDBへ保存。全モデル8件を保存。失敗時はNoneを返す。"""
        try:
            from src.data.database import get_db_manager
            from src.data.models import (
                ValuationCase,
                ValuationParameter,
                ValuationResult as ORMResult,
            )

            db = get_db_manager()
            with db.get_session() as session:
                # 1. ValuationCase
                case = ValuationCase(
                    case_name=f"{result.company_name} - {result.valuation_date}",
                    company_name=result.company_name,
                    is_deleted=0,
                    notes=f"業種: {result.industry}, 通貨: {result.currency}",
                )
                session.add(case)
                session.flush()

                # 2. ValuationParameter
                param = ValuationParameter(
                    case_id=case.id,
                    stock_price=result.stock_price,
                    strike_price=result.strike_price,
                    time_to_expiry=result.T,
                    risk_free_rate=result.risk_free_rate,
                    volatility=result.volatility,
                    dividend_yield=result.dividend_yield,
                    option_type=option_type,
                )
                session.add(param)

                # 3. 全モデル結果 8件
                records = [
                    ("weighted_call", result.call_price,  result.delta_call, result.gamma, result.theta, result.vega, result.rho),
                    ("weighted_put",  result.put_price,   None,              result.gamma, None,         result.vega, None),
                    ("bs_call",       result.bs_call,     result.delta_call, result.gamma, result.theta, result.vega, result.rho),
                    ("bs_put",        result.bs_put,      None,              result.gamma, None,         result.vega, None),
                    ("binomial_call", result.bin_call,    None,              None,         None,         None,        None),
                    ("binomial_put",  result.bin_put,     None,              None,         None,         None,        None),
                    ("mc_call",       result.mc_call,     None,              None,         None,         None,        None),
                    ("mc_put",        result.mc_put,      None,              None,         None,         None,        None),
                ]

                for model_type, option_value, delta, gamma, theta, vega, rho in records:
                    session.add(ORMResult(
                        case_id=case.id,
                        model_type=model_type,
                        option_value=option_value,
                        delta=delta,
                        gamma=gamma,
                        theta=theta,
                        vega=vega,
                        rho=rho,
                    ))

                return case.id

        except Exception:
            import traceback
            traceback.print_exc()
            return None
'''

new_content = before + new_save
path.write_text(new_content, encoding='utf-8')
print('書き込み完了')

# 検証
verify = path.read_text(encoding='utf-8')
count = verify.count('session.add(ORMResult(')
print(f'ORMResult追加数: {count} 件 (期待値: 8)')
for key in ['weighted_call', 'weighted_put', 'bs_call', 'bs_put', 'binomial_call', 'binomial_put', 'mc_call', 'mc_put']:
    mark = 'OK' if key in verify else 'NG'
    print(f'  [{mark}] {key}')
