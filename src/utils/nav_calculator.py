"""純資産価値(NAV)計算モジュール"""

class NAVCalculator:
    """非上場株式の純資産価値計算"""

    def calculate(
        self,
        total_assets: float,
        total_liabilities: float,
        shares_outstanding: float,
        illiquidity_discount: float = 0.3,
    ) -> dict:
        net_assets = total_assets - total_liabilities
        if net_assets <= 0:
            raise ValueError(
                f"純資産がゼロ以下です: {net_assets:,.0f}円 "
                "(総資産 - 総負債 > 0 になるよう入力してください)"
            )
        if not (0.0 <= illiquidity_discount < 1.0):
            raise ValueError(f"非流動性ディスカウントは0〜1未満で入力してください: {illiquidity_discount}")
        if shares_outstanding <= 0:
            raise ValueError(f"発行済株式数は正の値で入力してください: {shares_outstanding}")

        nav_per_share          = net_assets / shares_outstanding
        adjusted_nav_per_share = nav_per_share * (1.0 - illiquidity_discount)

        return {
            "net_assets":              net_assets,
            "nav_per_share":           nav_per_share,
            "adjusted_nav_per_share":  adjusted_nav_per_share,
            "illiquidity_discount":    illiquidity_discount,
            "shares_outstanding":      shares_outstanding,
        }
