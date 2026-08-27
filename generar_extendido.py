"""
generar_extendido.py
Genera el REPORTE CLIMÁTICO EXTENDIDO QUINCENAL — Don Antonio SRL.

Solo se emite los días 1 y 15 de cada mes. Contiene:
  1. Contexto climático global (estado ENSO — El Niño / La Niña)
  2. Pronóstico extendido 15 días por zona (con gráficos)
  3. Perspectiva estacional próximos 3 meses (con gráficos)
  4. Recomendaciones agronómicas por zona

USO:
    python3 generar_extendido.py                          # todas las localidades DA
    python3 generar_extendido.py --salida mi_reporte.pdf
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from clima_api import ClimaAPI
from analisis import AnalizadorClima
from interpretacion import (resumen_interpretativo, que_hacer_simple,
                             tendencia_trimestral_simple,
                             comparativa_simple, pictograma_clima,
                             calcular_semaforo)
from clima_enso import obtener_estado_enso
from generador_pdf_extendido import GeneradorPDFExtendido

TZ_AR = timezone(timedelta(hours=-3))


def _ahora_ar() -> datetime:
    return datetime.now(TZ_AR).replace(tzinfo=None)


def cargar_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def procesar_localidad(loc: dict, api: ClimaAPI, analizador: AnalizadorClima):
    try:
        # Ensemble multi-modelo (ECMWF + GFS + ICON + JMA) para 15 días
        pron = api.pronostico_15_dias_ensemble(loc["lat"], loc["lon"])
        resumen = analizador.resumen_15_dias(pron)
        alertas = analizador.detectar_alertas(pron)

        ap = api.comparativa_anio_pasado(loc["lat"], loc["lon"])
        normal = api.normal_climatica(loc["lat"], loc["lon"])
        comp = analizador.comparativa(resumen, ap, normal)

        try:
            tr = api.pronostico_trimestral(loc["lat"], loc["lon"])
            resumen_t = analizador.resumen_trimestral(tr)
            tendencia_t = tendencia_trimestral_simple(resumen_t, resumen)
        except Exception:
            resumen_t = {"tipo": "no_disponible"}
            tendencia_t = {}

        semaforo = calcular_semaforo(resumen, alertas)
        picto = pictograma_clima(resumen)
        interp = resumen_interpretativo(resumen, comp)
        acciones = que_hacer_simple(resumen, alertas)
        comp_frase = comparativa_simple(resumen, comp)

        return {
            "ok": True,
            "info": loc,
            "resumen": resumen,
            "alertas": alertas,
            "comparativa": comp,
            "trimestral": resumen_t,
            "tendencia_trimestral": tendencia_t,
            "semaforo": semaforo,
            "pictograma": {"emoji": picto[0], "descripcion": picto[1]},
            "interpretacion": interp,
            "acciones": acciones,
            "comparativa_frase": comp_frase,
        }
    except Exception as e:
        return {"ok": False, "info": loc, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Reporte climático extendido quincenal — Don Antonio SRL")
    parser.add_argument("--salida", default="")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--logo", default="logo.png")
    args = parser.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)

    print("=" * 60)
    print("  Reporte Climático Extendido — Don Antonio SRL")
    print("=" * 60)

    cfg = cargar_config(args.config)
    empresa = cfg["empresa"]

    # Solo las 10 localidades del grupo Don Antonio
    localidades = [l for l in cfg["localidades"]
                   if not l.get("grupo") or l.get("grupo") == "don_antonio"]

    # === Estado ENSO ===
    print("\n→ Obteniendo estado ENSO (El Niño / La Niña)...")
    enso = obtener_estado_enso()
    if enso.get("disponible"):
        print(f"  ✓ {enso['titulo']} — anomalía ONI {enso['anomalia']:+.2f}")
    else:
        print(f"  ⚠️ ENSO no disponible: {enso.get('error', '')}")

    # === Procesar zonas en paralelo ===
    api = ClimaAPI()
    analizador = AnalizadorClima(cfg["umbrales_alertas"])
    print(f"\n→ Procesando {len(localidades)} zonas en paralelo...")
    with ThreadPoolExecutor(max_workers=6) as ex:
        resultados = list(ex.map(
            lambda l: procesar_localidad(l, api, analizador), localidades))
    zonas = []
    for r in resultados:
        if r["ok"]:
            print(f"  ✓ {r['info']['nombre']:25s} — {len(r['alertas'])} alerta(s)")
            zonas.append(r)
        else:
            print(f"  ✗ {r['info']['nombre']}: {r['error']}")

    if not zonas:
        print("\n❌ No se pudo obtener datos de ninguna zona. Abortando.")
        sys.exit(1)

    # === Salida ===
    if args.salida:
        salida = args.salida
    else:
        os.makedirs("informes", exist_ok=True)
        fecha_str = _ahora_ar().strftime("%Y%m%d")
        salida = f"informes/extendido_{fecha_str}.pdf"

    print(f"\n📄 Generando PDF: {salida}")
    gen = GeneradorPDFExtendido(empresa, logo_path=args.logo)
    gen.generar(zonas, enso, output_path=salida)

    # Copia con nombre fijo para PWA/link
    import shutil
    shutil.copy(salida, "informes/extendido_hoy.pdf")
    print(f"  ✓ Copia en informes/extendido_hoy.pdf")

    print("\n✓ Reporte extendido generado.")
    print("=" * 60)


if __name__ == "__main__":
    main()
