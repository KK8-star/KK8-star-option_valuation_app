"""
ValuationInput - オプション評価パラメータの入力データクラス

new_valuation.py との互換性維持のために提供。
実際の計算は ValuationService または各モデルクラスが担う。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class ValuationInput:
    """
    オプション評価に必要な入力パラメータをまとめたデータクラス。

    Attributes
    ----------
    company_name    : 評価対象会社名
    stock_price     : 現在の株価 / 企業価値 (S)
    strike_price    : 権利行使価格 (K)
    risk_free_rate  : リスクフリーレート（年率, 小数）
    volatility      : ボラティリティ（年率, 小数）
    T               : 満期までの期間（年）
    dividend_yield  : 配当利回り（年率, 小数）
    industry        : 業種コード
    valuation_date  : 評価基準日
    currency        : 通貨コード
    expiry_date     : 満期日（省略時は valuation_date + T年から逆算）
    notes           : 備考
    """
    company_name: str
    stock_price: float
    strike_price: float
    risk_free_rate: float
    volatility: float
    T: float

    dividend_yield: float = 0.0
    industry: str = "other"
    valuation_date: date = field(default_factory=date.today)
    currency: str = "JPY"
    expiry_date: Optional[date] = None
    notes: str = ""

    def __post_init__(self) -> None:
        """入力値のバリデーション"""
        if self.stock_price <= 0:
            raise ValueError(f"株価 S は正の値が必要です: S={self.stock_price}")
        if self.strike_price <= 0:
            raise ValueError(f"権利行使価格 K は正の値が必要です: K={self.strike_price}")
        if self.T < 0:
            raise ValueError(f"満期 T は非負が必要です: T={self.T}")
        if self.volatility <= 0:
            raise ValueError(f"ボラティリティ σ は正の値が必要です: σ={self.volatility}")
        if not (0.0 <= self.dividend_yield < 1.0):
            raise ValueError(f"配当利回り q は 0〜1 の範囲が必要です: q={self.dividend_yield}")

    @property
    def moneyness(self) -> float:
        """モネーネス S/K"""
        return self.stock_price / self.strike_price

    @property
    def is_call_itm(self) -> bool:
        """コールオプションがイン・ザ・マネーかどうか"""
        return self.stock_price > self.strike_price

    @property
    def is_put_itm(self) -> bool:
        """プットオプションがイン・ザ・マネーかどうか"""
        return self.stock_price < self.strike_price

    def to_dict(self) -> dict:
        """ValuationService.calculate() のキーワード引数形式に変換"""
        return {
            "company_name": self.company_name,
            "stock_price": self.stock_price,
            "strike_price": self.strike_price,
            "risk_free_rate": self.risk_free_rate,
            "volatility": self.volatility,
            "T": self.T,
            "dividend_yield": self.dividend_yield,
            "industry": self.industry,
            "valuation_date": self.valuation_date,
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ValuationInput":
        """辞書から ValuationInput を生成"""
        return cls(
            company_name=data["company_name"],
            stock_price=float(data["stock_price"]),
            strike_price=float(data["strike_price"]),
            risk_free_rate=float(data["risk_free_rate"]),
            volatility=float(data["volatility"]),
            T=float(data["T"]),
            dividend_yield=float(data.get("dividend_yield", 0.0)),
            industry=data.get("industry", "other"),
            valuation_date=data.get("valuation_date", date.today()),
            currency=data.get("currency", "JPY"),
            expiry_date=data.get("expiry_date"),
            notes=data.get("notes", ""),
        )
