"""
volatility_estimator.py - 非上場企業のボラティリティ推定ユーティリティ
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None  # type: ignore
    YFINANCE_AVAILABLE = False

try:
    from scipy import stats as _scipy_stats
    SCIPY_AVAILABLE = True
except ImportError:
    _scipy_stats = None  # type: ignore
    SCIPY_AVAILABLE = False


# ============================================================
# 業種別ボラティリティベンチマーク (年率)
# ============================================================
INDUSTRY_VOLATILITY: dict[str, float] = {
    "technology":    0.45,
    "tech":          0.45,
    "healthcare":    0.35,
    "financial":     0.30,
    "finance":       0.30,
    "real_estate":   0.25,
    "consumer":      0.30,
    "industrial":    0.28,
    "energy":        0.40,
    "utilities":     0.20,
    "materials":     0.32,
    "communication": 0.38,
    "default":       0.35,
}


# ============================================================
# データクラス
# ============================================================
@dataclass
class VolatilityResult:
    """
    ボラティリティ推定結果

    Attributes
    ----------
    volatility          : 推定ボラティリティ（年率）
    method              : 推定手法名
    confidence          : 推定の信頼度 [0, 1]
    confidence_interval : (下限, 上限) の 95% 信頼区間
    details             : 追加情報
    """
    volatility: float
    method: str
    confidence: float = 1.0
    confidence_interval: tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if not np.isfinite(self.volatility):
            raise ValueError(f"volatility must be a finite number, got {self.volatility}")
        if not (0 < self.volatility < 10):
            raise ValueError(f"volatility must be between 0 and 10, got {self.volatility}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class PeerData:
    """ピアカンパニーの個別データ"""
    ticker: str
    volatility: float
    success: bool = True
    error: Optional[str] = None
    company_name: str = ""


@dataclass
class PeerVolatilitySummary:
    """
    ピアカンパニー群のボラティリティサマリー

    Attributes
    ----------
    tickers           : 処理対象ティッカーリスト
    mean_volatility   : 成功ティッカーの平均ボラティリティ
    median_volatility : 成功ティッカーの中央値ボラティリティ
    std_volatility    : 成功ティッカーの標準偏差
    failed_tickers    : 取得失敗ティッカーのリスト
    peers             : 全ピアデータ
    """
    tickers: list[str] = field(default_factory=list)
    mean_volatility: float = 0.0
    median_volatility: float = 0.0
    std_volatility: float = 0.0
    failed_tickers: list[str] = field(default_factory=list)
    peers: list[PeerData] = field(default_factory=list)

    @classmethod
    def from_peers(cls, peers: list[PeerData]) -> "PeerVolatilitySummary":
        tickers    = [p.ticker for p in peers]
        failed     = [p.ticker for p in peers if not p.success]
        successful = [p for p in peers if p.success]

        if successful:
            vols       = [p.volatility for p in successful]
            mean_vol   = float(np.mean(vols))
            median_vol = float(np.median(vols))
            std_vol    = float(np.std(vols, ddof=1)) if len(vols) > 1 else 0.0
        else:
            mean_vol = median_vol = std_vol = 0.0

        return cls(
            tickers=tickers,
            mean_volatility=mean_vol,
            median_volatility=median_vol,
            std_volatility=std_vol,
            failed_tickers=failed,
            peers=peers,
        )


# ============================================================
# VolatilityEstimator
# ============================================================
class VolatilityEstimator:
    """
    非上場企業向けボラティリティ推定クラス

    Parameters
    ----------
    industry : str
        業種コード (INDUSTRY_VOLATILITY のキー)。省略時は 'default'。
    """

    def __init__(self, industry: str = "default"):
        self.industry = (industry or "default").lower()
        self._last_historical_result: Optional[VolatilityResult] = None

    # ----------------------------------------------------------
    # 内部: リターン列の計算
    # ----------------------------------------------------------
    @staticmethod
    def _compute_log_returns(
        arr: np.ndarray,
        is_returns: bool,
    ) -> np.ndarray:
        """
        価格列またはリターン列から対数リターン配列を返す。

        自動判定:
          全要素の絶対値 < 0.5 かつ 正負混在 → リターン列と見なす
        """
        if not is_returns:
            if np.all(np.abs(arr) < 0.5) and np.any(arr < 0) and np.any(arr > 0):
                is_returns = True

        if is_returns:
            return arr.copy()

        if len(arr) < 2:
            raise ValueError("prices must have at least 2 data points")

        with np.errstate(divide="ignore", invalid="ignore"):
            log_ret = np.log(arr[1:] / arr[:-1])

        return log_ret[np.isfinite(log_ret)]

    # ----------------------------------------------------------
    # 1. 過去価格 / リターンからの計算 → float
    # ----------------------------------------------------------
    def calculate_historical_volatility(
        self,
        prices_or_returns: list[float] | np.ndarray,
        annualize: bool = True,
        annualization_factor: int = 252,
        is_returns: bool = False,
    ) -> float:
        """
        価格列またはリターン列から年率ボラティリティ(float)を計算する。

        詳細な結果が必要な場合は calculate_historical_volatility_result() を使用。
        """
        result = self.calculate_historical_volatility_result(
            prices_or_returns,
            annualize=annualize,
            annualization_factor=annualization_factor,
            is_returns=is_returns,
        )
        return result.volatility

    def calculate_historical_volatility_result(
        self,
        prices_or_returns: list[float] | np.ndarray,
        annualize: bool = True,
        annualization_factor: int = 252,
        is_returns: bool = False,
    ) -> VolatilityResult:
        """
        価格列またはリターン列から VolatilityResult を計算する。
        """
        arr     = np.asarray(prices_or_returns, dtype=float)
        log_ret = self._compute_log_returns(arr, is_returns)

        if len(log_ret) < 2:
            raise ValueError("Need at least 2 valid return observations")

        daily_std = float(np.std(log_ret, ddof=1))
        vol       = daily_std * np.sqrt(annualization_factor) if annualize else daily_std

        if not np.isfinite(vol) or vol <= 0:
            raise ValueError(f"Computed volatility is invalid: {vol}")

        # 95% 信頼区間 (Chi-square 近似)
        n = len(log_ret)
        if SCIPY_AVAILABLE and _scipy_stats is not None:
            alpha    = 0.05
            chi2_low  = _scipy_stats.chi2.ppf(alpha / 2,     df=n - 1)
            chi2_high = _scipy_stats.chi2.ppf(1 - alpha / 2, df=n - 1)
        else:
            chi2_low  = max((n - 1) * 0.5, 1e-9)
            chi2_high = (n - 1) * 1.5

        factor   = np.sqrt(annualization_factor) if annualize else 1.0
        ci_low   = float(daily_std * np.sqrt((n - 1) / chi2_high) * factor)
        ci_high  = float(daily_std * np.sqrt((n - 1) / chi2_low)  * factor)

        confidence = float(np.clip(0.5 + 0.4 * (n - 30) / max(252 - 30, 1), 0.5, 0.9))

        result = VolatilityResult(
            volatility=vol,
            method="historical",
            confidence=confidence,
            confidence_interval=(ci_low, ci_high),
            details={
                "n_observations":       n,
                "daily_std":            daily_std,
                "annualization_factor": annualization_factor,
            },
        )
        self._last_historical_result = result
        return result

    # ----------------------------------------------------------
    # 2. 業種ベンチマーク
    # ----------------------------------------------------------
    def get_industry_volatility(self) -> float:
        """業種ベンチマークのボラティリティ（スカラー）を返す"""
        return INDUSTRY_VOLATILITY.get(self.industry, INDUSTRY_VOLATILITY["default"])

    def estimate_from_industry(self) -> VolatilityResult:
        """業種ベンチマークから VolatilityResult を返す"""
        vol  = self.get_industry_volatility()
        half = vol * 0.2
        return VolatilityResult(
            volatility=vol,
            method="industry_benchmark",
            confidence=0.6,
            confidence_interval=(max(vol - half, 0.01), vol + half),
            details={"industry": self.industry},
        )

    # ----------------------------------------------------------
    # 3. 手動入力 / フォールバック → float
    # ----------------------------------------------------------
    def estimate(
        self,
        manual_vol: Optional[float] = None,
        peer_tickers: Optional[list[str]] = None,
        historical_data: Optional[list[float]] = None,
    ) -> float:
        """
        推定ボラティリティ（スカラー）を返す。

        優先順位: manual_vol > historical_data > peer_tickers > industry
        """
        if manual_vol is not None:
            return float(manual_vol)

        if historical_data is not None and len(historical_data) >= 2:
            return self.calculate_historical_volatility(historical_data)

        if peer_tickers:
            summary = self.fetch_peer_volatility(peer_tickers)
            if summary.mean_volatility > 0:
                return summary.mean_volatility

        return self.get_industry_volatility()

    # ----------------------------------------------------------
    # 4. バリデーション
    # ----------------------------------------------------------
    @staticmethod
    def validate_volatility(vol: float) -> bool:
        """ボラティリティが妥当な範囲 (0, 5] かどうかを検証する"""
        return 0.0 < vol <= 5.0

    # ----------------------------------------------------------
    # 5. ピアカンパニーからの推定
    # ----------------------------------------------------------
    def fetch_peer_volatility(
        self,
        peer_tickers: list[str],
        period: str = "1y",
    ) -> PeerVolatilitySummary:
        """
        ピアカンパニーの株価データからボラティリティを推定する。

        Parameters
        ----------
        peer_tickers : ティッカーシンボルのリスト
        period       : yfinance の期間文字列
        """
        peers: list[PeerData] = []

        for ticker in peer_tickers:
            try:
                vol = self._fetch_single_volatility(ticker, period)
                name = self._fetch_company_name(ticker)
                peers.append(PeerData(ticker=ticker, volatility=vol, success=True, company_name=name))
            except Exception as exc:
                peers.append(
                    PeerData(ticker=ticker, volatility=0.0, success=False, error=str(exc))
                )

        return PeerVolatilitySummary.from_peers(peers)

    def estimate_from_peers(
        self,
        peer_tickers: list[str],
        period: str = "1y",
    ) -> PeerVolatilitySummary:
        """fetch_peer_volatility の別名"""
        return self.fetch_peer_volatility(peer_tickers, period)

    def _fetch_single_volatility(self, ticker: str, period: str) -> float:
        """単一ティッカーの年率ボラティリティを取得する（内部用）"""
        if not YFINANCE_AVAILABLE or yf is None:
            raise ImportError("yfinance is not installed")

        ticker_obj = yf.Ticker(ticker)
        hist       = ticker_obj.history(period=period)

        if hist is None or hist.empty:
            raise ValueError(f"No data returned for ticker '{ticker}'")

        close = hist["Close"].dropna()
        if len(close) < 2:
            raise ValueError(f"Insufficient price data for ticker '{ticker}'")

        log_ret = np.log(close / close.shift(1)).dropna()
        return float(np.std(log_ret, ddof=1) * np.sqrt(252))

    def _fetch_company_name(self, ticker: str) -> str:
        """yfinance から企業名を取得する（取得失敗時は空文字列）"""
        try:
            if not YFINANCE_AVAILABLE or yf is None:
                return ""
            info = yf.Ticker(ticker).info
            return info.get("longName") or info.get("shortName") or ""
        except Exception:
            return ""

    # ----------------------------------------------------------
    # 6. 複合推定
    # ----------------------------------------------------------
    def estimate_combined(
        self,
        peer_tickers: Optional[list[str]] = None,
        historical_returns: Optional[list[float]] = None,
        peer_weight: float = 0.5,
        historical_weight: float = 0.3,
        industry_weight: float = 0.2,
    ) -> VolatilityResult:
        """複数手法を組み合わせてボラティリティを推定する"""
        estimates: list[tuple[float, float]] = []

        industry_vol = self.get_industry_volatility()
        estimates.append((industry_vol, industry_weight))

        if historical_returns is not None and len(historical_returns) >= 2:
            hist_vol = self.calculate_historical_volatility(
                historical_returns, is_returns=True
            )
            estimates.append((hist_vol, historical_weight))

        if peer_tickers:
            summary = self.fetch_peer_volatility(peer_tickers)
            if summary.mean_volatility > 0:
                estimates.append((summary.mean_volatility, peer_weight))

        total_weight = sum(w for _, w in estimates)
        weighted_vol = sum(v * w for v, w in estimates) / total_weight

        n_methods  = len(estimates)
        confidence = min(0.5 + 0.2 * n_methods, 0.95)
        half       = weighted_vol * 0.15

        return VolatilityResult(
            volatility=weighted_vol,
            method="combined",
            confidence=confidence,
            confidence_interval=(max(weighted_vol - half, 0.01), weighted_vol + half),
            details={
                "n_methods":  n_methods,
                "components": [{"volatility": v, "weight": w} for v, w in estimates],
            },
        )
