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
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

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

from precios_mercado import envase_legible


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
            name="Cell", fontName="Helvetica", fontSize=8,
            textColor=colors.black, alignment=TA_LEFT, leading=10
        ))
        s.add(ParagraphStyle(
            name="CellRight", fontName="Helvetica", fontSize=8,
            textColor=colors.black, alignment=TA_RIGHT, leading=10
        ))
        s.add(ParagraphStyle(
            name="CellCenter", fontName="Helvetica", fontSize=8,
            textColor=colors.black, alignment=TA_CENTER, leading=10
        ))
        s.add(ParagraphStyle(
            name="ThWhite", fontName="Helvetica-Bold", fontSize=7,
            textColor=colors.white, alignment=TA_CENTER, leading=9
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
                             f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
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
                Paragraph(it["variedad"] or "—", self.styles["Cell"]),
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
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
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
    # Tabla compacta de clima del día siguiente para todas las zonas
    # ------------------------------------------------------------------ #
    def _tabla_clima_manana(self, clima_manana: List[Dict]) -> Table:
        """
        clima_manana: lista de dicts:
        {
            "zona": "Apolinario Saravia",
            "provincia": "Salta",
            "tmax": 28, "tmin": 14,
            "lluvia_mm": 0, "prob_lluvia": 5,
            "alerta": None | "❄️ Helada" | "🌧️ Lluvia fuerte" | etc.
        }
        """
        rows = [[
            Paragraph("<b>ZONA</b>", self.styles["ThWhite"]),
            Paragraph("<b>T.MÁX</b>", self.styles["ThWhite"]),
            Paragraph("<b>T.MÍN</b>", self.styles["ThWhite"]),
            Paragraph("<b>LLUVIA</b>", self.styles["ThWhite"]),
            Paragraph("<b>PROB.</b>", self.styles["ThWhite"]),
            Paragraph("<b>ALERTA</b>", self.styles["ThWhite"]),
        ]]
        styles_extra = []
        for i, c in enumerate(clima_manana, start=1):
            alerta = c.get("alerta", "")
            if alerta:
                styles_extra.append(("BACKGROUND", (0, i), (-1, i),
                                     colors.HexColor("#FFF3E0")))
            rows.append([
                Paragraph(f"<b>{c['zona']}</b><br/>"
                          f"<font size='7' color='#888'>{c['provincia']}</font>",
                          self.styles["Cell"]),
                Paragraph(f"{c.get('tmax', '—'):.0f}°"
                          if isinstance(c.get('tmax'), (int, float)) else "—",
                          self.styles["CellCenter"]),
                Paragraph(f"{c.get('tmin', '—'):.0f}°"
                          if isinstance(c.get('tmin'), (int, float)) else "—",
                          self.styles["CellCenter"]),
                Paragraph(f"{c.get('lluvia_mm', 0):.0f} mm",
                          self.styles["CellCenter"]),
                Paragraph(f"{c.get('prob_lluvia', 0):.0f}%",
                          self.styles["CellCenter"]),
                Paragraph(alerta if alerta else
                          '<font color="#888">sin alertas</font>',
                          self.styles["Cell"]),
            ])
        t = Table(rows, colWidths=[
            3.5 * cm, 1.3 * cm, 1.3 * cm, 1.6 * cm, 1.4 * cm, 6.0 * cm
        ], repeatRows=1)
        base_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACENTO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO]),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS_CLARO),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        # Padding compacto
        base_styles_compact = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACENTO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO]),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS_CLARO),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        t.setStyle(TableStyle(base_styles_compact + styles_extra))
        return t

    # ------------------------------------------------------------------ #
    # Construcción del PDF
    # ------------------------------------------------------------------ #
    def generar(self, datos_hoy: Dict, datos_ayer: Dict,
                variaciones: Dict, output_path: str,
                cliente: str = "",
                clima_manana: List[Dict] = None) -> str:
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=1.2 * cm, rightMargin=1.2 * cm,
            topMargin=2.6 * cm, bottomMargin=1.7 * cm,
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
        fecha = datos_hoy.get("fecha_datos") or datetime.now()
        fecha_str = f"{fecha.day} de {meses_es[fecha.month]} de {fecha.year}"
        sub = f"Mercado Central de Buenos Aires &nbsp;·&nbsp; Datos del {fecha_str}"
        if cliente:
            sub = f"Para: <b>{cliente}</b> &nbsp;·&nbsp; {fecha_str}"
        story.append(Paragraph(sub, self.styles["SubtituloPortada"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARIO))
        story.append(Spacer(1, 0.4 * cm))

        # Resumen narrativo
        story.append(Paragraph(self._texto_resumen(datos_hoy, variaciones),
                               self.styles["ParrafoNarrativo"]))
        story.append(Spacer(1, 0.3 * cm))

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
                Paragraph(f"🥬 {esp.capitalize()} <font size='9' color='#888'>"
                          f"({n} cotizacion{'es' if n != 1 else ''})</font>",
                          self.styles["EspecieTitulo"]),
                self._tabla_producto(items, variaciones),
                Spacer(1, 0.15 * cm),
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

        # =========== CLIMA DE MAÑANA ===========
        if clima_manana:
            story.append(Spacer(1, 0.4 * cm))
            story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACENTO))
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph("🌤️ Clima previsto para mañana",
                                   self.styles["EspecieTitulo"]))

            # Calcular fecha de mañana
            manana = datetime.now() + timedelta(days=1)
            meses_es_dict = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo",
                             6: "junio", 7: "julio", 8: "agosto", 9: "septiembre",
                             10: "octubre", 11: "noviembre", 12: "diciembre"}
            fecha_manana = f"{manana.day} de {meses_es_dict[manana.month]} de {manana.year}"
            story.append(Paragraph(
                f"Pronóstico para el {fecha_manana} en las 10 zonas monitoreadas",
                self.styles["SubtituloPortada"]
            ))
            story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARIO))
            story.append(Spacer(1, 0.3 * cm))

            # Si hay alertas críticas, destacarlas arriba
            zonas_con_alerta = [c for c in clima_manana if c.get("alerta")]
            if zonas_con_alerta:
                texto_alertas = "<b>⚠️ Atención: alertas críticas para mañana</b><br/>"
                for c in zonas_con_alerta:
                    texto_alertas += f"• <b>{c['zona']}</b> ({c['provincia']}): {c['alerta']}<br/>"
                story.append(Paragraph(texto_alertas,
                    ParagraphStyle("alerta", fontName="Helvetica", fontSize=11,
                                   textColor=COLOR_ROJO, leading=15,
                                   leftIndent=10, rightIndent=10,
                                   borderColor=COLOR_ROJO, borderWidth=1,
                                   borderPadding=10, backColor=colors.HexColor("#FFEBEE"),
                                   spaceAfter=10)))
                story.append(Spacer(1, 0.2 * cm))
            else:
                story.append(Paragraph(
                    "Sin eventos extremos previstos para mañana en ninguna de las 10 zonas. "
                    "Condiciones generales dentro de lo normal.",
                    self.styles["ParrafoNarrativo"]
                ))
                story.append(Spacer(1, 0.2 * cm))

            # Tabla compacta con todas las zonas
            story.append(self._tabla_clima_manana(clima_manana))

        # =========== DISCLAIMER ===========
        story.append(Spacer(1, 0.3 * cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_GRIS))
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(
            "<b>Aclaración:</b> los precios publicados corresponden al relevamiento "
            "diario del Departamento de Estadísticas y Precios del Mercado Central de "
            "Buenos Aires. Son <b>precios mayoristas en pesos argentinos por bulto</b>, "
            "para los envases indicados. Las variaciones se calculan respecto al último "
            "día hábil con datos disponibles. Los precios pueden variar significativamente "
            "según el día, la calidad y la oferta. Este informe se brinda como herramienta "
            f"orientativa de mercado. <b>{self.empresa['nombre']}</b> no asume "
            "responsabilidad por decisiones comerciales tomadas en base a esta información.",
            self.styles["Disclaimer"]
        ))
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(
            "<b>Fuente:</b> Mercado Central de Buenos Aires — mercadocentral.gob.ar. "
            "Sección Precios Mayoristas, planilla diaria de hortalizas y frutas.",
            self.styles["Disclaimer"]
        ))

        doc.build(story, onFirstPage=self._header_footer,
                  onLaterPages=self._header_footer)
        return output_path
