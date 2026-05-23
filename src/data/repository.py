# src/data/repository.py
"""
Repository pattern - data access layer
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.data.models import ValuationCase, ComparableTicker


class ValuationCaseRepository:
    """ValuationCase CRUD operations"""

    def __init__(self, session: Session):
        self.session = session

    # ?? Create ??????????????????????????????
    def create(
        self,
        case_name: str,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str = "call",
        dividend_yield: float = 0.0,
        binomial_steps: int = 100,
        mc_simulations: int = 10000,
    ) -> ValuationCase:
        case = ValuationCase(
            case_name=case_name,
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type=option_type,
            dividend_yield=dividend_yield,
            binomial_steps=binomial_steps,
            mc_simulations=mc_simulations,
        )
        self.session.add(case)
        self.session.flush()
        return case

    # ?? Read ????????????????????????????????
    def get_by_id(self, case_id: int) -> Optional[ValuationCase]:
        return self.session.get(ValuationCase, case_id)

    def get_all(self) -> list:
        stmt = (
            select(ValuationCase)
            .order_by(ValuationCase.created_at.desc())
        )
        return list(self.session.scalars(stmt))


    def get_by_id_as_dict(self, case_id: int) -> Optional[dict]:
        """???????????????dict?????"""
        case = self.session.get(ValuationCase, case_id)
        if case is None:
            return None
        return {
            "id":             case.id,
            "case_name":      case.case_name,
            "stock_price":    case.stock_price,
            "strike_price":   case.strike_price,
            "risk_free_rate": case.risk_free_rate,
            "volatility":     case.volatility,
            "time_to_expiry": case.time_to_expiry,
            "option_type":    case.option_type,
            "dividend_yield": case.dividend_yield,
            "binomial_steps": case.binomial_steps,
            "mc_simulations": case.mc_simulations,
            "bs_price":       case.bs_price,
            "binomial_price": case.binomial_price,
            "mc_price":       case.mc_price,
            "weighted_price": case.weighted_price,
            "delta":          case.delta,
            "gamma":          case.gamma,
            "theta":          case.theta,
            "vega":           case.vega,
            "rho":            case.rho,
            "created_at":     case.created_at,
            "updated_at":     case.updated_at,
        }

    # ?? Update ??????????????????????????????
    def update(self, case_id: int, data: dict) -> Optional[ValuationCase]:
        case = self.get_by_id(case_id)
        if case is None:
            return None
        allowed = {
            "case_name", "stock_price", "strike_price", "risk_free_rate",
            "volatility", "time_to_expiry", "option_type", "dividend_yield",
            "binomial_steps", "mc_simulations",
            "bs_price", "binomial_price", "mc_price", "weighted_price",
            "delta", "gamma", "theta", "vega", "rho",
        }
        for key, value in data.items():
            if key in allowed:
                setattr(case, key, value)
        return case

    # ?? Delete ??????????????????????????????
    def delete(self, case_id: int) -> bool:
        case = self.get_by_id(case_id)
        if case is None:
            return False
        self.session.delete(case)
        return True


class ComparableTickerRepository:
    """ComparableTicker CRUD operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        case_id: int,
        ticker: str,
        volatility: float,
        company_label: str = "",
        vol_period: str = "1y",
        fetch_ok: bool = True,
        error_msg: str = "",
    ) -> ComparableTicker:
        row = ComparableTicker(
            case_id=case_id,
            ticker=ticker,
            volatility=volatility,
            company_label=company_label,
            vol_period=vol_period,
            fetch_ok=fetch_ok,
            error_msg=error_msg,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get_by_case(self, case_id: int) -> list:
        stmt = (
            select(ComparableTicker)
            .where(ComparableTicker.case_id == case_id)
            .order_by(ComparableTicker.id)
        )
        return list(self.session.scalars(stmt))

    def delete_by_case(self, case_id: int) -> int:
        rows = self.get_by_case(case_id)
        for row in rows:
            self.session.delete(row)
        return len(rows)
