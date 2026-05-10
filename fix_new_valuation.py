import pathlib, sys, textwrap

content = textwrap.dedent("""
    from __future__ import annotations
    import streamlit as st
    from datetime import date
    from src.services.valuation_service import ValuationService, VolatilityMeta


    def render():
        st.title("新規オプション評価")

        # ─── 企業情報 ───────────────────────────────────────────────
        st.subheader("企業情報")
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("企業名", value="Sample Corp")
            industry = st.selectbox("業種", ["general", "technology", "finance", "energy", "healthcare"])
        with col2:
            currency = st.selectbox("通貨", ["JPY", "USD", "EUR"])
            valuation_date = st.date_input("評価日", value=date.today())

        st.divider()

        # ─── 基本パラメータ ─────────────────────────────────────────
        st.subheader("基本パラメータ")
        col3, col4 = st.columns(2)
        with col3:
            stock_price  = st.number_input("株価 (S)",         value=100.0, min_value=0.01, step=1.0)
            strike_price = st.number_input("行使価格 (K)",      value=100.0, min_value=0.01, step=1.0)
            time_to_expiry = st.number_input("残存期間 (年, T)", value=1.0,   min_value=0.01, step=0.1)
        with col4:
            risk_free_rate = st.number_input("無リスク金利 (r)", value=0.02,  min_value=0.0,  step=0.001, format="%.3f")
            dividend_yield = st.number_input("配当利回り (q)",   value=0.0,   min_value=0.0,  step=0.001, format="%.3f")
            option_type    = st.selectbox("オプション種別", ["call", "put"])

        st.divider()

        # ─── ボラティリティ設定 ─────────────────────────────────────
        st.subheader("ボラティリティ設定")
        col5, col6 = st.columns(2)
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
        )

        st.divider()

        # ─── モデル設定 ─────────────────────────────────────────────
        st.subheader("モデル設定")
        col7, col8 = st.columns(2)
        with col7:
            american  = st.checkbox("アメリカンオプション", value=False)
            n_steps   = st.number_input("二項木ステップ数", value=200, min_value=10, max_value=1000, step=10)
        with col8:
            n_paths   = st.number_input("モンテカルロ試行数", value=10000, min_value=1000, max_value=100000, step=1000)

        st.divider()

        # ─── 計算実行 ────────────────────────────────────────────────
        if st.button("評価実行", type="primary", use_container_width=True):
            with st.spinner("計算中..."):
                try:
                    svc = ValuationService()
                    result = svc.calculate(
                        company_name=company_name,
                        stock_price=stock_price,
                        strike_price=strike_price,
                        risk_free_rate=risk_free_rate,
                        volatility=volatility,
                        T=time_to_expiry,
                        dividend_yield=dividend_yield,
                        industry=industry,
                        valuation_date=valuation_date,
                        currency=currency,
                        american=american,
                        n_steps=int(n_steps),
                        n_paths=int(n_paths),
                    )

                    vol_meta = VolatilityMeta(
                        vol_method=vol_method,
                        vol_period=vol_period,
                        vol_source=vol_source,
                        vol_data=vol_data_raw,
                    )

                    case_id = svc.save(result, option_type=option_type, vol_meta=vol_meta)

                    st.success(f"評価完了！ケースID: {case_id}")
                    st.session_state['last_case_id'] = case_id

                    # ─── 結果表示 ────────────────────────────────────
                    st.subheader("評価結果")
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.metric("加重平均 コール価値", f"{result.call_price:,.4f}")
                        st.metric("B-S コール",          f"{result.bs_call:,.4f}")
                        st.metric("二項木 コール",        f"{result.bin_call:,.4f}")
                        st.metric("MC コール",            f"{result.mc_call:,.4f} ± {result.mc_se:,.4f}")
                    with col_r2:
                        st.metric("加重平均 プット価値",  f"{result.put_price:,.4f}")
                        st.metric("B-S プット",           f"{result.bs_put:,.4f}")
                        st.metric("二項木 プット",         f"{result.bin_put:,.4f}")
                        st.metric("MC プット",             f"{result.mc_put:,.4f}")

                    st.subheader("Greeks")
                    gcol1, gcol2, gcol3, gcol4, gcol5 = st.columns(5)
                    gcol1.metric("Delta", f"{result.delta_call:.4f}")
                    gcol2.metric("Gamma", f"{result.gamma:.4f}")
                    gcol3.metric("Theta", f"{result.theta:.4f}")
                    gcol4.metric("Vega",  f"{result.vega:.4f}")
                    gcol5.metric("Rho",   f"{result.rho:.4f}")

                    st.subheader("ボラティリティ情報")
                    st.table({
                        "項目": ["推定方法", "参照期間", "データソース", "σ値"],
                        "値":   [vol_method, vol_period, vol_source, f"{volatility:.3f}"],
                    })

                except Exception as e:
                    st.error(f"計算エラー: {e}")
                    import traceback
                    st.code(traceback.format_exc())
""").lstrip("\\n")

pathlib.Path('src/ui/pages/new_valuation.py').write_text(content, encoding='utf-8')
print('DONE new_valuation.py')

c = pathlib.Path('src/ui/pages/new_valuation.py').read_text(encoding='utf-8')
for label, kw in [
    ('VolatilityMeta import', 'VolatilityMeta'),
    ('vol_method selectbox',  'vol_method'),
    ('vol_period selectbox',  'vol_period'),
    ('vol_source input',      'vol_source'),
    ('vol_meta 生成',         'VolatilityMeta('),
    ('svc.save vol_meta',     'vol_meta=vol_meta'),
]:
    print(('OK' if kw in c else 'NG') + ' ' + label)
