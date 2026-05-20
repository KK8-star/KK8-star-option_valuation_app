import numpy as np
from scipy.stats import norm
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class MonteCarloResult:
    """繝｢繝ｳ繝・き繝ｫ繝ｭ繧ｷ繝溘Η繝ｬ繝ｼ繧ｷ繝ｧ繝ｳ邨先棡"""
    price: float
    std_error: float
    confidence_interval: Tuple[float, float]
    n_simulations: int


class MonteCarloModel:
    """繝｢繝ｳ繝・き繝ｫ繝ｭ豕輔↓繧医ｋ繧ｪ繝励す繝ｧ繝ｳ萓｡譬ｼ險育ｮ・""

    def __init__(
        self,
        n_simulations: int = 50000,
        random_seed: Optional[int] = None,
        S: Optional[float] = None,
        K: Optional[float] = None,
        T: Optional[float] = None,
        r: Optional[float] = None,
        sigma: Optional[float] = None,
        option_type: str = "call",
        q: float = 0.0,
        seed: Optional[int] = None,
    ):
        self.n_simulations = n_simulations
        self.random_seed = seed if seed is not None else random_seed

        self._S = S
        self._K = K
        self._T = T
        self._r = r
        self._sigma = sigma
        self._option_type = option_type
        self._q = q

        if all(v is not None for v in [S, K, T, r, sigma]):
            result = self.calculate(S, K, T, r, sigma, option_type, q)
            self.price = result.price
            self.std_error = result.std_error
            self.confidence_interval = result.confidence_interval

    def calculate(
        self,
        S: float = None,
        K: float = None,
        T: float = None,
        r: float = None,
        sigma: float = None,
        option_type: str = "call",
        q: float = 0.0,
    ) -> MonteCarloResult:
        S     = S     if S     is not None else self._S
        K     = K     if K     is not None else self._K
        T     = T     if T     is not None else self._T
        r     = r     if r     is not None else self._r
        sigma = sigma if sigma is not None else self._sigma

        if any(v is None for v in [S, K, T, r, sigma]):
            raise ValueError("S, K, T, r, sigma 縺ｯ縺吶∋縺ｦ蠢・ｦ√〒縺・)

        option_type = option_type or self._option_type

        if option_type.lower() not in ("call", "put"):
            raise ValueError(
                f"option_type 縺ｯ 'call' 縺ｾ縺溘・ 'put' 縺悟ｿ・ｦ√〒縺・ {option_type}"
            )

        if self.random_seed is not None:
            np.random.seed(self.random_seed)

        Z  = np.random.standard_normal(self.n_simulations)
        ST = S * np.exp(
            (r - q - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * Z
        )

        if option_type.lower() == "call":
            payoffs = np.maximum(ST - K, 0.0)
        else:
            payoffs = np.maximum(K - ST, 0.0)

        discount   = np.exp(-r * T)
        discounted = discount * payoffs

        price     = float(np.mean(discounted))
        std_error = float(np.std(discounted) / np.sqrt(self.n_simulations))
        z95       = 1.96
        ci        = (price - z95 * std_error, price + z95 * std_error)

        return MonteCarloResult(
            price=price,
            std_error=std_error,
            confidence_interval=ci,
            n_simulations=self.n_simulations,
        )