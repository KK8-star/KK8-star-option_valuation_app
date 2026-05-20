"""
volatility_estimator.py - 髱樔ｸ雁ｴ莨∵･ｭ縺ｮ繝懊Λ繝・ぅ繝ｪ繝・ぅ謗ｨ螳壹Θ繝ｼ繝・ぅ繝ｪ繝・ぅ
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
# 讌ｭ遞ｮ蛻･繝懊Λ繝・ぅ繝ｪ繝・ぅ繝吶Φ繝√・繝ｼ繧ｯ (蟷ｴ邇・
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
# 繝・・繧ｿ繧ｯ繝ｩ繧ｹ
# ============================================================
@dataclass
class VolatilityResult:
    """
    繝懊Λ繝・ぅ繝ｪ繝・ぅ謗ｨ螳夂ｵ先棡

    Attributes
    ----------
    volatility          : 謗ｨ螳壹・繝ｩ繝・ぅ繝ｪ繝・ぅ・亥ｹｴ邇・ｼ・    method              : 謗ｨ螳壽焔豕募錐
    confidence          : 謗ｨ螳壹・菫｡鬆ｼ蠎ｦ [0, 1]
    confidence_interval : (荳矩剞, 荳企剞) 縺ｮ 95% 菫｡鬆ｼ蛹ｺ髢・    details             : 霑ｽ蜉諠・ｱ
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
    """繝斐い繧ｫ繝ｳ繝代ル繝ｼ縺ｮ蛟句挨繝・・繧ｿ"""
    ticker: str
    volatility: float
    success: bool = True
    error: Optional[str] = None
    company_name: str = ""


@dataclass
class PeerVolatilitySummary:
    """
    繝斐い繧ｫ繝ｳ繝代ル繝ｼ鄒､縺ｮ繝懊Λ繝・ぅ繝ｪ繝・ぅ繧ｵ繝槭Μ繝ｼ

    Attributes
    ----------
    tickers           : 蜃ｦ逅・ｯｾ雎｡繝・ぅ繝・き繝ｼ繝ｪ繧ｹ繝・    mean_volatility   : 謌仙粥繝・ぅ繝・き繝ｼ縺ｮ蟷ｳ蝮・・繝ｩ繝・ぅ繝ｪ繝・ぅ
    median_volatility : 謌仙粥繝・ぅ繝・き繝ｼ縺ｮ荳ｭ螟ｮ蛟､繝懊Λ繝・ぅ繝ｪ繝・ぅ
    std_volatility    : 謌仙粥繝・ぅ繝・き繝ｼ縺ｮ讓呎ｺ門￥蟾ｮ
    failed_tickers    : 蜿門ｾ怜､ｱ謨励ユ繧｣繝・き繝ｼ縺ｮ繝ｪ繧ｹ繝・    peers             : 蜈ｨ繝斐い繝・・繧ｿ
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
    髱樔ｸ雁ｴ莨∵･ｭ蜷代￠繝懊Λ繝・ぅ繝ｪ繝・ぅ謗ｨ螳壹け繝ｩ繧ｹ

    Parameters
    ----------
    industry : str
        讌ｭ遞ｮ繧ｳ繝ｼ繝・(INDUSTRY_VOLATILITY 縺ｮ繧ｭ繝ｼ)縲ら怐逡･譎ゅ・ 'default'縲・    """

    def __init__(self, industry: str = "default"):
        self.industry = (industry or "default").lower()
        self._last_historical_result: Optional[VolatilityResult] = None

    # ----------------------------------------------------------
    # 蜀・Κ: 繝ｪ繧ｿ繝ｼ繝ｳ蛻励・險育ｮ・    # ----------------------------------------------------------
    @staticmethod
    def _compute_log_returns(
        arr: np.ndarray,
        is_returns: bool,
    ) -> np.ndarray:
        """
        萓｡譬ｼ蛻励∪縺溘・繝ｪ繧ｿ繝ｼ繝ｳ蛻励°繧牙ｯｾ謨ｰ繝ｪ繧ｿ繝ｼ繝ｳ驟榊・繧定ｿ斐☆縲・
        閾ｪ蜍募愛螳・
          蜈ｨ隕∫ｴ縺ｮ邨ｶ蟇ｾ蛟､ < 0.5 縺九▽ 豁｣雋豺ｷ蝨ｨ 竊・繝ｪ繧ｿ繝ｼ繝ｳ蛻励→隕九↑縺・        """
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
    # 1. 驕主悉萓｡譬ｼ / 繝ｪ繧ｿ繝ｼ繝ｳ縺九ｉ縺ｮ險育ｮ・竊・float
    # ----------------------------------------------------------
    def calculate_historical_volatility(
        self,
        prices_or_returns: list[float] | np.ndarray,
        annualize: bool = True,
        annualization_factor: int = 252,
        is_returns: bool = False,
    ) -> float:
        """
        萓｡譬ｼ蛻励∪縺溘・繝ｪ繧ｿ繝ｼ繝ｳ蛻励°繧牙ｹｴ邇・・繝ｩ繝・ぅ繝ｪ繝・ぅ(float)繧定ｨ育ｮ励☆繧九・
        隧ｳ邏ｰ縺ｪ邨先棡縺悟ｿ・ｦ√↑蝣ｴ蜷医・ calculate_historical_volatility_result() 繧剃ｽｿ逕ｨ縲・        """
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
        萓｡譬ｼ蛻励∪縺溘・繝ｪ繧ｿ繝ｼ繝ｳ蛻励°繧・VolatilityResult 繧定ｨ育ｮ励☆繧九・        """
        arr     = np.asarray(prices_or_returns, dtype=float)
        log_ret = self._compute_log_returns(arr, is_returns)

        if len(log_ret) < 2:
            raise ValueError("Need at least 2 valid return observations")

        daily_std = float(np.std(log_ret, ddof=1))
        vol       = daily_std * np.sqrt(annualization_factor) if annualize else daily_std

        if not np.isfinite(vol) or vol <= 0:
            raise ValueError(f"Computed volatility is invalid: {vol}")

        # 95% 菫｡鬆ｼ蛹ｺ髢・(Chi-square 霑台ｼｼ)
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
    # 2. 讌ｭ遞ｮ繝吶Φ繝√・繝ｼ繧ｯ
    # ----------------------------------------------------------
    def get_industry_volatility(self) -> float:
        """讌ｭ遞ｮ繝吶Φ繝√・繝ｼ繧ｯ縺ｮ繝懊Λ繝・ぅ繝ｪ繝・ぅ・医せ繧ｫ繝ｩ繝ｼ・峨ｒ霑斐☆"""
        return INDUSTRY_VOLATILITY.get(self.industry, INDUSTRY_VOLATILITY["default"])

    def estimate_from_industry(self) -> VolatilityResult:
        """讌ｭ遞ｮ繝吶Φ繝√・繝ｼ繧ｯ縺九ｉ VolatilityResult 繧定ｿ斐☆"""
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
    # 3. 謇句虚蜈･蜉・/ 繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ 竊・float
    # ----------------------------------------------------------
    def estimate(
        self,
        manual_vol: Optional[float] = None,
        peer_tickers: Optional[list[str]] = None,
        historical_data: Optional[list[float]] = None,
    ) -> float:
        """
        謗ｨ螳壹・繝ｩ繝・ぅ繝ｪ繝・ぅ・医せ繧ｫ繝ｩ繝ｼ・峨ｒ霑斐☆縲・
        蜆ｪ蜈磯・ｽ・ manual_vol > historical_data > peer_tickers > industry
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
    # 4. 繝舌Μ繝・・繧ｷ繝ｧ繝ｳ
    # ----------------------------------------------------------
    @staticmethod
    def validate_volatility(vol: float) -> bool:
        """繝懊Λ繝・ぅ繝ｪ繝・ぅ縺悟ｦ･蠖薙↑遽・峇 (0, 5] 縺九←縺・°繧呈､懆ｨｼ縺吶ｋ"""
        return 0.0 < vol <= 5.0

    # ----------------------------------------------------------
    # 5. 繝斐い繧ｫ繝ｳ繝代ル繝ｼ縺九ｉ縺ｮ謗ｨ螳・    # ----------------------------------------------------------
    def fetch_peer_volatility(
        self,
        peer_tickers: list[str],
        period: str = "1y",
    ) -> PeerVolatilitySummary:
        """
        繝斐い繧ｫ繝ｳ繝代ル繝ｼ縺ｮ譬ｪ萓｡繝・・繧ｿ縺九ｉ繝懊Λ繝・ぅ繝ｪ繝・ぅ繧呈耳螳壹☆繧九・
        Parameters
        ----------
        peer_tickers : 繝・ぅ繝・き繝ｼ繧ｷ繝ｳ繝懊Ν縺ｮ繝ｪ繧ｹ繝・        period       : yfinance 縺ｮ譛滄俣譁・ｭ怜・
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
        """fetch_peer_volatility 縺ｮ蛻･蜷・""
        return self.fetch_peer_volatility(peer_tickers, period)

    def _fetch_single_volatility(self, ticker: str, period: str) -> float:
        """蜊倅ｸ繝・ぅ繝・き繝ｼ縺ｮ蟷ｴ邇・・繝ｩ繝・ぅ繝ｪ繝・ぅ繧貞叙蠕励☆繧具ｼ亥・驛ｨ逕ｨ・・""
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
        """yfinance 縺九ｉ莨∵･ｭ蜷阪ｒ蜿門ｾ励☆繧具ｼ亥叙蠕怜､ｱ謨玲凾縺ｯ遨ｺ譁・ｭ怜・・・""
        try:
            if not YFINANCE_AVAILABLE or yf is None:
                return ""
            info = yf.Ticker(ticker).info
            return info.get("longName") or info.get("shortName") or ""
        except Exception:
            return ""

    # ----------------------------------------------------------
    # 6. 隍・粋謗ｨ螳・    # ----------------------------------------------------------
    def estimate_combined(
        self,
        peer_tickers: Optional[list[str]] = None,
        historical_returns: Optional[list[float]] = None,
        peer_weight: float = 0.5,
        historical_weight: float = 0.3,
        industry_weight: float = 0.2,
    ) -> VolatilityResult:
        """隍・焚謇区ｳ輔ｒ邨・∩蜷医ｏ縺帙※繝懊Λ繝・ぅ繝ｪ繝・ぅ繧呈耳螳壹☆繧・""
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
