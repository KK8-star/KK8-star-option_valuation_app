# write_files.py
import os, pathlib

# ── 1. valuation_service.py ─────────────────────────────────────────────────
service_code = '''from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional
import numpy as np
from scipy.stats import norm


def _bs_price(S, K, T, r, sigma, q, is_call: bool) -> float:
    if T <= 0 or sigma <= 0:
        return max(0.0, (S - K) if is_call else (K - S))
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if is_call:
        return float(S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    return float(K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1))


def _bs_greeks(S, K, T, r, sigma, q, is_call: bool) -> dict:
    if T <= 0 or sigma <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
    sqT = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * sqT)
    d2 = d1 - sigma * sqT
    nd1 = norm.pdf(d1)
    delta = np.exp(-q * T) * norm.cdf(d1) if is_call else -np.exp(-q * T) * norm.cdf(-d1)
    gamma = np.exp(-q * T) * nd1 / (S * sigma * sqT)
    vega  = S * np.exp(-q * T) * nd1 * sqT / 100
    if is_call:
        theta = (-S * np.exp(-q * T) * nd1 * sigma / (2 * sqT)
                 - r * K * np.exp(-r * T) * norm.cdf(d2)
                 + q * S * np.exp(-q * T) * norm.cdf(d1))
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        theta = (-S * np.exp(-q * T) * nd1 * sigma / (2 * sqT)
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)
                 - q * S * np.exp(-q * T) * norm.cdf(-d1))
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta / 365),
        "vega":  float(vega),
        "rho":   float(rho),
    }


def _binomial_price(S, K, T, r, sigma, q, is_call: bool,
                    american: bool = False, n: int = 200) -> float:
    dt   = T / n
    u    = np.exp(sigma * np.sqrt(dt))
    d    = 1 / u
    disc = np.exp(-r * dt)
    p    = np.clip((np.exp((r - q) * dt) - d) / (u - d), 0, 1)
    j    = np.arange(n + 1)
    ST   = S * u ** (n - j) * d ** j
    pf   = np.maximum(ST - K, 0) if is_call else np.maximum(K - ST, 0)
    for step in range(n - 1, -1, -1):
        pf = disc * (p * pf[:-1] + (1 - p) * pf[1:])
        if american:
            j2     = np.arange(len(pf))
            ST_now = S * u ** (step - j2) * d ** j2
            intr   = np.maximum(ST_now - K, 0) if is_call else np.maximum(K - ST_now, 0)
            pf     = np.maximum(pf, intr)
    return float(pf[0])


def _mc_price(S, K, T, r, sigma, q, is_call: bool,
              n_paths: int = 10_000, seed: int = 42):
    rng  = np.random.default_rng(seed)
    Z    = rng.standard_normal(n_paths)
    ST   = S * np.exp((r - q - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)
    pf   = np.maximum(ST - K, 0) if is_call else np.maximum(K - ST, 0)
    disc_pf = np.exp(-r * T) * pf
    return float(disc_pf.mean()), float(disc_pf.std(ddof=1) / np.sqrt(n_paths))


@dataclass
class ValuationResult:
    call_price: float
    put_price:  float
    bs_call:    float = 0.0
    bs_put:     float = 0.0
    bin_call:   float = 0.0
    bin_put:    float = 0.0
    mc_call:    float = 0.0
    mc_put:     float = 0.0
    mc_se:      float = 0.0
    delta_call: float = 0.0
    gamma:      float = 0.0
    theta:      float = 0.0
    vega:       float = 0.0
    rho:        float = 0.0
    company_name:   str    = ""
    stock_price:    float  = 0.0
    strike_price:   float  = 0.0
    risk_free_rate: float  = 0.0
    volatility:     float  = 0.0
    T:              float  = 0.0
    dividend_yield: float  = 0.0
    industry:       str    = ""
    currency:       str    = "JPY"
    valuation_date: object = None


@dataclass
class VolatilityMeta:
    vol_method: str = "historical"
    vol_period: str = "1y"
    vol_source: str = ""
    vol_data:   str = ""


class ValuationService:
    WEIGHTS = {"bs": 0.50, "binomial": 0.30, "mc": 0.20}

    def calculate(
        self,
        company_name, stock_price, strike_price, risk_free_rate,
        volatility, T, dividend_yield=0.0, industry="general",
        valuation_date=None, currency="JPY",
        american=False, n_steps=200, n_paths=10_000,
    ):
        S, K, r, s, q = stock_price, strike_price, risk_free_rate, volatility, dividend_yield
        bs_c        = _bs_price(S, K, T, r, s, q, True)
        bs_p        = _bs_price(S, K, T, r, s, q, False)
        gr          = _bs_greeks(S, K, T, r, s, q, True)
        bin_c       = _binomial_price(S, K, T, r, s, q, True,  american, n_steps)
        bin_p       = _binomial_price(S, K, T, r, s, q, False, american, n_steps)
        mc_c, mc_se = _mc_price(S, K, T, r, s, q, True,  n_paths)
        mc_p, _     = _mc_price(S, K, T, r, s, q, False, n_paths)
        w    = self.WEIGHTS
        call = w["bs"] * bs_c + w["binomial"] * bin_c + w["mc"] * mc_c
        put  = w["bs"] * bs_p + w["binomial"] * bin_p + w["mc"] * mc_p
        return ValuationResult(
            call_price=call, put_price=put,
            bs_call=bs_c, bs_put=bs_p,
            bin_call=bin_c, bin_put=bin_p,
            mc_call=mc_c, mc_put=mc_p, mc_se=mc_se,
            delta_call=gr["delta"], gamma=gr["gamma"],
            theta=gr["theta"], vega=gr["vega"], rho=gr["rho"],
            company_name=company_name,
            stock_price=S, strike_price=K,
            risk_free_rate=r, volatility=s, T=T,
            dividend_yield=q, industry=industry,
            currency=currency,
            valuation_date=valuation_date or date.today(),
        )

    def save(self, result, option_type="call", vol_meta=None):
        try:
            from src.data.database import get_db_manager
            from src.data.models import (
                ValuationCase, ValuationParameter,
                ValuationResult as ORMResult,
            )
            meta = vol_meta or VolatilityMeta()
            db   = get_db_manager()
            with db.get_session() as session:
                case = ValuationCase(
                    case_name=f"{result.company_name} - {result.valuation_date}",
                    company_name=result.company_name,
                    is_deleted=0,
                    notes=f"industry: {result.industry}, currency: {result.currency}",
                )
                session.add(case)
                session.flush()
                param = ValuationParameter(
                    case_id=case.id,
                    stock_price=result.stock_price,
                    strike_price=result.strike_price,
                    time_to_expiry=result.T,
                    risk_free_rate=result.risk_free_rate,
                    volatility=result.volatility,
                    dividend_yield=result.dividend_yield,
                    option_type=option_type,
                    vol_method=meta.vol_method,
                    vol_period=meta.vol_period,
                    vol_source=meta.vol_source,
                    vol_data=meta.vol_data,
                )
                session.add(param)
                records = [
                    ("weighted_call", result.call_price,  result.delta_call, result.gamma, result.theta, result.vega, result.rho),
                    ("weighted_put",  result.put_price,   None, result.gamma, None, result.vega, None),
                    ("bs_call",       result.bs_call,     result.delta_call, result.gamma, result.theta, result.vega, result.rho),
                    ("bs_put",        result.bs_put,      None, result.gamma, None, result.vega, None),
                    ("binomial_call", result.bin_call,    None, None, None, None, None),
                    ("binomial_put",  result.bin_put,     None, None, None, None, None),
                    ("mc_call",       result.mc_call,     None, None, None, None, None),
                    ("mc_put",        result.mc_put,      None, None, None, None, None),
                ]
                for model_type, option_value, delta, gamma, theta, vega, rho in records:
                    session.add(ORMResult(
                        case_id=case.id,
                        model_type=model_type,
                        option_value=option_value,
                        delta=delta, gamma=gamma,
                        theta=theta, vega=vega, rho=rho,
                    ))
                return case.id
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    # ------------------------------------------------------------------ #
    #  READ / DELETE helpers                                               #
    # ------------------------------------------------------------------ #

    def list_cases(self) -> list[dict]:
        """論理削除されていない全ケースの概要リストを返す。"""
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationCase
            db = get_db_manager()
            with db.get_session() as session:
                rows = (
                    session.query(ValuationCase)
                    .filter(ValuationCase.is_deleted == 0)
                    .order_by(ValuationCase.id.desc())
                    .all()
                )
                return [
                    {
                        "id":           r.id,
                        "company_name": r.company_name,
                        "case_name":    r.case_name,
                        "notes":        r.notes,
                        "created_at":   str(r.created_at) if r.created_at else "",
                    }
                    for r in rows
                ]
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    def get_case(self, case_id: int) -> dict | None:
        """指定IDのケース基本情報を返す。"""
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationCase
            db = get_db_manager()
            with db.get_session() as session:
                row = (
                    session.query(ValuationCase)
                    .filter(ValuationCase.id == case_id,
                            ValuationCase.is_deleted == 0)
                    .first()
                )
                if row is None:
                    return None
                return {
                    "id":           row.id,
                    "company_name": row.company_name,
                    "case_name":    row.case_name,
                    "notes":        row.notes,
                    "created_at":   str(row.created_at) if row.created_at else "",
                }
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    def get_params(self, case_id: int) -> dict | None:
        """指定IDのパラメータ情報を返す。"""
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationParameter
            db = get_db_manager()
            with db.get_session() as session:
                row = (
                    session.query(ValuationParameter)
                    .filter(ValuationParameter.case_id == case_id)
                    .first()
                )
                if row is None:
                    return None
                return {c.name: getattr(row, c.name) for c in row.__table__.columns}
        except Exception:
            import traceback
            traceback.print_exc()
            return None

    def get_results(self, case_id: int) -> list[dict]:
        """指定IDの評価結果リストを返す。"""
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationResult as ORMResult
            db = get_db_manager()
            with db.get_session() as session:
                rows = (
                    session.query(ORMResult)
                    .filter(ORMResult.case_id == case_id)
                    .all()
                )
                return [
                    {c.name: getattr(r, c.name) for c in r.__table__.columns}
                    for r in rows
                ]
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    def delete_case(self, case_id: int) -> bool:
        """指定IDのケースを論理削除する（関連データは保持）。"""
        try:
            from src.data.database import get_db_manager
            from src.data.models import ValuationCase
            db = get_db_manager()
            with db.get_session() as session:
                case = (
                    session.query(ValuationCase)
                    .filter(ValuationCase.id == case_id)
                    .first()
                )
                if case is None:
                    return False
                case.is_deleted = 1
                session.flush()
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False
'''

# ── 2. case_detail.py ────────────────────────────────────────────────────────
detail_code = '''from __future__ import annotations
import streamlit as st
from src.services.valuation_service import ValuationService


def render(case_id: int | None = None):
    st.title("ケース詳細")

    svc = ValuationService()

    # ── ケース選択 ────────────────────────────────────────────────────────
    if case_id is None:
        cases = svc.list_cases()
        if not cases:
            st.info("保存済みケースがありません。")
            return
        options = {
            f"[{c[\'id\']}] {c[\'company_name\']} ({c[\'case_name\']})": c[\'id\']
            for c in cases
        }
        selected_label = st.selectbox("ケースを選択", list(options.keys()))
        case_id = options[selected_label]

    # ── データ取得 ────────────────────────────────────────────────────────
    case   = svc.get_case(case_id)
    params = svc.get_params(case_id)

    if case is None:
        st.error(f"ケースID {case_id} が見つかりません。")
        st.session_state.pop("selected_case_id", None)
        return

    # ── ケース基本情報 ────────────────────────────────────────────────────
    st.subheader("基本情報")
    col1, col2, col3 = st.columns(3)
    col1.metric("企業名",     case.get("company_name", "-"))
    col2.metric("ケース名",   case.get("case_name",    "-"))
    col3.metric("作成日時",   case.get("created_at",   "-"))

    notes = case.get("notes", "")
    if notes:
        st.caption(f"備考: {notes}")

    st.divider()

    # ── パラメータ ────────────────────────────────────────────────────────
    if params:
        p = params

        st.subheader("評価パラメータ")
        col4, col5, col6 = st.columns(3)
        col4.metric("株価 (S)",       f"{p.get(\'stock_price\',    \'-\')}")
        col5.metric("行使価格 (K)",   f"{p.get(\'strike_price\',   \'-\')}")
        col6.metric("残存期間 (T)",   f"{p.get(\'time_to_expiry\', \'-\')} 年")

        col7, col8, col9 = st.columns(3)
        col7.metric("無リスク金利",   f"{float(p.get(\'risk_free_rate\',  0)):.3%}")
        col8.metric("配当利回り",     f"{float(p.get(\'dividend_yield\',  0)):.3%}")
        col9.metric("オプション種別", p.get("option_type", "-"))

        st.divider()

        # ── ボラティリティ情報 ────────────────────────────────────────
        st.subheader("ボラティリティ情報")
        vol_value  = p.get("volatility",  None)
        vol_method = p.get("vol_method",  None)
        vol_period = p.get("vol_period",  None)
        vol_source = p.get("vol_source",  None)
        vol_data   = p.get("vol_data",    None)

        vcol1, vcol2, vcol3, vcol4 = st.columns(4)
        vcol1.metric("σ値",           f"{float(vol_value):.3f}" if vol_value else "-")
        vcol2.metric("推定方法",       vol_method or "-")
        vcol3.metric("計測期間",       vol_period or "-")
        vcol4.metric("データソース",   vol_source or "-")

        if vol_data:
            st.text_area("算出メモ", value=vol_data, height=80, disabled=True)

        st.divider()

        # ── 評価結果 ──────────────────────────────────────────────────
        st.subheader("評価結果")
        results = svc.get_results(case_id)
        res_map = {r["model_type"]: r for r in results} if results else {}

        def val(model_type: str, field: str) -> float:
            row = res_map.get(model_type, {})
            v   = row.get(field)
            return float(v) if v is not None else 0.0

        if res_map:
            rcol1, rcol2 = st.columns(2)
            with rcol1:
                st.metric("加重平均 コール", f"{val(\'weighted_call\', \'option_value\'):,.4f}")
                st.metric("B-S コール",      f"{val(\'bs_call\',       \'option_value\'):,.4f}")
                st.metric("二項 コール",     f"{val(\'binomial_call\', \'option_value\'):,.4f}")
                st.metric("MC コール",       f"{val(\'mc_call\',       \'option_value\'):,.4f}")
            with rcol2:
                st.metric("加重平均 プット", f"{val(\'weighted_put\',  \'option_value\'):,.4f}")
                st.metric("B-S プット",      f"{val(\'bs_put\',        \'option_value\'):,.4f}")
                st.metric("二項 プット",     f"{val(\'binomial_put\',  \'option_value\'):,.4f}")
                st.metric("MC プット",       f"{val(\'mc_put\',        \'option_value\'):,.4f}")

            st.divider()

            st.subheader("Greeks")
            gcol1, gcol2, gcol3, gcol4, gcol5 = st.columns(5)
            gcol1.metric("Delta", f"{val(\'weighted_call\', \'delta\'):.4f}")
            gcol2.metric("Gamma", f"{val(\'weighted_call\', \'gamma\'):.4f}")
            gcol3.metric("Theta", f"{val(\'weighted_call\', \'theta\'):.4f}")
            gcol4.metric("Vega",  f"{val(\'weighted_call\', \'vega\'):.4f}")
            gcol5.metric("Rho",   f"{val(\'weighted_call\', \'rho\'):.4f}")
        else:
            st.info("評価結果データが見つかりません。")
    else:
        st.info("パラメータデータが見つかりません。")

    st.divider()

    # ── 削除ボタン ────────────────────────────────────────────────────────
    with st.expander("危険な操作", expanded=False):
        st.warning("削除すると一覧から非表示になります。この操作は取り消せません。")
        if st.button("このケースを削除", type="secondary", key=f"del_{case_id}"):
            ok = svc.delete_case(case_id)
            if ok:
                st.success(f"ケースID {case_id} を削除しました。")
                st.session_state.pop("selected_case_id", None)
                st.rerun()
            else:
                st.error("削除に失敗しました。")
'''

pathlib.Path("src/services/valuation_service.py").write_text(service_code, encoding="utf-8")
print("OK: valuation_service.py")

pathlib.Path("src/ui/pages/case_detail.py").write_text(detail_code, encoding="utf-8")
print("OK: case_detail.py")
