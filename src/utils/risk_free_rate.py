"""
src/utils/risk_free_rate.py - 無リスク金利自動取得
優先順位: 1) 財務省HP (国債金利) 2) yfinance (^TNX等) 3) キャッシュ 4) デフォルト値
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# キャッシュファイルパス
_CACHE_PATH = Path(__file__).parent.parent.parent / ".cache" / "risk_free_rate.json"
_CACHE_TTL_HOURS = 24  # キャッシュ有効期間


@dataclass
class RFRResult:
    """無リスク金利取得結果"""
    rate_pct: float          # 金利（%表示）
    rate: float              # 金利（小数）
    source: str              # データソース名
    fetched_at: str          # 取得日時
    maturity: str = "10年"   # 満期
    error: Optional[str] = None

    @property
    def display(self) -> str:
        return f"{self.rate_pct:.3f}% ({self.source}, {self.fetched_at[:10]})"


def _load_cache() -> Optional[RFRResult]:
    """キャッシュから読み込み"""
    try:
        if not _CACHE_PATH.exists():
            return None
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        fetched = datetime.fromisoformat(data["fetched_at"])
        if datetime.now() - fetched > timedelta(hours=_CACHE_TTL_HOURS):
            return None
        return RFRResult(**data)
    except Exception:
        return None


def _save_cache(result: RFRResult) -> None:
    """キャッシュ保存"""
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "rate_pct"  : result.rate_pct,
            "rate"      : result.rate,
            "source"    : result.source,
            "fetched_at": result.fetched_at,
            "maturity"  : result.maturity,
            "error"     : result.error,
        }
        _CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception:
        pass


def _fetch_from_mof() -> Optional[RFRResult]:
    """
    財務省 国債金利情報CSV から10年債利回りを取得
    https://www.mof.go.jp/jgbs/reference/interest_rate/
    """
    url = "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (OptionValuationApp/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("shift_jis", errors="replace")

        lines = [ln for ln in raw.splitlines() if ln.strip()]

        # ヘッダー行を探す（「基準日」が含まれる行）
        header_idx = None
        for i, line in enumerate(lines):
            if "基準日" in line or "date" in line.lower():
                header_idx = i
                break

        if header_idx is None:
            return None

        headers = lines[header_idx].split(",")
        # 10年列インデックスを探す
        ten_yr_idx = None
        for j, h in enumerate(headers):
            if "10年" in h or "10" == h.strip():
                ten_yr_idx = j
                break

        if ten_yr_idx is None:
            return None

        # 最新データ行（ヘッダー以降で有効な最終行）
        latest_rate = None
        latest_date = ""
        for line in reversed(lines[header_idx + 1:]):
            cols = line.split(",")
            if len(cols) > ten_yr_idx:
                val = cols[ten_yr_idx].strip()
                try:
                    latest_rate = float(val)
                    latest_date = cols[0].strip()
                    break
                except ValueError:
                    continue

        if latest_rate is None:
            return None

        return RFRResult(
            rate_pct   = latest_rate,
            rate       = latest_rate / 100,
            source     = "財務省 国債金利情報",
            fetched_at = datetime.now().isoformat(),
            maturity   = "10年",
        )
    except Exception as e:
        return None


def _fetch_from_yfinance() -> Optional[RFRResult]:
    """yfinance から日本10年債 (^JGB10Y相当) を取得"""
    try:
        import yfinance as yf

        # 日本10年国債の代替ティッカー候補
        tickers = ["^JGB10Y", "JPY=X"]
        jgb_tickers = ["^JGB10Y", "IRJPY10YD=X"]

        for ticker_sym in ["^JGB10Y"]:
            try:
                tk = yf.Ticker(ticker_sym)
                hist = tk.history(period="5d")
                if hist.empty:
                    continue
                rate_pct = float(hist["Close"].dropna().iloc[-1])
                if 0 < rate_pct < 20:  # 妥当性チェック
                    return RFRResult(
                        rate_pct   = rate_pct,
                        rate       = rate_pct / 100,
                        source     = f"yfinance ({ticker_sym})",
                        fetched_at = datetime.now().isoformat(),
                        maturity   = "10年",
                    )
            except Exception:
                continue

        # 代替: 米10年債を参考値として取得
        tk = yf.Ticker("^TNX")
        hist = tk.history(period="5d")
        if not hist.empty:
            rate_pct = float(hist["Close"].dropna().iloc[-1])
            return RFRResult(
                rate_pct   = rate_pct,
                rate       = rate_pct / 100,
                source     = "yfinance (^TNX: 米国10年債 参考値)",
                fetched_at = datetime.now().isoformat(),
                maturity   = "10年",
            )
    except Exception:
        pass
    return None


def _fetch_from_stooq() -> Optional[RFRResult]:
    """Stooq から日本10年国債利回りを取得"""
    url = "https://stooq.com/q/d/l/?s=10gjpy.b&i=d"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")

        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if len(lines) < 2:
            return None

        # 最終行: Date,Open,High,Low,Close,Volume
        last_cols = lines[-1].split(",")
        if len(last_cols) < 5:
            return None

        rate_pct = float(last_cols[4])  # Close
        date_str = last_cols[0]

        if not (0 < rate_pct < 20):
            return None

        return RFRResult(
            rate_pct   = rate_pct,
            rate       = rate_pct / 100,
            source     = "Stooq (日本10年国債)",
            fetched_at = datetime.now().isoformat(),
            maturity   = "10年",
        )
    except Exception:
        return None


DEFAULT_RATES = {
    "日本 短期（1年以下）": 0.1,
    "日本 中期（2-5年）" : 0.4,
    "日本 長期（10年）"  : 1.0,
    "米国 長期（10年）"  : 4.5,
}


def fetch_risk_free_rate(
    use_cache: bool = True,
    force_source: Optional[str] = None,
) -> RFRResult:
    """
    無リスク金利を取得（複数ソースのフォールバック付き）

    Args:
        use_cache: Trueの場合、有効期限内のキャッシュを使用
        force_source: "mof" / "stooq" / "yfinance" / None

    Returns:
        RFRResult
    """
    # キャッシュ確認
    if use_cache and force_source is None:
        cached = _load_cache()
        if cached is not None:
            cached.source = cached.source + " [キャッシュ]"
            return cached

    result = None

    if force_source == "mof" or force_source is None:
        result = _fetch_from_mof()

    if result is None and (force_source == "stooq" or force_source is None):
        result = _fetch_from_stooq()

    if result is None and (force_source == "yfinance" or force_source is None):
        result = _fetch_from_yfinance()

    if result is None:
        # フォールバック: デフォルト値
        result = RFRResult(
            rate_pct   = 1.0,
            rate       = 0.01,
            source     = "デフォルト値（取得失敗）",
            fetched_at = datetime.now().isoformat(),
            maturity   = "10年",
            error      = "全ソースからの取得に失敗しました",
        )

    _save_cache(result)
    return result


def get_available_maturities() -> dict[str, float]:
    """よく使われる満期別デフォルト金利（手動選択用）"""
    return DEFAULT_RATES.copy()
