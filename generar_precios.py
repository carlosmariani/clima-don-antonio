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
from datetime import datetime

from precios_mercado import PreciosMCBA
from generador_pdf_precios import GeneradorPDFPrecios
from clima_api import ClimaAPI
from analisis import AnalizadorClima
from concurrent.futures import ThreadPoolExecutor


def obtener_clima_manana(cfg) -> list:
    """Obtiene pronóstico para el día siguiente en las 10 zonas configuradas."""
    api = ClimaAPI()
    analizador = AnalizadorClima(cfg["umbrales_alertas"])

    def _zona(loc):
        try:
            pron = api.pronostico_15_dias(loc["lat"], loc["lon"])
            d = pron["daily"]
            # Día 1 = hoy (índice 0), día 2 = mañana (índice 1)
            idx = 1 if len(d["time"]) > 1 else 0
            tmax = d["temperature_2m_max"][idx]
            tmin = d["temperature_2m_min"][idx]
            lluvia = d["precipitation_sum"][idx]
            prob = (d.get("precipitation_probability_max", [0])[idx] or 0)

            # Detectar alertas para mañana
            alerta = None
            ums = cfg["umbrales_alertas"]
            if tmin is not None and tmin <= ums["helada_temp_min"]:
                sev = "🔴 HELADA" if tmin <= 0 else "❄️ Riesgo de helada"
                alerta = f"{sev} ({tmin:.0f}°C)"
            elif tmax is not None and tmax >= ums["calor_extremo_temp_max"]:
                alerta = f"🌡️ Calor extremo ({tmax:.0f}°C)"
            elif lluvia is not None and lluvia >= ums["lluvia_intensa_mm_dia"]:
                alerta = f"🌧️ Lluvia intensa ({lluvia:.0f} mm)"
            v_arr = d.get("windgusts_10m_max") or d["windspeed_10m_max"]
            if alerta is None and v_arr and v_arr[idx] is not None and v_arr[idx] >= ums["viento_fuerte_kmh"]:
                alerta = f"💨 Viento fuerte ({v_arr[idx]:.0f} km/h)"

            return {
                "zona": loc["nombre"],
                "provincia": loc["provincia"],
                "tmax": tmax if tmax is not None else 0,
                "tmin": tmin if tmin is not None else 0,
                "lluvia_mm": lluvia if lluvia is not None else 0,
                "prob_lluvia": prob,
                "alerta": alerta,
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as ex:
        resultados = list(ex.map(_zona, cfg["localidades"]))

    # Mantener orden del config y filtrar None
    resultados = [r for r in resultados if r]
    orden = {l["nombre"]: i for i, l in enumerate(cfg["localidades"])}
    resultados.sort(key=lambda r: orden.get(r["zona"], 999))
    return resultados


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
        fecha = datetime.now()

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

    if args.salida:
        salida = args.salida
    else:
        os.makedirs("informes", exist_ok=True)
        fecha_str = datos_hoy["fecha_datos"].strftime("%Y%m%d")
        suf = f"_{args.cliente.replace(' ', '_')}" if args.cliente else ""
        salida = os.path.join("informes", f"precios_mcba_{fecha_str}{suf}.pdf")

    # Obtener clima de mañana para anexar
    clima_manana = None
    if not args.sin_clima:
        print("\n→ Obteniendo pronóstico para mañana en las 10 zonas...")
        clima_manana = obtener_clima_manana(cfg)
        n_alertas = sum(1 for c in clima_manana if c.get("alerta"))
        print(f"  ✓ {len(clima_manana)} zonas, {n_alertas} con alerta crítica")

    print(f"\n📄 Generando PDF: {salida}")
    gen = GeneradorPDFPrecios(empresa, logo_path=args.logo)
    gen.generar(datos_hoy, datos_ayer, variaciones,
                output_path=salida, cliente=args.cliente,
                clima_manana=clima_manana)

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

    resumen_dict = {
        "fecha_str": fecha_str,
        "n_cotizaciones": n_total,
        "texto_resumen": texto,
        "productos_top": productos_top,
        "clima_manana": clima_manana or [],
    }

    with open("informes/precios_hoy_resumen.json", "w", encoding="utf-8") as f:
        json.dump(resumen_dict, f, ensure_ascii=False, indent=2, default=str)
    print(f"  ✓ Resumen JSON guardado en informes/precios_hoy_resumen.json")

    print(f"\n✓ Informe generado: {salida}")
    print("=" * 60)


if __name__ == "__main__":
    main()
