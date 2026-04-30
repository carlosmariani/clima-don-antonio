"""
analisis.py
Motor de análisis climático y recomendaciones agronómicas para horticultura del NOA.
"""

from datetime import datetime
from typing import Dict, List, Any
from statistics import mean


class AnalizadorClima:
    """Procesa datos crudos y genera resúmenes, alertas y recomendaciones."""

    def __init__(self, umbrales: Dict[str, float]):
        self.umbrales = umbrales

    # -------------------------------------------------------------------- #
    # Resumen estadístico del pronóstico de 15 días
    # -------------------------------------------------------------------- #
    @staticmethod
    def _limpiar(seq, valor_default=0):
        """Reemplaza None por valor_default."""
        return [valor_default if v is None else v for v in (seq or [])]

    def resumen_15_dias(self, pronostico: Dict[str, Any]) -> Dict[str, Any]:
        d = pronostico["daily"]
        # Determinar el último día con datos válidos (todos los principales no-None)
        validos = []
        for i in range(len(d["time"])):
            if (d["temperature_2m_max"][i] is not None
                    and d["temperature_2m_min"][i] is not None
                    and d["precipitation_sum"][i] is not None):
                validos.append(i)
        if not validos:
            raise ValueError("No hay días con datos válidos en el pronóstico.")

        # Recortar todas las series a los índices válidos
        def s(key, default=0):
            arr = d.get(key, [])
            return [(arr[i] if (i < len(arr) and arr[i] is not None) else default)
                    for i in validos]

        time_v = [d["time"][i] for i in validos]
        tmax = s("temperature_2m_max")
        tmin = s("temperature_2m_min")
        tmean = s("temperature_2m_mean")
        precip = s("precipitation_sum")
        prob = s("precipitation_probability_max")
        viento = s("windspeed_10m_max")
        rafagas = s("windgusts_10m_max")
        et0 = s("et0_fao_evapotranspiration")
        uv = s("uv_index_max")
        n = len(time_v)
        # Reemplazar d con versión limpia para uso posterior
        d = {
            "time": time_v,
            "temperature_2m_max": tmax,
            "temperature_2m_min": tmin,
            "temperature_2m_mean": tmean,
            "precipitation_sum": precip,
            "precipitation_probability_max": prob,
            "windspeed_10m_max": viento,
            "windgusts_10m_max": rafagas,
            "et0_fao_evapotranspiration": et0,
            "uv_index_max": uv,
        }

        return {
            "n_dias": n,
            "fecha_inicio": d["time"][0],
            "fecha_fin": d["time"][-1],
            "temp_max_promedio": round(mean(tmax), 1),
            "temp_max_absoluta": round(max(tmax), 1),
            "temp_min_promedio": round(mean(tmin), 1),
            "temp_min_absoluta": round(min(tmin), 1),
            "temp_media": round(mean(tmean), 1),
            "lluvia_total_mm": round(sum(precip), 1),
            "lluvia_dias_con_lluvia": sum(1 for p in precip if p >= 1.0),
            "lluvia_max_dia_mm": round(max(precip), 1),
            "prob_lluvia_promedio": round(mean(prob), 0) if prob else 0,
            "viento_max_kmh": round(max(viento), 1),
            "rafaga_max_kmh": round(max(rafagas), 1),
            "et0_total_mm": round(sum(et0), 1),
            "uv_max": round(max(uv), 1) if uv else 0,
            "diario": {
                "fecha": d["time"],
                "tmax": tmax,
                "tmin": tmin,
                "lluvia": precip,
                "prob_lluvia": prob,
                "viento": viento,
            }
        }

    # -------------------------------------------------------------------- #
    # Resumen del pronóstico trimestral
    # -------------------------------------------------------------------- #
    def resumen_trimestral(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        if datos.get("_fallback"):
            d = datos["daily"]
            tmax = d["temperature_2m_max"]
            tmin = d["temperature_2m_min"]
            precip = d["precipitation_sum"]
            return {
                "tipo": "histórico",
                "nota": "Pronóstico estacional no disponible. Se muestra normal histórica de referencia.",
                "temp_max_promedio": round(mean(tmax), 1),
                "temp_min_promedio": round(mean(tmin), 1),
                "lluvia_promedio_mensual": round(sum(precip) / 3, 1),
            }

        sh = datos.get("six_hourly", {})
        if not sh:
            return {"tipo": "no_disponible"}

        temps = [t for t in sh.get("temperature_2m", []) if t is not None]
        precs = [p for p in sh.get("precipitation", []) if p is not None]
        # Cada paso es de 6 horas; 4 pasos por día
        dias_aprox = len(temps) // 4 if temps else 0

        return {
            "tipo": "estacional",
            "modelo": "CFSv2 - NOAA",
            "dias_cubiertos": dias_aprox,
            "temp_promedio": round(mean(temps), 1) if temps else None,
            "temp_max_periodo": round(max(temps), 1) if temps else None,
            "temp_min_periodo": round(min(temps), 1) if temps else None,
            "lluvia_total_mm": round(sum(precs), 1) if precs else 0,
            "lluvia_promedio_mensual": round(sum(precs) / 3, 1) if precs else 0,
        }

    # -------------------------------------------------------------------- #
    # Descomposición mensual del pronóstico trimestral (para PDF extendido)
    # -------------------------------------------------------------------- #
    def descomponer_trimestral_por_mes(self, datos: Dict[str, Any]) -> List[Dict]:
        """Devuelve lista de 3 meses con tmax/tmin/lluvia promedio para cada uno."""
        from datetime import datetime, timedelta
        meses = []
        if datos.get("_fallback"):
            # Fallback: agrupar histórico por mes
            d = datos["daily"]
            fechas = d["time"]
            tmax_arr = d["temperature_2m_max"]
            tmin_arr = d["temperature_2m_min"]
            precip_arr = d["precipitation_sum"]
            por_mes = {}
            for i, f in enumerate(fechas):
                mes = f[:7]  # YYYY-MM
                if mes not in por_mes:
                    por_mes[mes] = {"tmax": [], "tmin": [], "lluvia": []}
                if tmax_arr[i] is not None:
                    por_mes[mes]["tmax"].append(tmax_arr[i])
                if tmin_arr[i] is not None:
                    por_mes[mes]["tmin"].append(tmin_arr[i])
                if precip_arr[i] is not None:
                    por_mes[mes]["lluvia"].append(precip_arr[i])
            # Tomar últimos 3 meses agrupados (referencia histórica)
            keys = sorted(por_mes.keys())[-12:]
            # Promedio por mes-del-año
            por_mes_anual = {}
            for k in keys:
                m = k[5:7]  # MM
                if m not in por_mes_anual:
                    por_mes_anual[m] = {"tmax": [], "tmin": [], "lluvia_mes": []}
                por_mes_anual[m]["tmax"].extend(por_mes[k]["tmax"])
                por_mes_anual[m]["tmin"].extend(por_mes[k]["tmin"])
                por_mes_anual[m]["lluvia_mes"].append(sum(por_mes[k]["lluvia"]))
            # Construir los 3 meses calendario completos POSTERIORES al período de 15 días
            # (es decir: mes próximo + los dos siguientes, no incluye el mes en curso)
            meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            hoy = datetime.now()
            # Saltar al primer día del mes próximo
            if hoy.month == 12:
                inicio = datetime(hoy.year + 1, 1, 1)
            else:
                inicio = datetime(hoy.year, hoy.month + 1, 1)

            for offset in range(3):
                # Avanzar mes a mes, sumando ~32 días y normalizando al día 1
                m = inicio.month + offset
                anio = inicio.year + (m - 1) // 12
                m_real = ((m - 1) % 12) + 1
                m_str = f"{m_real:02d}"
                if m_str in por_mes_anual:
                    pm = por_mes_anual[m_str]
                    meses.append({
                        "mes": f"{meses_es[m_real - 1]} {anio}",
                        "mes_num": m_real,
                        "anio": anio,
                        "tmax_prom": round(mean(pm["tmax"]), 1) if pm["tmax"] else None,
                        "tmin_prom": round(mean(pm["tmin"]), 1) if pm["tmin"] else None,
                        "lluvia_prom": round(mean(pm["lluvia_mes"]), 1) if pm["lluvia_mes"] else 0,
                        "fuente": "Histórico (5 años)",
                    })
            return meses

        sh = datos.get("six_hourly", {})
        if not sh:
            return []

        # Agrupar pasos de 6h por mes
        times = sh.get("time", [])
        temps = sh.get("temperature_2m", [])
        precs = sh.get("precipitation", [])
        por_mes = {}
        for i, t in enumerate(times):
            mes = t[:7]  # YYYY-MM
            if mes not in por_mes:
                por_mes[mes] = {"temps": [], "precs": [], "fechas": []}
            if i < len(temps) and temps[i] is not None:
                por_mes[mes]["temps"].append(temps[i])
            if i < len(precs) and precs[i] is not None:
                por_mes[mes]["precs"].append(precs[i])
            por_mes[mes]["fechas"].append(t)

        meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        # Filtrar el mes en curso (ya está cubierto por los 15 días)
        # y tomar los 3 meses calendario siguientes
        from datetime import datetime
        hoy = datetime.now()
        mes_actual_str = hoy.strftime("%Y-%m")
        keys_filtradas = [k for k in sorted(por_mes.keys()) if k > mes_actual_str]
        keys_ordenadas = keys_filtradas[:3]
        for k in keys_ordenadas:
            datos_mes = por_mes[k]
            mes_num = int(k[5:7])
            anio = int(k[:4])
            t_arr = datos_mes["temps"]
            p_arr = datos_mes["precs"]
            if not t_arr:
                continue
            # Calcular Tmax y Tmin promedio diario (cada 4 muestras = 1 día)
            tmax_diario = []
            tmin_diario = []
            for j in range(0, len(t_arr) - 3, 4):
                bloque = t_arr[j:j+4]
                tmax_diario.append(max(bloque))
                tmin_diario.append(min(bloque))
            meses.append({
                "mes": f"{meses_es[mes_num - 1]} {anio}",
                "mes_num": mes_num,
                "anio": anio,
                "tmax_prom": round(mean(tmax_diario), 1) if tmax_diario else None,
                "tmin_prom": round(mean(tmin_diario), 1) if tmin_diario else None,
                "lluvia_prom": round(sum(p_arr), 1) if p_arr else 0,
                "fuente": "CFSv2 NOAA",
            })
        return meses

    # -------------------------------------------------------------------- #
    # Detección de alertas / eventos extremos
    # -------------------------------------------------------------------- #
    def detectar_alertas(self, pronostico: Dict[str, Any]) -> List[Dict[str, Any]]:
        d = pronostico["daily"]
        alertas = []

        for i, fecha in enumerate(d["time"]):
            tmin = d["temperature_2m_min"][i]
            tmax = d["temperature_2m_max"][i]
            lluvia = d["precipitation_sum"][i]
            viento_arr = d.get("windgusts_10m_max") or d["windspeed_10m_max"]
            viento = viento_arr[i] if i < len(viento_arr) else None
            # Saltar días con datos faltantes
            if tmin is None or tmax is None or lluvia is None:
                continue
            if viento is None:
                viento = 0

            if tmin <= self.umbrales["helada_temp_min"]:
                severidad = "ALTA" if tmin <= 0 else "MEDIA"
                alertas.append({
                    "tipo": "Riesgo de helada",
                    "severidad": severidad,
                    "fecha": fecha,
                    "valor": f"{tmin}°C de mínima",
                    "detalle": "Temperatura cercana o bajo cero — riesgo de daño por frío en cultivos sensibles."
                })

            if tmax >= self.umbrales["calor_extremo_temp_max"]:
                alertas.append({
                    "tipo": "Calor extremo",
                    "severidad": "ALTA" if tmax >= 40 else "MEDIA",
                    "fecha": fecha,
                    "valor": f"{tmax}°C de máxima",
                    "detalle": "Estrés térmico en cultivos. Aumentar frecuencia de riego."
                })

            if lluvia >= self.umbrales["lluvia_intensa_mm_dia"]:
                alertas.append({
                    "tipo": "Lluvia intensa",
                    "severidad": "ALTA" if lluvia >= 60 else "MEDIA",
                    "fecha": fecha,
                    "valor": f"{lluvia} mm",
                    "detalle": "Riesgo de anegamiento. Revisar drenajes y postergar siembras."
                })

            if viento >= self.umbrales["viento_fuerte_kmh"]:
                alertas.append({
                    "tipo": "Viento fuerte",
                    "severidad": "ALTA" if viento >= 70 else "MEDIA",
                    "fecha": fecha,
                    "valor": f"{viento} km/h en ráfagas",
                    "detalle": "Suspender aplicaciones fitosanitarias y revisar estructuras."
                })

        # Detección de período seco
        precip = [p for p in d["precipitation_sum"] if p is not None]
        max_seq_seca = 0
        seq = 0
        for p in precip:
            if p < 1.0:
                seq += 1
                max_seq_seca = max(max_seq_seca, seq)
            else:
                seq = 0
        if max_seq_seca >= self.umbrales["sequia_dias_sin_lluvia"]:
            alertas.append({
                "tipo": "Período seco prolongado",
                "severidad": "MEDIA",
                "fecha": "período",
                "valor": f"{max_seq_seca} días consecutivos sin lluvia significativa",
                "detalle": "Planificar riego complementario y monitorear humedad de suelo."
            })

        return alertas

    # -------------------------------------------------------------------- #
    # Comparativa con año pasado y normal climática
    # -------------------------------------------------------------------- #
    def comparativa(self, resumen_actual: Dict, datos_anio_pasado: Dict,
                    datos_normal: Dict) -> Dict[str, Any]:
        comp = {}

        if datos_anio_pasado and "daily" in datos_anio_pasado:
            d = datos_anio_pasado["daily"]
            tmax_arr = [v for v in d["temperature_2m_max"] if v is not None]
            tmin_arr = [v for v in d["temperature_2m_min"] if v is not None]
            lluvia_arr = [v for v in d["precipitation_sum"] if v is not None]
            tmax_ap = mean(tmax_arr) if tmax_arr else None
            tmin_ap = mean(tmin_arr) if tmin_arr else None
            lluvia_ap = sum(lluvia_arr) if lluvia_arr else 0
            comp["anio_pasado"] = {
                "temp_max_promedio": round(tmax_ap, 1) if tmax_ap else None,
                "temp_min_promedio": round(tmin_ap, 1) if tmin_ap else None,
                "lluvia_total_mm": round(lluvia_ap, 1),
                "delta_temp_max": round(resumen_actual["temp_max_promedio"] - tmax_ap, 1) if tmax_ap else None,
                "delta_temp_min": round(resumen_actual["temp_min_promedio"] - tmin_ap, 1) if tmin_ap else None,
                "delta_lluvia": round(resumen_actual["lluvia_total_mm"] - lluvia_ap, 1),
            }

        if datos_normal and datos_normal.get("registros"):
            tmax_n = []
            tmin_n = []
            lluvia_n = []
            for r in datos_normal["registros"]:
                if "daily" in r:
                    tmax_n.extend(v for v in r["daily"]["temperature_2m_max"] if v is not None)
                    tmin_n.extend(v for v in r["daily"]["temperature_2m_min"] if v is not None)
                    lluvias_validas = [v for v in r["daily"]["precipitation_sum"] if v is not None]
                    if lluvias_validas:
                        lluvia_n.append(sum(lluvias_validas))
            if tmax_n:
                comp["normal_5_anios"] = {
                    "temp_max_promedio": round(mean(tmax_n), 1),
                    "temp_min_promedio": round(mean(tmin_n), 1),
                    "lluvia_promedio_mm": round(mean(lluvia_n), 1) if lluvia_n else 0,
                    "anios_usados": datos_normal["anios_promediados"],
                }

        return comp

    # -------------------------------------------------------------------- #
    # Generador de recomendaciones agronómicas para horticultura
    # -------------------------------------------------------------------- #
    def recomendaciones(self, resumen: Dict, alertas: List[Dict]) -> List[str]:
        recs = []
        tmax = resumen["temp_max_promedio"]
        tmin = resumen["temp_min_promedio"]
        lluvia = resumen["lluvia_total_mm"]
        et0 = resumen.get("et0_total_mm", 0)
        viento = resumen["viento_max_kmh"]
        prob_lluvia = resumen["prob_lluvia_promedio"]

        # Recomendaciones de riego
        balance = lluvia - et0
        if balance < -30:
            recs.append(
                f"⚠️ Déficit hídrico esperado: la evapotranspiración ({et0} mm) supera ampliamente "
                f"la precipitación ({lluvia} mm). Programar riego complementario regular, "
                f"especialmente en cultivos de tomate, pimiento y hortalizas de hoja."
            )
        elif balance < 0:
            recs.append(
                f"💧 Balance hídrico levemente negativo ({balance:+.0f} mm). Mantener riego "
                f"moderado y monitorear humedad de suelo en cultivos sensibles."
            )
        else:
            recs.append(
                f"💧 Balance hídrico favorable ({balance:+.0f} mm). Posible reducción de "
                f"frecuencia de riego según tipo de cultivo y suelo."
            )

        # Recomendaciones según temperatura
        if tmax >= 35:
            recs.append(
                "🌡️ Temperaturas máximas altas: usar mallas de sombreo en cultivos sensibles "
                "(tomate, pimiento, lechuga). Regar en horas tempranas o tardías para reducir estrés."
            )
        if tmin <= 5:
            recs.append(
                "❄️ Riesgo de frío: en cultivos sensibles (poroto, tomate, pimiento) considerar "
                "cobertura con mantas térmicas, riego nocturno preventivo o calefactores en invernáculo."
            )

        # Recomendaciones según lluvia
        if lluvia > 80:
            recs.append(
                f"🌧️ Lluvias acumuladas elevadas ({lluvia} mm previstos): asegurar drenajes, "
                f"evitar tránsito de maquinaria pesada y postergar trasplantes a campo abierto. "
                f"Aumentar monitoreo de enfermedades fúngicas (tizón, mildiu, botrytis)."
            )
        elif lluvia < 10 and resumen["n_dias"] >= 10:
            recs.append(
                f"☀️ Período seco previsto ({lluvia} mm en {resumen['n_dias']} días): asegurar "
                f"sistema de riego operativo y planificar ciclos según ETo ({et0} mm)."
            )

        # Recomendaciones según viento
        if viento >= 40:
            recs.append(
                f"💨 Vientos máximos previstos de {viento} km/h: planificar aplicaciones de "
                f"agroquímicos en ventanas de baja velocidad de viento (idealmente <15 km/h). "
                f"Revisar tutorado de cultivos altos (tomate, poroto vara)."
            )

        # Recomendaciones según probabilidad de lluvia
        if prob_lluvia >= 60:
            recs.append(
                f"🌦️ Alta probabilidad de lluvia ({prob_lluvia}%): programar aplicaciones "
                f"sistémicas con anticipación (ventana de 4-6 horas previas a la lluvia para "
                f"absorción) y suspender de contacto bajo lluvia inminente."
            )

        # Recomendaciones según alertas
        if any(a["tipo"] == "Riesgo de helada" for a in alertas):
            recs.append(
                "🔴 ALERTA HELADA: implementar medidas preventivas anti-helada (riego por aspersión "
                "nocturno, encendido de calefactores, cobertura con plástico). Cosechar cultivos "
                "maduros antes del evento."
            )
        if any(a["tipo"] == "Lluvia intensa" for a in alertas):
            recs.append(
                "🔴 ALERTA LLUVIA INTENSA: revisar y limpiar canales de drenaje. Si hay cultivos "
                "próximos a cosecha, evaluar adelantar la misma. Reforzar aplicaciones preventivas "
                "antifúngicas."
            )
        if any(a["tipo"] == "Viento fuerte" for a in alertas):
            recs.append(
                "🔴 ALERTA VIENTO: asegurar invernaderos y mediasombras. Reforzar tutorados. "
                "Suspender pulverizaciones por riesgo de deriva."
            )

        # Recomendación general de monitoreo
        recs.append(
            "📋 Recomendación general: realizar recorridas semanales de monitoreo fitosanitario, "
            "ajustar fertilización según etapa fenológica y consultar a su asesor técnico ante "
            "dudas específicas del cultivo."
        )

        return recs


if __name__ == "__main__":
    print("Módulo de análisis cargado correctamente.")
