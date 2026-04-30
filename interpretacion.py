"""
interpretacion.py
Convierte los datos numéricos del clima en frases simples y claras
para productores y clientes — sin jerga técnica.
"""

from typing import Dict, List, Any, Tuple


# ---------------------------------------------------------------------------- #
# SEMÁFORO general: VERDE / AMARILLO / ROJO
# ---------------------------------------------------------------------------- #
def calcular_semaforo(resumen: Dict, alertas: List[Dict]) -> Dict[str, Any]:
    """
    Devuelve el estado general del período en formato semáforo:
        - VERDE: condiciones normales / favorables
        - AMARILLO: requiere atención / alertas medias
        - ROJO: alertas altas — tomar precauciones inmediatas
    """
    altas = sum(1 for a in alertas if a.get("severidad") == "ALTA")
    medias = sum(1 for a in alertas if a.get("severidad") == "MEDIA")

    if altas >= 1:
        nivel = "ROJO"
        emoji = "🔴"
        color_hex = "#C62828"
        titulo = "Atención: eventos extremos previstos"
    elif medias >= 2:
        nivel = "AMARILLO"
        emoji = "🟡"
        color_hex = "#EF6C00"
        titulo = "Algunas alertas a tener en cuenta"
    elif medias == 1:
        nivel = "AMARILLO"
        emoji = "🟡"
        color_hex = "#F9A825"
        titulo = "Una alerta menor a considerar"
    else:
        nivel = "VERDE"
        emoji = "🟢"
        color_hex = "#2E7D32"
        titulo = "Condiciones normales"

    return {
        "nivel": nivel,
        "emoji": emoji,
        "color_hex": color_hex,
        "titulo": titulo,
        "alertas_altas": altas,
        "alertas_medias": medias,
    }


# ---------------------------------------------------------------------------- #
# Pictograma del clima dominante
# ---------------------------------------------------------------------------- #
def pictograma_clima(resumen: Dict) -> Tuple[str, str]:
    """
    Devuelve (emoji, descripción) según las condiciones dominantes del período.
    """
    lluvia = resumen["lluvia_total_mm"]
    dias_lluvia = resumen["lluvia_dias_con_lluvia"]
    n = resumen["n_dias"]
    tmax = resumen["temp_max_promedio"]
    tmin = resumen["temp_min_promedio"]
    prob = resumen["prob_lluvia_promedio"]

    pct_dias_lluvia = (dias_lluvia / n) * 100 if n else 0

    # Período seco
    if lluvia < 5 and pct_dias_lluvia < 15:
        if tmax >= 32:
            return ("☀️", "Soleado y caluroso, sin lluvias previstas")
        elif tmin <= 8:
            return ("🌤️", "Días claros con noches frescas")
        else:
            return ("☀️", "Tiempo estable, soleado, sin lluvias")
    # Lluvioso
    if lluvia >= 50 or pct_dias_lluvia >= 50:
        if dias_lluvia >= 8:
            return ("🌧️", "Período lluvioso con varios días con precipitaciones")
        return ("🌦️", "Período variable con lluvias frecuentes")
    # Mixto
    if pct_dias_lluvia >= 25:
        return ("⛅", "Tiempo variable con algunas lluvias")
    if prob >= 40:
        return ("🌥️", "Tiempo nublado con probabilidad de lluvia")
    if tmax >= 32:
        return ("🌤️", "Mayormente soleado y cálido")
    return ("⛅", "Tiempo estable con cambios moderados")


# ---------------------------------------------------------------------------- #
# Resumen interpretativo en lenguaje natural
# ---------------------------------------------------------------------------- #
def resumen_interpretativo(resumen: Dict, comp: Dict) -> str:
    """
    Genera un párrafo simple que describe lo que va a pasar en lenguaje claro.
    """
    tmax = resumen["temp_max_promedio"]
    tmin = resumen["temp_min_promedio"]
    lluvia = resumen["lluvia_total_mm"]
    dias_lluvia = resumen["lluvia_dias_con_lluvia"]
    n = resumen["n_dias"]

    # Caracterizar temperatura
    if tmax >= 35:
        tono_temp = "muy caluroso"
    elif tmax >= 30:
        tono_temp = "caluroso"
    elif tmax >= 25:
        tono_temp = "templado-cálido"
    elif tmax >= 18:
        tono_temp = "templado"
    elif tmax >= 12:
        tono_temp = "fresco"
    else:
        tono_temp = "frío"

    # Caracterizar lluvia
    if lluvia < 5:
        tono_lluvia = f"prácticamente sin lluvias ({lluvia:.0f} mm en total)"
    elif lluvia < 20:
        tono_lluvia = f"con lluvias escasas ({lluvia:.0f} mm en {dias_lluvia} días)"
    elif lluvia < 50:
        tono_lluvia = f"con lluvias moderadas ({lluvia:.0f} mm en {dias_lluvia} días)"
    else:
        tono_lluvia = f"con lluvias importantes ({lluvia:.0f} mm en {dias_lluvia} días)"

    base = (f"Se esperan {n} días de tiempo {tono_temp}, {tono_lluvia}. "
            f"Las máximas rondarán los {tmax:.0f}°C y las mínimas los {tmin:.0f}°C.")

    # Comparativa simple
    ap = comp.get("anio_pasado", {})
    if ap and ap.get("delta_temp_max") is not None and ap.get("delta_lluvia") is not None:
        dtmax = ap["delta_temp_max"]
        dlluvia = ap["delta_lluvia"]
        partes_comp = []
        if abs(dtmax) >= 1.5:
            if dtmax > 0:
                partes_comp.append(f"más cálido (+{dtmax:.1f}°C)")
            else:
                partes_comp.append(f"más fresco ({dtmax:.1f}°C)")
        if abs(dlluvia) >= 10:
            if dlluvia > 0:
                partes_comp.append(f"más lluvioso (+{dlluvia:.0f} mm)")
            else:
                partes_comp.append(f"más seco ({dlluvia:.0f} mm)")
        if partes_comp:
            base += (" Comparado con el mismo período del año pasado, va a estar "
                     + " y ".join(partes_comp) + ".")
        else:
            base += " Las condiciones se asemejan a las del mismo período del año pasado."

    return base


# ---------------------------------------------------------------------------- #
# "¿Qué hacer esta quincena?" — recomendaciones simples y accionables
# ---------------------------------------------------------------------------- #
def que_hacer_simple(resumen: Dict, alertas: List[Dict]) -> List[str]:
    """
    Lista corta y clara de acciones concretas, en lenguaje plano.
    Reemplaza las recomendaciones técnicas largas.
    """
    tmax = resumen["temp_max_promedio"]
    tmin = resumen["temp_min_promedio"]
    lluvia = resumen["lluvia_total_mm"]
    et0 = resumen.get("et0_total_mm", 0)
    viento = resumen["viento_max_kmh"]
    prob = resumen["prob_lluvia_promedio"]

    acciones = []
    balance = lluvia - et0

    # Riego
    if balance < -30:
        acciones.append({
            "icono": "💧",
            "tema": "RIEGO",
            "accion": "Programar riego frecuente",
            "porque": f"Las plantas pierden más agua ({et0:.0f} mm) de la que va a llover ({lluvia:.0f} mm). Hay que reponer."
        })
    elif balance < 0:
        acciones.append({
            "icono": "💧",
            "tema": "RIEGO",
            "accion": "Mantener riego moderado",
            "porque": "El balance de agua es ajustado. Controlar humedad de suelo."
        })
    else:
        acciones.append({
            "icono": "💧",
            "tema": "RIEGO",
            "accion": "Reducir frecuencia de riego",
            "porque": f"La lluvia esperada ({lluvia:.0f} mm) cubre las necesidades del cultivo."
        })

    # Frío / Helada
    if any(a["tipo"] == "Riesgo de helada" for a in alertas):
        acciones.append({
            "icono": "❄️",
            "tema": "FRÍO",
            "accion": "Preparar protección contra helada",
            "porque": "Hay días con temperaturas críticas. Alistar coberturas, riego nocturno o calefacción."
        })
    elif tmin <= 5:
        acciones.append({
            "icono": "❄️",
            "tema": "FRÍO",
            "accion": "Atención por noches frescas",
            "porque": f"Algunas mínimas cerca de {tmin:.0f}°C. Cuidar cultivos sensibles."
        })

    # Calor
    if any(a["tipo"] == "Calor extremo" for a in alertas):
        acciones.append({
            "icono": "🌡️",
            "tema": "CALOR",
            "accion": "Reforzar riego y proteger del sol",
            "porque": "Días muy calurosos. Regar temprano o tarde y considerar mallas de sombreo."
        })
    elif tmax >= 33:
        acciones.append({
            "icono": "🌡️",
            "tema": "CALOR",
            "accion": "Regar en horas frescas",
            "porque": "Calor importante durante el día. Evitar el riego al mediodía."
        })

    # Lluvia intensa
    if any(a["tipo"] == "Lluvia intensa" for a in alertas):
        acciones.append({
            "icono": "🌧️",
            "tema": "LLUVIA FUERTE",
            "accion": "Revisar drenajes y postergar tareas",
            "porque": "Se esperan días con lluvias muy fuertes. Asegurar desagües y posponer trasplantes."
        })

    # Lluvia generalizada (alta probabilidad)
    if prob >= 50 and lluvia >= 30:
        acciones.append({
            "icono": "🍃",
            "tema": "ENFERMEDADES",
            "accion": "Prevenir enfermedades por humedad",
            "porque": "Días lluviosos favorecen hongos. Considerar tratamientos preventivos."
        })

    # Período seco
    if any(a["tipo"] == "Período seco prolongado" for a in alertas):
        acciones.append({
            "icono": "☀️",
            "tema": "SEQUÍA",
            "accion": "Asegurar el sistema de riego",
            "porque": "Se viene un período largo sin lluvias. Verificar bombas, cañerías y reservas."
        })

    # Viento
    if any(a["tipo"] == "Viento fuerte" for a in alertas):
        acciones.append({
            "icono": "💨",
            "tema": "VIENTO",
            "accion": "Suspender pulverizaciones",
            "porque": f"Vientos previstos de hasta {viento:.0f} km/h. La aplicación se desperdicia y deriva."
        })
    elif viento >= 35:
        acciones.append({
            "icono": "💨",
            "tema": "VIENTO",
            "accion": "Aplicar fitosanitarios temprano",
            "porque": "Vientos moderados durante el día. Aprovechar las primeras horas para pulverizar."
        })

    # Si todo está tranquilo, mensaje positivo
    if not any(a["severidad"] == "ALTA" for a in alertas):
        acciones.append({
            "icono": "✅",
            "tema": "PLANIFICACIÓN",
            "accion": "Buen momento para tareas a campo",
            "porque": "Sin eventos extremos previstos: aprovechar para siembras, fertilizaciones y trabajos generales."
        })

    return acciones[:5]  # máximo 5 para no saturar


# ---------------------------------------------------------------------------- #
# Comparativa simple en una frase
# ---------------------------------------------------------------------------- #
def comparativa_simple(resumen: Dict, comp: Dict) -> str:
    """Devuelve una frase corta tipo: 'Más cálido y más seco que el año pasado.'"""
    ap = comp.get("anio_pasado", {})
    if not ap:
        return "Sin datos del año pasado para comparar."

    dtmax = ap.get("delta_temp_max")
    dlluvia = ap.get("delta_lluvia")
    if dtmax is None or dlluvia is None:
        return "Comparativa con año pasado no disponible."

    partes = []
    if abs(dtmax) >= 1.5:
        partes.append("más cálido" if dtmax > 0 else "más fresco")
    elif abs(dtmax) < 0.5:
        partes.append("temperatura similar")
    else:
        partes.append("temperatura algo " + ("mayor" if dtmax > 0 else "menor"))

    if abs(dlluvia) >= 15:
        partes.append("más lluvioso" if dlluvia > 0 else "más seco")
    elif abs(dlluvia) < 5:
        partes.append("lluvias similares")
    else:
        partes.append("algo " + ("más lluvioso" if dlluvia > 0 else "más seco"))

    return f"Comparado con el año pasado: {', '.join(partes)}."


# ---------------------------------------------------------------------------- #
# Tendencia trimestral en lenguaje simple
# ---------------------------------------------------------------------------- #
def tendencia_trimestral_simple(resumen_t: Dict, resumen_15: Dict = None) -> Dict:
    """
    Genera tendencia general para el trimestre con semáforo y recomendación.
    """
    tipo = resumen_t.get("tipo")

    if tipo == "no_disponible":
        return {
            "disponible": False,
            "mensaje": "Pronóstico estacional no disponible en este momento.",
            "emoji": "❔",
        }

    if tipo == "histórico":
        tmax = resumen_t.get("temp_max_promedio", 0)
        tmin = resumen_t.get("temp_min_promedio", 0)
        lluvia = resumen_t.get("lluvia_promedio_mensual", 0)
        return {
            "disponible": True,
            "tipo": "referencia_historica",
            "emoji": "📊",
            "titulo": "Referencia histórica del trimestre",
            "descripcion": (f"Según los últimos años, en este trimestre se esperan máximas "
                            f"promedio de {tmax:.0f}°C, mínimas de {tmin:.0f}°C, y unas "
                            f"{lluvia:.0f} mm de lluvia por mes."),
            "recomendacion": ("Planificar la campaña según las condiciones típicas de la "
                              "estación. Consultar el dashboard semanalmente para ajustar."),
        }

    # Estacional con datos
    tprom = resumen_t.get("temp_promedio")
    lluvia_total = resumen_t.get("lluvia_total_mm", 0)
    lluvia_mes = resumen_t.get("lluvia_promedio_mensual", 0)

    # Determinar tendencia (comparando con resumen de 15 días si está disponible)
    descripcion = (f"Modelo CFSv2 (NOAA): temperatura promedio del trimestre cercana a "
                   f"{tprom:.0f}°C. Lluvia total estimada: {lluvia_total:.0f} mm "
                   f"({lluvia_mes:.0f} mm por mes en promedio).")

    # Generar recomendación de planificación
    if lluvia_mes < 30:
        recomendacion = ("Trimestre que se espera más bien seco. Planificar disponibilidad "
                         "de agua para riego durante los próximos meses.")
        emoji = "☀️"
    elif lluvia_mes > 100:
        recomendacion = ("Trimestre con lluvias por encima de lo habitual. Reforzar "
                         "drenajes y planificar manejo sanitario preventivo.")
        emoji = "🌧️"
    else:
        recomendacion = ("Trimestre con lluvias normales. Buen escenario para planificar "
                         "siembras y rotaciones según calendario habitual.")
        emoji = "⛅"

    return {
        "disponible": True,
        "tipo": "estacional",
        "emoji": emoji,
        "titulo": "Tendencia para los próximos 90 días",
        "descripcion": descripcion,
        "recomendacion": recomendacion,
    }


if __name__ == "__main__":
    print("Módulo de interpretación cargado correctamente.")
