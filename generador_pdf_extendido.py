"""
generador_pdf_extendido.py
Layout del reporte climático extendido quincenal — Don Antonio SRL.
Incluye gráficos (matplotlib) integrados como imágenes.
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, Image,
)
from reportlab.pdfgen import canvas
from reportlab.lib.pdfencrypt import StandardEncryption


COLOR_PRIMARIO = colors.HexColor("#1B5E20")
COLOR_ACENTO = colors.HexColor("#0D47A1")
COLOR_SEC = colors.HexColor("#F9A825")
COLOR_GRIS = colors.HexColor("#546E7A")
COLOR_GRIS_CLARO = colors.HexColor("#E0E0E0")


TZ_AR = timezone(timedelta(hours=-3))


def _ahora_ar() -> datetime:
    return datetime.now(TZ_AR).replace(tzinfo=None)


rcParams["font.family"] = "DejaVu Sans"
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False


class GeneradorPDFExtendido:
    def __init__(self, empresa: Dict, logo_path: str = "logo.png"):
        self.empresa = empresa
        self.logo_path = logo_path
        self.styles = self._build_styles()

    def _build_styles(self):
        s = getSampleStyleSheet()
        s.add(ParagraphStyle(
            name="Titulo1", fontName="Helvetica-Bold", fontSize=20,
            textColor=COLOR_PRIMARIO, alignment=TA_LEFT,
            spaceAfter=4, leading=24
        ))
        s.add(ParagraphStyle(
            name="Sub1", fontName="Helvetica", fontSize=11,
            textColor=COLOR_GRIS, alignment=TA_LEFT, spaceAfter=8, leading=14
        ))
        s.add(ParagraphStyle(
            name="Seccion", fontName="Helvetica-Bold", fontSize=16,
            textColor=COLOR_PRIMARIO, alignment=TA_LEFT,
            spaceBefore=6, spaceAfter=6, leading=20
        ))
        s.add(ParagraphStyle(
            name="ZonaHead", fontName="Helvetica-Bold", fontSize=13,
            textColor=COLOR_PRIMARIO, alignment=TA_LEFT,
            spaceBefore=6, spaceAfter=2, leading=17
        ))
        s.add(ParagraphStyle(
            name="Parr", fontName="Helvetica", fontSize=10,
            textColor=colors.black, alignment=TA_JUSTIFY,
            spaceAfter=6, leading=14
        ))
        s.add(ParagraphStyle(
            name="Small", fontName="Helvetica", fontSize=8.5,
            textColor=colors.HexColor("#555"), alignment=TA_LEFT,
            spaceAfter=4, leading=12
        ))
        s.add(ParagraphStyle(
            name="Disclaimer", fontName="Helvetica-Oblique", fontSize=8,
            textColor=COLOR_GRIS, alignment=TA_JUSTIFY, leading=10
        ))
        s.add(ParagraphStyle(
            name="Cell", fontName="Helvetica", fontSize=8,
            textColor=colors.black, alignment=TA_LEFT, leading=11
        ))
        s.add(ParagraphStyle(
            name="CellCenter", fontName="Helvetica", fontSize=8,
            textColor=colors.black, alignment=TA_CENTER, leading=11
        ))
        s.add(ParagraphStyle(
            name="ThWhite", fontName="Helvetica-Bold", fontSize=8,
            textColor=colors.white, alignment=TA_CENTER, leading=10
        ))
        return s

    def _marca_agua(self, canv: canvas.Canvas):
        """Marca de agua diagonal semi-transparente 'DON ANTONIO SRL'."""
        canv.saveState()
        canv.setFillColor(colors.HexColor("#1B5E20"))
        try:
            canv.setFillAlpha(0.09)
        except Exception:
            pass
        canv.setFont("Helvetica-Bold", 62)
        canv.translate(A4[0] / 2, A4[1] / 2)
        canv.rotate(35)
        canv.drawCentredString(0, 0, "DON ANTONIO SRL")
        canv.setFont("Helvetica", 22)
        canv.drawCentredString(0, -55, "Informe confidencial")
        canv.restoreState()

    def _header_footer(self, canv: canvas.Canvas, doc):
        # Marca de agua primero (queda atrás del contenido)
        self._marca_agua(canv)
        canv.saveState()
        # Header
        canv.setFillColor(COLOR_PRIMARIO)
        canv.rect(0, A4[1] - 1.4 * cm, A4[0], 1.4 * cm, fill=1, stroke=0)
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 12)
        canv.drawString(1.1 * cm, A4[1] - 0.9 * cm, self.empresa["nombre"])
        canv.setFont("Helvetica", 8.5)
        canv.drawString(1.1 * cm, A4[1] - 1.25 * cm,
                         "Reporte Climático Extendido Quincenal")
        canv.setFont("Helvetica", 8)
        fecha_str = _ahora_ar().strftime("%d/%m/%Y")
        canv.drawRightString(A4[0] - 1.1 * cm, A4[1] - 0.9 * cm,
                              f"Emitido: {fecha_str}")
        # Footer
        canv.setFillColor(COLOR_GRIS)
        canv.setFont("Helvetica-Oblique", 7.5)
        canv.drawString(1.1 * cm, 0.6 * cm,
                         "Fuentes: Promedio ensemble ECMWF + GFS-NOAA + ICON-DWD + JMA · NOAA CPC (ONI) · "
                         "Información orientativa, no reemplaza el criterio profesional.")
        canv.drawRightString(A4[0] - 1.1 * cm, 0.6 * cm,
                              f"Página {doc.page}")
        canv.restoreState()

    # ------------------------------------------------------------------ #
    # Gráficos
    # ------------------------------------------------------------------ #
    def _fig_a_image(self, fig, ancho_cm=17):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        img = Image(buf, width=ancho_cm * cm,
                     height=ancho_cm * cm * fig.get_figheight() / fig.get_figwidth())
        return img

    def _grafico_zona(self, r) -> Image:
        """Barras de lluvia + línea de temperaturas para una zona (15 días)."""
        resumen = r.get("resumen", {})
        diario = resumen.get("diario", {})
        fechas = diario.get("fecha", [])[:15]
        tmax = diario.get("tmax", [])[:15]
        tmin = diario.get("tmin", [])[:15]
        lluvia = diario.get("lluvia", [])[:15]

        # Etiquetas cortas de fechas (día/mes)
        etiquetas = []
        for f in fechas:
            try:
                dt = datetime.strptime(f, "%Y-%m-%d")
                etiquetas.append(f"{dt.day:02d}/{dt.month:02d}")
            except Exception:
                etiquetas.append(f)

        fig, ax1 = plt.subplots(figsize=(9, 3.2))
        ax2 = ax1.twinx()

        # Barras de lluvia (eje izquierdo)
        ax1.bar(range(len(fechas)), lluvia, color="#42A5F5",
                width=0.7, alpha=0.85, label="Lluvia (mm)")
        ax1.set_ylabel("Lluvia (mm)", color="#1976D2", fontsize=10)
        ax1.tick_params(axis="y", labelcolor="#1976D2", labelsize=8)
        ax1.set_ylim(0, max(max(lluvia + [10]), 10) * 1.15)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)

        # Líneas de temperatura (eje derecho)
        ax2.plot(range(len(fechas)), tmax, color="#E53935",
                 marker="o", markersize=4, linewidth=1.8, label="T. máx (°C)")
        ax2.plot(range(len(fechas)), tmin, color="#FB8C00",
                 marker="o", markersize=4, linewidth=1.8, label="T. mín (°C)")
        ax2.set_ylabel("Temperatura (°C)", color="#C62828", fontsize=10)
        ax2.tick_params(axis="y", labelcolor="#C62828", labelsize=8)

        ax1.set_xticks(range(len(fechas)))
        ax1.set_xticklabels(etiquetas, rotation=45, fontsize=8, ha="right")

        # Leyenda unificada
        lin1, lab1 = ax1.get_legend_handles_labels()
        lin2, lab2 = ax2.get_legend_handles_labels()
        ax1.legend(lin1 + lin2, lab1 + lab2, loc="upper right",
                   fontsize=8, framealpha=0.85)

        fig.tight_layout()
        return self._fig_a_image(fig, ancho_cm=17)

    def _grafico_enso(self, enso: Dict) -> Image:
        """Gráfico de tendencia ONI (últimos ~2 años)."""
        tend = enso.get("tendencia", [])
        etiquetas = [d["trimestre"] for d in tend]
        anoms = [d["anom"] for d in tend]

        fig, ax = plt.subplots(figsize=(9, 2.6))
        # Colorear por fase
        cols = []
        for a in anoms:
            if a >= 0.5:
                cols.append("#E53935")
            elif a <= -0.5:
                cols.append("#1E88E5")
            else:
                cols.append("#9E9E9E")
        ax.bar(range(len(anoms)), anoms, color=cols, width=0.75, alpha=0.9)
        ax.axhline(0.5, linestyle="--", color="#E53935", alpha=0.5,
                   label="Umbral El Niño (+0.5)")
        ax.axhline(-0.5, linestyle="--", color="#1E88E5", alpha=0.5,
                   label="Umbral La Niña (-0.5)")
        ax.axhline(0, color="black", linewidth=0.5, alpha=0.3)
        ax.set_ylabel("Anomalía ONI (°C)", fontsize=9)
        ax.set_xticks(range(len(anoms)))
        ax.set_xticklabels(etiquetas, rotation=45, fontsize=7.5, ha="right")
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.legend(fontsize=8, loc="upper left")
        fig.tight_layout()
        return self._fig_a_image(fig, ancho_cm=17)

    def _grafico_trimestral(self, zonas: List[Dict]) -> Image:
        """Barras comparando lluvia mensual esperada por zona."""
        nombres = [z["info"]["nombre"] for z in zonas]
        lluvias = []
        for z in zonas:
            t = z.get("trimestral", {}) or {}
            v = t.get("lluvia_promedio_mensual") or t.get("lluvia_total_mm") or 0
            lluvias.append(v)
        fig, ax = plt.subplots(figsize=(9, 3.0))
        ax.bar(nombres, lluvias, color="#42A5F5", alpha=0.9)
        ax.set_ylabel("Lluvia mensual esperada (mm)", fontsize=9)
        ax.tick_params(axis="x", rotation=30, labelsize=7.5)
        for lbl in ax.get_xticklabels():
            lbl.set_ha("right")
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        fig.tight_layout()
        return self._fig_a_image(fig, ancho_cm=17)

    # ------------------------------------------------------------------ #
    # Renderers de bloques
    # ------------------------------------------------------------------ #
    def _bloque_enso(self, enso: Dict) -> list:
        """Sección de contexto climático global (ENSO)."""
        bloque = []
        bloque.append(Paragraph("🌍 Contexto climático global",
                                self.styles["Seccion"]))
        if not enso.get("disponible"):
            bloque.append(Paragraph(enso.get("descripcion", "—"),
                                     self.styles["Parr"]))
            return bloque
        header_data = [[
            Paragraph(
                f"<font size='16' color='white'>{enso['emoji']} "
                f"<b>{enso['titulo']}</b></font>",
                ParagraphStyle("enso_head", fontName="Helvetica",
                                fontSize=13, textColor=colors.white,
                                alignment=TA_LEFT, leftIndent=10, leading=18)),
            Paragraph(
                f"<font size='9' color='white'>Índice ONI: "
                f"<b>{enso['anomalia']:+.2f} °C</b><br/>"
                f"Trimestre: {enso['trimestre']}</font>",
                ParagraphStyle("enso_sub", fontName="Helvetica",
                                fontSize=9, textColor=colors.white,
                                alignment=TA_RIGHT, leading=13,
                                rightIndent=10))
        ]]
        head_t = Table(header_data, colWidths=[10 * cm, 8 * cm])
        head_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1),
             colors.HexColor(enso["color"])),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        bloque.append(head_t)
        bloque.append(Spacer(1, 0.2 * cm))
        bloque.append(Paragraph(enso["descripcion"], self.styles["Parr"]))
        if enso.get("extra"):
            bloque.append(Paragraph(enso["extra"],
                ParagraphStyle("banner", fontName="Helvetica", fontSize=10,
                                textColor=colors.HexColor("#5D4037"),
                                leading=13, leftIndent=10, rightIndent=10,
                                borderColor=colors.HexColor("#C62828"),
                                borderWidth=1, borderPadding=8,
                                backColor=colors.HexColor("#FFEBEE"),
                                spaceAfter=10)))
        # Gráfico ONI
        bloque.append(Spacer(1, 0.15 * cm))
        bloque.append(Paragraph(
            "<b>Tendencia del índice ONI</b> "
            "<font size='8' color='#666'>(últimos ~2 años)</font>",
            self.styles["ZonaHead"]))
        try:
            bloque.append(self._grafico_enso(enso))
        except Exception as e:
            bloque.append(Paragraph(f"<i>(Gráfico no disponible: {e})</i>",
                                    self.styles["Small"]))
        bloque.append(Paragraph(
            "El índice ONI (Oceanic Niño Index) mide la anomalía de la "
            "temperatura del océano Pacífico ecuatorial (Niño 3.4). "
            "Valores por encima de +0.5°C indican <b>El Niño</b>; "
            "por debajo de -0.5°C indican <b>La Niña</b>.",
            self.styles["Small"]))

        # Nota sobre Súper Niño (dado que es un tema de mucha discusión)
        bloque.append(Spacer(1, 0.2 * cm))
        bloque.append(Paragraph(
            "<b>¿Qué es un Súper Niño?</b>",
            self.styles["ZonaHead"]))
        bloque.append(Paragraph(
            "Se llama <b>Súper Niño</b> cuando la anomalía ONI supera los "
            "<b>+2.0 °C</b>. Es un evento poco frecuente pero de alto impacto: "
            "los últimos ocurrieron en 1982-83, 1997-98 y 2015-16. En el NOA "
            "argentino, un Súper Niño suele traer <b>sequías intensas de verano</b>, "
            "olas de calor y adelanto del ciclo de cultivos. La comunidad "
            "científica monitorea de cerca la evolución del ONI para anticipar "
            "estos episodios.",
            self.styles["Parr"]))
        return bloque

    def _bloque_zona(self, r: Dict) -> list:
        """Sección de una zona en el pronóstico extendido 15 días."""
        info = r["info"]
        resumen = r.get("resumen", {})
        semaforo = r.get("semaforo", {})
        picto = r.get("pictograma", {})
        interp = r.get("interpretacion", "")
        acciones = r.get("acciones", [])
        alertas = r.get("alertas", [])
        comp = r.get("comparativa_frase", "")

        bloque = []
        # Título zona con semáforo
        color_sem = semaforo.get("color_hex", "#616161")
        titulo_texto = (f"{picto.get('emoji', '')} <b>{info['nombre']}</b> "
                         f"<font size='9' color='#666'>({info['provincia']})</font>")
        bloque.append(Paragraph(titulo_texto, self.styles["ZonaHead"]))

        # Métricas resumen — 4 cajas
        tmax = resumen.get("temp_max_promedio", 0)
        tmin = resumen.get("temp_min_promedio", 0)
        lluvia = resumen.get("lluvia_total_mm", 0)
        n_alertas = len(alertas)
        cell_val = ParagraphStyle("val", fontName="Helvetica-Bold",
                                    fontSize=15, alignment=TA_CENTER,
                                    leading=18,
                                    textColor=colors.HexColor("#1B5E20"))
        cell_val_alerta = ParagraphStyle("val_a", fontName="Helvetica-Bold",
                                          fontSize=15, alignment=TA_CENTER,
                                          leading=18,
                                          textColor=colors.HexColor(color_sem))
        cell_lab = ParagraphStyle("lab", fontName="Helvetica", fontSize=8,
                                    alignment=TA_CENTER,
                                    textColor=colors.HexColor("#666"),
                                    leading=10)
        metricas = [[
            Paragraph(f"{tmax:.0f}°", cell_val),
            Paragraph(f"{tmin:.0f}°", cell_val),
            Paragraph(f"{lluvia:.0f} mm", cell_val),
            Paragraph(f"{n_alertas}", cell_val_alerta),
        ], [
            Paragraph("T. MÁX prom", cell_lab),
            Paragraph("T. MÍN prom", cell_lab),
            Paragraph("LLUVIA 15d", cell_lab),
            Paragraph("ALERTAS 15d", cell_lab),
        ]]
        mt = Table(metricas, colWidths=[4.5 * cm] * 4)
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FA")),
            ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E0E0")),
            ("LINEBEFORE", (1, 0), (1, -1), 0.3, colors.HexColor("#E0E0E0")),
            ("LINEBEFORE", (2, 0), (2, -1), 0.3, colors.HexColor("#E0E0E0")),
            ("LINEBEFORE", (3, 0), (3, -1), 0.3, colors.HexColor("#E0E0E0")),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
            ("TOPPADDING", (0, 1), (-1, 1), 0),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ]))
        bloque.append(mt)
        bloque.append(Spacer(1, 0.15 * cm))
        # Gráfico 15 días
        try:
            bloque.append(self._grafico_zona(r))
        except Exception as e:
            bloque.append(Paragraph(f"<i>(Gráfico no disponible: {e})</i>",
                                    self.styles["Small"]))
        # Interpretación y comparativa (sin recomendaciones/acciones)
        if interp:
            bloque.append(Spacer(1, 0.1 * cm))
            bloque.append(Paragraph(interp, self.styles["Parr"]))
        if comp:
            bloque.append(Paragraph(f"<i>{comp}</i>", self.styles["Small"]))
        return bloque

    def _bloque_trimestral(self, zonas: List[Dict], tendencia_general: Dict = None) -> list:
        """Sección estacional 3 meses con tabla + gráfico comparativo."""
        bloque = []
        bloque.append(PageBreak())
        bloque.append(Paragraph("📊 Perspectiva estacional — próximos 3 meses",
                                self.styles["Titulo1"]))
        bloque.append(Paragraph(
            "Estimación de temperatura y lluvia para el próximo trimestre "
            "según modelos estacionales (CFSv2/NOAA) y normales históricas.",
            self.styles["Sub1"]))
        bloque.append(HRFlowable(width="100%", thickness=1.5,
                                  color=COLOR_PRIMARIO))
        bloque.append(Spacer(1, 0.2 * cm))

        # Tabla
        rows = [[
            Paragraph("<b>ZONA</b>", self.styles["ThWhite"]),
            Paragraph("<b>T. MÁX<br/>PROM</b>", self.styles["ThWhite"]),
            Paragraph("<b>T. MÍN<br/>PROM</b>", self.styles["ThWhite"]),
            Paragraph("<b>LLUVIA<br/>MENSUAL</b>", self.styles["ThWhite"]),
            Paragraph("<b>NOTAS</b>", self.styles["ThWhite"]),
        ]]
        for z in zonas:
            t = z.get("trimestral", {}) or {}
            tend = z.get("tendencia_trimestral", {}) or {}
            info = z["info"]
            tmax = t.get("temp_max_promedio")
            tmin = t.get("temp_min_promedio")
            lluvia = t.get("lluvia_promedio_mensual") or t.get("lluvia_total_mm") or 0
            desc = tend.get("descripcion") or t.get("nota", "—")
            rows.append([
                Paragraph(f"<b>{info['nombre']}</b><br/>"
                          f"<font size='7' color='#888'>{info['provincia']}</font>",
                          self.styles["Cell"]),
                Paragraph(f"{tmax:.0f}°C" if tmax is not None else "—",
                          self.styles["CellCenter"]),
                Paragraph(f"{tmin:.0f}°C" if tmin is not None else "—",
                          self.styles["CellCenter"]),
                Paragraph(f"{lluvia:.0f} mm",
                          self.styles["CellCenter"]),
                Paragraph(desc, self.styles["Cell"]),
            ])
        t = Table(rows, colWidths=[3.3 * cm, 1.7 * cm, 1.7 * cm,
                                     2.0 * cm, 8.5 * cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACENTO),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS_CLARO),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#FAFBFC")]),
        ]))
        bloque.append(t)

        # Gráfico comparativo
        bloque.append(Spacer(1, 0.3 * cm))
        bloque.append(Paragraph(
            "<b>Lluvia mensual esperada por zona</b>",
            self.styles["ZonaHead"]))
        try:
            bloque.append(self._grafico_trimestral(zonas))
        except Exception as e:
            bloque.append(Paragraph(f"<i>(Gráfico no disponible: {e})</i>",
                                     self.styles["Small"]))
        return bloque

    # ------------------------------------------------------------------ #
    # Método principal
    # ------------------------------------------------------------------ #
    def generar(self, zonas: List[Dict], enso: Dict, output_path: str) -> str:
        enc = StandardEncryption(
            userPassword="",
            ownerPassword="don_antonio_owner_2026",
            canPrint=1, canModify=0, canCopy=0, canAnnotate=0,
            strength=128,
        )
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=1.1 * cm, rightMargin=1.1 * cm,
            topMargin=2.0 * cm, bottomMargin=1.5 * cm,
            title="Reporte Climático Extendido — Don Antonio SRL",
            author=self.empresa["nombre"],
            subject="Reporte climático extendido quincenal",
            creator=self.empresa["nombre"],
            encrypt=enc,
        )
        story: List[Any] = []

        # === Portada ===
        story.append(Paragraph("Reporte Climático Extendido",
                                self.styles["Titulo1"]))
        story.append(Paragraph(
            f"Perspectiva 15 días + estacional 3 meses &nbsp;·&nbsp; "
            f"{_ahora_ar().strftime('%d de %B de %Y').replace('January','enero').replace('February','febrero').replace('March','marzo').replace('April','abril').replace('May','mayo').replace('June','junio').replace('July','julio').replace('August','agosto').replace('September','septiembre').replace('October','octubre').replace('November','noviembre').replace('December','diciembre')}",
            self.styles["Sub1"]))
        story.append(HRFlowable(width="100%", thickness=1.5,
                                  color=COLOR_PRIMARIO))
        story.append(Spacer(1, 0.3 * cm))

        # === Contexto ENSO ===
        for x in self._bloque_enso(enso):
            story.append(x)

        # === Pronóstico extendido por zona ===
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("🌦️ Pronóstico extendido — próximos 15 días",
                                self.styles["Titulo1"]))
        story.append(Paragraph(
            "Detalle día por día por zona con métricas resumidas y "
            "recomendaciones agronómicas específicas.",
            self.styles["Sub1"]))
        story.append(HRFlowable(width="100%", thickness=1.5,
                                  color=COLOR_PRIMARIO))
        story.append(Spacer(1, 0.2 * cm))
        for i, z in enumerate(zonas):
            if i > 0:
                story.append(Spacer(1, 0.35 * cm))
                story.append(HRFlowable(width="100%", thickness=0.3,
                                          color=COLOR_GRIS_CLARO))
                story.append(Spacer(1, 0.1 * cm))
            for x in self._bloque_zona(z):
                story.append(x)

        # === Perspectiva trimestral ===
        for x in self._bloque_trimestral(zonas):
            story.append(x)

        # === Cierre ===
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            "Este reporte se emite quincenalmente (días 1 y 15 de cada mes) "
            "como complemento del reporte diario de precios y clima. "
            "Los datos son orientativos y no reemplazan el criterio "
            "profesional del ingeniero agrónomo.",
            self.styles["Disclaimer"]))

        doc.build(story, onFirstPage=self._header_footer,
                   onLaterPages=self._header_footer)
        return output_path
