"""
BinomialModel テスト - CRR二項モデル
BinomialResult (dataclass) を返す現在のAPIに準拠
"""
import pytest
import numpy as np
from src.models.binomial import BinomialModel, BinomialResult


# ────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────

@pytest.fixture
def model():
    """標準200ステップモデル"""
    return BinomialModel(steps=200)


@pytest.fixture
def atm_call_params():
    """ATM（アット・ザ・マネー）コールの標準パラメータ"""
    return dict(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        volatility=0.20,
        time_to_expiry=1.0,
        option_type="call",
        exercise_type="european",
        dividend_yield=0.0,
    )


# ────────────────────────────────────────────────
# 基本動作テスト
# ────────────────────────────────────────────────

class TestBinomialModelInit:

    def test_default_steps(self):
        """デフォルトステップ数は200"""
        m = BinomialModel()
        assert m.steps == 200

    def test_custom_steps(self):
        """カスタムステップ数が設定できること"""
        m = BinomialModel(steps=100)
        assert m.steps == 100

    def test_steps_stored_in_result(self, model, atm_call_params):
        """結果にステップ数が記録されること"""
        result = model.price(**atm_call_params)
        assert result.steps == model.steps


# ────────────────────────────────────────────────
# BinomialResult 型テスト
# ────────────────────────────────────────────────

class TestBinomialResult:

    def test_returns_binomial_result(self, model, atm_call_params):
        """price() が BinomialResult を返すこと"""
        result = model.price(**atm_call_params)
        assert isinstance(result, BinomialResult)

    def test_result_has_price_attribute(self, model, atm_call_params):
        """result.price が float であること"""
        result = model.price(**atm_call_params)
        assert isinstance(result.price, float)
        assert result.price > 0.0

    def test_result_fields_match_inputs(self, model, atm_call_params):
        """結果のフィールドが入力パラメータと一致すること"""
        result = model.price(**atm_call_params)
        assert result.stock_price    == atm_call_params["stock_price"]
        assert result.strike_price   == atm_call_params["strike_price"]
        assert result.risk_free_rate == atm_call_params["risk_free_rate"]
        assert result.volatility     == atm_call_params["volatility"]
        assert result.time_to_expiry == atm_call_params["time_to_expiry"]
        assert result.option_type    == atm_call_params["option_type"]
        assert result.exercise_type  == atm_call_params["exercise_type"]
        assert result.dividend_yield == atm_call_params["dividend_yield"]

    def test_delta_property_returns_none(self, model, atm_call_params):
        """delta プロパティは None を返す（CRR基本実装）"""
        result = model.price(**atm_call_params)
        assert result.delta is None


# ────────────────────────────────────────────────
# 価格の妥当性テスト
# ────────────────────────────────────────────────

class TestPriceValidity:

    def test_call_price_positive(self, model, atm_call_params):
        """コール価格は正の値"""
        result = model.price(**atm_call_params)
        assert result.price > 0.0

    def test_put_price_positive(self, model, atm_call_params):
        """プット価格は正の値"""
        params = {**atm_call_params, "option_type": "put"}
        result = model.price(**params)
        assert result.price > 0.0

    def test_price_not_nan(self, model, atm_call_params):
        """価格はNaNでないこと"""
        result = model.price(**atm_call_params)
        assert not np.isnan(result.price)

    def test_price_not_infinite(self, model, atm_call_params):
        """価格は有限値であること"""
        result = model.price(**atm_call_params)
        assert np.isfinite(result.price)

    def test_call_price_upper_bound(self, model, atm_call_params):
        """コール価格 <= 原株価（上限境界）"""
        result = model.price(**atm_call_params)
        assert result.price <= atm_call_params["stock_price"]

    def test_put_price_upper_bound(self, model, atm_call_params):
        """プット価格 <= 行使価格（上限境界）"""
        params = {**atm_call_params, "option_type": "put"}
        result = model.price(**params)
        assert result.price <= atm_call_params["strike_price"]

    def test_deep_itm_call(self, model):
        """深いITMコール: 内在価値以上"""
        result = model.price(
            stock_price=200.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type="call",
            exercise_type="european",
        )
        intrinsic = 200.0 - 100.0
        assert result.price >= intrinsic * 0.95  # 割引考慮で5%マージン

    def test_deep_otm_call_near_zero(self, model):
        """深いOTMコール: ほぼゼロに近い"""
        result = model.price(
            stock_price=50.0,
            strike_price=200.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type="call",
            exercise_type="european",
        )
        assert result.price < 0.01


# ────────────────────────────────────────────────
# Put-Call Parity テスト（ヨーロピアン）
# ────────────────────────────────────────────────

class TestPutCallParity:

    def test_put_call_parity_european(self, model):
        """
        ヨーロピアン: C - P = S*exp(-q*T) - K*exp(-r*T)
        許容誤差: ±0.05 (ステップ離散化誤差込み)
        """
        S, K, r, sigma, T, q = 100.0, 100.0, 0.05, 0.20, 1.0, 0.0

        call = model.price(S, K, r, sigma, T, "call", "european", q)
        put  = model.price(S, K, r, sigma, T, "put",  "european", q)

        lhs = call.price - put.price
        rhs = S * np.exp(-q * T) - K * np.exp(-r * T)

        assert abs(lhs - rhs) < 0.05, (
            f"Put-Call Parity violation: C-P={lhs:.4f}, S-K*e^(-rT)={rhs:.4f}"
        )

    def test_put_call_parity_with_dividend(self, model):
        """配当ありのPut-Call Parity"""
        S, K, r, sigma, T, q = 100.0, 100.0, 0.05, 0.20, 1.0, 0.03

        call = model.price(S, K, r, sigma, T, "call", "european", q)
        put  = model.price(S, K, r, sigma, T, "put",  "european", q)

        lhs = call.price - put.price
        rhs = S * np.exp(-q * T) - K * np.exp(-r * T)

        assert abs(lhs - rhs) < 0.05


# ────────────────────────────────────────────────
# price_both() テスト
# ────────────────────────────────────────────────

class TestPriceBoth:

    def test_price_both_returns_tuple(self, model):
        """price_both() がタプルを返すこと"""
        result = model.price_both(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_price_both_types(self, model):
        """call, put ともに BinomialResult であること"""
        call, put = model.price_both(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        assert isinstance(call, BinomialResult)
        assert isinstance(put,  BinomialResult)

    def test_price_both_option_types(self, model):
        """call/put の option_type フィールドが正しいこと"""
        call, put = model.price_both(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        assert call.option_type == "call"
        assert put.option_type  == "put"

    def test_price_both_matches_individual(self, model):
        """price_both() の結果が個別 price() と一致すること"""
        params = dict(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            exercise_type="european",
            dividend_yield=0.0,
        )
        call_both, put_both = model.price_both(**params)
        call_single = model.price(**params, option_type="call")
        put_single  = model.price(**params, option_type="put")

        assert call_both.price == call_single.price
        assert put_both.price  == put_single.price


# ────────────────────────────────────────────────
# アメリカンオプション テスト
# ────────────────────────────────────────────────

class TestAmericanOption:

    def test_american_put_ge_european_put(self, model):
        """
        アメリカンプット >= ヨーロピアンプット
        (早期行使プレミアムの存在)
        """
        common = dict(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type="put",
            dividend_yield=0.0,
        )
        american = model.price(**common, exercise_type="american")
        european = model.price(**common, exercise_type="european")

        assert american.price >= european.price - 1e-9

    def test_american_call_no_dividend_equals_european(self, model):
        """
        無配当アメリカンコール == ヨーロピアンコール
        (早期行使が最適でない定理)
        """
        common = dict(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type="call",
            dividend_yield=0.0,
        )
        american = model.price(**common, exercise_type="american")
        european = model.price(**common, exercise_type="european")

        assert abs(american.price - european.price) < 0.05

    def test_american_call_with_dividend_ge_european(self, model):
        """
        高配当アメリカンコール >= ヨーロピアンコール
        """
        common = dict(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type="call",
            dividend_yield=0.08,   # 高配当
        )
        american = model.price(**common, exercise_type="american")
        european = model.price(**common, exercise_type="european")

        assert american.price >= european.price - 1e-9


# ────────────────────────────────────────────────
# ステップ数収束テスト
# ────────────────────────────────────────────────

class TestConvergence:

    # BSM理論価格 (S=K=100, r=0.05, σ=0.2, T=1, q=0) ≈ 10.45
    BS_REFERENCE = 10.45

    @pytest.mark.parametrize("steps,tol", [
        (50,  0.30),
        (100, 0.15),
        (200, 0.10),
        (500, 0.05),
    ])
    def test_convergence_to_bsm(self, steps, tol):
        """ステップ増加でBSM価格に収束すること"""
        m = BinomialModel(steps=steps)
        result = m.price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type="call",
            exercise_type="european",
            dividend_yield=0.0,
        )
        assert abs(result.price - self.BS_REFERENCE) < tol, (
            f"steps={steps}: price={result.price:.4f}, "
            f"ref={self.BS_REFERENCE}, tol={tol}"
        )


# ────────────────────────────────────────────────
# 配当テスト
# ────────────────────────────────────────────────

class TestDividend:

    def test_dividend_reduces_call_price(self, model):
        """配当ありのコール < 無配当コール"""
        base = dict(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type="call",
            exercise_type="european",
        )
        no_div  = model.price(**base, dividend_yield=0.0)
        with_div = model.price(**base, dividend_yield=0.05)

        assert with_div.price < no_div.price

    def test_dividend_increases_put_price(self, model):
        """配当ありのプット > 無配当プット"""
        base = dict(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type="put",
            exercise_type="european",
        )
        no_div   = model.price(**base, dividend_yield=0.0)
        with_div = model.price(**base, dividend_yield=0.05)

        assert with_div.price > no_div.price

    def test_zero_dividend_yield(self, model):
        """dividend_yield=0 でも正常動作"""
        result = model.price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
            dividend_yield=0.0,
        )
        assert result.price > 0.0
        assert result.dividend_yield == 0.0


# ────────────────────────────────────────────────
# エッジケーステスト
# ────────────────────────────────────────────────

class TestEdgeCases:

    def test_very_short_expiry(self, model):
        """満期直前（T=0.01）でも計算できること"""
        result = model.price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=0.01,
        )
        assert isinstance(result.price, float)
        assert np.isfinite(result.price)

    def test_high_volatility(self, model):
        """高ボラティリティ（σ=1.5）でも有限値を返すこと"""
        result = model.price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=1.5,
            time_to_expiry=1.0,
        )
        assert np.isfinite(result.price)
        assert result.price > 0.0

    def test_low_volatility(self, model):
        """低ボラティリティ（σ=0.01）でほぼ内在価値になること"""
        result = model.price(
            stock_price=100.0,
            strike_price=90.0,
            risk_free_rate=0.0,
            volatility=0.01,
            time_to_expiry=1.0,
            option_type="call",
        )
        # ITMコールは内在価値(10)に近くなる
        assert abs(result.price - 10.0) < 1.0

    def test_single_step(self):
        """steps=1 でも計算できること"""
        m = BinomialModel(steps=1)
        result = m.price(
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        assert isinstance(result.price, float)
        assert np.isfinite(result.price)
