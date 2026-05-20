# src/services/report_generator.py
"""
PDF繝ｻExcel 繝ｬ繝昴・繝育函謌舌し繝ｼ繝薙せ
"""
from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Any

# 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
# Excel (openpyxl)
# 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
try:
    import openpyxl
    from openpyxl import Workbook
    from openpyxl.styles import (
        Alignment, Border, Font, PatternFill, Side,
    )
    from openpyxl.utils import get_column_letter
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False

# 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
# PDF (reportlab)
# 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


# 笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏・
# 譌･譛ｬ隱槭ヵ繧ｩ繝ｳ繝育匳骭ｲ
# 笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏・
_JP_FONT_NAME = "HeiseiMin-W3"   # fallback (ReportLab 蜷梧｢ｱ)
_JP_FONT_REGISTERED = False

def _register_jp_font() -> str:
    """譌･譛ｬ隱槭ヵ繧ｩ繝ｳ繝医ｒ逋ｻ骭ｲ縺励∽ｽｿ逕ｨ縺吶ｋ繝輔か繝ｳ繝亥錐繧定ｿ斐☆"""
    global _JP_FONT_NAME, _JP_FONT_REGISTERED

    if _JP_FONT_REGISTERED:
        return _JP_FONT_NAME

    if not REPORTLAB_OK:
        return "Helvetica"

    # Windows 繧ｷ繧ｹ繝・Β繝輔か繝ｳ繝亥呵｣・
    candidates = [
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\YuGothM.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("JPFont", path))
                _JP_FONT_NAME = "JPFont"
                _JP_FONT_REGISTERED = True
                return _JP_FONT_NAME
            except Exception:
                continue

    # 繧ｷ繧ｹ繝・Β繝輔か繝ｳ繝医′辟｡縺・ｴ蜷医・ ReportLab 蜀・鳩 CID 繝輔か繝ｳ繝・
    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
        _JP_FONT_NAME = "HeiseiMin-W3"
        _JP_FONT_REGISTERED = True
    except Exception:
        _JP_FONT_NAME = "Helvetica"
        _JP_FONT_REGISTERED = True

    return _JP_FONT_NAME


# 笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏・
# ReportGenerator 繧ｯ繝ｩ繧ｹ
# 笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏・
class ReportGenerator:
    """
    PDF / Excel 繝ｬ繝昴・繝医ｒ逕滓・縺吶ｋ繧ｵ繝ｼ繝薙せ繧ｯ繝ｩ繧ｹ縲・

    Parameters
    ----------
    case : dict        ValuationCase 縺ｮ陦後ョ繝ｼ繧ｿ・・get_all_cases 縺ｮ1隕∫ｴ・・
    params : dict      ValuationParameter 繝輔ぅ繝ｼ繝ｫ繝峨・繝槭ャ繝斐Φ繧ｰ
    results : dict     ValuationResult 繝輔ぅ繝ｼ繝ｫ繝峨・繝槭ャ繝斐Φ繧ｰ・郁､・焚繝｢繝・Ν・・
    greeks : dict      Greeks 諠・ｱ・井ｻｻ諢擾ｼ・
    """

    # 繧ｫ繝ｩ繝ｼ繝代Ξ繝・ヨ
    COLOR_PRIMARY   = "#1E3A5F"
    COLOR_SECONDARY = "#2E86AB"
    COLOR_ACCENT    = "#F18F01"
    COLOR_BG_LIGHT  = "#F0F4F8"
    COLOR_SUCCESS   = "#27AE60"

    def __init__(
        self,
        case: dict,
        params: dict,
        results: dict,
        greeks: dict | None = None,
    ) -> None:
        self.case    = case
        self.params  = params
        self.results = results
        self.greeks  = greeks or {}
        self._font   = _register_jp_font()

    # 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    # 蜈ｬ髢・API
    # 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    def generate_pdf(self) -> bytes:
        """PDF 繝舌う繝亥・繧定ｿ斐☆"""
        if not REPORTLAB_OK:
            raise ImportError("reportlab 縺後う繝ｳ繧ｹ繝医・繝ｫ縺輔ｌ縺ｦ縺・∪縺帙ｓ")
        buf = io.BytesIO()
        self._build_pdf(buf)
        return buf.getvalue()

    def generate_excel(self) -> bytes:
        """Excel 繝舌う繝亥・繧定ｿ斐☆"""
        if not OPENPYXL_OK:
            raise ImportError("openpyxl 縺後う繝ｳ繧ｹ繝医・繝ｫ縺輔ｌ縺ｦ縺・∪縺帙ｓ")
        buf = io.BytesIO()
        self._build_excel(buf)
        return buf.getvalue()

    # 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    # PDF 蜀・Κ螳溯｣・
    # 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    def _build_pdf(self, buf: io.BytesIO) -> None:
        font = self._font
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm,  bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        st_title = ParagraphStyle(
            "Title_JP",
            fontName=font, fontSize=18, leading=24,
            textColor=colors.HexColor(self.COLOR_PRIMARY),
            spaceAfter=6,
        )
        st_h2 = ParagraphStyle(
            "H2_JP",
            fontName=font, fontSize=13, leading=18,
            textColor=colors.HexColor(self.COLOR_SECONDARY),
            spaceBefore=12, spaceAfter=4,
        )
        st_body = ParagraphStyle(
            "Body_JP",
            fontName=font, fontSize=9, leading=14,
        )
        st_small = ParagraphStyle(
            "Small_JP",
            fontName=font, fontSize=8, leading=12,
            textColor=colors.grey,
        )

        story: list[Any] = []

        # 笏笏 繧ｿ繧､繝医Ν 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
        story.append(Paragraph("繧ｪ繝励す繝ｧ繝ｳ隧穂ｾ｡繝ｬ繝昴・繝・, st_title))
        story.append(Paragraph(
            f"譯井ｻｶ蜷・ {self.case.get('name', '')} ・・"
            f"莨夂､ｾ蜷・ {self.case.get('company', '')}",
            st_body,
        ))
        story.append(Paragraph(
            f"菴懈・譌･譎・ {datetime.now().strftime('%Y蟷ｴ%m譛・d譌･ %H:%M')}",
            st_small,
        ))
        story.append(HRFlowable(
            width="100%", thickness=2,
            color=colors.HexColor(self.COLOR_PRIMARY),
            spaceAfter=8,
        ))

        # 笏笏 隧穂ｾ｡邨先棡繧ｵ繝槭Μ繝ｼ 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
        story.append(Paragraph("隧穂ｾ｡邨先棡繧ｵ繝槭Μ繝ｼ", st_h2))
        story.append(self._pdf_summary_table(font))
        story.append(Spacer(1, 8 * mm))

        # 笏笏 繝代Λ繝｡繝ｼ繧ｿ 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
        story.append(Paragraph("蜈･蜉帙ヱ繝ｩ繝｡繝ｼ繧ｿ", st_h2))
        story.append(self._pdf_params_table(font))
        story.append(Spacer(1, 8 * mm))

        # 笏笏 繝｢繝・Ν豈碑ｼ・笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
        story.append(Paragraph("繝｢繝・Ν蛻･隧穂ｾ｡邨先棡", st_h2))
        story.append(self._pdf_model_table(font))
        story.append(Spacer(1, 8 * mm))

        # 笏笏 Greeks 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
        if self.greeks:
            story.append(Paragraph("Greeks・域─蠢懷ｺｦ蛻・梵・・, st_h2))
            story.append(self._pdf_greeks_table(font))
            story.append(Spacer(1, 8 * mm))

        # 笏笏 繝輔ャ繧ｿ繝ｼ豕ｨ險・笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(
            "窶ｻ 譛ｬ繝ｬ繝昴・繝医・蜿り・､縺ｧ縺ゅｊ縲∵兜雉・愛譁ｭ縺ｮ譬ｹ諡縺ｨ縺吶ｋ繧ゅ・縺ｧ縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・
            "螳滄圀縺ｮ隧穂ｾ｡縺ｯ蟆る摩螳ｶ縺ｫ縺皮嶌隲・￥縺縺輔＞縲・,
            st_small,
        ))

        doc.build(story)

    def _pdf_table_style(
        self, header_color: str = "#1E3A5F"
    ) -> TableStyle:
        return TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor(header_color)),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, -1), self._font),
            ("FONTSIZE",    (0, 0), (-1, 0), 10),
            ("FONTSIZE",    (0, 1), (-1, -1), 9),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor(self.COLOR_BG_LIGHT)]),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])

    def _pdf_summary_table(self, font: str) -> Table:
        final_price = self.results.get("final_price")
        price_str = f"ﾂ･{final_price:,.2f}" if final_price is not None else "譛ｪ隧穂ｾ｡"
        data = [
            ["鬆・岼", "蛟､"],
            ["譛邨りｩ穂ｾ｡鬘・,      price_str],
            ["繧ｪ繝励す繝ｧ繝ｳ遞ｮ鬘・,  self.results.get("option_type", "窶・)],
            ["繧ｪ繝励す繝ｧ繝ｳ繧ｹ繧ｿ繧､繝ｫ", self.results.get("option_style", "窶・)],
            ["隧穂ｾ｡繝｢繝・Ν",      self.results.get("model", "蜉驥榊ｹｳ蝮・)],
        ]
        tbl = Table(data, colWidths=[80 * mm, 80 * mm])
        style = self._pdf_table_style(self.COLOR_PRIMARY)
        style.add("FONTSIZE", (0, 1), (0, 1), 10)
        style.add("TEXTCOLOR", (1, 1), (1, 1),
                  colors.HexColor(self.COLOR_ACCENT))
        tbl.setStyle(style)
        return tbl

    def _pdf_params_table(self, font: str) -> Table:
        p = self.params
        vol_pct = f"{p.get('volatility', 0) * 100:.1f}%" if p.get("volatility") else "窶・
        data = [
            ["繝代Λ繝｡繝ｼ繧ｿ", "蛟､"],
            ["譬ｪ萓｡ (S)",        f"ﾂ･{p.get('stock_price', 0):,.0f}"],
            ["陦御ｽｿ萓｡譬ｼ (K)",    f"ﾂ･{p.get('strike_price', 0):,.0f}"],
            ["谿句ｭ俶悄髢・(T)",    f"{p.get('time_to_expiry', 0):.4f} 蟷ｴ"],
            ["繝ｪ繧ｹ繧ｯ繝輔Μ繝ｼ繝ｬ繝ｼ繝・(r)", f"{p.get('risk_free_rate', 0) * 100:.2f}%"],
            ["繝懊Λ繝・ぅ繝ｪ繝・ぅ (ﾏ・", vol_pct],
            ["驟榊ｽ灘茜蝗槭ｊ (q)",  f"{p.get('dividend_yield', 0) * 100:.2f}%"],
        ]
        tbl = Table(data, colWidths=[80 * mm, 80 * mm])
        tbl.setStyle(self._pdf_table_style(self.COLOR_SECONDARY))
        return tbl

    def _pdf_model_table(self, font: str) -> Table:
        r = self.results
        data = [["繝｢繝・Ν", "隧穂ｾ｡鬘・, "驥阪∩"]]
        model_map = {
            "bs":       ("繝悶Λ繝・け繝ｻ繧ｷ繝ｧ繝ｼ繝ｫ繧ｺ", "50%"),
            "binomial": ("莠碁・Δ繝・Ν",           "30%"),
            "mc":       ("繝｢繝ｳ繝・き繝ｫ繝ｭ",         "20%"),
        }
        for key, (label, weight) in model_map.items():
            val = r.get(f"{key}_price")
            val_str = f"ﾂ･{val:,.4f}" if val is not None else "窶・
            data.append([label, val_str, weight])

        final = r.get("final_price")
        data.append(["蜉驥榊ｹｳ蝮・ｼ域怙邨ょ､・・,
                      f"ﾂ･{final:,.4f}" if final is not None else "窶・,
                      "窶・])

        tbl = Table(data, colWidths=[60 * mm, 70 * mm, 30 * mm])
        style = self._pdf_table_style(self.COLOR_SECONDARY)
        style.add("BACKGROUND", (0, -1), (-1, -1),
                  colors.HexColor(self.COLOR_ACCENT))
        style.add("TEXTCOLOR",  (0, -1), (-1, -1), colors.white)
        style.add("FONTSIZE",   (0, -1), (-1, -1), 10)
        tbl.setStyle(style)
        return tbl

    def _pdf_greeks_table(self, font: str) -> Table:
        g = self.greeks
        data = [
            ["Greeks", "蛟､", "諢丞袖"],
            ["Delta (ﾎ・", f"{g.get('delta', 0):.4f}",
             "譬ｪ萓｡ 1蜀・､牙虚譎ゅ・繧ｪ繝励す繝ｧ繝ｳ萓｡譬ｼ螟牙喧"],
            ["Gamma (ﾎ・", f"{g.get('gamma', 0):.6f}",
             "Delta 縺ｮ螟牙喧邇・],
            ["Theta (ﾎ・", f"{g.get('theta', 0):.4f}",
             "1譌･邨碁℃縺ｫ繧医ｋ繧ｪ繝励す繝ｧ繝ｳ萓｡譬ｼ螟牙喧"],
            ["Vega (ﾎｽ)",  f"{g.get('vega', 0):.4f}",
             "繝懊Λ繝・ぅ繝ｪ繝・ぅ 1% 螟牙虚譎ゅ・螟牙喧"],
            ["Rho (ﾏ・",   f"{g.get('rho', 0):.4f}",
             "驥大茜 1% 螟牙虚譎ゅ・螟牙喧"],
        ]
        tbl = Table(data, colWidths=[35 * mm, 35 * mm, 90 * mm])
        tbl.setStyle(self._pdf_table_style(self.COLOR_PRIMARY))
        return tbl

    # 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    # Excel 蜀・Κ螳溯｣・
    # 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    def _build_excel(self, buf: io.BytesIO) -> None:
        wb = Workbook()
        wb.remove(wb.active)  # 繝・ヵ繧ｩ繝ｫ繝医す繝ｼ繝亥炎髯､

        self._excel_summary_sheet(wb)
        self._excel_params_sheet(wb)
        self._excel_model_sheet(wb)
        if self.greeks:
            self._excel_greeks_sheet(wb)

        wb.save(buf)

    # 笏笏 繧ｹ繧ｿ繧､繝ｫ螳壽焚 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    @staticmethod
    def _hdr_fill(hex_color: str) -> PatternFill:
        return PatternFill("solid", fgColor=hex_color.lstrip("#"))

    @staticmethod
    def _thin_border() -> Border:
        s = Side(style="thin", color="AAAAAA")
        return Border(left=s, right=s, top=s, bottom=s)

    @staticmethod
    def _set_col_width(ws: Any, col: int, width: float) -> None:
        ws.column_dimensions[get_column_letter(col)].width = width

    def _write_header_row(
        self,
        ws: Any,
        row: int,
        headers: list[str],
        bg: str = "1E3A5F",
    ) -> None:
        for ci, hdr in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=ci, value=hdr)
            cell.font       = Font(bold=True, color="FFFFFF", size=10)
            cell.fill       = PatternFill("solid", fgColor=bg)
            cell.alignment  = Alignment(horizontal="center", vertical="center")
            cell.border     = self._thin_border()

    def _write_data_row(
        self,
        ws: Any,
        row: int,
        values: list[Any],
        bg: str = "FFFFFF",
    ) -> None:
        for ci, val in enumerate(values, start=1):
            cell = ws.cell(row=row, column=ci, value=val)
            cell.fill      = PatternFill("solid", fgColor=bg)
            cell.alignment = Alignment(horizontal="left", vertical="center",
                                       wrap_text=True)
            cell.border    = self._thin_border()

    def _write_title(self, ws: Any, title: str, ncols: int) -> None:
        ws.merge_cells(start_row=1, start_column=1,
                       end_row=1,   end_column=ncols)
        cell = ws.cell(row=1, column=1, value=title)
        cell.font      = Font(bold=True, size=14, color="1E3A5F")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

    def _excel_summary_sheet(self, wb: Workbook) -> None:
        ws = wb.create_sheet("隧穂ｾ｡繧ｵ繝槭Μ繝ｼ")
        self._write_title(ws, "繧ｪ繝励す繝ｧ繝ｳ隧穂ｾ｡繝ｬ繝昴・繝医繧ｵ繝槭Μ繝ｼ", 3)

        # 譯井ｻｶ諠・ｱ
        ws.cell(row=2, column=1,
                value=f"譯井ｻｶ蜷・ {self.case.get('name', '')}  ・・ "
                      f"莨夂､ｾ蜷・ {self.case.get('company', '')}  ・・ "
                      f"菴懈・譌･: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
                ).font = Font(size=9, color="666666")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)

        self._write_header_row(ws, 4, ["鬆・岼", "蛟､", "蛯呵・])
        r = self.results
        final_price = r.get("final_price")
        price_str = f"ﾂ･{final_price:,.2f}" if final_price is not None else "譛ｪ隧穂ｾ｡"

        rows_data = [
            ("譛邨りｩ穂ｾ｡鬘・,         price_str,                          "蜉驥榊ｹｳ蝮・),
            ("繧ｪ繝励す繝ｧ繝ｳ遞ｮ鬘・,     r.get("option_type", "窶・),          ""),
            ("繧ｪ繝励す繝ｧ繝ｳ繧ｹ繧ｿ繧､繝ｫ", r.get("option_style", "窶・),         ""),
            ("隧穂ｾ｡繝｢繝・Ν",         r.get("model", "蜉驥榊ｹｳ蝮・BS/Bi/MC)"), ""),
        ]
        bgs = ["FFFFFF", "F0F4F8"]
        for i, (item, val, note) in enumerate(rows_data):
            self._write_data_row(ws, 5 + i, [item, val, note], bgs[i % 2])

        # 蛻怜ｹ・
        for ci, w in enumerate([30, 25, 30], start=1):
            self._set_col_width(ws, ci, w)
        ws.row_dimensions[4].height = 18

    def _excel_params_sheet(self, wb: Workbook) -> None:
        ws = wb.create_sheet("蜈･蜉帙ヱ繝ｩ繝｡繝ｼ繧ｿ")
        self._write_title(ws, "蜈･蜉帙ヱ繝ｩ繝｡繝ｼ繧ｿ", 2)
        self._write_header_row(ws, 3, ["繝代Λ繝｡繝ｼ繧ｿ", "蛟､"], "2E86AB")

        p = self.params
        vol_pct = (f"{p.get('volatility', 0) * 100:.1f}%"
                   if p.get("volatility") else "窶・)
        rows_data = [
            ("譬ｪ萓｡ (S)",                  f"ﾂ･{p.get('stock_price', 0):,.0f}"),
            ("陦御ｽｿ萓｡譬ｼ (K)",              f"ﾂ･{p.get('strike_price', 0):,.0f}"),
            ("谿句ｭ俶悄髢・(T)",              f"{p.get('time_to_expiry', 0):.4f} 蟷ｴ"),
            ("繝ｪ繧ｹ繧ｯ繝輔Μ繝ｼ繝ｬ繝ｼ繝・(r)",    f"{p.get('risk_free_rate', 0) * 100:.2f}%"),
            ("繝懊Λ繝・ぅ繝ｪ繝・ぅ (ﾏ・",        vol_pct),
            ("驟榊ｽ灘茜蝗槭ｊ (q)",            f"{p.get('dividend_yield', 0) * 100:.2f}%"),
        ]
        bgs = ["FFFFFF", "F0F4F8"]
        for i, (k, v) in enumerate(rows_data):
            self._write_data_row(ws, 4 + i, [k, v], bgs[i % 2])

        self._set_col_width(ws, 1, 35)
        self._set_col_width(ws, 2, 25)

    def _excel_model_sheet(self, wb: Workbook) -> None:
        ws = wb.create_sheet("繝｢繝・Ν豈碑ｼ・)
        self._write_title(ws, "繝｢繝・Ν蛻･隧穂ｾ｡邨先棡", 3)
        self._write_header_row(ws, 3, ["繝｢繝・Ν", "隧穂ｾ｡鬘・, "驥阪∩"], "2E86AB")

        r = self.results
        model_map = [
            ("繝悶Λ繝・け繝ｻ繧ｷ繝ｧ繝ｼ繝ｫ繧ｺ", "bs_price",       "50%"),
            ("莠碁・Δ繝・Ν",           "binomial_price", "30%"),
            ("繝｢繝ｳ繝・き繝ｫ繝ｭ",         "mc_price",       "20%"),
        ]
        bgs = ["FFFFFF", "F0F4F8"]
        for i, (label, key, weight) in enumerate(model_map):
            val = r.get(key)
            val_str = f"ﾂ･{val:,.4f}" if val is not None else "窶・
            self._write_data_row(ws, 4 + i, [label, val_str, weight], bgs[i % 2])

        # 蜷郁ｨ郁｡鯉ｼ亥刈驥榊ｹｳ蝮・ｼ・
        final = r.get("final_price")
        final_str = f"ﾂ･{final:,.4f}" if final is not None else "窶・
        row = 4 + len(model_map)
        for ci, val in enumerate(["蜉驥榊ｹｳ蝮・ｼ域怙邨ょ､・・, final_str, "窶・], start=1):
            cell = ws.cell(row=row, column=ci, value=val)
            cell.font      = Font(bold=True, color="FFFFFF")
            cell.fill      = PatternFill("solid", fgColor="F18F01")
            cell.alignment = Alignment(horizontal="left", vertical="center")
            cell.border    = self._thin_border()

        for ci, w in enumerate([30, 25, 15], start=1):
            self._set_col_width(ws, ci, w)

    def _excel_greeks_sheet(self, wb: Workbook) -> None:
        ws = wb.create_sheet("Greeks")
        self._write_title(ws, "Greeks・域─蠢懷ｺｦ蛻・梵・・, 3)
        self._write_header_row(ws, 3, ["Greeks", "蛟､", "諢丞袖"], "1E3A5F")

        g = self.greeks
        rows_data = [
            ("Delta (ﾎ・", f"{g.get('delta', 0):.6f}",
             "譬ｪ萓｡ 1蜀・､牙虚譎ゅ・繧ｪ繝励す繝ｧ繝ｳ萓｡譬ｼ螟牙喧"),
            ("Gamma (ﾎ・", f"{g.get('gamma', 0):.8f}",
             "Delta 縺ｮ螟牙喧邇・),
            ("Theta (ﾎ・", f"{g.get('theta', 0):.6f}",
             "1譌･邨碁℃縺ｫ繧医ｋ繧ｪ繝励す繝ｧ繝ｳ萓｡譬ｼ螟牙喧"),
            ("Vega (ﾎｽ)",  f"{g.get('vega', 0):.6f}",
             "繝懊Λ繝・ぅ繝ｪ繝・ぅ 1% 螟牙虚譎ゅ・螟牙喧"),
            ("Rho (ﾏ・",   f"{g.get('rho', 0):.6f}",
             "驥大茜 1% 螟牙虚譎ゅ・螟牙喧"),
        ]
        bgs = ["FFFFFF", "F0F4F8"]
        for i, row_vals in enumerate(rows_data):
            self._write_data_row(ws, 4 + i, list(row_vals), bgs[i % 2])

        for ci, w in enumerate([18, 20, 45], start=1):
            self._set_col_width(ws, ci, w)
