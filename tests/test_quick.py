"""
クイックテスト - 主要機能の動作確認（APIを現在の実装に合わせて修正済み）
"""
import pytest
import math
from src.models.black_scholes import BlackScholes, BlackScholesModel


def test_imports():
    """主要モジュールのインポート確認"""
    print("\n【1. インポートテスト】")
    from src.models.binomial    import BinomialModel
    from src.models.monte_carlo import MonteCarloModel
    print("  ✅ 全モジュールインポート成功")


def test_black_scholes():
    """Black-Scholesの基本計算"""
    print("\n【2. Black-Scholesテスト】")
    bs = BlackScholes(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)
    call = bs.call_price
    put  = bs.put_price
    print(f"  Call={call:.4f}, Put={put:.4f}")
    assert call > 0 and put > 0
    assert abs(call - 10.45) < 0.5


def test_binomial():
    """二項モデルの基本計算"""
    print("\n【3. 二項モデルテスト】")
    from src.models.binomial import BinomialModel
    model = BinomialModel(steps=100)
    result = model.price(
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        volatility=0.20,
        time_to_expiry=1.0,
        option_type="call",
    )
    print(f"  Binomial call={result.price:.4f}")
    assert abs(result.price - 10.45) < 1.0


def test_put_call_parity():
    """プット・コール・パリティ検証"""
    print("\n【4. プット・コール・パリティ検証】")
    bs = BlackScholes(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)
    call = bs.call_price
    put  = bs.put_price
    S, K, r, T = bs.S, bs.K, bs.r, bs.T
    diff = abs(call - put - (S - K * math.exp(-r * T)))
    print(f"  パリティ差: {diff:.8f}")
    assert diff < 1e-6


def test_greeks_signs():
    """ギリシャ文字の符号確認"""
    print("\n【5. ギリシャ文字 符号検証】")
    bs = BlackScholes(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)
    g  = bs.greeks
    print(f"  Greeks: {g}")
    assert 0 < g['delta_call'] < 1
    assert -1 < g['delta_put'] < 0
    assert g['gamma'] > 0
    assert g['vega']  > 0
    assert g['theta_call'] < 0


def test_edge_cases():
    """エッジケーステスト"""
    print("\n【6. エッジケーステスト】")
    # T=0 ITM
    bs_itm = BlackScholes(S=110.0, K=100.0, T=0.0, r=0.05, sigma=0.20)
    assert abs(bs_itm.call_price - 10.0) < 1e-6, \
        f"T=0 ITM失敗: {bs_itm.call_price}"
    # T=0 OTM
    bs_otm = BlackScholes(S=90.0, K=100.0, T=0.0, r=0.05, sigma=0.20)
    assert bs_otm.call_price < 1e-6, \
        f"T=0 OTM失敗: {bs_otm.call_price}"
    print("  ✅ エッジケース全クリア")
