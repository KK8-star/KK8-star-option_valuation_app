import pathlib

path = pathlib.Path('src/ui/pages/new_valuation.py')
original = path.read_text(encoding='utf-8')

old_block = """    # ティッカーからσ自動計算
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
            st.warning(f"⚠️ 取得エラー: {e}")"""

new_block = """    # ティッカーからσ自動計算（複数ティッカー対応）
    auto_vol = None
    if ticker_symbol and vol_method == "historical":
        try:
            import yfinance as yf
            import numpy as np
            tickers = [t.strip() for t in ticker_symbol.split(",") if t.strip()]
            vols = []
            failed = []
            for t in tickers:
                hist = yf.Ticker(t).history(period=vol_period)
                if not hist.empty:
                    log_ret = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
                    v = float(log_ret.std() * np.sqrt(252))
                    vols.append((t, v))
                else:
                    failed.append(t)
            if vols:
                auto_vol = float(np.mean([v for _, v in vols]))
                detail = "  /  ".join([f"{t}: {v:.4f}" for t, v in vols])
                st.success(f"✅ 自動計算σ = {auto_vol:.4f}（平均値）  |  {detail}")
            if failed:
                st.warning(f"⚠️ 取得失敗: {', '.join(failed)}")
        except Exception as e:
            st.warning(f"⚠️ 取得エラー: {e}")"""

if old_block in original:
    patched = original.replace(old_block, new_block)
    path.write_text(patched, encoding='utf-8')
    print("PATCHED")
else:
    print("NG: 対象ブロックが見つかりません")
    old_lines = old_block.split("\n")
    for i, ol in enumerate(old_lines):
        if ol not in original:
            print(f"  不一致行 {i+1}: [{ol}]")
            break
