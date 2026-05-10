import pathlib

code = '''import streamlit as st
import sqlite3
import pandas as pd
import pathlib

DB_PATH = pathlib.Path("data/valuations.db")


def get_case(case_id: int):
    if not DB_PATH.exists():
        return None
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT * FROM valuation_cases WHERE id = ?", (case_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def get_results(case_id: int):
    if not DB_PATH.exists():
        return []
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT * FROM valuation_results WHERE case_id = ? ORDER BY created_at DESC",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def show():
    PAGE_LIST = "\U0001f4cb \u8a55\u4fa1\u4e00\u89a7"
    st.title("\U0001f4cb \u8a55\u4fa1\u8a73\u7d30")
    case_id = st.session_state.get("selected_case_id")

    if case_id is None:
        st.warning("\u6848\u4ef6\u304c\u9078\u629e\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002")
        if st.button("\u2190 \u8a55\u4fa1\u4e00\u89a7\u306b\u623b\u308b"):
            st.session_state["current_page"] = PAGE_LIST
            st.rerun()
        return

    case = get_case(case_id)
    if case is None:
        st.error(f"\u6848\u4ef6 ID={case_id} \u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3002")
        if st.button("\u2190 \u8a55\u4fa1\u4e00\u89a7\u306b\u623b\u308b"):
            st.session_state["current_page"] = PAGE_LIST
            st.rerun()
        return

    if st.button("\u2190 \u8a55\u4fa1\u4e00\u89a7\u306b\u623b\u308b"):
        st.session_state["current_page"] = PAGE_LIST
        st.rerun()

    st.divider()
    st.subheader("\u57fa\u672c\u60c5\u5831")
    col1, col2, col3 = st.columns(3)
    col1.metric("\u6848\u4ef6\u540d", case.get("case_name", "-"))
    col2.metric("\u30aa\u30d7\u30b7\u30e7\u30f3\u7a2e\u5225", case.get("option_type", "-"))
    col3.metric("\u4f5c\u6210\u65e5\u6642", str(case.get("created_at", "-"))[:19])

    st.divider()
    st.subheader("\u8a55\u4fa1\u30d1\u30e9\u30e1\u30fc\u30bf")
    params = [
        ("\u539f\u8cc7\u7523\u4fa1\u683c S", "underlying_price"),
        ("\u884c\u4f7f\u4fa1\u683c K", "strike_price"),
        ("\u6b8b\u5b58\u671f\u9593 T", "time_to_expiry"),
        ("\u30ea\u30b9\u30af\u30d5\u30ea\u30fc r", "risk_free_rate"),
        ("\u30dc\u30e9\u30c6\u30a3\u30ea\u30c6\u30a3", "volatility"),
        ("\u914d\u5f53\u5229\u56de\u308a q", "dividend_yield"),
    ]
    c1, c2, c3 = st.columns(3)
    for i, (label, key) in enumerate(params):
        col = [c1, c2, c3][i % 3]
        val = case.get(key)
        col.metric(label, f"{val:.4f}" if isinstance(val, float) else str(val) if val is not None else "-")

    st.divider()
    st.subheader("\u8a08\u7b97\u7d50\u679c")
    results = get_results(case_id)
    if not results:
        st.info("\u8a08\u7b97\u7d50\u679c\u304c\u307e\u3060\u3042\u308a\u307e\u305b\u3093\u3002")
    else:
        df = pd.DataFrame(results)
        want = ["method", "option_value", "delta", "gamma", "vega", "theta", "rho", "created_at"]
        cols = [c for c in want if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)

    st.divider()
    with st.expander("\u30c7\u30d0\u30c3\u30b0\u60c5\u5831", expanded=False):
        st.write("selected_case_id:", case_id)
        st.write("case data:", case)
'''

out = pathlib.Path("src/ui/pages/case_detail.py")
out.write_text(code, encoding="utf-8")
print("done:", out.stat().st_size, "bytes")
