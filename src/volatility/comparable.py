"""
類似会社比較法によるボラティリティ推定モジュール
非上場企業向けオプション評価システム
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class ComparableCompany:
    """類似会社データ"""
    name: str
    observed_volatility: float      # 観測ボラティリティ（小数）
    equity_value: float             # 株式時価総額
    debt_value: float               # 負債総額
    beta: Optional[float] = None    # ベータ値（任意）
    industry: Optional[str] = None  # 業種

    @property
    def leverage_ratio(self):
        """負債比率 D/(D+E)"""
        total = self.equity_value + self.debt_value
        return self.debt_value / total if total > 0 else 0.0

    @property
    def debt_to_equity(self):
        """D/E比率"""
        return self.debt_value / self.equity_value if self.equity_value > 0 else 0.0


@dataclass
class ComparableResult:
    """類似会社比較法の計算結果"""
    estimated_volatility: float         # 推定ボラティリティ
    method: str                         # 使用手法
    comparable_count: int               # 使用した類似会社数
    comparable_volatilities: list       # 各社のボラティリティ
    weights: list                       # 重み
    unlevered_volatilities: list        # アンレバードボラティリティ
    relevered_volatility: float         # リレバード後ボラティリティ
    target_leverage: float              # 対象会社の負債比率
    mean_volatility: float             # 単純平均
    median_volatility: float           # 中央値
    std_volatility: float              # 標準偏差
    confidence_range: tuple            # 信頼区間（±1σ）


class ComparableVolatilityEstimator:
    """
    類似会社比較法によるボラティリティ推定

    Hamada式を使用してレバレッジ調整を実施:
        σ_unlevered = σ_equity / sqrt(1 + (1-t) * D/E)
        σ_relevered = σ_unlevered * sqrt(1 + (1-t) * D*/E*)

    Parameters
    ----------
    target_equity_value : float
        対象会社の株式価値
    target_debt_value : float
        対象会社の負債総額
    tax_rate : float
        実効税率（デフォルト: 0.30）
    """

    def __init__(
        self,
        target_equity_value: float,
        target_debt_value: float,
        tax_rate: float = 0.30
    ):
        if target_equity_value <= 0:
            raise ValueError('株式価値は正の値が必要です')
        if target_debt_value < 0:
            raise ValueError('負債は0以上が必要です')
        if not (0 <= tax_rate < 1):
            raise ValueError('税率は0以上1未満が必要です')

        self.target_equity = target_equity_value
        self.target_debt = target_debt_value
        self.tax_rate = tax_rate
        self.target_de_ratio = target_debt_value / target_equity_value
        self.target_leverage = (
            target_debt_value / (target_equity_value + target_debt_value)
            if (target_equity_value + target_debt_value) > 0 else 0.0
        )

    def _unlever_volatility(self, sigma_equity: float, de_ratio: float) -> float:
        """
        Hamada式でアンレバード（事業）ボラティリティを計算
        σ_asset = σ_equity / sqrt(1 + (1-t) * D/E)
        """
        hamada_factor = np.sqrt(1 + (1 - self.tax_rate) * de_ratio)
        return sigma_equity / hamada_factor

    def _relever_volatility(self, sigma_asset: float) -> float:
        """
        対象会社の資本構成でリレバード
        σ_equity = σ_asset * sqrt(1 + (1-t) * D*/E*)
        """
        hamada_factor = np.sqrt(1 + (1 - self.tax_rate) * self.target_de_ratio)
        return sigma_asset * hamada_factor

    def estimate(
        self,
        comparables: list,
        weighting: str = 'equal'
    ) -> ComparableResult:
        """
        類似会社からボラティリティを推定

        Parameters
        ----------
        comparables : list[ComparableCompany]
            類似会社リスト（最低2社推奨）
        weighting : str
            重み付け方法: 'equal'（均等）, 'market_cap'（時価総額加重）

        Returns
        -------
        ComparableResult
        """
        if len(comparables) < 1:
            raise ValueError('類似会社は1社以上必要です')

        comp_vols = []
        unlevered_vols = []
        weights = []

        for comp in comparables:
            # アンレバード
            sigma_u = self._unlever_volatility(
                comp.observed_volatility,
                comp.debt_to_equity
            )
            unlevered_vols.append(sigma_u)
            comp_vols.append(comp.observed_volatility)

            # 重みの計算
            if weighting == 'market_cap':
                weights.append(comp.equity_value)
            else:
                weights.append(1.0)

        # 正規化
        total_weight = sum(weights)
        norm_weights = [w / total_weight for w in weights]

        # 加重平均アンレバードボラティリティ
        avg_unlevered = sum(
            w * v for w, v in zip(norm_weights, unlevered_vols)
        )

        # リレバード
        relevered = self._relever_volatility(avg_unlevered)

        # 統計
        vols_array = np.array(comp_vols)
        mean_vol = float(np.mean(vols_array))
        median_vol = float(np.median(vols_array))
        std_vol = float(np.std(vols_array, ddof=1)) if len(vols_array) > 1 else 0.0
        conf_range = (
            max(0.0, relevered - std_vol),
            relevered + std_vol
        )

        return ComparableResult(
            estimated_volatility=relevered,
            method=f'comparable_{weighting}_weight',
            comparable_count=len(comparables),
            comparable_volatilities=comp_vols,
            weights=norm_weights,
            unlevered_volatilities=unlevered_vols,
            relevered_volatility=relevered,
            target_leverage=self.target_leverage,
            mean_volatility=mean_vol,
            median_volatility=median_vol,
            std_volatility=std_vol,
            confidence_range=conf_range
        )

    def sensitivity_analysis(
        self,
        comparables: list,
        tax_rate_range: Optional[list] = None
    ) -> pd.DataFrame:
        """税率感応度分析"""
        if tax_rate_range is None:
            tax_rate_range = [0.20, 0.25, 0.30, 0.35, 0.40]

        records = []
        for t in tax_rate_range:
            original_tax = self.tax_rate
            self.tax_rate = t
            result = self.estimate(comparables)
            records.append({
                'tax_rate': t,
                'estimated_volatility': result.estimated_volatility,
                'unlevered_avg': np.mean(result.unlevered_volatilities)
            })
            self.tax_rate = original_tax

        return pd.DataFrame(records)
