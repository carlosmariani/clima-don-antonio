"""
generador_pdf.py
Generador de PDF COMPACTO Y NARRATIVO para Don Antonio SRL.

Filosofía del diseño:
  - El TEXTO manda. Las gráficas son apoyos orientativos.
  - Si todas las zonas están bien, el PDF es corto.
  - Solo las zonas con alertas reciben atención detallada.
  - Lectura rápida: que un productor entienda en menos de un minuto.

Estructura:
  1. Portada con resumen ejecutivo narrativo (1 página)
  2. Resumen regional por zona (tabla compacta)
  3. Detalle SOLO de zonas con alertas (1/2 página por zona con alerta)
  4. Tendencia trimestral narrativa con gráfico (1 página)
  5. (Opcional) Análisis trimestral detallado por zona si --extendido
  6. Aclaración breve al final
"""

import os
from datetime import datetime
from typing import Dict, List, Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime as dt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

from interpretacion import (
    calcular_semaforo, pictograma_clima, resumen_interpretativo,
    que_hacer_simple, comparativa_simple, tendencia_trimestral_simple,
)


COLOR_PRIMARIO = colors.HexColor("#1B5E20")
COLOR_SECUNDARIO = colors.HexColor("#F9A825")
COLOR_ACENTO = colors.HexColor("#0D47A1")
COLOR_GRIS = colors.HexColor("#555555")
COLOR_GRIS_CLARO = colors.HexColor("#EEEEEE")
COLOR_FONDO = colors.HexColor("#F5F7FA")


class GeneradorPDF:
    def __init__(self, empresa: Dict, logo_path: str = "logo.png"):
        self.empresa = empresa
        self.logo_path = logo_path
        self.styles = self._build_styles()

    def _build_styles(self):
        s = getSampleStyleSheet()
        s.add(ParagraphStyle(
            name="TituloPortada", fontName="Helvetica-Bold", fontSize=22,
            textColor=COLOR_PRIMARIO, alignment=TA_LEFT, spaceAfter=4, leading=26
        ))
        s.add(ParagraphStyle(
            name="SubtituloPortada", fontName="Helvetica", fontSize=11,
            textColor=COLOR_GRIS, alignment=TA_LEFT, spaceAfter=12, leading=14
        ))
        s.add(ParagraphStyle(
            name="ParrafoNarrativo", fontName="Helvetica", fontSize=11,
            textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=10, leading=16,
            firstLineIndent=12,
        ))
        s.add(ParagraphStyle(
            name="ZonaTitulo", fontName="Helvetica-Bold", fontSize=14,
            textColor=COLOR_PRIMARIO, alignment=TA_LEFT, spaceBefore=10, spaceAfter=4, leading=17
        ))
        s.add(ParagraphStyle(
            name="ZonaSubtit", fontName="Helvetica-Oblique", fontSize=9,
            textColor=COLOR_GRIS, alignment=TA_LEFT, spaceAfter=6, leading=11
        ))
        s.add(ParagraphStyle(
            name="ZonaParrafo", fontName="Helvetica", fontSize=10,
            textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=6, leading=14
        ))
        s.add(ParagraphStyle(
            name="SeccionH", fontName="Helvetica-Bold", fontSize=12,
            textColor=COLOR_PRIMARIO, spaceBefore=10, spaceAfter=6, leading=15,
            borderPadding=4
        ))
        s.add(ParagraphStyle(
            name="AccionLine", fontName="Helvetica", fontSize=10,
            textColor=colors.black, alignment=TA_LEFT, spaceAfter=3, leading=13,
            leftIndent=8
        ))
        s.add(ParagraphStyle(
            name="Disclaimer", fontName="Helvetica-Oblique", fontSize=8,
            textColor=COLOR_GRIS, alignment=TA_JUSTIFY, leading=11
        ))
        s.add(ParagraphStyle(
            name="MiniLabel", fontName="Helvetica-Bold", fontSize=8,
            textColor=colors.white, alignment=TA_CENTER, leading=10
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
        canv.drawRightString(A4[0] - 1.5 * cm, A4[1] - 1.85 * cm, "Informe Climático")
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
                             f"Generado: {datetime.now().strftime('%d/%m/%Y')}")
        canv.restoreState()

    # ------------------------------------------------------------------ #
    # Resumen ejecutivo NARRATIVO (no tabla)
    # ------------------------------------------------------------------ #
    def _texto_resumen_ejecutivo(self, datos: List[Dict]) -> str:
        """Devuelve un párrafo escrito describiendo el panorama regional."""
        rojas = [d for d in datos if d["semaforo"]["nivel"] == "ROJO"]
        amarillas = [d for d in datos if d["semaforo"]["nivel"] == "AMARILLO"]
        verdes = [d for d in datos if d["semaforo"]["nivel"] == "VERDE"]

        partes = []

        # Apertura: panorama general
        if not rojas and not amarillas:
            partes.append(
                "Las próximas dos semanas se presentan tranquilas en toda la región. "
                f"Las {len(datos)} localidades monitoreadas no muestran eventos extremos previstos, "
                "lo que permite planificar las tareas a campo con normalidad."
            )
        elif rojas:
            nombres_rojas = ", ".join(f"<b>{d['localidad']['nombre']}</b>" for d in rojas)
            partes.append(
                f"Atención: en {nombres_rojas} se prevén eventos extremos durante los próximos 15 días "
                "que requieren tomar precauciones específicas. "
                "El detalle por zona se presenta más abajo."
            )
            if amarillas:
                nombres_am = ", ".join(d['localidad']['nombre'] for d in amarillas)
                partes.append(
                    f"Adicionalmente, {len(amarillas)} localidad{'es' if len(amarillas) != 1 else ''} "
                    f"({nombres_am}) presenta{'n' if len(amarillas) != 1 else ''} alertas menores que conviene revisar."
                )
        else:
            nombres_am = ", ".join(f"<b>{d['localidad']['nombre']}</b>" for d in amarillas)
            partes.append(
                f"En {nombres_am} se han detectado alertas a tener en cuenta durante los próximos 15 días. "
                "El resto de las localidades muestran condiciones normales para esta época del año."
            )

        # Caracterización climática general (lluvia/temp regional)
        from statistics import mean
        tmaxes = [d['resumen_15_dias']['temp_max_promedio'] for d in datos]
        tmins = [d['resumen_15_dias']['temp_min_promedio'] for d in datos]
        lluvias = [d['resumen_15_dias']['lluvia_total_mm'] for d in datos]
        tmax_prom = mean(tmaxes)
        tmin_prom = mean(tmins)
        lluvia_prom = mean(lluvias)

        # Caracterización
        if tmax_prom >= 30:
            tono_temp = "calurosas"
        elif tmax_prom >= 24:
            tono_temp = "templado-cálidas"
        elif tmax_prom >= 18:
            tono_temp = "templadas"
        elif tmax_prom >= 12:
            tono_temp = "frescas"
        else:
            tono_temp = "frías"

        if lluvia_prom < 10:
            tono_lluvia = "con escasas lluvias"
        elif lluvia_prom < 30:
            tono_lluvia = "con lluvias moderadas"
        elif lluvia_prom < 80:
            tono_lluvia = "con lluvias frecuentes"
        else:
            tono_lluvia = "con lluvias importantes"

        partes.append(
            f"En promedio, las temperaturas previstas son {tono_temp} "
            f"(máximas cercanas a {tmax_prom:.0f}°C y mínimas a {tmin_prom:.0f}°C), "
            f"{tono_lluvia} (alrededor de {lluvia_prom:.0f} mm acumulados por zona en los 15 días). "
        )

        return "<br/><br/>".join(partes)

    # ------------------------------------------------------------------ #
    # Tabla compacta de zonas (vista rápida regional)
    # ------------------------------------------------------------------ #
    def _tabla_compacta_zonas(self, datos: List[Dict]) -> Table:
        rows = [[
            Paragraph("<b>ZONA</b>", self._th()),
            Paragraph("<b>EST.</b>", self._th()),
            Paragraph("<b>T.MÁX</b>", self._th()),
            Paragraph("<b>T.MÍN</b>", self._th()),
            Paragraph("<b>LLUVIA</b>", self._th()),
            Paragraph("<b>EN POCAS PALABRAS</b>", self._th()),
        ]]
        for d in datos:
            sem = d["semaforo"]
            r = d["resumen_15_dias"]
            rows.append([
                Paragraph(f"<b>{d['localidad']['nombre']}</b><br/>"
                          f"<font size='7' color='#888'>{d['localidad']['provincia']}</font>",
                          self._td()),
                Paragraph(sem["emoji"], ParagraphStyle("c", alignment=TA_CENTER, fontSize=14)),
                Paragraph(f"{r['temp_max_promedio']:.0f}°", self._td_center()),
                Paragraph(f"{r['temp_min_promedio']:.0f}°", self._td_center()),
                Paragraph(f"{r['lluvia_total_mm']:.0f}mm", self._td_center()),
                Paragraph(self._frase_corta_zona(d), self._td_small()),
            ])
        t = Table(rows, colWidths=[3 * cm, 1 * cm, 1.4 * cm, 1.4 * cm, 1.6 * cm, 9.6 * cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (4, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO]),
            ("GRID", (0, 0), (-1, -1), 0.3, COLOR_GRIS_CLARO),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    def _frase_corta_zona(self, d: Dict) -> str:
        r = d["resumen_15_dias"]
        alertas = d["alertas"]
        if any(a["tipo"] == "Riesgo de helada" for a in alertas):
            return f"❄️ Riesgo de helada — preparar protección"
        if any(a["tipo"] == "Calor extremo" for a in alertas):
            return f"🌡️ Calor extremo — reforzar riego y sombreo"
        if any(a["tipo"] == "Lluvia intensa" for a in alertas):
            return f"🌧️ Lluvia fuerte — revisar drenajes"
        if any(a["tipo"] == "Período seco prolongado" for a in alertas):
            return f"☀️ Período seco — asegurar riego"
        if any(a["tipo"] == "Viento fuerte" for a in alertas):
            return f"💨 Viento fuerte — suspender pulverizaciones"
        if r['lluvia_total_mm'] > 60:
            return f"Lluvioso ({r['lluvia_total_mm']:.0f} mm previstos)"
        if r['temp_min_absoluta'] <= 7:
            return f"Días frescos (mín. {r['temp_min_absoluta']:.0f}°C)"
        return f"Sin novedades"

    # ------------------------------------------------------------------ #
    # Bloque narrativo de una zona con alerta (compacto)
    # ------------------------------------------------------------------ #
    def _bloque_zona_alerta(self, d: Dict, graficos_temp: List) -> List:
        """Bloque compacto con narrativa, gráfico chico orientativo y acciones."""
        elementos = []
        loc = d["localidad"]
        resumen = d["resumen_15_dias"]
        sem = d["semaforo"]
        alertas = d["alertas"]
        comp = d["comparativa"]

        # Título de zona con barra de color del semáforo
        color_sem = colors.HexColor(sem["color_hex"])
        titulo_data = [[
            Paragraph(f'<font size="14" color="white">{sem["emoji"]}</font>',
                      ParagraphStyle("a", alignment=TA_CENTER, fontSize=14)),
            Paragraph(f'<font size="13" color="white"><b>{loc["nombre"]}</b> '
                      f'<font size="9">— {loc["provincia"]}</font></font>',
                      ParagraphStyle("b", alignment=TA_LEFT, fontSize=13, leading=15)),
            Paragraph(f'<font size="9" color="white">{sem["titulo"]}</font>',
                      ParagraphStyle("c", alignment=TA_RIGHT, fontSize=9)),
        ]]
        t = Table(titulo_data, colWidths=[1 * cm, 11 * cm, 6 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), color_sem),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elementos.append(t)
        elementos.append(Spacer(1, 0.15 * cm))

        # Texto narrativo: 1 párrafo describiendo lo que va a pasar
        narrativa = resumen_interpretativo(resumen, comp)
        # Agregar info de alertas en la narrativa
        if alertas:
            tipos_alertas = list(set(a["tipo"] for a in alertas))
            n_dias_alerta = len(set(a["fecha"] for a in alertas if a["fecha"] != "período"))
            narrativa += (f" <b>Atención particular</b> a "
                          f"{', '.join(tipos_alertas).lower()}")
            if n_dias_alerta > 0:
                narrativa += f" en {n_dias_alerta} día{'s' if n_dias_alerta != 1 else ''} del período."
            else:
                narrativa += "."
        elementos.append(Paragraph(narrativa, self.styles["ZonaParrafo"]))
        elementos.append(Spacer(1, 0.1 * cm))

        # Gráfico chico orientativo (más bajo y compacto)
        try:
            graf = self._grafico_compacto(resumen, loc["nombre"])
            graficos_temp.append(graf)
            # Tabla con gráfico izquierda + acciones derecha
            acciones = que_hacer_simple(resumen, alertas)[:3]  # solo 3 acciones máx
            acciones_html = "<br/>".join(
                f'<font size="8" color="#666"><b>{a["icono"]} {a["tema"]}</b></font> '
                f'<font size="8">{a["accion"]}</font>'
                for a in acciones
            )
            izq_der = [[
                Image(graf, width=10 * cm, height=4 * cm),
                Paragraph(
                    f'<font color="{COLOR_PRIMARIO.hexval()}"><b>¿Qué hacer?</b></font><br/>{acciones_html}',
                    ParagraphStyle("acc", fontName="Helvetica", fontSize=9, leading=12,
                                   leftIndent=4, alignment=TA_LEFT)
                )
            ]]
            t2 = Table(izq_der, colWidths=[10.2 * cm, 7.8 * cm])
            t2.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            elementos.append(t2)
        except Exception:
            pass

        elementos.append(Spacer(1, 0.3 * cm))
        return elementos

    # ------------------------------------------------------------------ #
    # Gráfico compacto (orientativo, no exhaustivo)
    # ------------------------------------------------------------------ #
    def _grafico_compacto(self, resumen: Dict, localidad: str) -> str:
        d = resumen["diario"]
        fechas = [dt.strptime(f, "%Y-%m-%d") for f in d["fecha"]]
        fig, ax1 = plt.subplots(figsize=(6, 2.4))

        ax1.plot(fechas, d["tmax"], color="#C62828", marker="o", markersize=3,
                 linewidth=1.5, label="Tmáx")
        ax1.plot(fechas, d["tmin"], color="#1565C0", marker="o", markersize=3,
                 linewidth=1.5, label="Tmín")
        ax1.fill_between(fechas, d["tmin"], d["tmax"], alpha=0.08, color="gray")
        ax1.set_ylabel("°C", fontsize=8, color="#444")
        ax1.tick_params(axis='y', labelsize=7)
        ax1.tick_params(axis='x', labelsize=7)
        ax1.grid(True, linestyle=":", alpha=0.3)

        ax2 = ax1.twinx()
        ax2.bar(fechas, d["lluvia"], width=0.6, alpha=0.5, color="#0277BD", label="Lluvia")
        ax2.set_ylabel("mm", fontsize=8, color="#444")
        ax2.tick_params(axis='y', labelsize=7)

        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=3))

        l1, lb1 = ax1.get_legend_handles_labels()
        l2, lb2 = ax2.get_legend_handles_labels()
        ax1.legend(l1 + l2, lb1 + lb2, loc="upper left", fontsize=7, ncol=3, framealpha=0.95)

        for s in ['top']:
            ax1.spines[s].set_visible(False)
            ax2.spines[s].set_visible(False)

        plt.tight_layout()
        path = f"_g_{localidad.replace(' ', '_')}.png"
        plt.savefig(path, format="png", dpi=130, bbox_inches="tight")
        plt.close()
        return path

    def _grafico_trimestral(self, meses: List[Dict], localidad: str = "regional") -> str:
        if not meses:
            return None
        fig, ax1 = plt.subplots(figsize=(7, 2.7))
        nombres = [m["mes"].split()[0].capitalize() for m in meses]
        tmax = [m.get("tmax_prom") or 0 for m in meses]
        tmin = [m.get("tmin_prom") or 0 for m in meses]
        lluvia = [m.get("lluvia_prom") or 0 for m in meses]
        x = list(range(len(nombres)))
        ax1.plot(x, tmax, color="#C62828", marker="o", markersize=8,
                 linewidth=2.2, label="Tmáx")
        ax1.plot(x, tmin, color="#1565C0", marker="o", markersize=8,
                 linewidth=2.2, label="Tmín")
        ax1.fill_between(x, tmin, tmax, alpha=0.1, color="gray")
        ax1.set_xticks(x)
        ax1.set_xticklabels(nombres, fontsize=10)
        ax1.set_ylabel("Temperatura (°C)", fontsize=9, color="#444")
        ax1.tick_params(axis='y', labelsize=8)
        ax1.grid(True, linestyle=":", alpha=0.4)
        ax2 = ax1.twinx()
        ax2.bar(x, lluvia, width=0.4, alpha=0.55, color="#0277BD", label="Lluvia mes")
        ax2.set_ylabel("Lluvia (mm)", fontsize=9, color="#444")
        ax2.tick_params(axis='y', labelsize=8)
        l1, lb1 = ax1.get_legend_handles_labels()
        l2, lb2 = ax2.get_legend_handles_labels()
        ax1.legend(l1 + l2, lb1 + lb2, loc="upper left", fontsize=8, ncol=3)
        for s in ['top']:
            ax1.spines[s].set_visible(False)
            ax2.spines[s].set_visible(False)
        plt.tight_layout()
        path = f"_gt_{localidad.replace(' ', '_')}.png"
        plt.savefig(path, format="png", dpi=130, bbox_inches="tight")
        plt.close()
        return path

    # ------------------------------------------------------------------ #
    # Sección trimestral NARRATIVA
    # ------------------------------------------------------------------ #
    def _texto_trimestral(self, trimestre_resumenes: List[Dict],
                          datos_localidades: List[Dict]) -> str:
        """Genera un párrafo narrativo describiendo la perspectiva trimestral."""
        # Tomar el primer trimestral disponible para sacar los meses
        meses_ref = []
        for tr in trimestre_resumenes:
            md = tr.get("meses_detalle", [])
            if md:
                meses_ref = md
                break

        if not meses_ref:
            return ("La perspectiva trimestral no está disponible en este momento. "
                    "Recomendamos consultar el dashboard semanalmente para ajustar la planificación.")

        nombres_meses = [m["mes"].split()[0] for m in meses_ref]
        meses_str = ", ".join(nombres_meses[:-1]) + f" y {nombres_meses[-1]}" if len(nombres_meses) > 1 else nombres_meses[0]

        # Promediar datos del trimestre por zona
        from statistics import mean
        tmax_trim = []
        tmin_trim = []
        lluvia_total_trim = []
        for tr in trimestre_resumenes:
            md = tr.get("meses_detalle", [])
            if md:
                tmaxes = [m["tmax_prom"] for m in md if m.get("tmax_prom") is not None]
                tmins = [m["tmin_prom"] for m in md if m.get("tmin_prom") is not None]
                lluvias = [m.get("lluvia_prom", 0) for m in md]
                if tmaxes: tmax_trim.append(mean(tmaxes))
                if tmins: tmin_trim.append(mean(tmins))
                lluvia_total_trim.append(sum(lluvias))

        if not tmax_trim:
            return ("La perspectiva trimestral no está disponible en este momento.")

        tmax_avg = mean(tmax_trim)
        tmin_avg = mean(tmin_trim)
        lluvia_avg = mean(lluvia_total_trim)

        # Caracterización
        if lluvia_avg < 80:
            caracter_lluvia = "se proyecta como un trimestre seco"
            consejo_lluvia = "Conviene revisar reservas de agua, bombas y cañerías de riego."
        elif lluvia_avg > 250:
            caracter_lluvia = "se anticipa un trimestre lluvioso"
            consejo_lluvia = "Reforzar drenajes y planificar manejo sanitario preventivo."
        else:
            caracter_lluvia = "presenta lluvias dentro de lo normal para la temporada"
            consejo_lluvia = "Buen escenario para la planificación habitual."

        if tmax_avg >= 30:
            caracter_temp = "con días cálidos"
        elif tmax_avg >= 22:
            caracter_temp = "con temperaturas templadas"
        else:
            caracter_temp = "con temperaturas frescas"

        if tmin_avg <= 5:
            consejo_temp = "Tener listo el sistema antiheladas: las mínimas previstas pueden afectar cultivos sensibles."
        elif tmin_avg <= 10:
            consejo_temp = "Las noches frescas pueden retrasar el crecimiento — considerar coberturas en cultivos termorresistentes."
        else:
            consejo_temp = ""

        partes = [
            f"Para los próximos meses (<b>{meses_str}</b>) {caracter_lluvia} en la región, "
            f"{caracter_temp} (máximas promedio cercanas a {tmax_avg:.0f}°C y mínimas a {tmin_avg:.0f}°C, "
            f"con un acumulado regional estimado de {lluvia_avg:.0f} mm en el trimestre)."
        ]
        partes.append(f"<b>Recomendación general:</b> {consejo_lluvia}")
        if consejo_temp:
            partes.append(consejo_temp)
        partes.append(
            "Recordá que esta es una <i>tendencia</i> orientativa: la precisión disminuye con el horizonte. "
            "El dashboard se actualiza con datos frescos cada vez que lo abrís."
        )

        return " ".join(partes)

    # ------------------------------------------------------------------ #
    # Helpers para tablas
    # ------------------------------------------------------------------ #
    def _th(self):
        return ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8,
                              textColor=colors.white, alignment=TA_LEFT)

    def _td(self):
        return ParagraphStyle("td", fontName="Helvetica", fontSize=10,
                              textColor=colors.black, leading=12)

    def _td_center(self):
        return ParagraphStyle("td", fontName="Helvetica", fontSize=10,
                              textColor=colors.black, leading=12, alignment=TA_CENTER)

    def _td_small(self):
        return ParagraphStyle("td2", fontName="Helvetica", fontSize=9,
                              textColor=colors.HexColor("#333333"), leading=12)

    # ------------------------------------------------------------------ #
    # Sección extendida: detalle trimestral por zona (modo --extendido)
    # ------------------------------------------------------------------ #
    def _seccion_trimestral_zona(self, loc: Dict, meses: List[Dict],
                                 graficos_temp: List) -> List:
        elementos = []
        if not meses:
            return elementos

        elementos.append(Paragraph(f"📍 {loc['nombre']} — {loc['provincia']}",
                                   self.styles["ZonaTitulo"]))

        # Caracterizar el trimestre en una frase
        from statistics import mean
        tmax_arr = [m["tmax_prom"] for m in meses if m.get("tmax_prom") is not None]
        tmin_arr = [m["tmin_prom"] for m in meses if m.get("tmin_prom") is not None]
        lluvia_total = sum(m.get("lluvia_prom", 0) for m in meses)
        tmax_avg = mean(tmax_arr) if tmax_arr else 0
        tmin_avg = mean(tmin_arr) if tmin_arr else 0

        if lluvia_total < 80:
            descr_lluvia = "trimestre seco previsto"
        elif lluvia_total > 250:
            descr_lluvia = "trimestre lluvioso previsto"
        else:
            descr_lluvia = "trimestre con lluvias normales"

        meses_str = ", ".join(m["mes"].split()[0] for m in meses)

        elementos.append(Paragraph(
            f"<b>{descr_lluvia.capitalize()}</b> ({meses_str}). "
            f"Temperaturas promedio entre {tmin_avg:.0f}°C y {tmax_avg:.0f}°C, "
            f"con un acumulado total estimado de {lluvia_total:.0f} mm de lluvia.",
            self.styles["ZonaParrafo"]
        ))

        # Gráfico mensual + tabla compacta lado a lado
        graf = self._grafico_trimestral(meses, loc["nombre"])
        if graf:
            graficos_temp.append(graf)
            # Tabla compacta de los 3 meses
            rows = [["Mes", "Tmáx", "Tmín", "Lluvia"]]
            for m in meses:
                rows.append([
                    m["mes"].split()[0].capitalize(),
                    f"{m.get('tmax_prom', 0):.0f}°",
                    f"{m.get('tmin_prom', 0):.0f}°",
                    f"{m.get('lluvia_prom', 0):.0f} mm"
                ])
            t = Table(rows, colWidths=[2.2 * cm, 1.4 * cm, 1.4 * cm, 1.7 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACENTO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FONDO]),
                ("GRID", (0, 0), (-1, -1), 0.3, COLOR_GRIS_CLARO),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            izq_der = [[Image(graf, width=11 * cm, height=4.2 * cm), t]]
            t_main = Table(izq_der, colWidths=[11.2 * cm, 6.8 * cm])
            t_main.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elementos.append(t_main)

        elementos.append(Spacer(1, 0.4 * cm))
        return elementos

    # ------------------------------------------------------------------ #
    # Construcción del PDF
    # ------------------------------------------------------------------ #
    def generar(self, datos_localidades: List[Dict],
                trimestre_resumenes: List[Dict],
                output_path: str,
                cliente: str = "",
                extendido: bool = False) -> str:
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=1.5 * cm, rightMargin=1.5 * cm,
            topMargin=2.9 * cm, bottomMargin=2.0 * cm,
            title="Informe Climático — Don Antonio SRL",
            author=self.empresa["nombre"],
            subject="Pronóstico climático para el sector hortícola",
        )

        for d in datos_localidades:
            d["semaforo"] = calcular_semaforo(d["resumen_15_dias"], d["alertas"])

        story: List[Any] = []
        graficos_temp = []

        # =========== PORTADA + RESUMEN NARRATIVO + TABLA REGIONAL ===========
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Informe Climático Hortícola", self.styles["TituloPortada"]))

        meses_es = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo",
                    6: "junio", 7: "julio", 8: "agosto", 9: "septiembre",
                    10: "octubre", 11: "noviembre", 12: "diciembre"}
        ahora = datetime.now()
        fecha_str = f"{ahora.day} de {meses_es[ahora.month]} de {ahora.year}"

        sub = f"Pronóstico para los próximos 15 días &nbsp;·&nbsp; {fecha_str}"
        if cliente:
            sub = f"Para: <b>{cliente}</b> &nbsp;·&nbsp; {fecha_str}"
        story.append(Paragraph(sub, self.styles["SubtituloPortada"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARIO))
        story.append(Spacer(1, 0.4 * cm))

        # Texto narrativo (NO tabla, NO bullets)
        texto = self._texto_resumen_ejecutivo(datos_localidades)
        story.append(Paragraph(texto, self.styles["ParrafoNarrativo"]))

        # Tabla compacta regional
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Vista rápida por zona", self.styles["SeccionH"]))
        story.append(self._tabla_compacta_zonas(datos_localidades))

        # =========== DETALLE: SOLO ZONAS CON ALERTAS ===========
        zonas_alerta = [d for d in datos_localidades
                        if d["semaforo"]["nivel"] in ("ROJO", "AMARILLO")]
        if zonas_alerta:
            story.append(PageBreak())
            story.append(Paragraph(
                f"Zonas que requieren atención ({len(zonas_alerta)})",
                self.styles["TituloPortada"]
            ))
            story.append(Paragraph(
                "Detalle de las localidades con alertas o eventos extremos previstos.",
                self.styles["SubtituloPortada"]
            ))
            story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARIO))
            story.append(Spacer(1, 0.3 * cm))

            for d in zonas_alerta:
                bloque = self._bloque_zona_alerta(d, graficos_temp)
                # KeepTogether evita que un bloque se corte mal
                story.append(KeepTogether(bloque))

        # =========== TENDENCIA TRIMESTRAL (NARRATIVA + GRÁFICO) ===========
        story.append(PageBreak())
        story.append(Paragraph("📅 Tendencia para los próximos meses",
                               self.styles["TituloPortada"]))

        meses_ref = []
        for tr in trimestre_resumenes:
            md = tr.get("meses_detalle", [])
            if md:
                meses_ref = md
                break
        if meses_ref:
            nombres = [m["mes"].split()[0] for m in meses_ref]
            sub_tri = "Perspectiva orientativa para " + ", ".join(nombres)
        else:
            sub_tri = "Perspectiva orientativa del próximo trimestre"
        story.append(Paragraph(sub_tri, self.styles["SubtituloPortada"]))
        story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARIO))
        story.append(Spacer(1, 0.3 * cm))

        # Texto narrativo trimestral
        story.append(Paragraph(self._texto_trimestral(trimestre_resumenes, datos_localidades),
                               self.styles["ParrafoNarrativo"]))
        story.append(Spacer(1, 0.2 * cm))

        # Gráfico orientativo del trimestre (promediado regional)
        if meses_ref and len(datos_localidades) > 0:
            from statistics import mean
            # Promediar todos los meses_detalle de todas las zonas
            # Usamos clave cronológica YYYY-MM para ordenar bien (no alfabético)
            por_mes = {}
            for tr in trimestre_resumenes:
                for m in tr.get("meses_detalle", []):
                    anio = m.get("anio") or datetime.now().year
                    mes_num = m.get("mes_num", 0)
                    k_orden = f"{anio:04d}-{mes_num:02d}"
                    if k_orden not in por_mes:
                        por_mes[k_orden] = {
                            "nombre": m.get("mes", ""),
                            "tmax": [], "tmin": [], "lluvia": []
                        }
                    if m.get("tmax_prom"): por_mes[k_orden]["tmax"].append(m["tmax_prom"])
                    if m.get("tmin_prom"): por_mes[k_orden]["tmin"].append(m["tmin_prom"])
                    por_mes[k_orden]["lluvia"].append(m.get("lluvia_prom", 0))

            meses_promedio = []
            for k in sorted(por_mes.keys()):  # cronológico
                pm = por_mes[k]
                meses_promedio.append({
                    "mes": pm["nombre"],
                    "tmax_prom": round(mean(pm["tmax"]), 1) if pm["tmax"] else None,
                    "tmin_prom": round(mean(pm["tmin"]), 1) if pm["tmin"] else None,
                    "lluvia_prom": round(mean(pm["lluvia"]), 1) if pm["lluvia"] else 0,
                })
            graf = self._grafico_trimestral(meses_promedio, "regional")
            if graf:
                graficos_temp.append(graf)
                story.append(Image(graf, width=17 * cm, height=6 * cm))
                story.append(Paragraph(
                    "<i>Gráfico orientativo: tendencia promedio regional. "
                    "El detalle por zona se incluye en el modo extendido del informe.</i>",
                    ParagraphStyle("c", fontSize=8, textColor=COLOR_GRIS, alignment=TA_CENTER)
                ))

        # =========== EXTENDIDO: detalle trimestral por zona ===========
        if extendido:
            story.append(PageBreak())
            story.append(Paragraph("Análisis trimestral por zona",
                                   self.styles["TituloPortada"]))
            story.append(Paragraph(
                "Detalle mensual y recomendaciones de planificación para cada zona.",
                self.styles["SubtituloPortada"]
            ))
            story.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARIO))
            story.append(Spacer(1, 0.3 * cm))

            for tr in trimestre_resumenes:
                bloque = self._seccion_trimestral_zona(
                    tr["localidad"], tr.get("meses_detalle", []), graficos_temp)
                if bloque:
                    story.append(KeepTogether(bloque))

        # =========== DISCLAIMER FINAL ===========
        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_GRIS))
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(
            "<b>Aclaración:</b> el pronóstico del clima es orientativo. "
            "Los próximos 1-3 días son altamente confiables (~85%); los 7-15 días, "
            "moderadamente confiables (~65-70%); el trimestre, una <i>tendencia</i>. "
            f"<b>{self.empresa['nombre']}</b> ofrece este informe como complemento de planificación. "
            "Las decisiones técnicas son responsabilidad del productor. "
            "Fuentes: Open-Meteo (modelos ECMWF, GFS-NOAA, ICON-DWD, JMA), SMN Argentina, INTA.",
            self.styles["Disclaimer"]
        ))

        doc.build(story, onFirstPage=self._header_footer,
                  onLaterPages=self._header_footer)

        for g in graficos_temp:
            try:
                os.remove(g)
            except Exception:
                pass

        return output_path

    @staticmethod
    def _formato_fecha(f: str) -> str:
        try:
            return dt.strptime(f, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return f
