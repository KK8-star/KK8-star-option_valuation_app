"""
VCメソッド（ベンチャーキャピタル法）によるボラティリティ推定
スタートアップ・成長企業向け
非上場企業向けオプション評価システム
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class VCMethodResult:
    """VC法の計算結果"""
    estimated_volatility: float
    method: str
    implied_return: float               # 投資収益率から逆算
    investment_horizon: float           # 投資期間（年）
    exit_multiple: float               # イグジット倍率
    success_probability: float         # 成功確率
    failure_probability: float         # 失敗確率（全損リスク）
    adjusted_volatility: float         # 成功確率調整済みボラティリティ
    stage_multiplier: float            # ステージ調整係数
    stage: str                         # 投資ステージ
    confidence_low: float
    confidence_high: float


class VCMethodVolatilityEstimator:
    """
    VCメソッドによるボラティリティ推定

    スタートアップの投資収益率・成功確率から
    オプション評価に使用するボラティリティを逆算

    アプローチ:
    1. 期待IRRから期待リターンを計算
    2. 成功/失敗の二値分布を仮定
    3. 実現ボラティリティを推定
    4. 投資ステージによる調整

    Parameters
    ----------
    current_valuation : float
        現在の企業価値（Pre-money）
    exit_valuation : float
        期待イグジット時の企業価値
    investment_horizon : float
        投資期間（年）
    success_probability : float
        成功確率（0〜1）
    stage : str
        投資ステージ: 'seed', 'series_a', 'series_b',
                      'series_c', 'pre_ipo', 'growth'
    """

    # 投資ステージ別ボラティリティ調整係数
    STAGE_MULTIPLIERS = {
        'seed':      2.00,   # シード：最高リスク
        'series_a':  1.60,   # シリーズA
        'series_b':  1.30,   # シリーズB
        'series_c':  1.10,   # シリーズC
        'pre_ipo':   0.90,   # IPO直前
        'growth':    1.20,   # 成長期
        'general':   1.30,   # 一般
    }

    # ステージ別デフォルト成功確率（参考値）
    DEFAULT_SUCCESS_PROB = {
        'seed':      0.10,
        'series_a':  0.20,
        'series_b':  0.35,
        'series_c':  0.50,
        'pre_ipo':   0.70,
        'growth':    0.55,
        'general':   0.40,
    }

    def __init__(
        self,
        current_valuation: float,
        exit_valuation: float,
        investment_horizon: float,
        success_probability: Optional[float] = None,
        stage: str = 'general'
    ):
        if current_valuation <= 0:
            raise ValueError('現在の企業価値は正の値が必要です')
        if exit_valuation <= 0:
            raise ValueError('イグジット価値は正の値が必要です')
        if investment_horizon <= 0:
            raise ValueError('投資期間は正の値が必要です')

        self.current_val = current_valuation
        self.exit_val = exit_valuation
        self.horizon = investment_horizon
        self.stage = stage
        self.stage_multiplier = self.STAGE_MULTIPLIERS.get(stage, 1.30)

        # 成功確率
        if success_probability is not None:
            if not (0 < success_probability <= 1):
                raise ValueError('成功確率は (0, 1] の範囲が必要です')
            self.success_prob = success_probability
        else:
            self.success_prob = self.DEFAULT_SUCCESS_PROB.get(stage, 0.40)

    def _calc_implied_volatility(self) -> float:
        """
        イグジット倍率から対数正規分布の標準偏差を逆算
        E[X] = S * exp(mu * T)  を解く

        成功時のリターン分布を対数正規と仮定:
        σ = sqrt(ln(exit/current)) / sqrt(T)
        """
        if self.exit_val > self.current_val:
            log_return = np.log(self.exit_val / self.current_val)
            return float(np.sqrt(abs(log_return) / self.horizon))
        return 0.50  # デフォルト

    def _adjust_for_failure_risk(self, base_vol: float) -> float:
        """
        失敗確率（全損リスク）を考慮したボラティリティ調整

        失敗リスクを含む有効ボラティリティ:
        σ_adj = σ * (1 + (1 - p_success) * k)
        k: 失敗リスク増幅係数
        """
        failure_prob = 1 - self.success_prob
        k = 2.0  # 失敗リスク増幅係数（実務上の経験値）
        adjustment = 1 + failure_prob * k
        return base_vol * adjustment

    def estimate(self) -> VCMethodResult:
        """ボラティリティを推定"""
        # イグジット倍率
        exit_multiple = self.exit_val / self.current_val

        # 期待IRR（対数）
        implied_return = float(
            np.log(exit_multiple) / self.horizon
        ) if exit_multiple > 0 else 0.0

        # 基本ボラティリティ
        base_vol = self._calc_implied_volatility()

        # 失敗リスク調整
        adj_vol = self._adjust_for_failure_risk(base_vol)

        # ステージ調整
        estimated = adj_vol * self.stage_multiplier

        # 合理的な範囲にクリップ（10%〜200%）
        estimated = float(np.clip(estimated, 0.10, 2.00))

        # 信頼区間（±40%：スタートアップは不確実性大）
        conf_low  = max(0.10, estimated * 0.60)
        conf_high = min(2.00, estimated * 1.40)

        return VCMethodResult(
            estimated_volatility=estimated,
            method='vc_method',
            implied_return=implied_return,
            investment_horizon=self.horizon,
            exit_multiple=exit_multiple,
            success_probability=self.success_prob,
            failure_probability=1 - self.success_prob,
            adjusted_volatility=adj_vol,
            stage_multiplier=self.stage_multiplier,
            stage=self.stage,
            confidence_low=conf_low,
            confidence_high=conf_high
        )

    def compare_stages(self) -> pd.DataFrame:
        """全ステージでの推定値比較"""
        records = []
        for stage, mult in self.STAGE_MULTIPLIERS.items():
            orig_stage = self.stage
            orig_mult = self.stage_multiplier
            orig_prob = self.success_prob
            self.stage = stage
            self.stage_multiplier = mult
            self.success_prob = self.DEFAULT_SUCCESS_PROB.get(stage, 0.40)
            result = self.estimate()
            records.append({
                'stage':                stage,
                'success_probability':  self.success_prob,
                'stage_multiplier':     mult,
                'estimated_volatility': result.estimated_volatility
            })
            self.stage = orig_stage
            self.stage_multiplier = orig_mult
            self.success_prob = orig_prob
        return pd.DataFrame(records)
