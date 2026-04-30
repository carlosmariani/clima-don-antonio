"""
clima_api.py
Módulo de obtención de datos climáticos para PRevisor del Clima.
Usa Open-Meteo (modelos ECMWF, GFS-NOAA, ICON-DWD, JMA) como ensamble principal.
No requiere API key.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any


class ClimaAPI:
    """Cliente para obtener pronósticos y datos históricos de Open-Meteo."""

    URL_FORECAST = "https://api.open-meteo.com/v1/forecast"
    URL_SEASONAL = "https://seasonal-api.open-meteo.com/v1/seasonal"
    URL_HISTORICAL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PRevisor del Clima - Don Antonio SRL"
        })

    def _get_json(self, url, params, max_retries=4):
        """GET con reintentos automáticos para evitar 429 (rate limit)."""
        import time
        last_exc = None
        for intento in range(max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 429:
                    if intento < max_retries - 1:
                        time.sleep((intento + 1) * 2)
                        continue
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as e:
                last_exc = e
                if intento < max_retries - 1:
                    time.sleep((intento + 1) * 2)
                    continue
                raise
        raise last_exc

    # -------------------------------------------------------------------- #
    # Pronóstico de corto plazo (hasta 16 días)
    # -------------------------------------------------------------------- #
    def pronostico_15_dias(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Pronóstico diario de 16 días. Usa el ensamble de mejores modelos.
        Devuelve datos diarios: temp max/min, lluvia, viento, etc.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "precipitation_sum",
                "precipitation_probability_max",
                "rain_sum",
                "windspeed_10m_max",
                "windgusts_10m_max",
                "winddirection_10m_dominant",
                "shortwave_radiation_sum",
                "et0_fao_evapotranspiration",
                "uv_index_max",
                "sunshine_duration",
            ]),
            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "weathercode",
                "windspeed_10m",
            ]),
            "timezone": "America/Argentina/Buenos_Aires",
            "forecast_days": 16,
            "models": "best_match",
        }
        return self._get_json(self.URL_FORECAST, params)

    # -------------------------------------------------------------------- #
    # Pronóstico estacional (trimestral)
    # -------------------------------------------------------------------- #
    def pronostico_trimestral(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Pronóstico estacional (~9 meses) usando modelo CFSv2 de NOAA.
        Devuelve un agregado de los próximos 90 días.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "six_hourly": ",".join([
                "temperature_2m",
                "precipitation",
            ]),
            "timezone": "America/Argentina/Buenos_Aires",
            "forecast_days": 92,
        }
        try:
            data = self._get_json(self.URL_SEASONAL, params, max_retries=2)
            # Verificar que la respuesta tenga datos útiles
            if data.get("six_hourly") and data["six_hourly"].get("time"):
                return data
            # Sin datos: caer al fallback histórico
            return self._pronostico_trimestral_fallback(lat, lon)
        except Exception:
            return self._pronostico_trimestral_fallback(lat, lon)

    def _pronostico_trimestral_fallback(self, lat: float, lon: float) -> Dict[str, Any]:
        """Si la API estacional falla, usar normales históricas como referencia."""
        hoy = datetime.now()
        inicio = (hoy - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
        fin = (hoy - timedelta(days=365)).strftime("%Y-%m-%d")
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": inicio,
            "end_date": fin,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "America/Argentina/Buenos_Aires",
        }
        data = self._get_json(self.URL_HISTORICAL, params)
        data["_fallback"] = True
        return data

    # -------------------------------------------------------------------- #
    # Históricos (año pasado mismo período + normal climática)
    # -------------------------------------------------------------------- #
    def historico_periodo(self, lat: float, lon: float,
                          fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
        """Datos históricos diarios para un período arbitrario (formato YYYY-MM-DD)."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "precipitation_sum",
                "windspeed_10m_max",
            ]),
            "timezone": "America/Argentina/Buenos_Aires",
        }
        return self._get_json(self.URL_HISTORICAL, params)

    def comparativa_anio_pasado(self, lat: float, lon: float, dias: int = 15) -> Dict[str, Any]:
        """Datos del mismo período pero del año anterior, para comparar."""
        hoy = datetime.now()
        inicio = (hoy - timedelta(days=365)).strftime("%Y-%m-%d")
        fin = (hoy - timedelta(days=365) + timedelta(days=dias)).strftime("%Y-%m-%d")
        return self.historico_periodo(lat, lon, inicio, fin)

    def normal_climatica(self, lat: float, lon: float, dias: int = 15) -> Dict[str, Any]:
        """
        Calcula la 'normal climática' (promedio de últimos 5 años para el mismo período).
        """
        hoy = datetime.now()
        # Promediar los últimos 5 años para el mismo período del año
        registros = []
        for i in range(1, 6):
            inicio = (hoy - timedelta(days=365 * i)).strftime("%Y-%m-%d")
            fin = (hoy - timedelta(days=365 * i) + timedelta(days=dias)).strftime("%Y-%m-%d")
            try:
                d = self.historico_periodo(lat, lon, inicio, fin)
                registros.append(d)
            except Exception:
                continue
        return {"registros": registros, "anios_promediados": len(registros)}


if __name__ == "__main__":
    # Test rápido con Orán
    api = ClimaAPI()
    print("Probando API con Orán, Salta...")
    pron = api.pronostico_15_dias(-23.1369, -64.3275)
    print(f"  Pronóstico 15 días: OK ({len(pron['daily']['time'])} días)")
    hist = api.comparativa_anio_pasado(-23.1369, -64.3275)
    print(f"  Histórico año pasado: OK")
    print("Test completado.")
