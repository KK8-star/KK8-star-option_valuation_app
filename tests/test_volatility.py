import pytest
import numpy as np
from src.utils.volatility_estimator import VolatilityEstimator, INDUSTRY_VOLATILITY


@pytest.fixture
def vol_est():
    return VolatilityEstimator(industry="technology")


class TestVolatilityEstimator:

    def test_historical_volatility(self, vol_est):
        """実現ボラティリティの計算テスト"""
        np.random.seed(42)
        returns = np.random.normal(0, 0.01, 252)
        vol = vol_est.calculate_historical_volatility(returns, annualize=True)
        assert 0.05 < vol < 0.5, f"Volatility {vol} out of plausible range"

    def test_industry_average(self, vol_est):
        """業種平均ボラティリティの取得テスト"""
        vol = vol_est.get_industry_volatility()
        assert vol == INDUSTRY_VOLATILITY["technology"]
        assert 0.0 < vol < 1.0

    def test_manual_input(self, vol_est):
        """手動入力ボラティリティのテスト"""
        result = vol_est.estimate(manual_vol=0.25)
        assert result == 0.25

    def test_invalid_volatility(self, vol_est):
        """無効なボラティリティの検証テスト"""
        assert not vol_est.validate_volatility(-0.1)
        assert not vol_est.validate_volatility(0.0)
        assert not vol_est.validate_volatility(6.0)
        assert vol_est.validate_volatility(0.3)

    def test_estimate_fallback_to_industry(self):
        """類似企業なしの場合は業種平均にフォールバック"""
        est = VolatilityEstimator(industry="finance")
        result = est.estimate()
        assert result == INDUSTRY_VOLATILITY["finance"]

    def test_unknown_industry_default(self):
        """未知の業種はデフォルト値を返す"""
        est = VolatilityEstimator(industry="unknown_sector_xyz")
        vol = est.get_industry_volatility()
        assert vol == INDUSTRY_VOLATILITY["default"]
