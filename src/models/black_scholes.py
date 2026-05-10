"""
Black-Scholes オプション価格計算モデル
"""
import numpy as np
from scipy.stats import norm
from dataclasses import dataclass
from typing import Optional


@dataclass
class BlackScholesResult:
    """Black-Scholes 計算結果"""
    call_price: float
    put_price: float
    delta_call: float
    delta_put: float
    gamma: float
    vega: float
    theta_call: float
    theta_put: float
    rho_call: float
    rho_put: float
    d1: float
    d2: float


class BlackScholes:
    """
    Merton拡張 Black-Scholes モデル
    連続配当利回りに対応
    """

    def __init__(
        self,
        S: float,       # 株価
        K: float,       # 権利行使価格
        T: float,       # 満期までの期間（年）
        r: float,       # リスクフリーレート（年率）
        sigma: float,   # ボラティリティ（年率）
        q: float = 0.0  # 配当利回り（年率）
    ):
        # ── 入力バリデーション ──────────────────────────
        if S <= 0:
            raise ValueError(f"株価 S は正の値が必要です: S={S}")
        if K <= 0:
            raise ValueError(f"権利行使価格 K は正の値が必要です: K={K}")
        if T < 0:
            raise ValueError(f"満期 T は非負が必要です: T={T}")
        if sigma <= 0:
            raise ValueError(f"ボラティリティ sigma は正の値が必要です: sigma={sigma}")

        self.S = float(S)
        self.K = float(K)
        self.T = float(T)
        self.r = float(r)
        self.sigma = float(sigma)
        self.q = float(q)

        # T=0 の場合は即時行使価値を使用
        if T == 0:
            self._d1 = np.inf if S > K else (-np.inf if S < K else 0.0)
            self._d2 = self._d1
        else:
            self._d1 = (
                np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T
            ) / (sigma * np.sqrt(T))
            self._d2 = self._d1 - sigma * np.sqrt(T)

    @property
    def d1(self) -> float:
        return float(self._d1)

    @property
    def d2(self) -> float:
        return float(self._d2)

    # ── オプション価格 ──────────────────────────────────

    @property
    def call_price(self) -> float:
        if self.T == 0:
            return float(max(self.S - self.K, 0.0))
        return float(
            self.S * np.exp(-self.q * self.T) * norm.cdf(self._d1)
            - self.K * np.exp(-self.r * self.T) * norm.cdf(self._d2)
        )

    @property
    def put_price(self) -> float:
        if self.T == 0:
            return float(max(self.K - self.S, 0.0))
        return float(
            self.K * np.exp(-self.r * self.T) * norm.cdf(-self._d2)
            - self.S * np.exp(-self.q * self.T) * norm.cdf(-self._d1)
        )

    # ── Greeks ─────────────────────────────────────────

    @property
    def delta_call(self) -> float:
        if self.T == 0:
            return 1.0 if self.S > self.K else 0.0
        return float(np.exp(-self.q * self.T) * norm.cdf(self._d1))

    @property
    def delta_put(self) -> float:
        if self.T == 0:
            return -1.0 if self.S < self.K else 0.0
        return float(np.exp(-self.q * self.T) * (norm.cdf(self._d1) - 1))

    @property
    def gamma(self) -> float:
        if self.T == 0:
            return 0.0
        return float(
            np.exp(-self.q * self.T) * norm.pdf(self._d1)
            / (self.S * self.sigma * np.sqrt(self.T))
        )

    @property
    def vega(self) -> float:
        """1%ボラティリティ変化に対する価格変化"""
        if self.T == 0:
            return 0.0
        return float(
            self.S * np.exp(-self.q * self.T)
            * norm.pdf(self._d1) * np.sqrt(self.T) / 100
        )

    @property
    def theta_call(self) -> float:
        """1日あたりの時間的価値減少"""
        if self.T == 0:
            return 0.0
        term1 = -(self.S * np.exp(-self.q * self.T) * norm.pdf(self._d1) * self.sigma) \
                / (2 * np.sqrt(self.T))
        term2 = -self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(self._d2)
        term3 = self.q * self.S * np.exp(-self.q * self.T) * norm.cdf(self._d1)
        return float((term1 + term2 + term3) / 365)

    @property
    def theta_put(self) -> float:
        """1日あたりの時間的価値減少"""
        if self.T == 0:
            return 0.0
        term1 = -(self.S * np.exp(-self.q * self.T) * norm.pdf(self._d1) * self.sigma) \
                / (2 * np.sqrt(self.T))
        term2 = self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(-self._d2)
        term3 = -self.q * self.S * np.exp(-self.q * self.T) * norm.cdf(-self._d1)
        return float((term1 + term2 + term3) / 365)

    @property
    def rho_call(self) -> float:
        """1%金利変化に対する価格変化"""
        if self.T == 0:
            return 0.0
        return float(
            self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(self._d2) / 100
        )

    @property
    def rho_put(self) -> float:
        """1%金利変化に対する価格変化"""
        if self.T == 0:
            return 0.0
        return float(
            -self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(-self._d2) / 100
        )


    @property
    def greeks(self) -> dict:
        """全Greeksを辞書で返す（テスト・UI用ショートカット）"""
        return {
            "delta_call": self.delta_call,
            "delta_put":  self.delta_put,
            "gamma":      self.gamma,
            "vega":       self.vega,
            "theta_call": self.theta_call,
            "theta_put":  self.theta_put,
            "rho_call":   self.rho_call,
            "rho_put":    self.rho_put,
        }
    def calculate(self) -> BlackScholesResult:
        """全計算結果をまとめて返す"""
        return BlackScholesResult(
            call_price=self.call_price,
            put_price=self.put_price,
            delta_call=self.delta_call,
            delta_put=self.delta_put,
            gamma=self.gamma,
            vega=self.vega,
            theta_call=self.theta_call,
            theta_put=self.theta_put,
            rho_call=self.rho_call,
            rho_put=self.rho_put,
            d1=self.d1,
            d2=self.d2
        )

    def __repr__(self) -> str:
        return (
            f"BlackScholes(S={self.S}, K={self.K}, T={self.T:.4f}, "
            f"r={self.r:.4f}, sigma={self.sigma:.4f}, q={self.q:.4f})"
        )


# ── 後方互換エイリアス ──────────────────────────────────
# 既存テスト (BlackScholesModel) との互換性維持
BlackScholesModel = BlackScholes

