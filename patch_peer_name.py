# -*- coding: utf-8 -*-
import re

# ============================================================
# volatility_estimator.py の修正
# ============================================================
path_ve = 'src/utils/volatility_estimator.py'
content = open(path_ve, encoding='utf-8-sig').read()

# 修正1: PeerData に company_name フィールドを追加
old1 = (
    "@dataclass\n"
    "class PeerData:\n"
    '    """ピアカンパニーの個別データ"""\n'
    "    ticker: str\n"
    "    volatility: float\n"
    "    success: bool = True\n"
    "    error: Optional[str] = None"
)
new1 = (
    "@dataclass\n"
    "class PeerData:\n"
    '    """ピアカンパニーの個別データ"""\n'
    "    ticker: str\n"
    "    volatility: float\n"
    "    success: bool = True\n"
    "    error: Optional[str] = None\n"
    '    company_name: str = ""'
)
if old1 in content:
    content = content.replace(old1, new1)
    print("✅ 修正1 (PeerData.company_name) 適用済み")
else:
    print("⚠️  修正1: 対象文字列が見つかりませんでした")

# 修正2: _fetch_company_name メソッドを追加（_fetch_single_volatility の直後）
insert_after = "        return float(np.std(log_ret, ddof=1) * np.sqrt(252))\n"
new_method = (
    "\n"
    "    def _fetch_company_name(self, ticker: str) -> str:\n"
    '        """yfinance から企業名を取得する（取得失敗時は空文字列）"""\n'
    "        try:\n"
    "            if not YFINANCE_AVAILABLE or yf is None:\n"
    '                return ""\n'
    "            info = yf.Ticker(ticker).info\n"
    '            return info.get("longName") or info.get("shortName") or ""\n'
    "        except Exception:\n"
    '            return ""\n'
)

if insert_after in content and "_fetch_company_name" not in content:
    # _fetch_single_volatility の return 文の直後に挿入
    idx = content.index(insert_after) + len(insert_after)
    content = content[:idx] + new_method + content[idx:]
    print("✅ 修正2 (_fetch_company_name メソッド) 適用済み")
elif "_fetch_company_name" in content:
    print("ℹ️  修正2: _fetch_company_name は既に存在します")
else:
    print("⚠️  修正2: 挿入位置が見つかりませんでした")

# 修正3: fetch_peer_volatility 内の PeerData 生成に company_name を追加
old3 = "                peers.append(PeerData(ticker=ticker, volatility=vol, success=True))"
new3 = (
    "                name = self._fetch_company_name(ticker)\n"
    "                peers.append(PeerData(ticker=ticker, volatility=vol, success=True, company_name=name))"
)
if old3 in content:
    content = content.replace(old3, new3)
    print("✅ 修正3 (PeerData生成に company_name) 適用済み")
elif "company_name=name" in content:
    print("ℹ️  修正3: company_name=name は既に存在します")
else:
    print("⚠️  修正3: 対象文字列が見つかりませんでした")

# BOMなし UTF-8 で保存
open(path_ve, 'w', encoding='utf-8', newline='\n').write(content)
print(f"💾 {path_ve} を保存しました")

# ============================================================
# new_valuation.py の修正
# ============================================================
path_nv = 'src/ui/pages/new_valuation.py'
content2 = open(path_nv, encoding='utf-8-sig').read()

old_table = (
    "                peer_df = pd.DataFrame([{\n"
    '                    "ティッカー": p.ticker,\n'
    '                    "ボラティリティ": f"{p.volatility:.1%}" if p.success else "取得失敗",\n'
    '                    "ステータス": "✅ 成功" if p.success else f"❌ {p.error or \'失敗\'}",\n'
    "                } for p in summary.peers])\n"
    "                st.dataframe(peer_df, use_container_width=True)"
)
new_table = (
    "                peer_df = pd.DataFrame([{\n"
    '                    "ティッカー": p.ticker,\n'
    '                    "企業名": p.company_name if p.company_name else "–",\n'
    '                    "ボラティリティ": f"{p.volatility:.1%}" if p.success else "取得失敗",\n'
    '                    "ステータス": "✅ 成功" if p.success else f"❌ {p.error or \'失敗\'}",\n'
    "                } for p in summary.peers])\n"
    "                st.dataframe(peer_df, use_container_width=True)"
)

if old_table in content2:
    content2 = content2.replace(old_table, new_table)
    print("✅ 修正4 (new_valuation テーブルに企業名列) 適用済み")
elif '"企業名"' in content2:
    print("ℹ️  修正4: 企業名列は既に存在します")
else:
    print("⚠️  修正4: 対象文字列が見つかりませんでした")

open(path_nv, 'w', encoding='utf-8', newline='\n').write(content2)
print(f"💾 {path_nv} を保存しました")

print("\n🎉 全修正完了")
