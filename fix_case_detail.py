import pathlib

new_content = """\
from __future__ import annotations
import streamlit as st
from src.services.valuation_service import ValuationService


def render(case_id: int | None = None):
    st.title("ケース詳細")

    svc = ValuationService()

    # ─── ケース選択 ──────────────────────────────────────────────
    if case_id is None:
        cases = svc.list_cases()
        if not cases:
            st.info("保存済みケースがありません。")
            return
        options = {f"[{c['id']}] {c['company_name']} ({c['case_name']})": c['id'] for c in cases}
        selected_label = st.selectbox("ケースを選択", list(options.keys()))
        case_id = options[selected_label]

    # ─── データ取得 ──────────────────────────────────────────────
    case   = svc.get_case(case_id)
    params = svc.get_params(case_id)

    if case is None:
        st.error(f"ケースID {case_id} が見つかりません。")
        return

    # ─── ケース基本情報 ──────────────────────────────────────────
    st.subheader("基本情報")
    col1, col2 = st.columns(2)
    col1.metric("企業名",   case.get('company_name', '-'))
    col2.metric("ケース名", case.get('case_name', '-'))

    notes = case.get('notes', '')
    if notes:
        st.caption(f"備考: {notes}")

    st.divider()

    # ─── パラメータ ──────────────────────────────────────────────
    if params:
        p = params

        st.subheader("評価パラメータ")
        col4, col5, col6 = st.columns(3)
        col4.metric("株価 (S)",       f"{p.get('stock_price', '-')}")
        col5.metric("行使価格 (K)",   f"{p.get('strike_price', '-')}")
        col6.metric("残存期間 (T)",   f"{p.get('time_to_expiry', '-')} 年")

        col7, col8, col9 = st.columns(3)
        col7.metric("無リスク金利",   f"{float(p.get('risk_free_rate', 0)):.3%}")
        col8.metric("配当利回り",     f"{float(p.get('dividend_yield', 0)):.3%}")
        col9.metric("オプション種別", p.get('option_type', '-'))

        st.divider()

        # ─── ボラティリティ情報 ──────────────────────────────────
        st.subheader("ボラティリティ情報")

        vol_value  = p.get('volatility', None)
        vol_method = p.get('vol_method', None)
        vol_period = p.get('vol_period', None)
        vol_source = p.get('vol_source', None)
        vol_data   = p.get('vol_data',   None)

        vcol1, vcol2, vcol3, vcol4 = st.columns(4)
        vcol1.metric("σ値",       f"{float(vol_value):.3f}" if vol_value else "-")
        vcol2.metric("推定方法",   vol_method or "-")
        vcol3.metric("参照期間",   vol_period or "-")
        vcol4.metric("データソース", vol_source or "-")

        if vol_data:
            st.text_area("計算メモ", value=vol_data, height=80, disabled=True)

        st.divider()

        # ─── 評価結果 ────────────────────────────────────────────
        st.subheader("評価結果")
        results = svc.get_results(case_id)  # list[dict]

        # model_type をキーにした辞書に変換
        res_map = {r['model_type']: r for r in results} if results else {}

        def val(model_type: str, field: str) -> float:
            row = res_map.get(model_type, {})
            v = row.get(field)
            return float(v) if v is not None else 0.0

        if res_map:
            rcol1, rcol2 = st.columns(2)
            with rcol1:
                st.metric("加重平均 コール", f"{val('weighted_call', 'option_value'):,.4f}")
                st.metric("B-S コール",      f"{val('bs_call',       'option_value'):,.4f}")
                st.metric("二項木 コール",   f"{val('binomial_call', 'option_value'):,.4f}")
                st.metric("MC コール",       f"{val('mc_call',       'option_value'):,.4f}")
            with rcol2:
                st.metric("加重平均 プット", f"{val('weighted_put',  'option_value'):,.4f}")
                st.metric("B-S プット",      f"{val('bs_put',        'option_value'):,.4f}")
                st.metric("二項木 プット",   f"{val('binomial_put',  'option_value'):,.4f}")
                st.metric("MC プット",       f"{val('mc_put',        'option_value'):,.4f}")

            st.divider()

            st.subheader("Greeks")
            gcol1, gcol2, gcol3, gcol4, gcol5 = st.columns(5)
            gcol1.metric("Delta", f"{val('weighted_call', 'delta'):.4f}")
            gcol2.metric("Gamma", f"{val('weighted_call', 'gamma'):.4f}")
            gcol3.metric("Theta", f"{val('weighted_call', 'theta'):.4f}")
            gcol4.metric("Vega",  f"{val('weighted_call', 'vega'):.4f}")
            gcol5.metric("Rho",   f"{val('weighted_call', 'rho'):.4f}")
        else:
            st.info("評価結果データが見つかりません。")
    else:
        st.info("パラメータデータが見つかりません。")

    st.divider()

    # ─── 削除ボタン ──────────────────────────────────────────────
    with st.expander("危険な操作", expanded=False):
        if st.button("このケースを削除", type="secondary"):
            svc.delete_case(case_id)
            st.success(f"ケースID {case_id} を削除しました。")
            st.rerun()
"""

pathlib.Path('src/ui/pages/case_detail.py').write_text(new_content, encoding='utf-8')
print("WRITTEN")
