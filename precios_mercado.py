"""
precios_mercado.py
Cliente para obtener precios mayoristas del Mercado Central de Buenos Aires (MCBA).

El MCBA publica archivos XLS diarios (de lunes a viernes) en ZIPs mensuales:
  https://mercadocentral.gob.ar/sites/default/files/precios_mayoristas/HORTALIZAS_MES-AÑO.zip
  https://mercadocentral.gob.ar/sites/default/files/precios_mayoristas/FRUTAS_MES-AÑO.zip

Formato de archivo XLS (RHddmmaa.XLS o RFddmmaa.XLS):
  Columnas: ESP | VAR | PROC | ENV | KG | CAL | TAM | GRADO | MAddmmaa | MOddmmaa | MIddmmaa | MAPK | MOPK | MIPK
    ESP   = Especie  (ej: TOMATE)
    VAR   = Variedad (ej: REDONDO)
    PROC  = Procedencia
    ENV   = Envase   (TO=tomate, BO=bolsa, JA=jaula, PE=pelado, CA=cajón, etc.)
    KG    = Peso del bulto en kg
    MA/MO/MI = Precio Máximo / Medio / Mínimo por bulto
    MAPK/MOPK/MIPK = Precio Máximo / Medio / Mínimo por kilo
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import requests
import xlrd


URL_BASE = "https://mercadocentral.gob.ar/sites/default/files/precios_mayoristas/"

MESES_ES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

MESES_ES_CORTO = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


class PreciosMCBA:
    """Cliente para obtener precios del Mercado Central de Buenos Aires."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PRevisor del Clima - Don Antonio SRL"
        })
        # Cache de archivos ZIP descargados (clave = url, valor = bytes)
        self._zip_cache: Dict[str, bytes] = {}

    # ------------------------------------------------------------------ #
    # Construcción de URLs y nombres de archivo
    # ------------------------------------------------------------------ #
    @staticmethod
    def _candidatos_url_zip(tipo: str, fecha: datetime) -> List[str]:
        """
        Devuelve URLs candidatas para un mes/año dado.
        El sitio del MCBA usa nombres inconsistentes, hay que probar varios:
          - HORTALIZAS_ABRIL2026.zip
          - HORTALIZAS_ABRIL-2026.zip
          - HORTALIZAS_ABRIL-2026_0.zip
          - HORTALIZAS_ABRIL-26.zip
          - HORTALIZAS_ABRIL-26_0.zip
          - HORTALIZAS ABRIL2026.zip   (con espacio)
          - HORTALIZAS_ABRIL_2026.zip
        """
        prefix = "HORTALIZAS" if tipo == "hortalizas" else "FRUTAS"
        mes = MESES_ES[fecha.month]
        a4 = fecha.year
        a2 = fecha.year % 100
        candidatos = [
            f"{prefix}_{mes}{a4}.zip",
            f"{prefix}_{mes}{a4}_0.zip",   # ← variante con sufijo _0
            f"{prefix}_{mes}-{a4}.zip",
            f"{prefix}_{mes}-{a4}_0.zip",
            f"{prefix}_{mes}-{a2}.zip",
            f"{prefix}_{mes}-{a2}_0.zip",
            f"{prefix} {mes}{a4}.zip",
            f"{prefix} {mes}{a4}_0.zip",
            f"{prefix}_{mes} {a4}.zip",
            f"{prefix}_{mes}_{a4}.zip",
            f"{prefix}  {mes}-{a2}.zip",
            f"{prefix}  {mes}-{a2}_0.zip",
            f"{prefix}  {mes}{a4}.zip",
            f"{prefix}  {mes}{a4}_0.zip",
            f"{prefix} {mes}-{a4}.zip",
            f"{prefix} {mes}-{a2}.zip",
            f"{prefix}  {mes} {a4}.zip",  # con doble espacio + espacio (ENERO 2026)
            f"{prefix}  {mes} {a4}_0.zip",
        ]
        return [URL_BASE + requests.utils.requote_uri(c) for c in candidatos]

    @staticmethod
    def _nombre_xls_dia(tipo: str, fecha: datetime) -> str:
        """Nombre del archivo XLS dentro del ZIP (RHddmmaa.XLS o RFddmmaa.XLS)."""
        prefix = "RH" if tipo == "hortalizas" else "RF"
        return f"{prefix}{fecha.day:02d}{fecha.month:02d}{fecha.year % 100:02d}.XLS"

    # ------------------------------------------------------------------ #
    # Descarga del ZIP del mes
    # ------------------------------------------------------------------ #
    def _descargar_zip(self, tipo: str, fecha: datetime) -> Optional[bytes]:
        """Descarga el ZIP del mes correspondiente a la fecha. Retorna bytes o None."""
        for url in self._candidatos_url_zip(tipo, fecha):
            if url in self._zip_cache:
                return self._zip_cache[url]
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 200 and resp.content[:2] == b"PK":
                    self._zip_cache[url] = resp.content
                    return resp.content
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------ #
    # Extracción y parseo de un archivo del día
    # ------------------------------------------------------------------ #
    def _leer_xls_dia(self, tipo: str, fecha: datetime) -> Optional[List[Dict[str, Any]]]:
        """
        Devuelve una lista de filas (dicts) del archivo del día, o None si no
        se encontró (puede ser feriado, fin de semana, o aún no publicado).
        """
        zip_bytes = self._descargar_zip(tipo, fecha)
        if not zip_bytes:
            return None
        nombre_xls = self._nombre_xls_dia(tipo, fecha)
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # Buscar el archivo (case insensitive)
                names = {n.upper(): n for n in zf.namelist()}
                if nombre_xls.upper() not in names:
                    return None
                with zf.open(names[nombre_xls.upper()]) as f:
                    contenido = f.read()
        except Exception:
            return None

        try:
            # Forzar encoding latin-1: el MCBA exporta sin codepage y la Ñ
            # aparece como ¥ por defecto. Con encoding_override="cp1252" se
            # interpreta correctamente.
            wb = xlrd.open_workbook(file_contents=contenido,
                                     encoding_override="cp1252")
            sheet = wb.sheet_by_index(0)
        except Exception:
            return None

        filas = []
        for i in range(1, sheet.nrows):  # saltar header
            esp = str(sheet.cell_value(i, 0)).strip()
            var = str(sheet.cell_value(i, 1)).strip()
            proc = str(sheet.cell_value(i, 2)).strip()
            env = str(sheet.cell_value(i, 3)).strip()
            try:
                kg = float(sheet.cell_value(i, 4) or 0)
            except Exception:
                kg = 0.0
            cal = str(sheet.cell_value(i, 5)).strip()
            tam = str(sheet.cell_value(i, 6)).strip()

            def _num(j):
                try:
                    return float(sheet.cell_value(i, j) or 0)
                except Exception:
                    return 0.0

            ma = _num(8)   # Precio máximo bulto
            mo = _num(9)   # Precio medio bulto
            mi = _num(10)  # Precio mínimo bulto
            mapk = _num(11)  # Precio máximo /kg
            mopk = _num(12)  # Precio medio /kg
            mipk = _num(13)  # Precio mínimo /kg

            # Saltar filas vacías o de promedio
            if not esp:
                continue
            es_promedio = "Prom" in var

            filas.append({
                "especie": esp,
                "variedad": var,
                "es_promedio": es_promedio,
                "procedencia": proc,
                "envase": env,
                "kg_bulto": kg,
                "calidad": cal,
                "tamano": tam,
                "precio_max_bulto": ma,
                "precio_med_bulto": mo,
                "precio_min_bulto": mi,
                "precio_max_kg": mapk,
                "precio_med_kg": mopk,
                "precio_min_kg": mipk,
            })

        return filas

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def precios_del_dia(self, fecha: datetime,
                        productos_hortalizas: List[Dict],
                        productos_frutas: List[Dict],
                        max_dias_atras: int = 5,
                        procedencias_filtro: List[str] = None,
                        procedencias_prioritarias: List[str] = None,
                        procedencias_fallback: List[str] = None) -> Dict[str, Any]:
        """
        Devuelve los precios del día más cercano disponible (puede ser hoy o
        un día anterior si el MCBA aún no publicó). Si pasaron más de
        max_dias_atras días sin datos, devuelve un dict vacío.

        Estructura de retorno:
        {
            "fecha_datos": datetime,        # día efectivamente consultado
            "fecha_solicitada": datetime,
            "esta_actualizado": bool,        # True si fecha_datos == hoy
            "productos": {
                "TOMATE": [
                    {"variedad": "REDONDO", "procedencia": "BS. AS.", ...},
                    ...
                ],
                ...
            }
        }
        """
        # Buscar el archivo del día más cercano
        fecha_consultada = fecha
        filas_hortalizas = None
        for _ in range(max_dias_atras + 1):
            filas_hortalizas = self._leer_xls_dia("hortalizas", fecha_consultada)
            if filas_hortalizas is not None:
                break
            fecha_consultada -= timedelta(days=1)

        if filas_hortalizas is None:
            return {
                "fecha_solicitada": fecha,
                "fecha_datos": None,
                "esta_actualizado": False,
                "productos": {},
                "error": "No se encontró archivo del MCBA en los últimos días"
            }

        filas_frutas = self._leer_xls_dia("frutas", fecha_consultada) or []

        # Filtrar por productos configurados
        proc_filtro_norm = [p.upper().strip() for p in (procedencias_filtro or [])]
        prio_norm = [p.upper().strip() for p in (procedencias_prioritarias or [])]
        fallback_norm = [p.upper().strip() for p in (procedencias_fallback or [])]

        def _en(proc: str, lista: List[str]) -> bool:
            if not lista:
                return False
            p = proc.upper().strip()
            return any(f in p for f in lista)

        def _filtrar(filas, productos_cfg):
            """
            Si hay procedencias_prioritarias y _fallback, aplica esa lógica:
            por cada (especie, variedad), prefiere las prioritarias; si no hay
            ninguna ese día, cae a las fallback (marcando es_fallback=True).
            Si no, usa el filtro simple procedencias_filtro.
            """
            resultado_local = {}
            for cfg in productos_cfg:
                esp = cfg["especie"].upper()
                vars_filtro = [v.upper() for v in cfg.get("variedades", [])]
                items_esp = [
                    f for f in filas
                    if f["especie"].upper() == esp
                    and not f["es_promedio"]
                    and (not vars_filtro or any(v in f["variedad"].upper() for v in vars_filtro))
                ]
                if not items_esp:
                    continue

                if prio_norm:
                    # Lógica con fallback: agrupar por variedad
                    por_variedad = {}
                    for it in items_esp:
                        v = it["variedad"]
                        por_variedad.setdefault(v, []).append(it)
                    items_finales = []
                    for v, lista_v in por_variedad.items():
                        prio = [i for i in lista_v if _en(i["procedencia"], prio_norm)]
                        if prio:
                            items_finales.extend(prio)
                        elif fallback_norm:
                            fb = [i for i in lista_v if _en(i["procedencia"], fallback_norm)]
                            for i in fb:
                                i = dict(i)  # copia para no mutar
                                i["es_fallback"] = True
                                items_finales.append(i)
                    if items_finales:
                        resultado_local[esp] = items_finales
                elif proc_filtro_norm:
                    # Filtro simple
                    items = [i for i in items_esp if _en(i["procedencia"], proc_filtro_norm)]
                    if items:
                        resultado_local[esp] = items
                else:
                    resultado_local[esp] = items_esp
            return resultado_local

        resultado = {}
        resultado.update(_filtrar(filas_hortalizas, productos_hortalizas))
        resultado.update(_filtrar(filas_frutas, productos_frutas))

        hoy = datetime.now()
        return {
            "fecha_solicitada": fecha,
            "fecha_datos": fecha_consultada,
            "esta_actualizado": fecha_consultada.date() == hoy.date(),
            "productos": resultado,
        }

    def precios_dia_anterior(self, fecha_actual: datetime,
                             productos_hortalizas: List[Dict],
                             productos_frutas: List[Dict],
                             procedencias_filtro: List[str] = None,
                             procedencias_prioritarias: List[str] = None,
                             procedencias_fallback: List[str] = None) -> Dict[str, Any]:
        """Precios del día hábil anterior — útil para calcular variación."""
        anterior = fecha_actual - timedelta(days=1)
        # Si cae sábado/domingo, retroceder al viernes
        while anterior.weekday() >= 5:  # 5=sábado, 6=domingo
            anterior -= timedelta(days=1)
        return self.precios_del_dia(
            anterior, productos_hortalizas, productos_frutas,
            max_dias_atras=5,
            procedencias_filtro=procedencias_filtro,
            procedencias_prioritarias=procedencias_prioritarias,
            procedencias_fallback=procedencias_fallback,
        )

    # ------------------------------------------------------------------ #
    # Helpers analíticos
    # ------------------------------------------------------------------ #
    @staticmethod
    def calcular_variaciones(precios_hoy: Dict, precios_ayer: Dict) -> Dict:
        """
        Calcula la variación porcentual del precio medio por bulto entre dos días.
        Devuelve dict {(especie, variedad, procedencia): variacion_porcentual}.
        """
        variaciones = {}
        for esp, items in precios_hoy.get("productos", {}).items():
            for it_hoy in items:
                clave = (esp, it_hoy["variedad"], it_hoy["procedencia"])
                # Buscar el item correspondiente en ayer
                items_ayer = precios_ayer.get("productos", {}).get(esp, [])
                it_ayer = next(
                    (a for a in items_ayer
                     if a["variedad"] == it_hoy["variedad"]
                     and a["procedencia"] == it_hoy["procedencia"]),
                    None
                )
                if it_ayer and it_ayer["precio_med_bulto"] > 0:
                    delta = it_hoy["precio_med_bulto"] - it_ayer["precio_med_bulto"]
                    variaciones[clave] = (delta / it_ayer["precio_med_bulto"]) * 100
        return variaciones


def envase_legible(env: str) -> str:
    """Convierte el código de envase del MCBA a nombre legible."""
    mapa = {
        "TO": "cajón tomate",
        "JA": "jaula",
        "BO": "bolsa",
        "PE": "pelado",
        "CA": "cajón",
        "RT": "red",
        "AT": "atado",
        "GR": "granel",
    }
    return mapa.get(env.strip().upper(), env or "—")


if __name__ == "__main__":
    # Test rápido
    import json
    cli = PreciosMCBA()
    cfg = json.load(open("config.json"))
    p = cfg["precios_mercado_central"]
    hoy = datetime.now()
    res = cli.precios_del_dia(hoy, p["productos_hortalizas"], p["productos_frutas"])
    print(f"Fecha datos: {res['fecha_datos']}")
    print(f"Productos encontrados: {list(res['productos'].keys())}")
    for esp, items in res["productos"].items():
        print(f"\n{esp} ({len(items)} ítems):")
        for it in items[:3]:
            print(f"  {it['variedad']:15s} | {it['procedencia']:12s} | "
                  f"{it['kg_bulto']}kg | ${it['precio_med_bulto']:.0f}/bulto | "
                  f"${it['precio_med_kg']:.0f}/kg")
