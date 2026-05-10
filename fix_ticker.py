import pathlib

path = pathlib.Path('src/ui/pages/new_valuation.py')
original = path.read_text(encoding='utf-8')

# 差し替え対象：col5/col6ブロック全体 + vol_data_raw
old_block = """    col5, col6 = st.columns(2)
    with col5:
        vol_method = st.selectbox(
            "推定方法",
            ["historical", "implied", "garch", "manual"],
            help="historical: 過去データから計算 / implied: オプション市場から逆算 / garch: GARCHモデル / manual: 手動入力"
        )
        vol_period = st.selectbox(
            "参照期間",
            ["1m", "3m", "6m", "1y", "2y", "3y"],
            index=3,
            help="ボラティリティ計算に使用した過去データの期間"
        )
    with col6:
        vol_source = st.text_input(
            "データソース",
            value="Yahoo Finance",
            help="例: Yahoo Finance, Bloomberg, 手動入力"
        )
        volatility = st.number_input(
            "ボラティリティ (σ)",
            value=0.20,
            min_value=0.001,
            max_value=5.0,
            step=0.01,
            format="%.3f"
        )

    vol_data_raw = st.text_area(
        "ボラティリティ計算メモ（任意）",
        value="",
        height=80,
        help="計算根拠・参照したデータの概要など自由記述"
    )"""

new_block = """    col5, col6 = st.columns(2)
    with col5:
        vol_method = st.selectbox(
            "推定方法",
            ["historical", "implied", "garch", "manual"],
            help="historical: 過去データから計算 / implied: オプション市場から逆算 / garch: GARCHモデル / manual: 手動入力"
        )
        vol_period = st.selectbox(
            "参照期間",
            ["1m", "3m", "6m", "1y", "2y", "3y"],
            index=3,
            help="ボラティリティ計算に使用した過去データの期間"
        )
    with col6:
        ticker_symbol = st.text_input(
            "ティッカーシンボル（自動取得用）",
            value="",
            placeholder="例: 7203.T, AAPL",
            help="入力すると Yahoo Finance から株価を取得してσを自動計算します"
        )
        vol_source = st.text_input(
            "データソース",
            value="Yahoo Finance",
            help="例: Yahoo Finance, Bloomberg, 手動入力"
        )

    # ティッカーからσ自動計算
    auto_vol = None
    if ticker_symbol and vol_method == "historical":
        try:
            import yfinance as yf
            import numpy as np
            hist = yf.Ticker(ticker_symbol).history(period=vol_period)
            if not hist.empty:
                log_ret = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
                auto_vol = float(log_ret.std() * np.sqrt(252))
                st.success(f"✅ 自動計算σ = {auto_vol:.4f}（年率、{vol_period}データ使用）")
            else:
                st.warning("⚠️ データ取得失敗。ティッカーを確認してください。")
        except Exception as e:
            st.warning(f"⚠️ 取得エラー: {e}")

    volatility = st.number_input(
        "ボラティリティ (σ)",
        value=float(f"{auto_vol:.4f}") if auto_vol else 0.20,
        min_value=0.001,
        max_value=5.0,
        step=0.01,
        format="%.3f"
    )

    vol_data_raw = st.text_area(
        "ボラティリティ計算メモ（任意）",
        value=f"ティッカー: {ticker_symbol} / 期間: {vol_period} / 自動計算σ: {auto_vol:.4f}" if auto_vol else "",
        height=80,
        help="計算根拠・参照したデータの概要など自由記述"
    )"""

if old_block in original:
    patched = original.replace(old_block, new_block)
    path.write_text(patched, encoding='utf-8')
    print("PATCHED")
else:
    print("NG: 対象ブロックが見つかりません")
    # デバッグ用：最初の不一致行を表示
    old_lines = old_block.split("\n")
    src_lines = original.split("\n")
    for i, ol in enumerate(old_lines):
        if ol not in original:
            print(f"  不一致行 {i+1}: [{ol}]")
            break
