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

# ── パラメータ DTO ──────────────────────────────────────────────
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

# ── 計算結果 DTO ────────────────────────────────────────────────
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

# ── Black-Scholes ───────────────────────────────────────────────
def _bs(p: ValuationParams) -> tuple[float, dict]:
    S, K, r, σ, T, q = (p.stock_price, p.strike_price, p.risk_free_rate,
                         p.volatility, p.time_to_expiry, p.dividend_yield)
    if T <= 0 or σ <= 0:
        return 0.0, {}
    d1 = (math.log(S / K) + (r - q + 0.5 * σ**2) * T) / (σ * math.sqrt(T))
    d2 = d1 - σ * math.sqrt(T)
    if p.option_type == "call":
        price = S * math.exp(-q*T)*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)
        delta = math.exp(-q*T) * norm.cdf(d1)
        rho   = K * T * math.exp(-r*T) * norm.cdf(d2) / 100
    else:
        price = K*math.exp(-r*T)*norm.cdf(-d2) - S*math.exp(-q*T)*norm.cdf(-d1)
        delta = -math.exp(-q*T) * norm.cdf(-d1)
        rho   = -K * T * math.exp(-r*T) * norm.cdf(-d2) / 100
    gamma = math.exp(-q*T)*norm.pdf(d1) / (S * σ * math.sqrt(T))
    theta = (-(S*math.exp(-q*T)*norm.pdf(d1)*σ)/(2*math.sqrt(T))
             - r*K*math.exp(-r*T)*norm.cdf(d2 if p.option_type=="call" else -d2)) / 365
    vega  = S * math.exp(-q*T) * norm.pdf(d1) * math.sqrt(T) / 100
    return price, dict(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)

# ── 二項モデル ──────────────────────────────────────────────────
def _binomial(p: ValuationParams) -> float:
    S, K, r, σ, T, q, N = (p.stock_price, p.strike_price, p.risk_free_rate,
                             p.volatility, p.time_to_expiry, p.dividend_yield,
                             p.binomial_steps)
    if T <= 0 or σ <= 0:
        return 0.0
    dt = T / N
    u  = math.exp(σ * math.sqrt(dt))
    d  = 1 / u
    pu = (math.exp((r - q) * dt) - d) / (u - d)
    pd = 1 - pu
    disc = math.exp(-r * dt)
    prices = np.array([S * u**j * d**(N-j) for j in range(N+1)])
    vals   = np.maximum(prices - K, 0) if p.option_type=="call" else np.maximum(K - prices, 0)
    for _ in range(N):
        vals = disc * (pu * vals[1:] + pd * vals[:-1])
    return float(vals[0])

# ── モンテカルロ ────────────────────────────────────────────────
def _mc(p: ValuationParams) -> float:
    S, K, r, σ, T, q = (p.stock_price, p.strike_price, p.risk_free_rate,
                         p.volatility, p.time_to_expiry, p.dividend_yield)
    if T <= 0 or σ <= 0:
        return 0.0
    rng = np.random.default_rng(42)
    Z   = rng.standard_normal(p.mc_simulations)
    ST  = S * np.exp((r - q - 0.5*σ**2)*T + σ*math.sqrt(T)*Z)
    payoff = np.maximum(ST - K, 0) if p.option_type=="call" else np.maximum(K - ST, 0)
    return float(np.exp(-r*T) * payoff.mean())

# ── データ転写ヘルパー ──────────────────────────────────────────
def _case_to_dict(case: ValuationCase) -> dict:
    """セッション内でカラム値をすべて dict に取り出す"""
    return {c.key: getattr(case, c.key)
            for c in case.__mapper__.column_attrs}

def _ticker_to_dict(t: ComparableTicker) -> dict:
    return {c.key: getattr(t, c.key)
            for c in t.__mapper__.column_attrs}

# ── メインサービス ──────────────────────────────────────────────
class ValuationService:

    def calculate(self, p: ValuationParams) -> ValuationResult:
        bs_price, greeks = _bs(p)
        bin_price        = _binomial(p)
        mc_price         = _mc(p)
        weighted         = 0.5*bs_price + 0.3*bin_price + 0.2*mc_price
        return ValuationResult(
            bs_price       = bs_price,
            binomial_price = bin_price,
            mc_price       = mc_price,
            weighted_price = weighted,
            delta          = greeks.get("delta", 0.0),
            gamma          = greeks.get("gamma", 0.0),
            theta          = greeks.get("theta", 0.0),
            vega           = greeks.get("vega",  0.0),
            rho            = greeks.get("rho",   0.0),
        )

    def save(self, p: ValuationParams, r: ValuationResult,
             comparables: list[ComparableTickerRow] | None = None) -> int:
        with get_session() as sess:
            case = ValuationCase(
                case_name       = p.case_name,
                stock_price     = p.stock_price,
                strike_price    = p.strike_price,
                risk_free_rate  = p.risk_free_rate,
                volatility      = p.volatility,
                time_to_expiry  = p.time_to_expiry,
                option_type     = p.option_type,
                dividend_yield  = p.dividend_yield,
                binomial_steps  = p.binomial_steps,
                mc_simulations  = p.mc_simulations,
                bs_price        = r.bs_price,
                binomial_price  = r.binomial_price,
                mc_price        = r.mc_price,
                weighted_price  = r.weighted_price,
                delta           = r.delta,
                gamma           = r.gamma,
                theta           = r.theta,
                vega            = r.vega,
                rho             = r.rho,
            )
            sess.add(case)
            sess.flush()   # id を確定させる
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
            sess.commit()
            return case.id   # コミット後なので id は確定済み

    def update(self, case_id: int, p: ValuationParams, r: ValuationResult,
               comparables: list[ComparableTickerRow] | None = None) -> None:
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
                ComparableTicker.case_id == case_id).delete()
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
            sess.commit()

    def get_all_cases(self) -> list[dict]:
        """セッションが閉じた後も安全に使えるよう dict のリストで返す"""
        with get_session() as sess:
            cases = sess.query(ValuationCase).order_by(
                ValuationCase.created_at.desc()).all()
            return [_case_to_dict(c) for c in cases]

    def get_case(self, case_id: int) -> Optional[dict]:
        """dict で返すのでセッション外でも安全"""
        with get_session() as sess:
            case = sess.get(ValuationCase, case_id)
            if case is None:
                return None
            return _case_to_dict(case)

    def get_comparable_tickers(self, case_id: int) -> list[dict]:
        with get_session() as sess:
            tickers = sess.query(ComparableTicker).filter(
                ComparableTicker.case_id == case_id).all()
            return [_ticker_to_dict(t) for t in tickers]

    def delete_case(self, case_id: int) -> None:
        with get_session() as sess:
            case = sess.get(ValuationCase, case_id)
            if case:
                sess.delete(case)
                sess.commit()
