"""
generar_informe.py
Script principal: orquesta la obtención de datos, análisis y generación del PDF.
Las consultas a la API se hacen en paralelo para ser rápidas.

USO:
    python3 generar_informe.py                         # informe genérico
    python3 generar_informe.py --cliente "Juan Pérez"  # informe personalizado
    python3 generar_informe.py --salida mi_informe.pdf

Requisitos:
    pip install reportlab matplotlib requests
"""

import argparse
import json
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from clima_api import ClimaAPI
from analisis import AnalizadorClima
from generador_pdf import GeneradorPDF


def cargar_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def procesar_localidad(loc: dict, api: ClimaAPI, analizador: AnalizadorClima):
    """Procesa una localidad: trae todos los datos y los analiza."""
    try:
        # Pronóstico 15 días + alertas
        pron = api.pronostico_15_dias(loc["lat"], loc["lon"])
        resumen = analizador.resumen_15_dias(pron)
        alertas = analizador.detectar_alertas(pron)

        # Histórico año pasado
        ap = api.comparativa_anio_pasado(loc["lat"], loc["lon"])
        # Normal climática (5 años)
        normal = api.normal_climatica(loc["lat"], loc["lon"])
        comp = analizador.comparativa(resumen, ap, normal)
        recs = analizador.recomendaciones(resumen, alertas)

        # Trimestral (con descomposición mensual para modo extendido)
        try:
            tr = api.pronostico_trimestral(loc["lat"], loc["lon"])
            resumen_t = analizador.resumen_trimestral(tr)
            meses_detalle = analizador.descomponer_trimestral_por_mes(tr)
        except Exception:
            resumen_t = {"tipo": "no_disponible"}
            meses_detalle = []

        return {
            "ok": True,
            "loc": loc,
            "datos": {
                "localidad": loc,
                "resumen_15_dias": resumen,
                "alertas": alertas,
                "recomendaciones": recs,
                "comparativa": comp,
            },
            "trimestral": {
                "localidad": loc,
                "resumen_trimestral": resumen_t,
                "meses_detalle": meses_detalle,
            }
        }
    except Exception as e:
        return {"ok": False, "loc": loc, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Generador de informes climáticos — Don Antonio SRL")
    parser.add_argument("--cliente", default="")
    parser.add_argument("--salida", default="")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--logo", default="logo.png")
    parser.add_argument("--localidad", default="",
                        help="Filtrar a una sola localidad (por nombre)")
    parser.add_argument("--localidades", default="",
                        help="Filtrar a varias localidades, separadas por coma "
                             "(ej: 'Apolinario Saravia,Pichanal')")
    parser.add_argument("--extendido", action="store_true",
                        help="Generar informe extendido con análisis trimestral detallado")
    args = parser.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)

    print("=" * 60)
    print("  PRevisor del Clima — Don Antonio SRL")
    print("=" * 60)

    cfg = cargar_config(args.config)
    empresa = cfg["empresa"]
    localidades = cfg["localidades"]
    if args.localidad:
        localidades = [l for l in localidades
                       if l["nombre"].lower() == args.localidad.lower()]
        if not localidades:
            print(f"❌ No se encontró la localidad '{args.localidad}'")
            sys.exit(1)
    elif args.localidades:
        nombres_pedidos = [n.strip().lower() for n in args.localidades.split(",")]
        localidades = [l for l in localidades
                       if l["nombre"].lower() in nombres_pedidos]
        if not localidades:
            print(f"❌ No se encontró ninguna de las localidades pedidas")
            sys.exit(1)
        print(f"  Filtrando a: {', '.join(l['nombre'] for l in localidades)}")

    api = ClimaAPI()
    analizador = AnalizadorClima(cfg["umbrales_alertas"])

    print(f"\n→ Procesando {len(localidades)} localidad(es) en paralelo...")
    datos_localidades = [None] * len(localidades)
    trimestre_resumenes = [None] * len(localidades)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {
            ex.submit(procesar_localidad, loc, api, analizador): i
            for i, loc in enumerate(localidades)
        }
        for f in as_completed(futures):
            i = futures[f]
            r = f.result()
            if r["ok"]:
                datos_localidades[i] = r["datos"]
                trimestre_resumenes[i] = r["trimestral"]
                n = len(r["datos"]["alertas"])
                print(f"  ✓ {r['loc']['nombre']:25s} ({r['loc']['provincia']}) — "
                      f"{n} alerta(s)")
            else:
                print(f"  ❌ {r['loc']['nombre']:25s} — {r['error']}")

    # Filtrar None (localidades fallidas)
    datos_localidades = [d for d in datos_localidades if d]
    trimestre_resumenes = [t for t in trimestre_resumenes if t]

    if not datos_localidades:
        print("\n❌ No se pudo obtener datos de ninguna localidad. Abortando.")
        sys.exit(1)

    if args.salida:
        salida = args.salida
    else:
        os.makedirs("informes", exist_ok=True)
        fecha = datetime.now().strftime("%Y%m%d_%H%M")
        suf = f"_{args.cliente.replace(' ', '_')}" if args.cliente else ""
        ext = "_EXTENDIDO" if args.extendido else ""
        # Indicar zonas en el nombre si fue filtrado
        if args.localidad:
            zona_str = f"_{args.localidad.replace(' ', '')}"
        elif args.localidades:
            n = len([x for x in args.localidades.split(',') if x.strip()])
            zona_str = f"_{n}zonas"
        else:
            zona_str = ""
        salida = os.path.join("informes", f"informe_clima{ext}{zona_str}_{fecha}{suf}.pdf")

    tipo = "EXTENDIDO" if args.extendido else "estándar"
    print(f"\n📄 Generando PDF {tipo}: {salida}")
    gen = GeneradorPDF(empresa, logo_path=args.logo)
    gen.generar(datos_localidades, trimestre_resumenes,
                output_path=salida, cliente=args.cliente,
                extendido=args.extendido)

    print(f"\n✓ Informe generado exitosamente: {salida}")
    print(f"  Localidades procesadas: {len(datos_localidades)}")
    total_alertas = sum(len(d["alertas"]) for d in datos_localidades)
    print(f"  Total de alertas: {total_alertas}")
    print("=" * 60)


if __name__ == "__main__":
    main()
