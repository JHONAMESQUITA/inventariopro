import os
from datetime import datetime
from fpdf import FPDF
from database.connection import db_query
from services.inventario import obtener_reporte_estadisticas, obtener_alertas_activas
from services.excel_service import ruta_exportacion
from services.auditoria import log_auditoria


PDF_STYLES = {
    "bg_dark": (15, 23, 42),
    "bg_card": (30, 41, 59),
    "primary": (56, 189, 248),
    "success": (16, 185, 129),
    "danger": (248, 113, 113),
    "warning": (245, 158, 11),
    "text": (203, 213, 225),
    "text_dim": (100, 116, 139),
    "white": (248, 250, 252),
}


class PDFReport(FPDF):
    def header(self):
        self.set_fill_color(*PDF_STYLES["bg_dark"])
        self.rect(0, 0, 210, 15, 'F')
        self.set_text_color(*PDF_STYLES["primary"])
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 10, "INVENTARIO PRO - Reporte", align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_fill_color(*PDF_STYLES["bg_dark"])
        self.rect(0, self.get_y(), 210, 15, 'F')
        self.set_text_color(*PDF_STYLES["text_dim"])
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align='C')

    def section_title(self, title, color=None):
        if color is None:
            color = PDF_STYLES["primary"]
        self.set_fill_color(*color)
        self.set_text_color(*PDF_STYLES["white"])
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def card(self, lines, col1_width=80):
        self.set_fill_color(*PDF_STYLES["bg_card"])
        x = self.get_x()
        y = self.get_y()
        line_h = 7
        h = len(lines) * line_h + 6
        self.rect(x, y, 190, h, 'F')
        self.set_xy(x + 4, y + 3)
        self.set_text_color(*PDF_STYLES["text"])
        self.set_font("Helvetica", "", 10)
        for label, value in lines:
            self.set_font("Helvetica", "B", 10)
            self.cell(col1_width, line_h, f"{label}:")
            self.set_font("Helvetica", "", 10)
            self.cell(0, line_h, str(value), new_x="LMARGIN", new_y="NEXT")
            self.set_x(x + 4)
        self.set_y(y + h + 4)


def generar_pdf() -> str:
    ruta = ruta_exportacion(f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    stats = obtener_reporte_estadisticas()
    alertas = obtener_alertas_activas()

    pdf.section_title("RESUMEN EJECUTIVO", PDF_STYLES["warning"])
    pdf.card([
        ("Total Movimientos", stats["total_movimientos"]),
        ("Entradas", stats["entradas"]),
        ("Salidas", stats["salidas"]),
        ("Materiales", stats["materiales"]),
        ("Responsables", stats["responsables"]),
        ("Material mas activo", stats["material_top"]),
    ])

    pdf.section_title("VOLUMENES", PDF_STYLES["success"])
    pdf.card([
        ("Vol. Entradas", stats["vol_entradas"]),
        ("Vol. Salidas", stats["vol_salidas"]),
        ("Balance Neto", round(stats["vol_entradas"] - stats["vol_salidas"], 2)),
        ("Ratio E/S", round(stats["entradas"] / max(stats["salidas"], 1), 2)),
    ])

    if alertas:
        pdf.section_title(f"ALERTAS DE STOCK ({len(alertas)})", PDF_STYLES["danger"])
        pdf.card([(mat, f"Disp: {disp} / Min: {minimo}") for mat, disp, minimo in alertas])

    if stats["top5_materiales"]:
        pdf.section_title("TOP 5 MATERIALES", PDF_STYLES["primary"])
        pdf.card([(m, str(cnt)) for m, cnt in stats["top5_materiales"]])

    if stats["mats_inactivos"]:
        pdf.section_title("MATERIALES INACTIVOS", PDF_STYLES["text_dim"])
        pdf.card([(m, "+30d sin mov") for m in stats["mats_inactivos"][:10]])

    pdf.set_text_color(*PDF_STYLES["text_dim"])
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 10, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align='C')

    pdf.output(ruta)
    log_auditoria("PDF_EXPORT", ruta)
    return ruta
