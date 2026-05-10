"""
Pydantic v2 によるパラメータ入力バリデーション
未上場企業オプション評価に適した制約値を設定
"""

from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional, Literal
from enum import Enum


# ─────────────────────────────────────────
# 列挙型定義
# ─────────────────────────────────────────
class OptionType(str, Enum):
    CALL = "call"
    PUT  = "put"

class OptionStyle(str, Enum):
    EUROPEAN = "european"
    AMERICAN = "american"

class PricingModel(str, Enum):
    BLACK_SCHOLES = "black_scholes"
    BINOMIAL      = "binomial"

class VolatilityMethod(str, Enum):
    COMPARABLE    = "comparable"
    REVENUE_BASED = "revenue_based"
    VC_METHOD     = "vc_method"
    MANUAL        = "manual"

class IndustryType(str, Enum):
    TECHNOLOGY    = "technology"
    BIOTECH       = "biotech"
    RETAIL        = "retail"
    MANUFACTURING = "manufacturing"
    FINANCE       = "finance"
    REAL_ESTATE   = "real_estate"
    ENERGY        = "energy"
    GENERAL       = "general"

class StartupStage(str, Enum):
    SEED      = "seed"
    SERIES_A  = "series_a"
    SERIES_B  = "series_b"
    SERIES_C  = "series_c"
    PRE_IPO   = "pre_ipo"
    GROWTH    = "growth"


# ─────────────────────────────────────────
# オプションパラメータ バリデーター
# ─────────────────────────────────────────
class OptionParameters(BaseModel):
    """オプション評価の入力パラメータ"""
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "stock_price":    100.0,
                "strike_price":   100.0,
                "time_to_expiry": 1.0,
                "risk_free_rate": 0.05,
                "volatility":     0.30,
                "option_type":    "call",
                "option_style":   "european",
            }
        }
    )

    stock_price:    float = Field(gt=0,    description="原資産価格 S（円 or 倍数）")
    strike_price:   float = Field(gt=0,    description="行使価格 K")
    time_to_expiry: float = Field(gt=0, le=30.0, description="残存期間 T（年）: 0超〜30年")
    risk_free_rate: float = Field(ge=0, le=0.20,  description="無リスク金利 r: 0%〜20%")
    volatility:     float = Field(gt=0, le=5.0,   description="ボラティリティ σ: 0超〜500%")
    dividend_yield: float = Field(ge=0, le=1.0,   default=0.0, description="配当利回り q")

    option_type:  OptionType  = Field(default=OptionType.CALL)
    option_style: OptionStyle = Field(default=OptionStyle.EUROPEAN)
    pricing_model: PricingModel = Field(default=PricingModel.BLACK_SCHOLES)
    binomial_steps: int = Field(default=200, ge=10, le=1000,
                                description="二項ツリーのステップ数")

    @model_validator(mode="after")
    def check_moneyness(self) -> "OptionParameters":
        """極端なモネーネスに対する警告（エラーではない）"""
        ratio = self.stock_price / self.strike_price
        if ratio < 0.1 or ratio > 10.0:
            import warnings
            warnings.warn(
                f"S/K = {ratio:.2f} は極端な値です（Deep ITM/OTM）。"
                "計算精度が低下する可能性があります。",
                UserWarning, stacklevel=2
            )
        return self


# ─────────────────────────────────────────
# 評価案件 バリデーター
# ─────────────────────────────────────────
class CaseCreateRequest(BaseModel):
    """評価案件作成リクエスト"""
    name:        str = Field(min_length=1, max_length=200, description="案件名")
    company:     str = Field(min_length=1, max_length=200, description="対象会社名")
    industry:    Optional[IndustryType] = Field(default=None, description="業種")
    stage:       Optional[StartupStage] = Field(default=None, description="ステージ")
    description: Optional[str]          = Field(default=None, max_length=2000)


# ─────────────────────────────────────────
# ボラティリティ推定入力 バリデーター
# ─────────────────────────────────────────
class ComparableCompany(BaseModel):
    """類似会社データ"""
    name:        str   = Field(min_length=1, max_length=100)
    volatility:  float = Field(gt=0, le=5.0, description="観測ボラティリティ")
    debt:        float = Field(ge=0,          description="有利子負債")
    equity:      float = Field(gt=0,          description="株主資本（時価）")
    tax_rate:    float = Field(ge=0, le=0.60, default=0.30)
    market_cap:  Optional[float] = Field(default=None, ge=0)


class ComparableVolInput(BaseModel):
    """類似会社比較法 入力"""
    companies:    list[ComparableCompany] = Field(min_length=1)
    target_debt:  float = Field(ge=0, description="対象会社 有利子負債")
    target_equity: float = Field(gt=0, description="対象会社 株主資本")
    target_tax_rate: float = Field(ge=0, le=0.60, default=0.30)
    use_market_cap_weight: bool = Field(default=False)


class RevenueVolInput(BaseModel):
    """収益ベース推定法 入力"""
    revenues:  list[float] = Field(min_length=3, description="売上高系列（時系列順）")
    ebitdas:   list[float] = Field(min_length=3, description="EBITDA系列")
    interest_expense: float = Field(ge=0, default=0.0)
    ebit:             float = Field(description="EBIT（直近期）")
    industry:  IndustryType = Field(default=IndustryType.GENERAL)

    @model_validator(mode="after")
    def check_length_match(self) -> "RevenueVolInput":
        if len(self.revenues) != len(self.ebitdas):
            raise ValueError("revenues と ebitdas の期数が一致しません")
        return self


class VCMethodInput(BaseModel):
    """VCメソッド 入力"""
    current_value:  float = Field(gt=0, description="現在価値（投資額）")
    exit_value:     float = Field(gt=0, description="期待イグジット価値")
    time_horizon:   float = Field(gt=0, le=20.0, description="投資期間（年）")
    success_prob:   float = Field(gt=0, le=1.0, description="成功確率 0〜1")
    stage:          StartupStage = Field(default=StartupStage.SERIES_A)
