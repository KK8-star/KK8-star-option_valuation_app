"""
収益ベースのボラティリティ推定モジュール
売上高・EBITDAの変動性から株式ボラティリティを推定
非上場企業向けオプション評価システム
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class RevenueBasedResult:
    """収益ベース推定の結果"""
    estimated_volatility: float
    method: str
    revenue_volatility: float           # 売上高ボラティリティ
    ebitda_volatility: Optional[float]  # EBITDAボラティリティ
    operating_leverage: float           # 営業レバレッジ
    financial_leverage: float           # 財務レバレッジ
    total_leverage: float               # 総合レバレッジ
    years_used: int                     # 使用データ年数
    growth_rates: list                  # 売上成長率
    confidence_low: float
    confidence_high: float


class RevenueBasedVolatilityEstimator:
    """
    収益変動性ベースのボラティリティ推定

    アプローチ:
    1. 売上高の年次変動率からボラティリティを計算
    2. 営業レバレッジ・財務レバレッジで増幅
    3. 業種マルチプルで調整

    Parameters
    ----------
    revenue_history : list[float]
        過去の年次売上高（古い順、最低3期分推奨）
    ebitda_history : list[float], optional
        過去のEBITDA（任意、より精度向上）
    debt_value : float
        負債総額
    equity_value : float
        株式価値（推定）
    tax_rate : float
        実効税率
    """

    # 業種別ボラティリティ調整係数（参考値）
    INDUSTRY_MULTIPLIERS = {
        'technology':       1.30,
        'biotech':          1.60,
        'retail':           1.10,
        'manufacturing':    1.00,
        'financial':        1.20,
        'real_estate':      0.90,
        'utilities':        0.70,
        'general':          1.00,
    }

    def __init__(
        self,
        revenue_history: list,
        ebitda_history: Optional[list] = None,
        debt_value: float = 0.0,
        equity_value: float = 1.0,
        tax_rate: float = 0.30,
        industry: str = 'general'
    ):
        if len(revenue_history) < 2:
            raise ValueError('売上高データは2期分以上必要です（3期以上推奨）')
        if any(r <= 0 for r in revenue_history):
            raise ValueError('売上高はすべて正の値が必要です')

        self.revenues = revenue_history
        self.ebitda = ebitda_history
        self.debt = debt_value
        self.equity = equity_value
        self.tax_rate = tax_rate
        self.industry = industry
        self.industry_multiplier = self.INDUSTRY_MULTIPLIERS.get(industry, 1.0)

    def _calculate_growth_volatility(self, values: list) -> tuple:
        """年次成長率とその標準偏差（ボラティリティ）を計算"""
        growth_rates = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                g = np.log(values[i] / values[i - 1])  # 対数成長率
                growth_rates.append(g)

        if len(growth_rates) == 0:
            return 0.0, []

        vol = float(np.std(growth_rates, ddof=1)) if len(growth_rates) > 1 else abs(growth_rates[0])
        return vol, growth_rates

    def _calc_operating_leverage(self) -> float:
        """
        営業レバレッジの推定
        DOL = (売上高変動率) / (EBITDA変動率) の近似
        データがない場合は業種デフォルト値を使用
        """
        if self.ebitda and len(self.ebitda) >= 2:
            rev_vol, _ = self._calculate_growth_volatility(self.revenues)
            ebitda_vol, _ = self._calculate_growth_volatility(self.ebitda)
            if rev_vol > 0:
                return min(ebitda_vol / rev_vol, 5.0)  # 上限5倍
        # デフォルト（業種によって異なるが一般的に1.5〜3.0）
        return 2.0

    def _calc_financial_leverage(self) -> float:
        """
        財務レバレッジ = 1 + (1-t) * D/E
        """
        if self.equity > 0:
            return 1.0 + (1 - self.tax_rate) * (self.debt / self.equity)
        return 1.0

    def estimate(self) -> RevenueBasedResult:
        """ボラティリティを推定"""
        # 売上高ボラティリティ
        rev_vol, growth_rates = self._calculate_growth_volatility(self.revenues)

        # EBITDAボラティリティ
        ebitda_vol = None
        if self.ebitda and len(self.ebitda) >= 2:
            ebitda_vol, _ = self._calculate_growth_volatility(self.ebitda)

        # レバレッジ
        op_lev = self._calc_operating_leverage()
        fin_lev = self._calc_financial_leverage()
        total_lev = op_lev * fin_lev

        # 株式ボラティリティ推定
        base_vol = ebitda_vol if ebitda_vol is not None else rev_vol
        estimated = base_vol * total_lev * self.industry_multiplier

        # 合理的な範囲にクリップ（5%〜150%）
        estimated = float(np.clip(estimated, 0.05, 1.50))

        # 信頼区間（±30%）
        conf_low  = max(0.05, estimated * 0.70)
        conf_high = min(1.50, estimated * 1.30)

        return RevenueBasedResult(
            estimated_volatility=estimated,
            method='revenue_based',
            revenue_volatility=rev_vol,
            ebitda_volatility=ebitda_vol,
            operating_leverage=op_lev,
            financial_leverage=fin_lev,
            total_leverage=total_lev,
            years_used=len(self.revenues) - 1,
            growth_rates=[float(g) for g in growth_rates],
            confidence_low=conf_low,
            confidence_high=conf_high
        )

    def scenario_analysis(self) -> pd.DataFrame:
        """楽観・基本・悲観シナリオ"""
        base = self.estimate()
        records = [
            {
                'scenario':             '悲観（Pessimistic）',
                'operating_leverage':   base.operating_leverage * 1.3,
                'estimated_volatility': min(1.50, base.estimated_volatility * 1.3)
            },
            {
                'scenario':             '基本（Base）',
                'operating_leverage':   base.operating_leverage,
                'estimated_volatility': base.estimated_volatility
            },
            {
                'scenario':             '楽観（Optimistic）',
                'operating_leverage':   base.operating_leverage * 0.7,
                'estimated_volatility': max(0.05, base.estimated_volatility * 0.7)
            },
        ]
        return pd.DataFrame(records)
