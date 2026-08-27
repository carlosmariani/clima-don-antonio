"""
generador_pdf_precios.py
Genera el PDF "Informe de Precios Mayoristas" — Don Antonio SRL.

Estructura:
  - Portada con resumen ejecutivo (cuántos productos, variación general)
  - Tabla por producto con: variedad / procedencia / envase / peso / precio bulto (max/medio/min)
  - Variación vs día hábil anterior (↑↓)
  - Disclaimer y fuente
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

# Zona horaria Argentina (UTC-3) — no usar zoneinfo para evitar problemas
# en runners GitHub Actions sin tzdata instalado
TZ_AR = timezone(timedelta(hours=-3))


def _ahora_ar() -> datetime:
    """Devuelve la hora actual en Argentina (UTC-3)."""
    return datetime.now(TZ_AR)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

from precios_mercado import envase_legible, variedad_legible


COLOR_PRIMARIO = colors.HexColor("#1B5E20")
COLOR_SECUNDARIO = colors.HexColor("#F9A825")
COLOR_ACENTO = colors.HexColor("#0D47A1")
COLOR_GRIS = colors.HexColor("#555555")
COLOR_GRIS_CLARO = colors.HexColor("#EEEEEE")
COLOR_FONDO = colors.HexColor("#F5F7FA")
COLOR_VERDE = colors.HexColor("#2E7D32")
COLOR_ROJO = colors.HexColor("#C62828")


class GeneradorPDFPrecios:
    def __init__(self, empresa: Dict, logo_path: str = "logo.png"):
        self.empresa = empresa
        self.logo_path = logo_path
        self.styles = self._build_styles()

    def _build_styles(self):
        s = getSampleStyleSheet()
        s.add(ParagraphStyle(
            name="TituloPortada", fontName="Helvetica-Bold", fontSize=18,
            textColor=COLOR_PRIMARIO, alignment=TA_LEFT, spaceAfter=2, leading=22
        ))
        s.add(ParagraphStyle(
            name="SubtituloPortada", fontName="Helvetica", fontSize=10,
            textColor=COLOR_GRIS, alignment=TA_LEFT, spaceAfter=8, leading=13
        ))
        s.add(ParagraphStyle(
            name="ParrafoNarrativo", fontName="Helvetica", fontSize=9,
            textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=6, leading=12,
        ))
        s.add(ParagraphStyle(
            name="EspecieTitulo", fontName="Helvetica-Bold", fontSize=11,
            textColor=COLOR_PRIMARIO, alignment=TA_LEFT, spaceBefore=6, spaceAfter=2, leading=13
        ))
        s.add(ParagraphStyle(
            name="Disclaimer", fontName="Helvetica-Oblique", fontSize=7,
            textColor=COLOR_GRIS, alignment=TA_JUSTIFY, leading=9
        ))
        s.add(ParagraphStyle(
            name="Cell", fontName="Helvetica", fontSize=7.5,
            textColor=colors.black, alignment=TA_LEFT, leading=9
        ))
        s.add(ParagraphStyle(
            name="CellRight", fontName="Helvetica", fontSize=7.5,
            textColor=colors.black, alignment=TA_RIGHT, leading=9
        ))
        s.add(ParagraphStyle(
            name="CellCenter", fontName="Helvetica", fontSize=7.5,
            textColor=colors.black, alignment=TA_CENTER, leading=9
        ))
        s.add(ParagraphStyle(
            name="ThWhite", fontName="Helvetica-Bold", fontSize=7,
            textColor=colors.white, alignment=TA_CENTER, leading=9
        ))
        # Estilos nuevos para las cards de clima por zona
        s.add(ParagraphStyle(
            name="ZonaClima", fontName="Helvetica-Bold", fontSize=13,
            textColor=colors.white, alignment=TA_LEFT,
            leading=16, spaceBefore=0, spaceAfter=0,
            leftIndent=8
        ))
        s.add(ParagraphStyle(
            name="ZonaClimaSub", fontName="Helvetica-Oblique", fontSize=8,
            textColor=colors.white, alignment=TA_LEFT,
            leading=10, leftIndent=8
        ))
        return s

    # ------------------------------------------------------------------ #
    # Encabezado y pie en cada página
    # ------------------------------------------------------------------ #
    def _header_footer(self, canv: canvas.Canvas, doc):
        canv.saveState()
        if os.path.exists(self.logo_path):
            try:
                canv.drawImage(self.logo_path, 1.5 * cm, A4[1] - 2.4 * cm,
                               width=4.5 * cm, height=1.5 * cm, mask='auto',
                               preserveAspectRatio=True)
            except Exception:
                pass
        canv.setFont("Helvetica-Bold", 9)
        canv.setFillColor(COLOR_PRIMARIO)
        canv.drawRightString(A4[0] - 1.5 * cm, A4[1] - 1.4 * cm, self.empresa["nombre"])
        canv.setFont("Helvetica", 8)
        canv.setFillColor(COLOR_GRIS)
        canv.drawRightString(A4[0] - 1.5 * cm, A4[1] - 1.85 * cm,
                             "Informe de Precios — Mercado Central")
        canv.setStrokeColor(COLOR_PRIMARIO)
        canv.setLineWidth(1.5)
        canv.line(1.5 * cm, A4[1] - 2.6 * cm, A4[0] - 1.5 * cm, A4[1] - 2.6 * cm)

        canv.setStrokeColor(COLOR_GRIS_CLARO)
        canv.setLineWidth(0.5)
        canv.line(1.5 * cm, 1.7 * cm, A4[0] - 1.5 * cm, 1.7 * cm)
        canv.setFont("Helvetica", 7)
        canv.setFillColor(COLOR_GRIS)
        canv.drawString(1.5 * cm, 1.3 * cm,
                        f"{self.empresa['nombre']} — {self.empresa.get('rubro', '')}")
        canv.drawString(1.5 * cm, 1.0 * cm,
                        f"{self.empresa.get('web', '')}    {self.empresa.get('email', '')}".strip())
        canv.drawRightString(A4[0] - 1.5 * cm, 1.3 * cm, f"Página {doc.page}")
        canv.drawRightString(A4[0] - 1.5 * cm, 1.0 * cm,
                             f"Generado: {_ahora_ar().strftime('%d/%m/%Y %H:%M')} hs")
        canv.restoreState()

    # ------------------------------------------------------------------ #
    # Tabla por especie
    # ------------------------------------------------------------------ #
    def _tabla_producto(self, items: List[Dict], variaciones: Dict) -> Table:
        rows = [[
            Paragraph("<b>VARIEDAD</b>", self.styles["ThWhite"]),
            Paragraph("<b>PROCEDENCIA</b>", self.styles["ThWhite"]),
            Paragraph("<b>ENVASE</b>", self.styles["ThWhite"]),
            Paragraph("<b>BULTO</b>", self.styles["ThWhite"]),
            Paragraph("<b>$ MÍN</b>", self.styles["ThWhite"]),
            Paragraph("<b>$ MEDIO</b>", self.styles["ThWhite"]),
            Paragraph("<b>$ MÁX</b>", self.styles["ThWhite"]),
            Paragraph("<b>VS AYER</b>", self.styles["ThWhite"]),
        ]]
        for it in items:
            esp = it["especie"]
            clave = (esp, it["variedad"], it["procedencia"])
            var_pct = variaciones.get(clave)

            if var_pct is None or it["precio_med_bulto"] == 0:
                var_str = "—"
                var_color = "#666666"
            elif var_pct > 0:
                var_str = f"↑ {var_pct:+.1f}%"
                var_color = "#C62828"  # rojo: subió
            elif var_pct < 0:
                var_str = f"↓ {var_pct:+.1f}%"
                var_color = "#2E7D32"  # verde: bajó
            else:
                var_str = "= 0%"
                var_color = "#666666"

            es_fb = it.get("es_fallback", False)
            asterisco = " *" if es_fb else ""
            proc_str = (it['procedencia'] or "—") + asterisco

            rows.append([
                Paragraph(variedad_legible(it["variedad"]), self.styles["Cell"]),
                Paragraph(proc_str, self.styles["Cell"]),
                Paragraph(envase_legible(it["envase"]), self.styles["Cell"]),
                Paragraph(f"{it['kg_bulto']:.0f} kg" if it['kg_bulto'] else "—",
                          self.styles["CellCenter"]),
                Paragraph(f"${it['precio_min_bulto']:,.0f}".replace(",", "."),
                          self.styles["CellRight"]),
                Paragraph(f"<b>${it['precio_med_bulto']:,.0f}</b>".replace(",", "."),
                          self.styles["CellRight"]),
                Paragraph(f"${it['precio_max_bulto']:,.0f}".replace(",", "."),
                          self.styles["CellRight"]),
                Paragraph(f'<font color="{var_color}">{var_str}</font>',
                          self.styles["CellCenter"]),
            ])

        t = Table(rows, colWidths=[
            2.6 * cm,  # variedad
            2.4 * cm,  # procedencia
            2.0 * cm,  # envase
            1.5 * cm,  # bulto kg
            1.9 * cm,  # min
            2.1 * cm,  # medio
            1.9 * cm,  # max
            1.8 * cm,  # variación
        ], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO]),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS_CLARO),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        return t

    # ------------------------------------------------------------------ #
    # Resumen ejecutivo
    # ------------------------------------------------------------------ #
    def _texto_resumen(self, datos: Dict, variaciones: Dict) -> str:
        productos = datos.get("productos", {})
        n_prod = len(productos)
        n_items = sum(len(v) for v in productos.values())

        # Calcular productos que subieron y bajaron
        subieron = sum(1 for v in variaciones.values() if v > 5)
        bajaron = sum(1 for v in variaciones.values() if v < -5)
        estables = sum(1 for v in variaciones.values() if -5 <= v <= 5)

        texto = (
            f"Este informe presenta los precios mayoristas relevados hoy en el "
            f"<b>Mercado Central de Buenos Aires</b> para "
            f"<b>{n_prod} grupos de productos</b> hortícolas y frutícolas seleccionados, "
            f"con un total de <b>{n_items} cotizaciones</b> diferenciadas por variedad, "
            f"procedencia y tipo de envase. "
        )
        if variaciones:
            if subieron > bajaron:
                texto += (
                    f"Comparando con el día hábil anterior, "
                    f"<b>{subieron} cotizaciones subieron</b> más de un 5%, "
                    f"<b>{bajaron} bajaron</b> y "
                    f"<b>{estables} se mantuvieron estables</b>. "
                )
            elif bajaron > subieron:
                texto += (
                    f"Comparando con el día hábil anterior, "
                    f"<b>{bajaron} cotizaciones bajaron</b> más de un 5%, "
                    f"<b>{subieron} subieron</b> y "
                    f"<b>{estables} se mantuvieron estables</b>. "
                )
            else:
                texto += (
                    f"En comparación con el día hábil anterior, los precios se mantuvieron "
                    f"mayormente estables ({estables} sin variación significativa). "
                )
        if not datos.get("esta_actualizado", False):
            texto += (
                "<br/><br/><i>Atención:</i> el MCBA aún no publicó los datos de hoy. "
                "Los precios mostrados corresponden al último día hábil con información disponible."
            )
        return texto

    # ------------------------------------------------------------------ #
    # Tabla compacta de clima 48hs (mañana + pasado) para todas las zonas
    # ------------------------------------------------------------------ #
    def _tabla_clima_48h(self, clima_48h: List[Dict]) -> Table:
        """
        Tabla horizontal con columnas: Zona | Mañana (Máx/Mín/mm) | Pasado (Máx/Mín/mm)
        Pensada para caber en una sola página y ser fácil de leer en email/PDF.
        """
        # Encabezado de 2 niveles
        rows = [
            [
                Paragraph("<b>ZONA</b>", self.styles["ThWhite"]),
                Paragraph("<b>MAÑANA</b>", self.styles["ThWhite"]),
                "", "",
                Paragraph("<b>PASADO</b>", self.styles["ThWhite"]),
                "", "",
            ],
            [
                "",
                Paragraph("<b>Máx</b>", self.styles["ThWhite"]),
                Paragraph("<b>Mín</b>", self.styles["ThWhite"]),
                Paragraph("<b>Lluvia</b>", self.styles["ThWhite"]),
                Paragraph("<b>Máx</b>", self.styles["ThWhite"]),
                Paragraph("<b>Mín</b>", self.styles["ThWhite"]),
                Paragraph("<b>Lluvia</b>", self.styles["ThWhite"]),
            ]
        ]
        styles_extra = []
        for i, c in enumerate(clima_48h, start=2):  # +2 por dos filas de header
            if c.get("alerta"):
                styles_extra.append(("BACKGROUND", (0, i), (-1, i),
                                     colors.HexColor("#FFF3E0")))
            rows.append([
                Paragraph(f"<b>{c['zona']}</b><br/>"
                          f"<font size='7' color='#888'>{c['provincia']}</font>",
                          self.styles["Cell"]),
                Paragraph(f"{c.get('tmax', 0):.0f}°", self.styles["CellCenter"]),
                Paragraph(f"{c.get('tmin', 0):.0f}°", self.styles["CellCenter"]),
                Paragraph(f"{c.get('lluvia_mm', 0):.0f} mm",
                          self.styles["CellCenter"]),
                Paragraph(f"{c.get('tmax_pasado', 0):.0f}°",
                          self.styles["CellCenter"]),
                Paragraph(f"{c.get('tmin_pasado', 0):.0f}°",
                          self.styles["CellCenter"]),
                Paragraph(f"{c.get('lluvia_pasado', 0):.0f} mm",
                          self.styles["CellCenter"]),
            ])

        t = Table(rows, colWidths=[
            4.0 * cm,    # zona
            1.4 * cm, 1.4 * cm, 1.7 * cm,  # mañana
            1.4 * cm, 1.4 * cm, 1.7 * cm,  # pasado
        ], repeatRows=2)
        base_styles = [
            ("BACKGROUND", (0, 0), (-1, 1), COLOR_ACENTO),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.white),
            ("SPAN", (0, 0), (0, 1)),         # ZONA span filas 0-1
            ("SPAN", (1, 0), (3, 0)),         # MAÑANA span 3 cols
            ("SPAN", (4, 0), (6, 0)),         # PASADO span 3 cols
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, COLOR_FONDO]),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS_CLARO),
            ("LINEAFTER", (3, 0), (3, -1), 0.6, COLOR_ACENTO),  # separador
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        t.setStyle(TableStyle(base_styles + styles_extra))
        return t

    # ------------------------------------------------------------------ #
    # Tabla de alertas previstas en los próximos 15 días
    # ------------------------------------------------------------------ #
    def _tabla_pronostico_diario(self, dias: List[Dict]) -> Table:
        """
        Tabla con el pronóstico día por día (próximos 7 días) para una zona.
        Solo se incluye cuando se filtra el reporte por zona específica.
        Columnas: Día | Tmáx | Tmín | Lluvia | Comentario
        """
        meses_es = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may",
                    6: "jun", 7: "jul", 8: "ago", 9: "sep",
                    10: "oct", 11: "nov", 12: "dic"}
        dias_semana = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue",
                       4: "Vie", 5: "Sáb", 6: "Dom"}

        rows = [[
            Paragraph("<b>DÍA</b>", self.styles["ThWhite"]),
            Paragraph("<b>T.MÁX</b>", self.styles["ThWhite"]),
            Paragraph("<b>T.MÍN</b>", self.styles["ThWhite"]),
            Paragraph("<b>LLUVIA</b>", self.styles["ThWhite"]),
            Paragraph("<b>PROB.</b>", self.styles["ThWhite"]),
            Paragraph("<b>COMENTARIO</b>", self.styles["ThWhite"]),
        ]]
        styles_extra = []
        for i, dia in enumerate(dias, start=1):
            try:
                f_dt = datetime.strptime(dia["fecha"], "%Y-%m-%d")
                f_str = f"{dias_semana[f_dt.weekday()]} {f_dt.day:02d}/{meses_es[f_dt.month]}"
            except Exception:
                f_str = dia.get("fecha", "—")

            coment = dia.get("comentario", "")
            # Resaltar filas con eventos críticos
            if any(k in coment for k in ["Helada", "Calor extremo", "Lluvia intensa", "Viento fuerte"]):
                styles_extra.append(("BACKGROUND", (0, i), (-1, i),
                                     colors.HexColor("#FFEBEE")))
            elif "Lluvia" in coment or "Probable" in coment:
                styles_extra.append(("BACKGROUND", (0, i), (-1, i),
                                     colors.HexColor("#E3F2FD")))

            rows.append([
                Paragraph(f"<b>{f_str}</b>", self.styles["CellCenter"]),
                Paragraph(f"{dia.get('tmax', 0):.0f}°", self.styles["CellCenter"]),
                Paragraph(f"{dia.get('tmin', 0):.0f}°", self.styles["CellCenter"]),
                Paragraph(f"{dia.get('lluvia', 0):.0f} mm",
                          self.styles["CellCenter"]),
                Paragraph(f"{dia.get('prob_lluvia', 0):.0f}%",
                          self.styles["CellCenter"]),
                Paragraph(coment, self.styles["Cell"]),
            ])

        t = Table(rows, colWidths=[
            2.6 * cm,  # día
            1.4 * cm,  # tmax
            1.4 * cm,  # tmin
            1.6 * cm,  # lluvia
            1.4 * cm,  # prob
            6.4 * cm,  # comentario
        ], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACENTO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS_CLARO),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ] + styles_extra))
        return t

    def _tabla_alertas_15d(self, alertas_15d: List[Dict]) -> Table:
        """
        Construye una tabla con todas las alertas previstas en los próximos
        15 días, ordenadas por fecha. Cada fila: Fecha · Zona · Tipo · Detalle · Sev.
        """
        # Aplanar: una fila por (zona, alerta)
        filas_plano = []
        for z in alertas_15d:
            for a in z["alertas"]:
                filas_plano.append({
                    "fecha": a["fecha"],
                    "zona": z["zona"],
                    "provincia": z["provincia"],
                    "tipo": a["tipo"],
                    "icono": a["icono"],
                    "valor": a["valor"],
                    "detalle": a.get("detalle", ""),
                    "severidad": a["severidad"],
                })
        # Ordenar por fecha y luego por severidad (ALTA primero)
        sev_orden = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
        filas_plano.sort(key=lambda r: (r["fecha"],
                                          sev_orden.get(r["severidad"], 9)))

        rows = [[
            Paragraph("<b>FECHA</b>", self.styles["ThWhite"]),
            Paragraph("<b>ZONA</b>", self.styles["ThWhite"]),
            Paragraph("<b>TIPO</b>", self.styles["ThWhite"]),
            Paragraph("<b>DETALLE</b>", self.styles["ThWhite"]),
            Paragraph("<b>SEV.</b>", self.styles["ThWhite"]),
        ]]
        styles_extra = []
        meses_es = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may",
                    6: "jun", 7: "jul", 8: "ago", 9: "sep",
                    10: "oct", 11: "nov", 12: "dic"}
        for i, r in enumerate(filas_plano, start=1):
            try:
                f_dt = datetime.strptime(r["fecha"], "%Y-%m-%d")
                f_str = f"{f_dt.day:02d}/{meses_es[f_dt.month]}"
            except Exception:
                f_str = r["fecha"]

            if r["severidad"] == "ALTA":
                styles_extra.append(("BACKGROUND", (0, i), (-1, i),
                                     colors.HexColor("#FFEBEE")))
                sev_str = '<font color="#C62828"><b>ALTA</b></font>'
            elif r["severidad"] == "MEDIA":
                styles_extra.append(("BACKGROUND", (0, i), (-1, i),
                                     colors.HexColor("#FFF3E0")))
                sev_str = '<font color="#EF6C00"><b>MEDIA</b></font>'
            else:
                sev_str = '<font color="#888">BAJA</font>'

            rows.append([
                Paragraph(f"<b>{f_str}</b>", self.styles["CellCenter"]),
                Paragraph(f"<b>{r['zona']}</b><br/>"
                          f"<font size='7' color='#888'>{r['provincia']}</font>",
                          self.styles["Cell"]),
                Paragraph(f"{r['icono']} {r['tipo']}", self.styles["Cell"]),
                Paragraph(f"{r['detalle']}", self.styles["Cell"]),
                Paragraph(sev_str, self.styles["CellCenter"]),
            ])

        t = Table(rows, colWidths=[
            1.7 * cm,  # fecha
            3.4 * cm,  # zona
            3.6 * cm,  # tipo
            5.3 * cm,  # detalle
            1.2 * cm,  # severidad
        ], repeatRows=1)
        base_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACENTO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS_CLARO),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        t.setStyle(TableStyle(base_styles + styles_extra))
        return t

    def _tabla_trimestral(self, trimestral: List[Dict]) -> Table:
        """
        Tabla compacta con el pronóstico trimestral (~90 días) por zona.
        Columnas: Zona · Temp máx prom · Temp mín prom · Lluvia mensual · Tendencia.
        """
        rows = [[
            Paragraph("<b>ZONA</b>", self.styles["ThWhite"]),
            Paragraph("<b>T. MÁX<br/>PROM</b>", self.styles["ThWhite"]),
            Paragraph("<b>T. MÍN<br/>PROM</b>", self.styles["ThWhite"]),
            Paragraph("<b>LLUVIA<br/>MENSUAL</b>", self.styles["ThWhite"]),
            Paragraph("<b>TENDENCIA</b>", self.styles["ThWhite"]),
        ]]
        for r in trimestral:
            res = r.get("resumen", {}) or {}
            tend = r.get("tendencia", {}) or {}
            tmax = res.get("temp_max_promedio")
            tmin = res.get("temp_min_promedio")
            lluvia_m = res.get("lluvia_promedio_mensual") or res.get("lluvia_total_mm") or 0
            desc = tend.get("descripcion") or res.get("nota", "—")
            emoji = tend.get("emoji", "📊")
            rows.append([
                Paragraph(
                    f"<b>{r['zona']}</b><br/>"
                    f"<font size='7' color='#888'>{r['provincia']}</font>",
                    self.styles["Cell"]),
                Paragraph(f"{tmax:.0f}°C" if tmax is not None else "—",
                          self.styles["CellCenter"]),
                Paragraph(f"{tmin:.0f}°C" if tmin is not None else "—",
                          self.styles["CellCenter"]),
                Paragraph(f"{lluvia_m:.0f} mm",
                          self.styles["CellCenter"]),
                Paragraph(f"{emoji} {desc}", self.styles["Cell"]),
            ])
        t = Table(rows, colWidths=[
            3.2 * cm,  # zona
            1.6 * cm,  # tmax
            1.6 * cm,  # tmin
            2.0 * cm,  # lluvia
            6.8 * cm,  # tendencia
        ], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACENTO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS_CLARO),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#FAFBFC")]),
        ]))
        return t

    def _nota_proximo_extendido(self, hoy) -> str:
        """
        Devuelve el texto del pie: 'Próximo extendido trimestral: día X (en Y días)'.
        El extendido sale los días 1 y 15 de cada mes.
        """
        from datetime import date, timedelta
        h = hoy.date() if hasattr(hoy, "date") else hoy
        # Próximo día 1 o 15
        if h.day < 15:
            proximo = h.replace(day=15)
        else:
            # Ir al día 1 del próximo mes
            if h.month == 12:
                proximo = h.replace(year=h.year + 1, month=1, day=1)
            else:
                proximo = h.replace(month=h.month + 1, day=1)
        dias = (proximo - h).days
        meses_es = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo",
                    6: "junio", 7: "julio", 8: "agosto", 9: "septiembre",
                    10: "octubre", 11: "noviembre", 12: "diciembre"}
        fecha_str = f"{proximo.day} de {meses_es[proximo.month]}"
        if dias == 0:
            return f"📊 Extendido trimestral publicado hoy."
        elif dias == 1:
            return f"📊 Próximo extendido trimestral: mañana ({fecha_str})."
        else:
            return (f"📊 Próximo extendido trimestral: {fecha_str} "
                    f"(en {dias} días).")

    # ------------------------------------------------------------------ #
    # Construcción del PDF
    # ------------------------------------------------------------------ #
    def generar(self, datos_hoy: Dict, datos_ayer: Dict,
                variaciones: Dict, output_path: str,
                cliente: str = "",
                clima_48h: List[Dict] = None,
                alertas_7d: List[Dict] = None,
                pronostico_diario: List[Dict] = None,
                trimestral: List[Dict] = None) -> str:
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=1.1 * cm, rightMargin=1.1 * cm,
            topMargin=2.4 * cm, bottomMargin=1.5 * cm,
            title="Informe de Precios — Don Antonio SRL",
            author=self.empresa["nombre"],
            subject="Precios mayoristas del Mercado Central de Buenos Aires",
        )

        story: List[Any] = []

        # =========== PORTADA ===========
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Precios Mayoristas", self.styles["TituloPortada"]))

        meses_es = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo",
                    6: "junio", 7: "julio", 8: "agosto", 9: "septiembre",
                    10: "octubre", 11: "noviembre", 12: "diciembre"}
        fecha = datos_hoy.get("fecha_datos") or _ahora_ar()
        fecha_str = f"{fecha.day} de {meses_es[fecha.month]} de {fecha.year}"
        sub = f"Mercado Central de Buenos Aires &nbsp;·&nbsp; Datos del {fecha_str}"
        if cliente:
            sub = f"Para: <b>{cliente}</b> &nbsp;·&nbsp; {fecha_str}"
        story.append(Paragraph(sub, self.styles["SubtituloPortada"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARIO))
        story.append(Spacer(1, 0.4 * cm))

        # Resumen narrativo
        # Banner amarillo destacado si los datos están atrasados
        fecha_datos_dt = datos_hoy.get("fecha_datos")
        hoy_dt = _ahora_ar().replace(tzinfo=None)  # naive para comparar fechas
        if fecha_datos_dt:
            dias_atraso = (hoy_dt.date() - fecha_datos_dt.date()).days
        else:
            dias_atraso = 0
        if dias_atraso >= 1:
            meses_es = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo",
                        6: "junio", 7: "julio", 8: "agosto", 9: "septiembre",
                        10: "octubre", 11: "noviembre", 12: "diciembre"}
            fecha_str_aviso = f"{fecha_datos_dt.day} de {meses_es[fecha_datos_dt.month]}"
            if dias_atraso == 1:
                msg_atraso = (f"⚠️ <b>Datos del día anterior ({fecha_str_aviso}).</b> "
                              "El Mercado Central aún no publicó los datos de hoy.")
            else:
                msg_atraso = (f"⚠️ <b>Datos atrasados — última publicación: {fecha_str_aviso}</b> "
                              f"(hace {dias_atraso} días). El MCBA puede tardar al cambiar de mes "
                              "o por feriados. Se actualizará automáticamente cuando publiquen.")
            story.append(Paragraph(msg_atraso,
                ParagraphStyle("aviso", fontName="Helvetica", fontSize=10,
                               textColor=colors.HexColor("#5D4037"),
                               leading=13, leftIndent=10, rightIndent=10,
                               borderColor=colors.HexColor("#F9A825"),
                               borderWidth=1, borderPadding=10,
                               backColor=colors.HexColor("#FFF8E1"),
                               spaceAfter=10)))
            story.append(Spacer(1, 0.1 * cm))

        # === Banner de alertas críticas (antes de los precios) ===
        if alertas_7d:
            criticas = []
            for z in alertas_7d:
                for a in z.get("alertas", []):
                    if a.get("severidad") in ("ALTA", "MEDIA"):
                        criticas.append({
                            "zona": z["zona"],
                            "provincia": z["provincia"],
                            **a
                        })
            if criticas:
                # Ordenar por severidad y fecha
                sev_order = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
                criticas.sort(key=lambda x: (sev_order.get(x["severidad"], 9),
                                              x.get("fecha", "")))
                # Mostrar hasta 5 alertas top
                top = criticas[:5]
                meses_cortos = {1: "ene", 2: "feb", 3: "mar", 4: "abr",
                                 5: "may", 6: "jun", 7: "jul", 8: "ago",
                                 9: "sep", 10: "oct", 11: "nov", 12: "dic"}
                lineas = []
                for a in top:
                    try:
                        f = datetime.strptime(a["fecha"], "%Y-%m-%d")
                        f_str = f"{f.day:02d}/{meses_cortos[f.month]}"
                    except Exception:
                        f_str = a["fecha"]
                    lineas.append(
                        f"<b>{f_str} · {a['zona']}</b> — {a['icono']} "
                        f"{a['tipo']} ({a.get('valor', '')})"
                    )
                extra = ("" if len(criticas) <= 5
                         else f" &nbsp; <i>(+{len(criticas)-5} más al final)</i>")
                bloque_txt = (
                    "<b>⚠️ Alertas destacadas de la semana</b>"
                    f"{extra}<br/>"
                    + "<br/>".join(f"• {l}" for l in lineas)
                )
                story.append(Paragraph(bloque_txt,
                    ParagraphStyle("banner_alerta", fontName="Helvetica",
                                    fontSize=9,
                                    textColor=colors.HexColor("#5D4037"),
                                    leading=13, leftIndent=10, rightIndent=10,
                                    borderColor=colors.HexColor("#C62828"),
                                    borderWidth=1.2, borderPadding=8,
                                    backColor=colors.HexColor("#FFEBEE"),
                                    spaceAfter=10)))

        story.append(Paragraph(self._texto_resumen(datos_hoy, variaciones),
                               self.styles["ParrafoNarrativo"]))
        story.append(Spacer(1, 0.15 * cm))

        # =========== TABLAS POR PRODUCTO ===========
        productos = datos_hoy.get("productos", {})
        hay_fallback = any(it.get("es_fallback") for items in productos.values()
                           for it in items)

        # Ordenar por nombre de especie
        for esp in sorted(productos.keys()):
            items = productos[esp]
            if not items:
                continue
            n = len(items)
            bloque = [
                Paragraph(f"🥬 {esp.capitalize()} <font size='8' color='#888'>"
                          f"({n})</font>",
                          self.styles["EspecieTitulo"]),
                self._tabla_producto(items, variaciones),
                Spacer(1, 0.08 * cm),
            ]
            story.append(KeepTogether(bloque))

        # Nota sobre fallback Bs As
        if hay_fallback:
            story.append(Spacer(1, 0.1 * cm))
            story.append(Paragraph(
                "<b>*</b> Procedencia Buenos Aires — referencia mostrada cuando no hubo "
                "cotización de Salta o Jujuy para esa variedad en el día.",
                self.styles["Disclaimer"]
            ))

        # =========== CLIMA — PRÓXIMOS 7 DÍAS (por zona) ===========
        # (título en tamaño grande, mismo que "Precios Mayoristas")
        if pronostico_diario:
            story.append(PageBreak())
            story.append(Paragraph("Pronóstico Climático",
                                   self.styles["TituloPortada"]))
            story.append(Paragraph(
                f"Próximos 7 días por zona &nbsp;·&nbsp; {fecha_str}",
                self.styles["SubtituloPortada"]))
            story.append(HRFlowable(width="100%", thickness=1.5,
                                     color=COLOR_PRIMARIO))
            story.append(Spacer(1, 0.3 * cm))

            def _metricas_zona(z):
                dias = z.get("dias", [])
                tmax_max = max((d.get("tmax", 0) for d in dias), default=0)
                tmin_min = min((d.get("tmin", 0) for d in dias), default=0)
                lluvia_tot = sum(d.get("lluvia", 0) for d in dias)
                # Conteos de eventos críticos por tipo
                n_helada = sum(1 for d in dias if "Helada" in d.get("comentario", ""))
                n_viento = sum(1 for d in dias if "Viento fuerte" in d.get("comentario", ""))
                n_calor = sum(1 for d in dias if "Calor extremo" in d.get("comentario", ""))
                n_lluvia_int = sum(1 for d in dias if "Lluvia intensa" in d.get("comentario", ""))
                crit = (n_helada + n_viento + n_calor + n_lluvia_int) > 0
                emoji = "⚠️" if crit else "☀️"
                return (tmax_max, tmin_min, lluvia_tot, emoji,
                        n_helada, n_viento, n_calor, n_lluvia_int)

            for z in pronostico_diario:
                if not z.get("dias"):
                    continue
                (tmax_max, tmin_min, lluvia_tot, emoji,
                 n_helada, n_viento, n_calor, n_lluvia_int) = _metricas_zona(z)

                # ==== Badges destacados de eventos críticos (helada/viento) ====
                badges = []
                if n_helada:
                    badges.append(
                        f"<font color='#0277BD'><b>❄️ {n_helada} "
                        f"{'helada' if n_helada == 1 else 'heladas'}</b></font>")
                if n_viento:
                    badges.append(
                        f"<font color='#EF6C00'><b>💨 {n_viento} "
                        f"día{'s' if n_viento != 1 else ''} viento fuerte</b></font>")
                if n_calor:
                    badges.append(
                        f"<font color='#C62828'><b>🌡️ {n_calor} "
                        f"día{'s' if n_calor != 1 else ''} calor extremo</b></font>")
                if n_lluvia_int:
                    badges.append(
                        f"<font color='#1565C0'><b>🌧️ {n_lluvia_int} "
                        f"día{'s' if n_lluvia_int != 1 else ''} lluvia intensa</b></font>")
                badges_str = "  ·  ".join(badges) if badges else ""

                # ==== Encabezado: nombre + provincia + badges ====
                encabezado_html = (
                    f"<font size='14' color='#1B5E20'><b>{emoji} {z['zona']}</b></font>"
                    f"  <font size='9' color='#666'>{z['provincia']}</font>"
                )
                if badges_str:
                    encabezado_html += f"<br/><font size='9'>{badges_str}</font>"
                encabezado = [[
                    Paragraph(
                        encabezado_html,
                        ParagraphStyle("card_head", fontName="Helvetica",
                                        fontSize=11, alignment=TA_LEFT,
                                        leading=15))
                ]]
                head_t = Table(encabezado, colWidths=[18.6 * cm])
                head_t.setStyle(TableStyle([
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#1B5E20")),
                ]))

                # ==== Mini-dashboard: 3 métricas grandes ====
                mini_estilo_val = ParagraphStyle(
                    "mini_val", fontName="Helvetica-Bold", fontSize=17,
                    alignment=TA_CENTER, leading=20,
                    textColor=colors.HexColor("#1B5E20"))
                mini_estilo_lab = ParagraphStyle(
                    "mini_lab", fontName="Helvetica", fontSize=8,
                    alignment=TA_CENTER, leading=11,
                    textColor=colors.HexColor("#666"))

                metricas = [[
                    Paragraph(f"{tmax_max:.0f}°", mini_estilo_val),
                    Paragraph(f"{tmin_min:.0f}°", mini_estilo_val),
                    Paragraph(f"{lluvia_tot:.0f} mm", mini_estilo_val),
                ], [
                    Paragraph("MÁX semana", mini_estilo_lab),
                    Paragraph("MÍN semana", mini_estilo_lab),
                    Paragraph("LLUVIA total", mini_estilo_lab),
                ]]
                mini_t = Table(metricas, colWidths=[6.2 * cm, 6.2 * cm, 6.2 * cm])
                mini_t.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, 0), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
                    ("TOPPADDING", (0, 1), (-1, 1), 0),
                    ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FA")),
                    ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E0E0")),
                    ("LINEBEFORE", (1, 0), (1, -1), 0.4, colors.HexColor("#E0E0E0")),
                    ("LINEBEFORE", (2, 0), (2, -1), 0.4, colors.HexColor("#E0E0E0")),
                ]))

                bloque = [
                    head_t,
                    Spacer(1, 0.15 * cm),
                    mini_t,
                    Spacer(1, 0.15 * cm),
                    self._tabla_pronostico_diario(z["dias"]),
                    Spacer(1, 0.4 * cm),
                ]
                story.append(KeepTogether(bloque))

        # =========== ALERTAS PRÓXIMOS 7 DÍAS (AL FINAL) ===========
        if alertas_7d:
            n_total_alertas = sum(len(z["alertas"]) for z in alertas_7d)
            if n_total_alertas > 0:
                story.append(Spacer(1, 0.3 * cm))
                story.append(Paragraph(
                    f"⚠️ Alertas en los próximos 7 días "
                    f"<font size='8' color='#888'>"
                    f"({n_total_alertas} en {len(alertas_7d)} zona"
                    f"{'s' if len(alertas_7d) != 1 else ''})</font>",
                    self.styles["EspecieTitulo"]))
                story.append(self._tabla_alertas_15d(alertas_7d))

        # =========== DISCLAIMER (compacto) ===========
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f"<b>Fuente:</b> MCBA (mercadocentral.gob.ar) · "
            f"Pronóstico: Open-Meteo · "
            f"Precios mayoristas en pesos por bulto. Variaciones vs último "
            f"día hábil con datos. Información orientativa.",
            self.styles["Disclaimer"]
        ))

        doc.build(story, onFirstPage=self._header_footer,
                  onLaterPages=self._header_footer)
        return output_path
