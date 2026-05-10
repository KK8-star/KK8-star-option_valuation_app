"""
Black-Scholesモデル テストスイート
現在のAPI: BlackScholes(S, K, T, r, sigma, q=0)
"""
import pytest
from src.models.black_scholes import BlackScholes, BlackScholesModel, BlackScholesResult


class TestBlackScholes:
    """Black-Scholesモデルのテストクラス"""

    @pytest.fixture
    def bs_model(self):
        """標準的なテスト用パラメータでモデルを生成"""
        return BlackScholes(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)

    def test_call_option_basic(self, bs_model):
        """コールオプション基本テスト"""
        call = bs_model.call_price
        print(f"\nCall price: {call:.4f}")
        assert call > 0, "コール価格は正であるべき"
        assert call < bs_model.S, "コール価格は原資産価格より低いべき"
        # 理論値 ≈ 10.45 (ATM, T=1, r=5%, σ=20%)
        assert abs(call - 10.45) < 0.5, f"ATMコール価格が範囲外: {call:.4f}"

    def test_put_option_basic(self, bs_model):
        """プットオプション基本テスト"""
        put = bs_model.put_price
        print(f"\nPut price: {put:.4f}")
        assert put > 0, "プット価格は正であるべき"
        assert put < bs_model.K, "プット価格は行使価格より低いべき"

    def test_put_call_parity(self, bs_model):
        """プット・コール・パリティ検証: C - P = S - K*e^(-rT)"""
        import math
        call = bs_model.call_price
        put  = bs_model.put_price
        S, K, r, T = bs_model.S, bs_model.K, bs_model.r, bs_model.T
        parity = call - put - (S - K * math.exp(-r * T))
        print(f"\nCall={call:.4f}, Put={put:.4f}, Parity diff={parity:.6f}")
        assert abs(parity) < 1e-6, f"パリティが成立しない: diff={parity}"

    def test_deep_itm_call(self):
        """深いイン・ザ・マネー コール"""
        bs = BlackScholes(S=150.0, K=100.0, T=1.0, r=0.05, sigma=0.20)
        call = bs.call_price
        intrinsic = 150.0 - 100.0
        print(f"\nDeep ITM call: {call:.4f}, intrinsic: {intrinsic:.4f}")
        assert call > intrinsic, "コール価格はイントリンシック価値より高いべき"
        assert call < 150.0, "コール価格は原資産価格より低いべき"

    def test_deep_otm_call(self):
        """深いアウト・オブ・ザ・マネー コール"""
        bs = BlackScholes(S=50.0, K=100.0, T=1.0, r=0.05, sigma=0.20)
        call = bs.call_price
        print(f"\nDeep OTM call: {call:.6f}")
        assert call >= 0, "コール価格は非負であるべき"
        assert call < 1.0, f"深いOTMコールは非常に小さいはず: {call:.4f}"

    def test_invalid_params(self):
        """不正パラメータのバリデーション"""
        with pytest.raises((ValueError, Exception)):
            BlackScholes(S=-100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)

        with pytest.raises((ValueError, Exception)):
            BlackScholes(S=100.0, K=-100.0, T=1.0, r=0.05, sigma=0.20)

        with pytest.raises((ValueError, Exception)):
            BlackScholes(S=100.0, K=100.0, T=1.0, r=0.05, sigma=-0.20)

    def test_zero_time(self):
        """満期時点 (T=0) のエッジケース"""
        # ITM: コール = S - K
        bs_itm = BlackScholes(S=110.0, K=100.0, T=0.0, r=0.05, sigma=0.20)
        assert abs(bs_itm.call_price - 10.0) < 1e-6, \
            f"T=0 ITMコール ≠ 10: {bs_itm.call_price}"

        # OTM: コール = 0
        bs_otm = BlackScholes(S=90.0, K=100.0, T=0.0, r=0.05, sigma=0.20)
        assert abs(bs_otm.call_price) < 1e-6, \
            f"T=0 OTMコール ≠ 0: {bs_otm.call_price}"

    def test_alias_compatibility(self):
        """BlackScholesModel エイリアスが同一クラスを指すこと"""
        assert BlackScholesModel is BlackScholes
        bs = BlackScholesModel(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)
        assert bs.call_price > 0

    def test_greeks(self, bs_model):
        """ギリシャ文字の符号テスト"""
        g = bs_model.greeks
        print(f"\nGreeks: {g}")
        assert 0 < g['delta_call'] < 1,   f"コールδ範囲外: {g['delta_call']}"
        assert -1 < g['delta_put'] < 0,   f"プットδ範囲外: {g['delta_put']}"
        assert g['gamma'] > 0,             f"γ は正のはず: {g['gamma']}"
        assert g['vega']  > 0,             f"νega は正のはず: {g['vega']}"
        assert g['theta_call'] < 0,        f"コールθは負のはず: {g['theta_call']}"
        assert g['rho_call']   > 0,        f"コールρは正のはず: {g['rho_call']}"
