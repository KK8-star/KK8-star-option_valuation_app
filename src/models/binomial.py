"""
Binomial option pricing model (Cox-Ross-Rubinstein).
Supports European and American options with dividend yields.
"""
from dataclasses import dataclass
from typing import Literal
import numpy as np


@dataclass
class BinomialResult:
    """Result from binomial model pricing."""
    price: float
    option_type: str
    exercise_type: str
    steps: int
    stock_price: float
    strike_price: float
    risk_free_rate: float
    volatility: float
    time_to_expiry: float
    dividend_yield: float = 0.0

    @property
    def delta(self) -> float | None:
        """Delta is not directly computed in basic CRR; return None."""
        return None


class BinomialModel:
    """
    Cox-Ross-Rubinstein (CRR) binomial option pricing model.

    Supports:
    - European and American exercise types
    - Call and put options
    - Continuous dividend yields
    """

    def __init__(self, steps: int = 200):
        """
        Initialize binomial model.

        Args:
            steps: Number of time steps in the binomial tree.
        """
        self.steps = steps

    def price(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: Literal["call", "put"] = "call",
        exercise_type: Literal["european", "american"] = "european",
        dividend_yield: float = 0.0,
    ) -> BinomialResult:
        """
        Price an option using the binomial model.

        Args:
            stock_price: Current stock price (S)
            strike_price: Option strike price (K)
            risk_free_rate: Risk-free interest rate (annualized, decimal)
            volatility: Volatility of the underlying (annualized, decimal)
            time_to_expiry: Time to expiry in years (T)
            option_type: "call" or "put"
            exercise_type: "european" or "american"
            dividend_yield: Continuous dividend yield (annualized, decimal)

        Returns:
            BinomialResult with computed option price.
        """
        price_value = self._compute_price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type=option_type,
            exercise_type=exercise_type,
            dividend_yield=dividend_yield,
        )

        return BinomialResult(
            price=price_value,
            option_type=option_type,
            exercise_type=exercise_type,
            steps=self.steps,
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            dividend_yield=dividend_yield,
        )

    def price_both(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        exercise_type: Literal["european", "american"] = "european",
        dividend_yield: float = 0.0,
    ) -> tuple[BinomialResult, BinomialResult]:
        """
        Price both call and put options.

        Returns:
            Tuple of (call_result, put_result)
        """
        call = self.price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type="call",
            exercise_type=exercise_type,
            dividend_yield=dividend_yield,
        )
        put = self.price(
            stock_price=stock_price,
            strike_price=strike_price,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type="put",
            exercise_type=exercise_type,
            dividend_yield=dividend_yield,
        )
        return call, put

    def _compute_price(
        self,
        stock_price: float,
        strike_price: float,
        risk_free_rate: float,
        volatility: float,
        time_to_expiry: float,
        option_type: str,
        exercise_type: str,
        dividend_yield: float,
    ) -> float:
        """Core CRR binomial tree computation."""
        N = self.steps
        T = time_to_expiry
        S = stock_price
        K = strike_price
        r = risk_free_rate
        sigma = volatility
        q = dividend_yield

        dt = T / N
        u = np.exp(sigma * np.sqrt(dt))
        d = 1.0 / u
        discount = np.exp(-r * dt)
        p = (np.exp((r - q) * dt) - d) / (u - d)
        p = np.clip(p, 0.0, 1.0)
        q_prob = 1.0 - p

        # Terminal stock prices
        j = np.arange(N + 1)
        ST = S * (u ** (N - j)) * (d ** j)

        # Terminal payoffs
        if option_type == "call":
            payoff = np.maximum(ST - K, 0.0)
        else:
            payoff = np.maximum(K - ST, 0.0)

        # Backward induction
        for i in range(N - 1, -1, -1):
            payoff = discount * (p * payoff[:-1] + q_prob * payoff[1:])
            if exercise_type == "american":
                j = np.arange(i + 1)
                ST_early = S * (u ** (i - j)) * (d ** j)
                if option_type == "call":
                    intrinsic = np.maximum(ST_early - K, 0.0)
                else:
                    intrinsic = np.maximum(K - ST_early, 0.0)
                payoff = np.maximum(payoff, intrinsic)

        return float(payoff[0])
