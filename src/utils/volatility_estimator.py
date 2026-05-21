"""
volatility_estimator.py
Non-listed company volatility estimation utility.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False

try:
    from scipy import stats as _scipy_stats
    SCIPY_AVAILABLE = True
except ImportError:
    _scipy_stats = None
    SCIPY_AVAILABLE = False


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


@dataclass
class VolatilityResult:
    volatility: float
    method: str
    confidence: float = 1.0
    confidence_interval: tuple[float, float] = field(
        default_factory=lambda: (0.0, 0.0)
    )
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if not np.isfinite(self.volatility):
            raise ValueError(f"volatility must be finite: {self.volatility}")
        if not (0 < self.volatility < 10):
            raise ValueError(f"volatility out of range: {self.volatility}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence out of range: {self.confidence}")


@dataclass
class PeerData:
    ticker: str
    volatility: float
    success: bool = True
    error: Optional[str] = None
    company_name: str = ""


@dataclass
class PeerVolatilitySummary:
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


class VolatilityEstimator:
    def __init__(self, industry: str = "default"):
        self.industry = (industry or "default").lower()
        self._last_historical_result: Optional[VolatilityResult] = None

    @staticmethod
    def _compute_log_returns(arr: np.ndarray, is_returns: bool) -> np.ndarray:
        if not is_returns:
            if (np.all(np.abs(arr) < 0.5) and np.any(arr < 0) and np.any(arr > 0)):
                is_returns = True
        if is_returns:
            return arr.copy()
        if len(arr) < 2:
            raise ValueError("prices must have at least 2 data points")
        with np.errstate(divide="ignore", invalid="ignore"):
            log_ret = np.log(arr[1:] / arr[:-1])
        return log_ret[np.isfinite(log_ret)]

    def calculate_historical_volatility(
        self,
        prices_or_returns: list[float] | np.ndarray,
        annualize: bool = True,
        annualization_factor: int = 252,
        is_returns: bool = False,
    ) -> float:
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
        arr     = np.asarray(prices_or_returns, dtype=float)
        log_ret = self._compute_log_returns(arr, is_returns)
        if len(log_ret) < 2:
            raise ValueError("Need at least 2 valid return observations")
        daily_std = float(np.std(log_ret, ddof=1))
        vol = daily_std * np.sqrt(annualization_factor) if annualize else daily_std
        if not np.isfinite(vol) or vol <= 0:
            raise ValueError(f"Computed volatility is invalid: {vol}")
        n = len(log_ret)
        if SCIPY_AVAILABLE and _scipy_stats is not None:
            alpha     = 0.05
            chi2_low  = _scipy_stats.chi2.ppf(alpha / 2,     df=n - 1)
            chi2_high = _scipy_stats.chi2.ppf(1 - alpha / 2, df=n - 1)
        else:
            chi2_low  = max((n - 1) * 0.5, 1e-9)
            chi2_high = (n - 1) * 1.5
        factor  = np.sqrt(annualization_factor) if annualize else 1.0
        ci_low  = float(daily_std * np.sqrt((n - 1) / chi2_high) * factor)
        ci_high = float(daily_std * np.sqrt((n - 1) / chi2_low)  * factor)
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

    def get_industry_volatility(self) -> float:
        return INDUSTRY_VOLATILITY.get(self.industry, INDUSTRY_VOLATILITY["default"])

    def estimate_from_industry(self) -> VolatilityResult:
        vol  = self.get_industry_volatility()
        half = vol * 0.2
        return VolatilityResult(
            volatility=vol,
            method="industry_benchmark",
            confidence=0.6,
            confidence_interval=(max(vol - half, 0.01), vol + half),
            details={"industry": self.industry},
        )

    def estimate(
        self,
        manual_vol: Optional[float] = None,
        peer_tickers: Optional[list[str]] = None,
        historical_data: Optional[list[float]] = None,
    ) -> float:
        if manual_vol is not None:
            return float(manual_vol)
        if historical_data is not None and len(historical_data) >= 2:
            return self.calculate_historical_volatility(historical_data)
        if peer_tickers:
            summary = self.fetch_peer_volatility(peer_tickers)
            if summary.mean_volatility > 0:
                return summary.mean_volatility
        return self.get_industry_volatility()

    @staticmethod
    def validate_volatility(vol: float) -> bool:
        return 0.0 < vol <= 5.0

    def fetch_peer_volatility(
        self,
        peer_tickers: list[str],
        period: str = "1y",
    ) -> PeerVolatilitySummary:
        peers: list[PeerData] = []
        for ticker in peer_tickers:
            try:
                vol  = self._fetch_single_volatility(ticker, period)
                name = self._fetch_company_name(ticker)
                peers.append(PeerData(ticker=ticker, volatility=vol, success=True, company_name=name))
            except Exception as exc:
                peers.append(PeerData(ticker=ticker, volatility=0.0, success=False, error=str(exc)))
        return PeerVolatilitySummary.from_peers(peers)

    def estimate_from_peers(self, peer_tickers: list[str], period: str = "1y") -> PeerVolatilitySummary:
        return self.fetch_peer_volatility(peer_tickers, period)

    def _fetch_single_volatility(self, ticker: str, period: str) -> float:
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
        try:
            if not YFINANCE_AVAILABLE or yf is None:
                return ""
            info = yf.Ticker(ticker).info
            return info.get("longName") or info.get("shortName") or ""
        except Exception:
            return ""

    def estimate_combined(
        self,
        peer_tickers: Optional[list[str]] = None,
        historical_returns: Optional[list[float]] = None,
        peer_weight: float = 0.5,
        historical_weight: float = 0.3,
        industry_weight: float = 0.2,
    ) -> VolatilityResult:
        estimates: list[tuple[float, float]] = []
        industry_vol = self.get_industry_volatility()
        estimates.append((industry_vol, industry_weight))
        if historical_returns is not None and len(historical_returns) >= 2:
            hist_vol = self.calculate_historical_volatility(historical_returns, is_returns=True)
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
