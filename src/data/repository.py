"""
リポジトリパターンによるデータアクセス層
ビジネスロジックとDB操作を分離
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from src.data.models import ValuationCase, ValuationParameter, ValuationResult


# ─────────────────────────────────────────
# 評価案件リポジトリ
# ─────────────────────────────────────────
class ValuationCaseRepository:
    """ValuationCase CRUD操作"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        name: str,
        company: str,
        industry: str = None,
        stage: str = None,
        description: str = None,
    ) -> ValuationCase:
        case = ValuationCase(
            name=name,
            company=company,
            industry=industry,
            stage=stage,
            description=description,
        )
        self.session.add(case)
        self.session.flush()   # IDを確定させる（commitは呼び出し元）
        return case

    def get_by_id(self, case_id: int) -> Optional[ValuationCase]:
        return self.session.get(ValuationCase, case_id)

    def get_all_active(self) -> list[ValuationCase]:
        stmt = (
            select(ValuationCase)
            .where(ValuationCase.is_active == True)
            .order_by(ValuationCase.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def soft_delete(self, case_id: int) -> bool:
        case = self.get_by_id(case_id)
        if case is None:
            return False
        case.is_active = False
        case.updated_at = datetime.utcnow()
        return True

    def update(self, case_id: int, **kwargs) -> Optional[ValuationCase]:
        case = self.get_by_id(case_id)
        if case is None:
            return None
        allowed = {"name", "company", "industry", "stage", "description"}
        for key, value in kwargs.items():
            if key in allowed:
                setattr(case, key, value)
        case.updated_at = datetime.utcnow()
        return case


# ─────────────────────────────────────────
# パラメータリポジトリ
# ─────────────────────────────────────────
class ValuationParameterRepository:
    """ValuationParameter CRUD操作"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        case_id: int,
        stock_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        dividend_yield: float = 0.0,
        vol_method: str = None,
        vol_params: dict = None,
    ) -> ValuationParameter:
        param = ValuationParameter(
            case_id=case_id,
            stock_price=stock_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            dividend_yield=dividend_yield,
            vol_method=vol_method,
            vol_params=vol_params or {},
        )
        self.session.add(param)
        self.session.flush()
        return param

    def get_by_case(self, case_id: int) -> list[ValuationParameter]:
        stmt = (
            select(ValuationParameter)
            .where(ValuationParameter.case_id == case_id)
            .order_by(ValuationParameter.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def get_latest_by_case(self, case_id: int) -> Optional[ValuationParameter]:
        results = self.get_by_case(case_id)
        return results[0] if results else None


# ─────────────────────────────────────────
# 結果リポジトリ
# ─────────────────────────────────────────
class ValuationResultRepository:
    """ValuationResult CRUD操作"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        case_id: int,
        model: str,
        option_type: str,
        option_style: str,
        option_price: float,
        parameter_id: int = None,
        delta: float = None,
        gamma: float = None,
        theta: float = None,
        vega: float = None,
        rho: float = None,
        notes: str = None,
    ) -> ValuationResult:
        result = ValuationResult(
            case_id=case_id,
            parameter_id=parameter_id,
            model=model,
            option_type=option_type,
            option_style=option_style,
            option_price=option_price,
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
            notes=notes,
        )
        self.session.add(result)
        self.session.flush()
        return result

    def get_by_case(self, case_id: int) -> list[ValuationResult]:
        stmt = (
            select(ValuationResult)
            .where(ValuationResult.case_id == case_id)
            .order_by(ValuationResult.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def get_latest_by_case(self, case_id: int) -> Optional[ValuationResult]:
        results = self.get_by_case(case_id)
        return results[0] if results else None
