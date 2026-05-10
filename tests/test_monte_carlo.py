"""MonteCarloModel テスト"""
import pytest
from src.models.monte_carlo import MonteCarloModel, MonteCarloResult
from src.models.black_scholes import BlackScholes


@pytest.fixture
def params():
    return dict(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)


@pytest.fixture
def mc_model(params):
    return MonteCarloModel(
        S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20,
        n_simulations=50_000, seed=42,
    )


class TestMonteCarlo:

    def test_call_option(self, mc_model):
        result = mc_model.calculate(option_type="call")
        assert isinstance(result, MonteCarloResult)
        assert result.price > 0
        assert result.std_error > 0
        assert result.confidence_interval[0] < result.price < result.confidence_interval[1]

    def test_put_option(self, mc_model):
        result = mc_model.calculate(option_type="put")
        assert result.price > 0

    def test_consistency_with_bs(self, params):
        mc = MonteCarloModel(**params, n_simulations=100_000, seed=0)
        bs = BlackScholes(**params)

        call_mc = mc.calculate(option_type="call").price
        put_mc  = mc.calculate(option_type="put").price

        assert abs(call_mc - bs.call_price) < 1.0, (
            f"Call差異: MC={call_mc:.4f}, BS={bs.call_price:.4f}"
        )
        assert abs(put_mc - bs.put_price) < 1.0, (
            f"Put差異: MC={put_mc:.4f}, BS={bs.put_price:.4f}"
        )

    def test_confidence_interval(self, mc_model):
        result = mc_model.calculate(option_type="call")
        lo, hi = result.confidence_interval
        assert lo < result.price < hi
        assert hi - lo < result.price * 0.5  # CI幅が価格の50%以内

    def test_large_simulations(self, params):
        mc = MonteCarloModel(**params, n_simulations=200_000, seed=1)
        bs = BlackScholes(**params)
        call_mc = mc.calculate(option_type="call").price
        assert abs(call_mc - bs.call_price) < 0.5, (
            f"大規模シミュ差異: MC={call_mc:.4f}, BS={bs.call_price:.4f}"
        )

    def test_put_call_parity_mc(self, params):
        mc   = MonteCarloModel(**params, n_simulations=200_000, seed=99)
        call = mc.calculate(option_type="call").price
        put  = mc.calculate(option_type="put").price
        S, K, T, r = params["S"], params["K"], params["T"], params["r"]
        import math
        parity = call - put - S + K * math.exp(-r * T)
        assert abs(parity) < 1.5, f"Put-call parity violation: {parity:.4f}"

    def test_invalid_option_type(self, mc_model):
        with pytest.raises((ValueError, Exception)):
            mc_model.calculate(option_type="invalid")
