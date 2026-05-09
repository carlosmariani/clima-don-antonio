"""
generar_precios.py
Script principal para generar el PDF de precios del Mercado Central.

USO:
    python3 generar_precios.py                       # PDF genérico, fecha de hoy
    python3 generar_precios.py --cliente "Juan Pérez"
    python3 generar_precios.py --fecha 2026-04-30    # Datos de un día específico
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from precios_mercado import PreciosMCBA
from generador_pdf_precios import GeneradorPDFPrecios
from clima_api import ClimaAPI
from analisis import AnalizadorClima
from concurrent.futures import ThreadPoolExecutor

# Zona horaria Argentina (UTC-3) — para que en GitHub Actions se use la hora correcta
TZ_AR = timezone(timedelta(hours=-3))


def _ahora_ar() -> datetime:
    """Devuelve la fecha/hora actual en Argentina, como datetime naive."""
    return datetime.now(TZ_AR).replace(tzinfo=None)


def _detectar_alertas_dia(d, idx, ums):
    """Devuelve lista de alertas detectadas para un día específico."""
    alertas = []
    tmin = d["temperature_2m_min"][idx] if idx < len(d["temperature_2m_min"]) else None
    tmax = d["temperature_2m_max"][idx] if idx < len(d["temperature_2m_max"]) else None
    lluvia = d["precipitation_sum"][idx] if idx < len(d["precipitation_sum"]) else None
    v_arr = d.get("windgusts_10m_max") or d["windspeed_10m_max"]
    viento = v_arr[idx] if v_arr and idx < len(v_arr) else None

    if tmin is not None and tmin <= ums["helada_temp_min"]:
        if tmin <= 0:
            alertas.append({
                "tipo": "Helada",
                "icono": "🔴",
                "severidad": "ALTA",
                "valor": f"{tmin:.0f}°C",
                "detalle": f"Mínima {tmin:.0f}°C"
            })
        else:
            alertas.append({
                "tipo": "Riesgo de helada",
                "icono": "❄️",
                "severidad": "MEDIA",
                "valor": f"{tmin:.0f}°C",
                "detalle": f"Mínima {tmin:.0f}°C"
            })
    if tmax is not None and tmax >= ums["calor_extremo_temp_max"]:
        alertas.append({
            "tipo": "Calor extremo",
            "icono": "🌡️",
            "severidad": "ALTA" if tmax >= 40 else "MEDIA",
            "valor": f"{tmax:.0f}°C",
            "detalle": f"Máxima {tmax:.0f}°C"
        })
    if lluvia is not None and lluvia >= ums["lluvia_intensa_mm_dia"]:
        alertas.append({
            "tipo": "Lluvia intensa",
            "icono": "🌧️",
            "severidad": "ALTA" if lluvia >= 60 else "MEDIA",
            "valor": f"{lluvia:.0f} mm",
            "detalle": f"{lluvia:.0f} mm en el día"
        })
    if viento is not None and viento >= ums["viento_fuerte_kmh"]:
        alertas.append({
            "tipo": "Viento fuerte",
            "icono": "💨",
            "severidad": "ALTA" if viento >= 70 else "MEDIA",
            "valor": f"{viento:.0f} km/h",
            "detalle": f"Ráfagas hasta {viento:.0f} km/h"
        })
    return alertas


def obtener_clima_y_alertas(cfg) -> tuple:
    """
    Obtiene:
    - Pronóstico para las próximas 48 hs (mañana + pasado) en cada zona (clima_48h)
    - Alertas detectadas en los próximos 7 días por zona (alertas_7d)
    """
    api = ClimaAPI()
    ums = cfg["umbrales_alertas"]
    HORIZONTE_ALERTAS = 7  # días

    def _zona(loc):
        try:
            pron = api.pronostico_15_dias(loc["lat"], loc["lon"])
            d = pron["daily"]
            n_dias = len(d["time"])

            def _safe(arr, i):
                if arr is None: return None
                return arr[i] if i < len(arr) else None

            # === Mañana (idx 1) y Pasado (idx 2) ===
            idx_man = 1 if n_dias > 1 else 0
            idx_pas = 2 if n_dias > 2 else idx_man

            # Alertas combinadas mañana+pasado para mostrar resumen
            alertas_48h = (_detectar_alertas_dia(d, idx_man, ums)
                           + _detectar_alertas_dia(d, idx_pas, ums))
            alerta_str = None
            if alertas_48h:
                # Quedarnos con alertas únicas por tipo
                vistos = set()
                pieces = []
                for a in alertas_48h:
                    if a["tipo"] in vistos: continue
                    vistos.add(a["tipo"])
                    pieces.append(f"{a['icono']} {a['tipo']} ({a['valor']})")
                alerta_str = " · ".join(pieces)

            clima_48h = {
                "zona": loc["nombre"],
                "provincia": loc["provincia"],
                # Mañana
                "tmax": _safe(d["temperature_2m_max"], idx_man) or 0,
                "tmin": _safe(d["temperature_2m_min"], idx_man) or 0,
                "lluvia_mm": _safe(d["precipitation_sum"], idx_man) or 0,
                "prob_lluvia": (_safe(d.get("precipitation_probability_max"),
                                       idx_man) or 0),
                # Pasado mañana
                "tmax_pasado": _safe(d["temperature_2m_max"], idx_pas) or 0,
                "tmin_pasado": _safe(d["temperature_2m_min"], idx_pas) or 0,
                "lluvia_pasado": _safe(d["precipitation_sum"], idx_pas) or 0,
                "prob_lluvia_pasado": (_safe(
                    d.get("precipitation_probability_max"), idx_pas) or 0),
                "alerta": alerta_str,
            }

            # === Alertas en los próximos 7 días (saltar día 0 = hoy) ===
            alertas_proximos = []
            limite = min(HORIZONTE_ALERTAS + 1, n_dias)  # idx 1..7
            for i in range(1, limite):
                fecha = d["time"][i]
                aa = _detectar_alertas_dia(d, i, ums)
                for a in aa:
                    a_copy = dict(a)
                    a_copy["fecha"] = fecha
                    alertas_proximos.append(a_copy)

            return {
                "clima_48h": clima_48h,
                "alertas_7d": {
                    "zona": loc["nombre"],
                    "provincia": loc["provincia"],
                    "alertas": alertas_proximos,
                }
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as ex:
        resultados = list(ex.map(_zona, cfg["localidades"]))

    resultados = [r for r in resultados if r]
    orden = {l["nombre"]: i for i, l in enumerate(cfg["localidades"])}
    resultados.sort(key=lambda r: orden.get(r["clima_48h"]["zona"], 999))

    clima_48h = [r["clima_48h"] for r in resultados]
    alertas_7d = [r["alertas_7d"] for r in resultados if r["alertas_7d"]["alertas"]]
    return clima_48h, alertas_7d


# Compatibilidad hacia atrás
def obtener_clima_manana(cfg):
    """Compat: solo devuelve el clima de las próximas 48hs."""
    clima, _ = obtener_clima_y_alertas(cfg)
    return clima


def cargar_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Generador de informe de precios — Don Antonio SRL"
    )
    parser.add_argument("--cliente", default="",
                        help="Nombre del cliente (aparece en la portada)")
    parser.add_argument("--salida", default="",
                        help="Ruta del PDF de salida")
    parser.add_argument("--fecha", default="",
                        help="Fecha en formato YYYY-MM-DD (default: hoy)")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--logo", default="logo.png")
    parser.add_argument("--sin-clima", action="store_true",
                        help="No incluir la sección de clima de mañana")
    parser.add_argument("--zona", default="",
                        help="Filtrar clima/alertas a una zona específica "
                             "(ej: 'Orán', 'Apolinario Saravia'). "
                             "Por defecto incluye todas las zonas.")
    args = parser.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)

    print("=" * 60)
    print("  Generador de Precios — Don Antonio SRL")
    print("=" * 60)

    cfg = cargar_config(args.config)
    cfg_p = cfg["precios_mercado_central"]
    empresa = cfg["empresa"]

    if args.fecha:
        try:
            fecha = datetime.strptime(args.fecha, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Fecha inválida: {args.fecha}. Usar formato YYYY-MM-DD")
            sys.exit(1)
    else:
        fecha = _ahora_ar()

    cli = PreciosMCBA()

    prio = cfg_p.get("procedencias_prioritarias", [])
    fb = cfg_p.get("procedencias_fallback", [])
    procedencias_filtro = cfg_p.get("procedencias_filtro", [])
    if prio:
        print(f"\n→ Procedencias prioritarias: {', '.join(prio)}")
        if fb:
            print(f"  Fallback si no hay datos del día: {', '.join(fb)}")
    elif procedencias_filtro:
        print(f"\n→ Filtrando por procedencias: {', '.join(procedencias_filtro)}")

    print(f"\n→ Consultando precios del {fecha.strftime('%d/%m/%Y')}...")
    datos_hoy = cli.precios_del_dia(fecha,
                                     cfg_p["productos_hortalizas"],
                                     cfg_p["productos_frutas"],
                                     procedencias_filtro=procedencias_filtro,
                                     procedencias_prioritarias=prio,
                                     procedencias_fallback=fb)
    if not datos_hoy["productos"]:
        print(f"❌ No se encontraron precios para esa fecha.")
        sys.exit(1)

    print(f"  ✓ Datos del {datos_hoy['fecha_datos'].strftime('%d/%m/%Y')}")
    n_total = sum(len(v) for v in datos_hoy['productos'].values())
    n_fallback = sum(1 for items in datos_hoy['productos'].values()
                      for it in items if it.get("es_fallback"))
    print(f"  ✓ {n_total} cotizaciones en {len(datos_hoy['productos'])} grupos "
          f"({n_fallback} con fallback Bs As)")

    print("\n→ Consultando precios del día anterior (para variación)...")
    datos_ayer = cli.precios_dia_anterior(datos_hoy["fecha_datos"],
                                          cfg_p["productos_hortalizas"],
                                          cfg_p["productos_frutas"],
                                          procedencias_filtro=procedencias_filtro,
                                          procedencias_prioritarias=prio,
                                          procedencias_fallback=fb)
    if datos_ayer.get("fecha_datos"):
        print(f"  ✓ Datos previos del {datos_ayer['fecha_datos'].strftime('%d/%m/%Y')}")
    variaciones = cli.calcular_variaciones(datos_hoy, datos_ayer)
    print(f"  ✓ {len(variaciones)} variaciones calculadas")

    # Slug para el nombre del archivo si se filtra por zona
    def _slug(s):
        # Sin tildes, sin espacios, ascii-friendly
        import unicodedata
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
        return s.lower().replace(' ', '_').replace('.', '')

    if args.salida:
        salida = args.salida
    else:
        os.makedirs("informes", exist_ok=True)
        fecha_str = datos_hoy["fecha_datos"].strftime("%Y%m%d")
        suf = f"_{args.cliente.replace(' ', '_')}" if args.cliente else ""
        if args.zona:
            suf += f"_{_slug(args.zona)}"
        salida = os.path.join("informes", f"precios_mcba_{fecha_str}{suf}.pdf")

    # Obtener clima 48hs + alertas próximos 7 días
    clima_48h = None
    alertas_7d = None
    if not args.sin_clima:
        print("\n→ Obteniendo pronóstico 48hs + alertas próximos 7 días...")
        clima_48h, alertas_7d = obtener_clima_y_alertas(cfg)

        # Filtrar a zona específica si se pidió
        if args.zona:
            zona_norm = args.zona.lower().strip()
            clima_48h_filt = [c for c in clima_48h
                               if c["zona"].lower().strip() == zona_norm]
            if not clima_48h_filt:
                print(f"  ⚠️ Zona '{args.zona}' no encontrada. "
                      f"Zonas válidas: {[c['zona'] for c in clima_48h]}")
                sys.exit(1)
            clima_48h = clima_48h_filt
            alertas_7d = [z for z in (alertas_7d or [])
                          if z["zona"].lower().strip() == zona_norm]
            print(f"  → Filtrado a zona: {clima_48h[0]['zona']}")

        n_alertas_48h = sum(1 for c in clima_48h if c.get("alerta"))
        n_zonas_7d = len(alertas_7d) if alertas_7d else 0
        n_alertas_7d = sum(len(z["alertas"]) for z in (alertas_7d or []))
        print(f"  ✓ {len(clima_48h)} zonas — {n_alertas_48h} con alerta 48hs")
        print(f"  ✓ {n_alertas_7d} alertas previstas en próximos 7 días "
              f"({n_zonas_7d} zonas)")

    print(f"\n📄 Generando PDF: {salida}")
    gen = GeneradorPDFPrecios(empresa, logo_path=args.logo)
    gen.generar(datos_hoy, datos_ayer, variaciones,
                output_path=salida, cliente=args.cliente,
                clima_48h=clima_48h,
                alertas_7d=alertas_7d)

    # Guardar también una copia con nombre fijo "precios_hoy.pdf" para la URL pública
    import shutil
    shutil.copy(salida, "informes/precios_hoy.pdf")
    shutil.copy(salida, "precios_hoy.pdf")  # También en la raíz para GitHub Pages

    # Generar el JSON resumen que consume enviar_email_precios.py
    fecha_dt = datos_hoy["fecha_datos"]
    meses_es = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo",
                6: "junio", 7: "julio", 8: "agosto", 9: "septiembre",
                10: "octubre", 11: "noviembre", 12: "diciembre"}
    fecha_str = f"{fecha_dt.day} de {meses_es[fecha_dt.month]} de {fecha_dt.year}"

    # Top productos: tomar el medio de cada (especie, variedad)
    productos_top = []
    for esp, items in datos_hoy["productos"].items():
        # Agrupar por variedad
        por_var = {}
        for it in items:
            por_var.setdefault(it["variedad"], []).append(it)
        for var, items_v in por_var.items():
            # Promedio del precio medio para esa variedad
            precios = [i["precio_med_bulto"] for i in items_v if i["precio_med_bulto"] > 0]
            if not precios:
                continue
            precio_med = sum(precios) / len(precios)
            # Tomar el primer item como representante para procedencia/envase
            it_rep = items_v[0]
            clave = (esp, it_rep["variedad"], it_rep["procedencia"])
            from precios_mercado import envase_legible
            productos_top.append({
                "especie": esp,
                "variedad": var,
                "procedencia": it_rep["procedencia"] + (" *" if it_rep.get("es_fallback") else ""),
                "envase": envase_legible(it_rep["envase"]),
                "kg_bulto": it_rep["kg_bulto"],
                "precio": precio_med,
                "variacion": variaciones.get(clave),
            })

    # Texto narrativo
    n_total = sum(len(v) for v in datos_hoy['productos'].values())
    sub = sum(1 for v in variaciones.values() if v > 5)
    baj = sum(1 for v in variaciones.values() if v < -5)
    est = sum(1 for v in variaciones.values() if -5 <= v <= 5)
    if sub or baj:
        texto = (f"Hoy se relevaron <b>{n_total} cotizaciones</b> en el MCBA para tus productos. "
                 f"{baj} cotizaciones bajaron, {sub} subieron y {est} se mantuvieron estables "
                 "respecto al día hábil anterior.")
    else:
        texto = (f"Hoy se relevaron <b>{n_total} cotizaciones</b> en el MCBA para tus productos. "
                 "Sin variaciones significativas respecto al día hábil anterior.")

    # Calcular días de atraso (si MCBA no publicó hoy)
    dias_atraso = (_ahora_ar().date() - fecha_dt.date()).days

    resumen_dict = {
        "fecha_str": fecha_str,
        "fecha_iso": fecha_dt.strftime("%Y-%m-%d"),
        "dias_atraso": dias_atraso,
        "n_cotizaciones": n_total,
        "texto_resumen": texto,
        "productos_top": productos_top,
        "clima_48h": clima_48h or [],
        "alertas_7d": alertas_7d or [],
    }

    with open("informes/precios_hoy_resumen.json", "w", encoding="utf-8") as f:
        json.dump(resumen_dict, f, ensure_ascii=False, indent=2, default=str)
    print(f"  ✓ Resumen JSON guardado en informes/precios_hoy_resumen.json")

    print(f"\n✓ Informe generado: {salida}")
    print("=" * 60)


if __name__ == "__main__":
    main()
