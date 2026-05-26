# src/services/valuation_service.py
from __future__ import annotations
import datetime, math, logging
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from scipy.stats import norm
from sqlalchemy.orm import Session
from src.data.models import ValuationCase, ComparableTicker, JST
from src.data.database import get_session

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# データクラス
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@dataclass
class ValuationParams:
    case_name:        str
    stock_price:      float
    strike_price:     float
    risk_free_rate:   float
    volatility:       float
    time_to_expiry:   float
    option_type:      str   = "call"
    dividend_yield:   float = 0.0
    binomial_steps:   int   = 100
    mc_simulations:   int   = 10_000


@dataclass
class ComparableTickerRow:
    ticker:        str
    company_label: str   = ""
    volatility:    float = 0.0
    vol_period:    str   = "1y"
    fetch_ok:      bool  = True
    error_msg:     str   = ""


@dataclass
class ValuationResult:
    bs_price:       float
    binomial_price: float
    mc_price:       float
    weighted_price: float
    delta:          float
    gamma:          float
    theta:          float
    vega:           float
    rho:            float
    bs_detail:      dict = field(default_factory=dict)
    bin_detail:     dict = field(default_factory=dict)
    mc_detail:      dict = field(default_factory=dict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 計算エンジン（プライベート関数）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _bs(p: ValuationParams) -> tuple[float, dict]:
    S, K, r, sigma, T, q = (
        p.stock_price, p.strike_price, p.risk_free_rate,
        p.volatility, p.time_to_expiry, p.dividend_yield,
    )
    if T <= 0 or sigma <= 0:
        return 0.0, {}
    log_SK    = math.log(S / K)
    sig_sqrtT = sigma * math.sqrt(T)
    d1 = (log_SK + (r - q + 0.5 * sigma**2) * T) / sig_sqrtT
    d2 = d1 - sig_sqrtT
    exp_qT = math.exp(-q * T)
    exp_rT = math.exp(-r * T)
    Nd1  = norm.cdf(d1);  Nd2  = norm.cdf(d2)
    Nnd1 = norm.cdf(-d1); Nnd2 = norm.cdf(-d2)
    nd1  = norm.pdf(d1)
    if p.option_type == "call":
        price = S * exp_qT * Nd1 - K * exp_rT * Nd2
        delta = exp_qT * Nd1
        rho   = K * T * exp_rT * Nd2 / 100
    else:
        price = K * exp_rT * Nnd2 - S * exp_qT * Nnd1
        delta = -exp_qT * Nnd1
        rho   = -K * T * exp_rT * Nnd2 / 100
    gamma = exp_qT * nd1 / (S * sig_sqrtT)
    theta = (
        -(S * exp_qT * nd1 * sigma) / (2 * math.sqrt(T))
        - r * K * exp_rT * (Nd2 if p.option_type == "call" else Nnd2)
    ) / 365
    vega = S * exp_qT * nd1 * math.sqrt(T) / 100
    detail = dict(
        d1=d1, d2=d2,
        log_SK=log_SK, sigma_sqrtT=sig_sqrtT,
        exp_qT=exp_qT, exp_rT=exp_rT,
        Nd1=Nd1, Nd2=Nd2, Nnd1=Nnd1, Nnd2=Nnd2, nd1=nd1,
        delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho,
    )
    return price, detail


def _binomial(p: ValuationParams) -> tuple[float, dict]:
    S, K, r, sigma, T, q, N = (
        p.stock_price, p.strike_price, p.risk_free_rate,
        p.volatility, p.time_to_expiry, p.dividend_yield,
        p.binomial_steps,
    )
    if T <= 0 or sigma <= 0:
        return 0.0, {}
    dt   = T / N
    u    = math.exp(sigma * math.sqrt(dt))
    d    = 1 / u
    pu   = (math.exp((r - q) * dt) - d) / (u - d)
    pd   = 1 - pu
    disc = math.exp(-r * dt)
    terminal_prices  = np.array([S * u**j * d**(N - j) for j in range(N + 1)])
    if p.option_type == "call":
        terminal_payoffs = np.maximum(terminal_prices - K, 0)
    else:
        terminal_payoffs = np.maximum(K - terminal_prices, 0)
    sample_prices:  list = []
    sample_payoffs: list = []
    for i in range(min(5, N + 1)):
        sample_prices.append(float(terminal_prices[i]))
        sample_payoffs.append(float(terminal_payoffs[i]))
    if N + 1 > 9:
        sample_prices.append("...")
        sample_payoffs.append("...")
        for i in range(max(5, N - 3), N + 1):
            sample_prices.append(float(terminal_prices[i]))
            sample_payoffs.append(float(terminal_payoffs[i]))
    vals = terminal_payoffs.copy()
    for _ in range(N):
        vals = disc * (pu * vals[1:] + pd * vals[:-1])
    n_itm = int(np.sum(terminal_payoffs > 0))
    detail = dict(
        dt=dt, u=u, d=d, p_up=pu, p_down=pd,
        discount=disc, steps=N,
        terminal_prices_sample=sample_prices,
        terminal_payoffs_sample=sample_payoffs,
        max_terminal_price=float(terminal_prices.max()),
        min_terminal_price=float(terminal_prices.min()),
        n_itm=n_itm,
    )
    return float(vals[0]), detail


def _mc(p: ValuationParams) -> tuple[float, dict]:
    S, K, r, sigma, T, q = (
        p.stock_price, p.strike_price, p.risk_free_rate,
        p.volatility, p.time_to_expiry, p.dividend_yield,
    )
    if T <= 0 or sigma <= 0:
        return 0.0, {}
    rng    = np.random.default_rng(42)
    Z      = rng.standard_normal(p.mc_simulations)
    ST     = S * np.exp((r - q - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * Z)
    if p.option_type == "call":
        payoff = np.maximum(ST - K, 0)
    else:
        payoff = np.maximum(K - ST, 0)
    disc_f = math.exp(-r * T)
    mean_p = float(payoff.mean())
    std_p  = float(payoff.std())
    se     = float(std_p / math.sqrt(p.mc_simulations))
    price  = disc_f * mean_p
    ci_lo  = disc_f * (mean_p - 1.96 * se)
    ci_hi  = disc_f * (mean_p + 1.96 * se)
    n_itm  = int(np.sum(payoff > 0))
    rng2   = np.random.default_rng(99)
    idx    = rng2.choice(len(ST), size=min(2000, len(ST)), replace=False)
    detail = dict(
        n_simulations   = p.mc_simulations,
        mean_ST         = float(ST.mean()),
        std_ST          = float(ST.std()),
        min_ST          = float(ST.min()),
        max_ST          = float(ST.max()),
        n_itm           = n_itm,
        itm_ratio       = n_itm / p.mc_simulations,
        mean_payoff     = mean_p,
        std_payoff      = std_p,
        discount_factor = disc_f,
        std_error       = se,
        ci95_lower      = ci_lo,
        ci95_upper      = ci_hi,
        ST_hist         = ST[idx].tolist(),
        payoff_hist     = payoff[idx].tolist(),
        mean=mean_p, std=std_p, se=se,
        ci_low=ci_lo, ci_high=ci_hi,
        simulations=p.mc_simulations,
    )
    return price, detail


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ヘルパー
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _case_to_dict(case: ValuationCase) -> dict:
    return {c.key: getattr(case, c.key) for c in case.__mapper__.column_attrs}


def _ticker_to_dict(t: ComparableTicker) -> dict:
    return {c.key: getattr(t, c.key) for c in t.__mapper__.column_attrs}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# サービスクラス
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ValuationService:

    # ── 計算 ───────────────────────────────
    def calculate(self, p: ValuationParams) -> ValuationResult:
        bs_price,  bs_detail  = _bs(p)
        bin_price, bin_detail = _binomial(p)
        mc_price,  mc_detail  = _mc(p)
        weighted = 0.5 * bs_price + 0.3 * bin_price + 0.2 * mc_price
        return ValuationResult(
            bs_price       = bs_price,
            binomial_price = bin_price,
            mc_price       = mc_price,
            weighted_price = weighted,
            delta          = bs_detail.get("delta", 0.0),
            gamma          = bs_detail.get("gamma", 0.0),
            theta          = bs_detail.get("theta", 0.0),
            vega           = bs_detail.get("vega",  0.0),
            rho            = bs_detail.get("rho",   0.0),
            bs_detail      = bs_detail,
            bin_detail     = bin_detail,
            mc_detail      = mc_detail,
        )

    # ── 新規保存 ───────────────────────────
    def save(
        self,
        p: ValuationParams,
        r: ValuationResult,
        comparables: list[ComparableTickerRow] | None = None,
    ) -> int:
        with get_session() as sess:
            case = ValuationCase(
                case_name      = p.case_name,
                stock_price    = p.stock_price,
                strike_price   = p.strike_price,
                risk_free_rate = p.risk_free_rate,
                volatility     = p.volatility,
                time_to_expiry = p.time_to_expiry,
                option_type    = p.option_type,
                dividend_yield = p.dividend_yield,
                binomial_steps = p.binomial_steps,
                mc_simulations = p.mc_simulations,
                bs_price       = r.bs_price,
                binomial_price = r.binomial_price,
                mc_price       = r.mc_price,
                weighted_price = r.weighted_price,
                delta          = r.delta,
                gamma          = r.gamma,
                theta          = r.theta,
                vega           = r.vega,
                rho            = r.rho,
            )
            sess.add(case)
            sess.flush()
            if comparables:
                for c in comparables:
                    sess.add(ComparableTicker(
                        case_id       = case.id,
                        ticker        = c.ticker,
                        company_label = c.company_label,
                        volatility    = c.volatility,
                        vol_period    = c.vol_period,
                        fetch_ok      = c.fetch_ok,
                        error_msg     = c.error_msg,
                    ))
            return case.id   # commit は get_session() が担う

    # ── 更新 ───────────────────────────────
    def update(
        self,
        case_id: int,
        p: ValuationParams,
        r: ValuationResult,
        comparables: list[ComparableTickerRow] | None = None,
    ) -> None:
        with get_session() as sess:
            case = sess.get(ValuationCase, case_id)
            if case is None:
                raise ValueError(f"Case {case_id} not found")
            case.case_name      = p.case_name
            case.stock_price    = p.stock_price
            case.strike_price   = p.strike_price
            case.risk_free_rate = p.risk_free_rate
            case.volatility     = p.volatility
            case.time_to_expiry = p.time_to_expiry
            case.option_type    = p.option_type
            case.dividend_yield = p.dividend_yield
            case.binomial_steps = p.binomial_steps
            case.mc_simulations = p.mc_simulations
            case.bs_price       = r.bs_price
            case.binomial_price = r.binomial_price
            case.mc_price       = r.mc_price
            case.weighted_price = r.weighted_price
            case.delta          = r.delta
            case.gamma          = r.gamma
            case.theta          = r.theta
            case.vega           = r.vega
            case.rho            = r.rho
            case.updated_at     = datetime.datetime.now(JST)
            sess.query(ComparableTicker).filter(
                ComparableTicker.case_id == case_id
            ).delete()
            if comparables:
                for c in comparables:
                    sess.add(ComparableTicker(
                        case_id       = case_id,
                        ticker        = c.ticker,
                        company_label = c.company_label,
                        volatility    = c.volatility,
                        vol_period    = c.vol_period,
                        fetch_ok      = c.fetch_ok,
                        error_msg     = c.error_msg,
                    ))
            # commit は get_session() が担う

    # ── 再計算して更新（ショートカット） ──
    def update_case(
        self,
        case_id: int,
        p: ValuationParams,
        comparables: list[ComparableTickerRow] | None = None,
    ) -> None:
        r = self.calculate(p)
        self.update(case_id, p, r, comparables)

    # ── 削除 ───────────────────────────────
    def delete_case(self, case_id: int) -> None:
        with get_session() as sess:
            case = sess.get(ValuationCase, case_id)
            if case:
                sess.delete(case)
            # commit は get_session() が担う

    # ── 一覧取得 ───────────────────────────
    def get_all_cases(self) -> list[dict]:
        with get_session() as sess:
            cases = (
                sess.query(ValuationCase)
                .order_by(ValuationCase.created_at.desc())
                .all()
            )
            return [_case_to_dict(c) for c in cases]

    # ── 単件取得 ───────────────────────────
    def get_case(self, case_id: int) -> Optional[dict]:
        with get_session() as sess:
            case = sess.get(ValuationCase, case_id)
            if case is None:
                return None
            return _case_to_dict(case)

    # ── 類似会社一覧取得 ───────────────────
    def get_comparable_tickers(self, case_id: int) -> list[dict]:
        with get_session() as sess:
            tickers = (
                sess.query(ComparableTicker)
                .filter(ComparableTicker.case_id == case_id)
                .all()
            )
            return [_ticker_to_dict(t) for t in tickers]

    def add_comparable_ticker(self, case_id, ticker, company_label="", vol_period="1y"):
        import yfinance as yf
        import numpy as np
        t = ticker.upper().strip()
        label = company_label
        vol = 0.0
        ok = True
        err = ""
        try:
            hist = yf.Ticker(t).history(period=vol_period)
            if hist.empty:
                raise ValueError("no data")
            lr = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
            vol = float(lr.std() * np.sqrt(252))
            if not label:
                info = yf.Ticker(t).info
                label = info.get("longName") or info.get("shortName") or t
        except Exception as e:
            ok = False
            err = str(e)
        with get_session() as sess:
            obj = ComparableTicker(
                case_id=case_id,
                ticker=t,
                company_label=label,
                volatility=vol,
                vol_period=vol_period,
                fetch_ok=ok,
                error_msg=err,
            )
            sess.add(obj)
            sess.flush()
            return _ticker_to_dict(obj)

    def delete_comparable_ticker(self, case_id, ticker):
        with get_session() as sess:
            sess.query(ComparableTicker).filter(
                ComparableTicker.case_id == case_id,
                ComparableTicker.ticker == ticker.upper().strip(),
            ).delete()

    def refetch_all_tickers(self, case_id):
        import yfinance as yf
        import numpy as np
        with get_session() as sess:
            rows = sess.query(ComparableTicker).filter(
                ComparableTicker.case_id == case_id
            ).all()
            out = []
            for r in rows:
                try:
                    period = r.vol_period if r.vol_period else "1y"
                    hist = yf.Ticker(r.ticker).history(period=period)
                    if hist.empty:
                        raise ValueError("no data")
                    lr = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
                    r.volatility = float(lr.std() * np.sqrt(252))
                    r.fetch_ok = True
                    r.error_msg = ""
                except Exception as e:
                    r.fetch_ok = False
                    r.error_msg = str(e)
                out.append(_ticker_to_dict(r))
            return out
