# tests/test_volatility_estimator.py
"""
VolatilityEstimator の単体テスト
（yfinance 非依存のオフラインテストを主体とする）
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.utils.volatility_estimator import VolatilityEstimator, PeerVolatilitySummary


# -----------------------------------------------------------------------
# オフラインテスト（yfinance 不要）
# -----------------------------------------------------------------------

def test_single():
    """履歴価格からのボラティリティ計算（yfinance 不使用）"""
    np.random.seed(42)
    estimator = VolatilityEstimator()

    # 252 営業日分の疑似価格を生成
    prices = [100.0]
    for _ in range(251):
        prices.append(prices[-1] * np.exp(np.random.normal(0.0003, 0.015)))

    result = estimator.calculate_historical_volatility_result(prices)

    assert result.volatility > 0, "ボラティリティは正の値"
    assert result.volatility < 2.0, "ボラティリティは 200% 未満"
    assert result.confidence_interval[0] < result.volatility, "下限 < 推定値"
    assert result.volatility < result.confidence_interval[1], "推定値 < 上限"
    print(f"\nEstimated volatility : {result.volatility:.2%}")
    print(f"95% CI               : {result.confidence_interval[0]:.2%} - {result.confidence_interval[1]:.2%}")


def test_peers_with_mock():
    """複数ティッカーのボラティリティ取得（yfinance をモック）"""
    np.random.seed(0)
    estimator = VolatilityEstimator()
    tickers = ["7203.T", "7267.T", "7269.T"]
    n = 252
    dates = pd.date_range("2023-01-01", periods=n, freq="B")

    def mock_ticker_factory(symbol):
        ticker_mock = MagicMock()
        prices = 1000.0 * np.cumprod(
            1 + np.random.normal(0.0003, 0.015, n)
        )
        hist_df = pd.DataFrame({"Close": prices}, index=dates)
        ticker_mock.history.return_value = hist_df
        return ticker_mock

    with patch("src.utils.volatility_estimator.yf") as mock_yf:
        mock_yf.Ticker.side_effect = mock_ticker_factory

        summary = estimator.fetch_peer_volatility(tickers)

    print(f"\nPeerVolatilitySummary (mocked):")
    print(f"  mean_volatility  : {summary.mean_volatility:.2%}")
    print(f"  median_volatility: {summary.median_volatility:.2%}")
    print(f"  failed_tickers   : {summary.failed_tickers}")

    assert isinstance(summary, PeerVolatilitySummary)
    assert len(summary.tickers) == 3
    assert not np.isnan(summary.mean_volatility), "mean_volatility が NaN"
    assert summary.mean_volatility > 0, "mean_volatility は正の値"
    assert len(summary.failed_tickers) == 0, "失敗したティッカーなし"


# -----------------------------------------------------------------------
# オンラインテスト（ネットワーク不可環境はスキップ）
# -----------------------------------------------------------------------

def test_peers():
    """
    実際の yfinance を使用するテスト。
    ネットワーク不可・データ取得失敗時は自動スキップ。
    """
    try:
        import yfinance as yf
        hist = yf.Ticker("7203.T").history(period="5d")
        if hist is None or hist.empty:
            pytest.skip("yfinance データ取得不可（ネットワーク問題）")
    except Exception as exc:
        pytest.skip(f"yfinance 利用不可: {exc}")

    estimator = VolatilityEstimator()
    tickers = ["7203.T", "7267.T", "7269.T"]
    summary = estimator.fetch_peer_volatility(tickers)

    print(f"\nPeerVolatilitySummary (live):")
    print(f"  mean_volatility  : {summary.mean_volatility:.2%}")
    print(f"  median_volatility: {summary.median_volatility:.2%}")
    print(f"  failed_tickers   : {summary.failed_tickers}")

    successful = [t for t in tickers if t not in summary.failed_tickers]
    if len(successful) == 0:
        pytest.skip("全ティッカーの取得失敗 - ネットワーク問題の可能性")

    assert isinstance(summary, PeerVolatilitySummary)
    assert summary.mean_volatility > 0
    assert not np.isnan(summary.mean_volatility)

