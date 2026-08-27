"""
clima_enso.py
Cliente simple para obtener el estado actual del ENSO (El Niño / La Niña)
desde el índice ONI oficial de NOAA. Devuelve un dict con la fase, intensidad
y un texto amigable para incluir en informes.

Umbrales oficiales NOAA (basados en anomalía ONI en °C):
  >= +2.0   → Súper El Niño
  >= +1.5   → El Niño fuerte
  >= +1.0   → El Niño moderado
  >= +0.5   → El Niño débil
  entre ±0.5 → Neutro
  <= -0.5   → La Niña débil
  <= -1.0   → La Niña moderada
  <= -1.5   → La Niña fuerte
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
import requests


ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"


def _clasificar(anom: float) -> Dict[str, str]:
    """Devuelve la fase y descripción según la anomalía ONI."""
    if anom >= 2.0:
        return {"fase": "SUPER_NINO", "titulo": "Súper El Niño",
                "emoji": "🔥", "color": "#B71C1C"}
    if anom >= 1.5:
        return {"fase": "NINO_FUERTE", "titulo": "El Niño fuerte",
                "emoji": "🌡️", "color": "#D32F2F"}
    if anom >= 1.0:
        return {"fase": "NINO_MODERADO", "titulo": "El Niño moderado",
                "emoji": "🌡️", "color": "#E64A19"}
    if anom >= 0.5:
        return {"fase": "NINO_DEBIL", "titulo": "El Niño débil",
                "emoji": "🌤️", "color": "#F57C00"}
    if anom > -0.5:
        return {"fase": "NEUTRO", "titulo": "Fase neutra (ni Niño ni Niña)",
                "emoji": "⚖️", "color": "#616161"}
    if anom > -1.0:
        return {"fase": "NINA_DEBIL", "titulo": "La Niña débil",
                "emoji": "🌧️", "color": "#0288D1"}
    if anom > -1.5:
        return {"fase": "NINA_MODERADA", "titulo": "La Niña moderada",
                "emoji": "💧", "color": "#0277BD"}
    return {"fase": "NINA_FUERTE", "titulo": "La Niña fuerte",
            "emoji": "🌊", "color": "#01579B"}


def _implicancia_noa(fase: str) -> str:
    """Texto breve sobre qué implica cada fase para el NOA argentino."""
    if fase.startswith("NINO"):
        return ("Para el NOA argentino, El Niño suele traer <b>veranos más "
                "secos y cálidos</b> de lo normal, con mayor riesgo de "
                "estrés hídrico en cultivos de verano. Las lluvias monzónicas "
                "tienden a llegar tarde o ser más escasas.")
    if fase.startswith("NINA"):
        return ("Para el NOA argentino, La Niña suele traer <b>más lluvias "
                "de lo normal en verano</b> y mayor humedad ambiente. Buenas "
                "condiciones para cultivos de secano pero también mayor "
                "riesgo de enfermedades fúngicas y anegamiento.")
    return ("En fase neutra, se esperan <b>condiciones cercanas a los valores "
            "normales</b> para la región. Sin señales climáticas fuertes: "
            "vale planificar según promedios históricos.")


def _implicancia_super(fase: str) -> Optional[str]:
    """Advertencia extra si es Súper Niño / Niña fuerte."""
    if fase == "SUPER_NINO":
        return ("⚠️ <b>Súper El Niño:</b> episodio de intensidad extrema. "
                "Mayor probabilidad de sequía persistente, olas de calor y "
                "reducción marcada de rendimientos en cultivos sensibles.")
    if fase == "NINA_FUERTE":
        return ("⚠️ <b>La Niña fuerte:</b> episodio intenso. Mayor "
                "probabilidad de lluvias abundantes, tormentas severas y "
                "riesgo de inundaciones o encharcamiento.")
    return None


def obtener_estado_enso(timeout: int = 15) -> Dict[str, Any]:
    """
    Descarga y parsea el índice ONI de NOAA. Devuelve un dict con:
      - anomalia: float (última anomalía disponible)
      - trimestre: str (ej: "MJJ 2026")
      - fase, titulo, emoji, color: clasificación
      - descripcion: qué implica para el NOA
      - tendencia: lista de los últimos 6 trimestres (para gráfico)

    Si falla, devuelve un dict con `disponible=False` y texto genérico.
    """
    try:
        resp = requests.get(ONI_URL, timeout=timeout,
                            headers={"User-Agent": "PRevisor del Clima"})
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}")
        lineas = [l.strip() for l in resp.text.strip().split("\n") if l.strip()]
        # header line ~ "SEAS YR TOTAL ANOM"
        datos: List[Dict[str, Any]] = []
        for l in lineas[1:]:
            partes = l.split()
            if len(partes) < 4:
                continue
            try:
                sea = partes[0]
                yr = int(partes[1])
                total = float(partes[2])
                anom = float(partes[3])
                datos.append({"trimestre": f"{sea} {yr}",
                               "total": total, "anom": anom})
            except Exception:
                continue
        if not datos:
            raise Exception("No se pudieron parsear datos")
        ultimo = datos[-1]
        anom = ultimo["anom"]
        clas = _clasificar(anom)
        implic = _implicancia_noa(clas["fase"])
        extra = _implicancia_super(clas["fase"])
        return {
            "disponible": True,
            "anomalia": anom,
            "trimestre": ultimo["trimestre"],
            **clas,
            "descripcion": implic,
            "extra": extra,
            "tendencia": datos[-8:],  # últimos ~2 años para gráfico
        }
    except Exception as e:
        return {
            "disponible": False,
            "error": str(e),
            "titulo": "Estado ENSO no disponible",
            "emoji": "❓",
            "color": "#616161",
            "descripcion": ("No se pudo obtener el estado actualizado del "
                             "índice ENSO. Consultar boletín del SMN o "
                             "NOAA CPC para la última información."),
        }


if __name__ == "__main__":
    import json
    est = obtener_estado_enso()
    print(json.dumps(est, indent=2, ensure_ascii=False, default=str))
