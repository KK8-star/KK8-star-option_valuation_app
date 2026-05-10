"""NAV計算のテスト"""
import pytest
from src.utils.nav_calculator import NAVCalculator

@pytest.fixture
def nav_calc():
    return NAVCalculator()

class TestNAVCalculator:
    def test_basic_nav(self, nav_calc):
        result = nav_calc.calculate(
            total_assets=100_000_000,
            total_liabilities=40_000_000,
            shares_outstanding=100_000,
            illiquidity_discount=0.3
        )
        assert result["nav_per_share"] > 0
        assert result["adjusted_nav_per_share"] > 0
        assert result["adjusted_nav_per_share"] < result["nav_per_share"]

    def test_zero_discount(self, nav_calc):
        result = nav_calc.calculate(
            total_assets=100_000_000,
            total_liabilities=40_000_000,
            shares_outstanding=100_000,
            illiquidity_discount=0.0
        )
        assert result["nav_per_share"] == result["adjusted_nav_per_share"]

    def test_negative_equity(self, nav_calc):
        with pytest.raises(Exception):
            nav_calc.calculate(
                total_assets=30_000_000,
                total_liabilities=40_000_000,
                shares_outstanding=100_000,
                illiquidity_discount=0.3
            )

    def test_calculation_formula(self, nav_calc):
        result = nav_calc.calculate(
            total_assets=10_000_000,
            total_liabilities=4_000_000,
            shares_outstanding=100_000,
            illiquidity_discount=0.3
        )
        expected_nav = (10_000_000 - 4_000_000) / 100_000
        expected_adj = expected_nav * (1 - 0.3)
        assert abs(result["nav_per_share"] - expected_nav) < 0.01
        assert abs(result["adjusted_nav_per_share"] - expected_adj) < 0.01
