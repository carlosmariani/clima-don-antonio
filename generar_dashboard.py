"""
generar_dashboard.py
Genera dashboard.html INTERACTIVO con el mismo estilo del PDF nuevo.
Los KPIs son clickeables (filtran las zonas), las zonas con alertas van arriba,
click en mapa o tabla rápida scrollea a la card de la zona.

Uso:
    python3 generar_dashboard.py
"""

import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from clima_api import ClimaAPI
from analisis import AnalizadorClima
from interpretacion import (
    calcular_semaforo, pictograma_clima, resumen_interpretativo,
    que_hacer_simple, comparativa_simple, tendencia_trimestral_simple,
)


def cargar_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def procesar_localidad(loc, api, analizador):
    try:
        pron = api.pronostico_15_dias(loc["lat"], loc["lon"])
        resumen = analizador.resumen_15_dias(pron)
        alertas = analizador.detectar_alertas(pron)
        ap = api.comparativa_anio_pasado(loc["lat"], loc["lon"])
        normal = api.normal_climatica(loc["lat"], loc["lon"])
        comp = analizador.comparativa(resumen, ap, normal)

        try:
            tr = api.pronostico_trimestral(loc["lat"], loc["lon"])
            resumen_t = analizador.resumen_trimestral(tr)
        except Exception:
            resumen_t = {"tipo": "no_disponible"}

        sem = calcular_semaforo(resumen, alertas)
        picto, picto_desc = pictograma_clima(resumen)
        interp = resumen_interpretativo(resumen, comp)
        comp_simple = comparativa_simple(resumen, comp)
        acciones = que_hacer_simple(resumen, alertas)
        tend = tendencia_trimestral_simple(resumen_t)

        return {
            "ok": True,
            "info": loc,
            "resumen": resumen,
            "alertas": alertas,
            "comparativa": comp,
            "trimestral": resumen_t,
            "semaforo": sem,
            "pictograma": {"emoji": picto, "descripcion": picto_desc},
            "interpretacion": interp,
            "comparativa_frase": comp_simple,
            "acciones": acciones,
            "tendencia": tend,
        }
    except Exception as e:
        return {"ok": False, "info": loc, "error": str(e)}


def recolectar_datos():
    cfg = cargar_config()
    api = ClimaAPI()
    analizador = AnalizadorClima(cfg["umbrales_alertas"])

    salida = {
        "empresa": cfg["empresa"],
        "fecha_actualizacion": datetime.now().isoformat(),
        "localidades": [],
    }

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(procesar_localidad, loc, api, analizador): loc
                for loc in cfg["localidades"]}
        resultados = []
        for f in as_completed(futs):
            r = f.result()
            if r["ok"]:
                print(f"  ✓ {r['info']['nombre']}")
                resultados.append(r)
            else:
                print(f"  ❌ {r['info']['nombre']}: {r['error']}")

    # Ordenar: ROJO primero, AMARILLO después, VERDE al final.
    # Dentro de cada grupo, mantener el orden del config.
    orden_cfg = {l["nombre"]: i for i, l in enumerate(cfg["localidades"])}
    nivel_peso = {"ROJO": 0, "AMARILLO": 1, "VERDE": 2}
    resultados.sort(key=lambda r: (
        nivel_peso.get(r["semaforo"]["nivel"], 9),
        orden_cfg.get(r["info"]["nombre"], 999)
    ))
    salida["localidades"] = resultados

    # Precios del MCBA: leer el JSON resumen que genera el workflow de precios
    # (si existe). Si no, dejar vacío y la sección no se muestra en el HTML.
    precios_path = os.path.join(os.path.dirname(__file__),
                                  "informes", "precios_hoy_resumen.json")
    if os.path.exists(precios_path):
        try:
            with open(precios_path, "r", encoding="utf-8") as f:
                salida["precios"] = json.load(f)
        except Exception:
            salida["precios"] = None
    else:
        salida["precios"] = None
    return salida


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clima Don Antonio</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --primario: #1B5E20;
  --primario-claro: #2E7D32;
  --secundario: #F9A825;
  --acento: #0D47A1;
  --rojo: #C62828;
  --naranja: #EF6C00;
  --azul: #1565C0;
  --gris: #555;
  --gris-claro: #f0f3f7;
  --fondo: #f5f7fa;
}
html { scroll-behavior: smooth; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--fondo); color: #222; line-height: 1.5;
}

/* === HEADER === */
.header {
  background: linear-gradient(135deg, var(--primario) 0%, var(--primario-claro) 100%);
  color: #fff; padding: 22px 32px;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; box-shadow: 0 2px 10px rgba(0,0,0,.1);
  position: sticky; top: 0; z-index: 100;
}
.header-brand { display: flex; align-items: center; gap: 16px; }
.logo-circle {
  width: 50px; height: 50px; background: #fff; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 26px;
}
.header h1 { font-size: 20px; margin-bottom: 2px; }
.header .subtitle { font-size: 12px; opacity: .9; }
.header-meta { font-size: 11px; opacity: .9; text-align: right; }
.header-meta strong { display: block; font-size: 13px; }

.container { max-width: 1400px; margin: 0 auto; padding: 22px; }

/* === ESTADO REGIONAL === */
.estado-regional {
  background: #fff; border-radius: 14px; padding: 22px 26px;
  margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,.07);
  display: flex; gap: 22px; align-items: center; flex-wrap: wrap;
  border-left: 6px solid var(--primario); cursor: pointer;
  transition: transform .15s, box-shadow .15s;
}
.estado-regional:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,.1); }
.estado-regional.alerta { border-left-color: var(--rojo); }
.estado-regional.warning { border-left-color: var(--naranja); }
.estado-regional .big-number {
  font-size: 56px; font-weight: 800; line-height: 1; color: var(--primario);
}
.estado-regional.alerta .big-number { color: var(--rojo); }
.estado-regional.warning .big-number { color: var(--naranja); }
.estado-regional .info { flex: 1; min-width: 240px; }
.estado-regional h2 { font-size: 22px; color: #222; margin-bottom: 4px; }
.estado-regional .sub { font-size: 13px; color: #666; }
.estado-regional .cta {
  font-size: 12px; color: var(--primario); margin-top: 6px; font-weight: 600;
  display: none;
}
.estado-regional:hover .cta { display: block; }

/* === KPI CARDS clickeables === */
.summary-bar {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
  gap: 12px; margin-bottom: 22px;
}
.stat {
  background: #fff; padding: 14px; border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06); text-align: center;
  cursor: pointer; transition: transform .15s, box-shadow .15s;
  border-top: 3px solid transparent;
}
.stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,.12);
}
.stat.activo {
  border-top-color: var(--primario);
  background: #fff;
  box-shadow: 0 0 0 2px var(--primario), 0 4px 14px rgba(27,94,32,.18);
}
.stat .label {
  font-size: 10px; color: #666; text-transform: uppercase;
  letter-spacing: .5px; margin-bottom: 4px; font-weight: 600;
}
.stat .value { font-size: 26px; font-weight: 700; color: var(--primario); line-height: 1; }
.stat .sub { font-size: 11px; color: #999; margin-top: 4px; }
.stat .click-hint {
  font-size: 9px; color: var(--primario); margin-top: 4px; opacity: 0;
  transition: opacity .15s; font-weight: 600;
}
.stat:hover .click-hint { opacity: 1; }
.stat.no-clic { cursor: default; }
.stat.no-clic:hover { transform: none; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.stat.no-clic .click-hint { display: none; }
.stat.verde .value { color: var(--primario); }
.stat.rojo .value { color: var(--rojo); }
.stat.amarillo .value { color: var(--naranja); }
.stat.azul .value { color: var(--azul); }

/* === SECCIONES === */
.section-title {
  font-size: 17px; font-weight: 700; color: var(--primario);
  margin: 14px 0 12px; padding-left: 10px;
  border-left: 4px solid var(--secundario);
  display: flex; align-items: center; gap: 8px;
}
.section-title .badge {
  background: var(--primario); color: #fff; font-size: 11px;
  padding: 2px 8px; border-radius: 10px; font-weight: 600;
}
.section-title .badge.rojo { background: var(--rojo); }
.section-title .badge.amarillo { background: var(--naranja); }

/* === TABLA QUICK-VIEW === */
.quick-table {
  background: #fff; border-radius: 10px; overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,.06); margin-bottom: 22px;
}
.quick-table table { width: 100%; border-collapse: collapse; }
.quick-table thead {
  background: var(--primario); color: #fff;
}
.quick-table th {
  text-align: left; padding: 10px 14px; font-size: 11px;
  font-weight: 600; letter-spacing: .3px;
}
.quick-table td {
  padding: 10px 14px; border-top: 1px solid #eee; font-size: 13px;
  vertical-align: middle;
}
.quick-table tr {
  cursor: pointer; transition: background-color .12s;
}
.quick-table tr:hover { background: #f5fbf5; }
.quick-table .nombre { font-weight: 600; color: var(--primario); }
.quick-table .nombre small { display: block; font-weight: 400; color: #888; font-size: 11px; }
.quick-table .est { text-align: center; font-size: 16px; }
.quick-table .num { text-align: center; font-weight: 600; }
.quick-table .frase { color: #555; font-size: 12px; }
.quick-table .ver-btn {
  display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 10px;
  background: var(--primario); color: #fff; opacity: 0;
  transition: opacity .12s; font-weight: 600;
}
.quick-table tr:hover .ver-btn { opacity: 1; }

/* === MAPA === */
#mapa {
  height: 320px; border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 22px;
}

/* === FILTROS === */
.filtros {
  background: #fff; padding: 12px 16px; border-radius: 10px;
  margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.06);
  display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
}
.filtros label { font-size: 12px; color: #555; font-weight: 600; }
.filtros input, .filtros select {
  padding: 7px 10px; border: 1px solid #ddd; border-radius: 6px;
  font-size: 13px; font-family: inherit;
}
.filtros .btn {
  background: var(--primario); color: #fff; padding: 7px 14px; border: none;
  border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
}
.filtros .btn:hover { background: var(--primario-claro); }
.filtros .btn-clear {
  background: #fff; color: var(--primario); border: 1px solid var(--primario);
}
.filtros .btn-clear:hover { background: var(--gris-claro); }
.filtros .contador {
  margin-left: auto; font-size: 12px; color: #555; font-weight: 600;
}
.filtros .contador strong { color: var(--primario); }

/* === CARDS === */
.cards-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(440px, 1fr));
  gap: 18px;
}
.card {
  background: #fff; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 6px rgba(0,0,0,.08);
  transition: box-shadow .15s, transform .15s;
  scroll-margin-top: 100px;
}
.card.highlighted {
  box-shadow: 0 0 0 3px var(--secundario), 0 4px 14px rgba(0,0,0,.12);
  animation: pulse 1.2s ease-in-out 2;
}
@keyframes pulse {
  0%,100% { box-shadow: 0 0 0 3px var(--secundario), 0 4px 14px rgba(0,0,0,.12); }
  50%     { box-shadow: 0 0 0 6px rgba(249,168,37,.45), 0 4px 14px rgba(0,0,0,.12); }
}
.card:hover { box-shadow: 0 4px 14px rgba(0,0,0,.12); }
.card-header-loc { padding: 14px 18px; background: #fafbfc; border-bottom: 1px solid #eee; }
.card-header-loc .loc-nombre { font-size: 18px; font-weight: 700; color: var(--primario); }
.card-header-loc .loc-meta { font-size: 11px; color: #888; margin-top: 2px; }

.semaforo-banner {
  padding: 14px 18px; color: #fff;
  display: flex; align-items: center; gap: 14px;
}
.semaforo-banner .emoji-grande { font-size: 36px; line-height: 1; }
.semaforo-banner .titulo {
  font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px;
}
.semaforo-banner .descripcion { font-size: 12px; opacity: .95; margin-top: 2px; }

.card-body { padding: 16px 18px; }
.interpretacion {
  font-size: 13px; color: #333; line-height: 1.55;
  background: #f7f9fb; padding: 10px 12px; border-radius: 8px;
  margin-bottom: 12px; border-left: 3px solid var(--azul);
}

.kpis {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 6px; margin-bottom: 12px;
}
.kpi {
  text-align: center; padding: 8px 4px; background: #fafbfc;
  border-radius: 8px; border: 1px solid #eee;
}
.kpi .v { font-size: 19px; font-weight: 800; color: var(--primario); line-height: 1; }
.kpi .v.rojo { color: var(--rojo); }
.kpi .v.azul { color: var(--azul); }
.kpi .l {
  font-size: 8.5px; color: #888; text-transform: uppercase;
  letter-spacing: .3px; margin-top: 4px; line-height: 1.2;
}

.comparativa-frase {
  font-size: 12px; color: var(--acento); font-style: italic; margin-bottom: 10px;
}
.chart-container { height: 170px; margin-bottom: 12px; position: relative; }

.que-hacer { border-top: 1px solid #eee; padding-top: 12px; margin-top: 4px; }
.que-hacer h3 {
  font-size: 13px; font-weight: 700; color: var(--primario); margin-bottom: 8px;
}
.accion {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 6px 0; border-bottom: 1px dashed #f0f0f0;
}
.accion:last-child { border-bottom: none; }
.accion-icono { font-size: 22px; width: 30px; text-align: center; flex-shrink: 0; }
.accion-tema {
  font-size: 10.5px; font-weight: 700; color: var(--primario);
  text-transform: uppercase; letter-spacing: .3px;
}
.accion-titulo { font-size: 13px; font-weight: 600; color: #222; margin: 1px 0 1px; }
.accion-porque { font-size: 11px; color: #666; line-height: 1.4; }

/* === TRIMESTRAL === */
.precios-section {
  background: #fff; padding: 18px 22px; border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06); margin-top: 22px;
}
.precios-section h2 { color: var(--primario); font-size: 17px; }
.precios-section table tbody tr { border-bottom: 1px solid #eee; }
.precios-section table tbody tr:nth-child(even) { background: #fafbfc; }
.precios-section table td { padding: 7px 10px; }
.precios-section .var-up { color: var(--rojo); font-weight: 600; }
.precios-section .var-down { color: var(--primario); font-weight: 600; }
.precios-section .var-flat { color: #888; }

.trimestral-section {
  background: #fff; padding: 18px 22px; border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06); margin-top: 22px;
}
.trimestral-section h2 { color: var(--primario); margin-bottom: 6px; font-size: 17px; }
.trimestral-section .desc { font-size: 12px; color: #555; margin-bottom: 14px; }
.trimestral-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}
.trimestral-card {
  border: 1px solid #eee; border-radius: 8px;
  padding: 12px 14px; background: #fafbfc;
}
.trimestral-card .zona {
  font-size: 14px; font-weight: 700; color: var(--primario); margin-bottom: 4px;
}
.trimestral-card .icono { font-size: 22px; margin-right: 6px; }
.trimestral-card .desc { font-size: 12px; color: #444; line-height: 1.5; margin-bottom: 6px; }
.trimestral-card .rec {
  font-size: 11px; color: #555; padding: 6px 8px;
  background: #fff8e1; border-left: 3px solid var(--secundario);
  border-radius: 4px;
}

.disclaimer {
  background: #fff8e1; border-left: 4px solid var(--secundario);
  padding: 12px 16px; margin: 22px 0 12px; border-radius: 6px;
  font-size: 12px; color: #5D4037; line-height: 1.6;
}

footer {
  margin-top: 28px; padding: 18px; text-align: center;
  color: #888; font-size: 11px; border-top: 1px solid #ddd; background: #fff;
}

/* Botón flotante "volver arriba" */
.btn-top {
  position: fixed; right: 24px; bottom: 24px;
  background: var(--primario); color: #fff; border: none;
  width: 44px; height: 44px; border-radius: 50%; cursor: pointer;
  font-size: 20px; box-shadow: 0 3px 12px rgba(0,0,0,.25);
  opacity: 0; pointer-events: none; transition: opacity .2s;
  z-index: 50;
}
.btn-top.visible { opacity: 1; pointer-events: auto; }
.btn-top:hover { background: var(--primario-claro); }

@media (max-width: 700px) {
  .header { padding: 14px; flex-direction: column; align-items: flex-start; }
  .header-meta { text-align: left; margin-top: 8px; }
  .container { padding: 12px; }
  .cards-grid { grid-template-columns: 1fr; }
  .quick-table { overflow-x: auto; }
}
</style>
</head>
<body>

<div class="header">
  <div class="header-brand">
    <div class="logo-circle">🌿</div>
    <div>
      <h1 id="empresa-nombre">Don Antonio SRL</h1>
      <div class="subtitle">PRevisor del Clima — Insumos Agrícolas NOA</div>
    </div>
  </div>
  <div class="header-meta">
    <strong>Última actualización</strong>
    <span id="fecha-act">—</span>
  </div>
</div>

<div class="container">

  <!-- Estado regional grande, clickeable -->
  <div id="estado-regional" class="estado-regional"
       title="Click para ver las zonas que requieren atención"></div>

  <!-- KPIs clickeables -->
  <div class="summary-bar" id="summary"></div>

  <!-- Vista rápida tabular - click en fila scrollea a la card -->
  <h2 class="section-title">📋 Vista rápida — click en una zona para ir a su detalle</h2>
  <div class="quick-table">
    <table id="tabla-quick"><thead><tr>
      <th>Zona</th><th>Estado</th><th>T.máx</th><th>T.mín</th><th>Lluvia 15d</th>
      <th>En pocas palabras</th><th></th>
    </tr></thead><tbody></tbody></table>
  </div>

  <!-- Mapa con marcadores clickeables -->
  <h2 class="section-title">📍 Mapa — click en un punto para ir a su detalle</h2>
  <div id="mapa"></div>

  <!-- Filtros -->
  <div class="filtros">
    <label>Buscar:</label>
    <input type="text" id="filtro-texto" placeholder="Nombre de localidad…" />
    <label>Provincia:</label>
    <select id="filtro-prov"><option value="">Todas</option></select>
    <label>Mostrar:</label>
    <select id="filtro-alertas">
      <option value="todas">Todas</option>
      <option value="con-alertas">Con alertas</option>
      <option value="solo-helada">Riesgo de helada</option>
      <option value="solo-lluvia">Lluvia fuerte</option>
    </select>
    <button class="btn btn-clear" onclick="limpiarFiltros()">Limpiar filtros</button>
    <span class="contador">Mostrando <strong id="contador-num">—</strong> zonas</span>
  </div>

  <!-- Cards de detalle -->
  <h2 class="section-title" id="titulo-cards">🌤️ Detalle por zona</h2>
  <div id="cards" class="cards-grid"></div>

  <!-- Precios MCBA (solo si hay datos) -->
  <div id="precios-section" class="precios-section" style="display:none">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px">
      <div>
        <h2 style="margin:0">📊 Precios mayoristas — Mercado Central</h2>
        <div style="font-size:12px; color:#555; margin-top:2px" id="precios-fecha">—</div>
      </div>
      <a href="precios_hoy.pdf" target="_blank" style="background:var(--primario);color:#fff;padding:9px 18px;text-decoration:none;border-radius:6px;font-weight:600;font-size:13px">
        📄 Ver PDF completo
      </a>
    </div>
    <div id="precios-resumen" style="font-size:13px; color:#333; line-height:1.55; margin:12px 0 14px 0; padding:10px 14px; background:#f7f9fb; border-radius:8px; border-left:3px solid var(--azul)"></div>
    <div style="overflow-x:auto">
      <table id="tabla-precios" style="width:100%; border-collapse:collapse; font-size:12.5px; min-width:560px">
        <thead style="background:var(--primario); color:#fff">
          <tr>
            <th style="padding:8px 10px; text-align:left">Producto</th>
            <th style="padding:8px 10px; text-align:left">Procedencia · Envase</th>
            <th style="padding:8px 10px; text-align:right">$ Medio (bulto)</th>
            <th style="padding:8px 10px; text-align:center">VS Ayer</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
    <div style="font-size:10.5px; color:#888; margin-top:8px; font-style:italic">
      * Procedencia Buenos Aires — referencia cuando no hubo cotización de Salta o Jujuy ese día.
      Datos del MCBA. Se actualizan automáticamente de lunes a viernes.
    </div>
  </div>

  <!-- Trimestral -->
  <div class="trimestral-section">
    <h2>📅 Tendencia para los próximos meses</h2>
    <div class="desc">Perspectiva orientativa — útil para planificar campañas.</div>
    <div id="trimestral" class="trimestral-grid"></div>
  </div>

  <div class="disclaimer">
    <strong>⚠️ Importante:</strong> Los pronósticos son inherentemente probabilísticos.
    1-3 días: ~85% de confiabilidad · 7-15 días: ~65-70% · trimestral: solo orientativo.
    Fuentes: Open-Meteo (ECMWF, GFS-NOAA, ICON-DWD, JMA), SMN Argentina, INTA.
  </div>

</div>

<footer>
  <div id="footer-empresa">Don Antonio SRL — Insumos Agrícolas para el sector hortícola</div>
</footer>

<button class="btn-top" id="btn-top" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="Volver arriba">↑</button>

<script>
const DATOS = __DATOS__;
let chartsCreados = [];
let mapMarkers = {};

function init() {
  document.getElementById("empresa-nombre").textContent = DATOS.empresa.nombre;
  document.getElementById("footer-empresa").textContent =
    DATOS.empresa.nombre + " — " + DATOS.empresa.rubro;
  document.getElementById("fecha-act").textContent =
    new Date(DATOS.fecha_actualizacion).toLocaleString("es-AR");

  renderEstadoRegional();
  renderResumen();
  renderQuickTable();
  renderMapa();
  renderFiltros();
  renderCards(DATOS.localidades);
  renderTrimestral();
  renderPrecios();

  document.getElementById("filtro-texto").addEventListener("input", aplicarFiltros);
  document.getElementById("filtro-prov").addEventListener("change", aplicarFiltros);
  document.getElementById("filtro-alertas").addEventListener("change", aplicarFiltros);

  // Botón "volver arriba" cuando scrolleás
  window.addEventListener("scroll", () => {
    const btn = document.getElementById("btn-top");
    if (window.scrollY > 400) btn.classList.add("visible");
    else btn.classList.remove("visible");
  });
}

function renderEstadoRegional() {
  const total = DATOS.localidades.length;
  const rojas = DATOS.localidades.filter(l => l.semaforo.nivel === "ROJO").length;
  const amarillas = DATOS.localidades.filter(l => l.semaforo.nivel === "AMARILLO").length;
  const verdes = DATOS.localidades.filter(l => l.semaforo.nivel === "VERDE").length;

  let clase = "", texto, num, sub, accion;
  if (rojas > 0) {
    clase = "alerta"; num = rojas;
    texto = "Localidad" + (rojas !== 1 ? "es" : "") + " con eventos extremos";
    sub = "Requieren atención inmediata. Click acá para ver el detalle.";
    accion = () => filtrarYScroll("con-alertas");
  } else if (amarillas > 0) {
    clase = "warning"; num = amarillas;
    texto = "Localidad" + (amarillas !== 1 ? "es" : "") + " con alertas a considerar";
    sub = "El resto en condiciones normales. Click acá para ver el detalle.";
    accion = () => filtrarYScroll("con-alertas");
  } else {
    num = verdes;
    texto = "Todas las zonas en condiciones normales";
    sub = "Sin eventos extremos previstos. Hacé click para ver el detalle de las zonas.";
    accion = () => filtrarYScroll("todas");
  }

  const div = document.getElementById("estado-regional");
  div.className = "estado-regional " + clase;
  div.innerHTML = `
    <div class="big-number">${num}</div>
    <div class="info">
      <h2>${texto}</h2>
      <div class="sub">${sub}</div>
      <div class="cta">→ Click para ver las zonas</div>
    </div>
  `;
  div.onclick = accion;
}

function renderResumen() {
  const total = DATOS.localidades.length;
  const con_helada = DATOS.localidades.filter(l =>
    l.alertas.some(a => a.tipo.toLowerCase().includes("helada"))).length;
  const con_lluvia = DATOS.localidades.filter(l =>
    l.alertas.some(a => a.tipo === "Lluvia intensa")).length;
  const con_alerta = DATOS.localidades.filter(l => l.alertas.length > 0).length;
  const tmax = Math.max(...DATOS.localidades.map(l => l.resumen.temp_max_absoluta));
  const tmin = Math.min(...DATOS.localidades.map(l => l.resumen.temp_min_absoluta));
  const lluvia_max = Math.max(...DATOS.localidades.map(l => l.resumen.lluvia_total_mm));

  const stats = [
    {clase: 'verde no-clic', label: 'Localidades', value: total, sub: 'monitoreadas'},
    {clase: con_alerta ? 'amarillo' : 'verde no-clic',
     label: 'Con alertas', value: con_alerta,
     sub: con_alerta ? 'click para ver' : 'sin alertas',
     hint: con_alerta ? '→ Ver zonas' : '',
     filter: con_alerta ? 'con-alertas' : null},
    {clase: con_helada ? 'azul' : 'verde no-clic',
     label: 'Riesgo helada', value: con_helada,
     sub: con_helada ? 'click para ver' : 'sin riesgo',
     hint: con_helada ? '→ Ver zonas' : '',
     filter: con_helada ? 'solo-helada' : null},
    {clase: con_lluvia ? 'amarillo' : 'verde no-clic',
     label: 'Lluvia fuerte', value: con_lluvia,
     sub: con_lluvia ? 'click para ver' : 'sin alerta',
     hint: con_lluvia ? '→ Ver zonas' : '',
     filter: con_lluvia ? 'solo-lluvia' : null},
    {clase: 'rojo no-clic', label: 'Tmáx Regional', value: tmax + '°', sub: 'algún día'},
    {clase: 'azul no-clic', label: 'Tmín Regional', value: tmin + '°', sub: 'algún día'},
    {clase: 'azul no-clic', label: 'Mayor lluvia', value: lluvia_max + 'mm', sub: 'en 15 días'},
  ];

  document.getElementById("summary").innerHTML = stats.map((s, i) => `
    <div class="stat ${s.clase}" ${s.filter ? `data-filter="${s.filter}"` : ''}>
      <div class="label">${s.label}</div>
      <div class="value">${s.value}</div>
      <div class="sub">${s.sub}</div>
      <div class="click-hint">${s.hint || ''}</div>
    </div>
  `).join("");

  // Atachar click handlers a los KPIs filtrables
  document.querySelectorAll(".stat[data-filter]").forEach(el => {
    el.addEventListener("click", () => {
      const f = el.getAttribute("data-filter");
      filtrarYScroll(f);
    });
  });
}

function filtrarYScroll(filtro) {
  document.getElementById("filtro-alertas").value = filtro;
  document.getElementById("filtro-texto").value = "";
  document.getElementById("filtro-prov").value = "";
  aplicarFiltros();
  // Scroll a la sección de cards
  setTimeout(() => {
    document.getElementById("titulo-cards").scrollIntoView({ behavior: "smooth", block: "start" });
  }, 50);
}

function limpiarFiltros() {
  document.getElementById("filtro-texto").value = "";
  document.getElementById("filtro-prov").value = "";
  document.getElementById("filtro-alertas").value = "todas";
  aplicarFiltros();
}

function renderQuickTable() {
  const tbody = document.querySelector("#tabla-quick tbody");
  tbody.innerHTML = DATOS.localidades.map(l => {
    const sem = l.semaforo;
    const r = l.resumen;
    return `
      <tr data-zona="${slug(l.info.nombre)}">
        <td class="nombre">${l.info.nombre}<small>${l.info.provincia}</small></td>
        <td class="est">${sem.emoji}</td>
        <td class="num">${Math.round(r.temp_max_promedio)}°</td>
        <td class="num">${Math.round(r.temp_min_promedio)}°</td>
        <td class="num">${Math.round(r.lluvia_total_mm)} mm</td>
        <td class="frase">${fraseCorta(l)}</td>
        <td><span class="ver-btn">Ver →</span></td>
      </tr>
    `;
  }).join("");
  tbody.querySelectorAll("tr").forEach(tr => {
    tr.addEventListener("click", () => {
      const z = tr.getAttribute("data-zona");
      irACard(z);
    });
  });
}

function fraseCorta(l) {
  const r = l.resumen;
  if (l.alertas.some(a => a.tipo === "Riesgo de helada")) return "❄️ Riesgo de helada — preparar protección";
  if (l.alertas.some(a => a.tipo === "Calor extremo")) return "🌡️ Calor extremo — reforzar riego";
  if (l.alertas.some(a => a.tipo === "Lluvia intensa")) return "🌧️ Lluvia fuerte — revisar drenajes";
  if (l.alertas.some(a => a.tipo === "Período seco prolongado")) return "☀️ Período seco — asegurar riego";
  if (l.alertas.some(a => a.tipo === "Viento fuerte")) return "💨 Viento fuerte — suspender pulverizaciones";
  if (r.lluvia_total_mm > 60) return "🌧️ Lluvioso";
  if (r.temp_min_absoluta <= 7) return "🌤️ Días frescos";
  return "🟢 Sin novedades";
}

function slug(s) {
  return s.toLowerCase().replace(/[^a-z0-9]/g, '-');
}

function irACard(zonaSlug) {
  // Si está oculta por filtro, primero limpiamos filtros
  const card = document.querySelector(`.card[data-zona="${zonaSlug}"]`);
  if (!card || card.style.display === "none") {
    limpiarFiltros();
  }
  setTimeout(() => {
    const c = document.querySelector(`.card[data-zona="${zonaSlug}"]`);
    if (c) {
      c.scrollIntoView({ behavior: "smooth", block: "start" });
      c.classList.add("highlighted");
      setTimeout(() => c.classList.remove("highlighted"), 2500);
    }
  }, 100);
}

function renderMapa() {
  const map = L.map("mapa").setView([-23.7, -64.5], 8);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap', maxZoom: 18
  }).addTo(map);

  DATOS.localidades.forEach(l => {
    const color = l.semaforo.color_hex;
    const icon = L.divIcon({
      className: "custom-marker",
      html: `<div style="background:${color}; color:#fff; width:32px; height:32px;
        border-radius:50%; display:flex; align-items:center; justify-content:center;
        font-weight:700; font-size:12px; border:3px solid #fff;
        box-shadow:0 2px 6px rgba(0,0,0,.4); cursor:pointer">${l.alertas.length}</div>`,
      iconSize: [32, 32], iconAnchor: [16, 16],
    });
    const marker = L.marker([l.info.lat, l.info.lon], { icon }).addTo(map);
    marker.bindPopup(`
      <div style="text-align:center">
        <strong style="color:#1B5E20; font-size:14px">${l.info.nombre}</strong><br/>
        <small>${l.info.provincia} · ${l.info.altitud}m</small><br/>
        <span style="font-size:18px">${l.semaforo.emoji}</span> <b>${l.semaforo.titulo}</b><br/>
        Tmax: <b>${l.resumen.temp_max_promedio}°</b> · Tmin: <b>${l.resumen.temp_min_promedio}°</b><br/>
        Lluvia: <b>${l.resumen.lluvia_total_mm} mm</b><br/>
        <button onclick="irACard('${slug(l.info.nombre)}')"
          style="margin-top:6px; background:#1B5E20; color:#fff; border:none;
          padding:5px 12px; border-radius:6px; cursor:pointer; font-weight:600;">
          Ver detalle →
        </button>
      </div>
    `);
    mapMarkers[slug(l.info.nombre)] = marker;
  });
}

function renderFiltros() {
  const provs = [...new Set(DATOS.localidades.map(l => l.info.provincia))].sort();
  const sel = document.getElementById("filtro-prov");
  provs.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p; opt.textContent = p;
    sel.appendChild(opt);
  });
}

function aplicarFiltros() {
  const txt = document.getElementById("filtro-texto").value.toLowerCase();
  const prov = document.getElementById("filtro-prov").value;
  const alertas = document.getElementById("filtro-alertas").value;

  // Highlight del KPI activo
  document.querySelectorAll(".stat[data-filter]").forEach(el => {
    if (el.getAttribute("data-filter") === alertas) el.classList.add("activo");
    else el.classList.remove("activo");
  });

  let lista = DATOS.localidades.filter(l => {
    if (txt && !l.info.nombre.toLowerCase().includes(txt)) return false;
    if (prov && l.info.provincia !== prov) return false;
    if (alertas === "con-alertas" && l.alertas.length === 0) return false;
    if (alertas === "solo-helada" &&
      !l.alertas.some(a => a.tipo.toLowerCase().includes("helada"))) return false;
    if (alertas === "solo-lluvia" &&
      !l.alertas.some(a => a.tipo === "Lluvia intensa")) return false;
    return true;
  });
  renderCards(lista);

  // Actualizar contador y título
  document.getElementById("contador-num").textContent = `${lista.length} de ${DATOS.localidades.length}`;
  let t = "🌤️ Detalle por zona";
  if (alertas === "con-alertas") t = "⚠️ Zonas con alertas";
  else if (alertas === "solo-helada") t = "❄️ Zonas con riesgo de helada";
  else if (alertas === "solo-lluvia") t = "🌧️ Zonas con lluvia fuerte";
  document.getElementById("titulo-cards").innerHTML =
    t + ` <span class="badge ${alertas !== 'todas' ? 'amarillo' : ''}">${lista.length}</span>`;
}

function renderCards(lista) {
  chartsCreados.forEach(c => { try { c.destroy(); } catch (e) {} });
  chartsCreados = [];

  const cont = document.getElementById("cards");
  if (!lista.length) {
    cont.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:#888;">No hay localidades que coincidan con el filtro. <a href="#" onclick="limpiarFiltros();return false">Limpiar filtros</a></div>';
    document.getElementById("contador-num").textContent = '0 de ' + DATOS.localidades.length;
    return;
  }

  cont.innerHTML = lista.map((l, idx) => {
    const r = l.resumen;
    const sem = l.semaforo;
    const picto = l.pictograma;

    const colTmax = r.temp_max_promedio >= 33 ? "rojo" : "";
    const colTmin = r.temp_min_promedio <= 5 ? "azul" : "";
    const colLluvia = r.lluvia_total_mm >= 30 ? "azul" : "";

    const accionesHTML = l.acciones.map(a => `
      <div class="accion">
        <div class="accion-icono">${a.icono}</div>
        <div>
          <div class="accion-tema">${a.tema}</div>
          <div class="accion-titulo">${a.accion}</div>
          <div class="accion-porque">${a.porque}</div>
        </div>
      </div>
    `).join("");

    return `
      <div class="card" data-zona="${slug(l.info.nombre)}">
        <div class="card-header-loc">
          <div class="loc-nombre">📍 ${l.info.nombre}</div>
          <div class="loc-meta">${l.info.provincia} · ${l.info.altitud}m · ${r.fecha_inicio} al ${r.fecha_fin}</div>
        </div>
        <div class="semaforo-banner" style="background:${sem.color_hex}">
          <div class="emoji-grande">${sem.emoji} ${picto.emoji}</div>
          <div>
            <div class="titulo">${sem.titulo}</div>
            <div class="descripcion">${picto.descripcion}</div>
          </div>
        </div>
        <div class="card-body">
          <div class="interpretacion">${l.interpretacion}</div>
          <div class="kpis">
            <div class="kpi"><div class="v ${colTmax}">${Math.round(r.temp_max_promedio)}°</div><div class="l">TEMP. MÁX<br/>promedio</div></div>
            <div class="kpi"><div class="v ${colTmin}">${Math.round(r.temp_min_promedio)}°</div><div class="l">TEMP. MÍN<br/>promedio</div></div>
            <div class="kpi"><div class="v ${colLluvia}">${Math.round(r.lluvia_total_mm)}mm</div><div class="l">LLUVIA<br/>15 días</div></div>
            <div class="kpi"><div class="v">${r.lluvia_dias_con_lluvia}</div><div class="l">DÍAS<br/>con lluvia</div></div>
          </div>
          <div class="comparativa-frase">${l.comparativa_frase}</div>
          <div class="chart-container">
            <canvas id="chart-${idx}"></canvas>
          </div>
          <div class="que-hacer">
            <h3>📋 ¿Qué hacer esta quincena?</h3>
            ${accionesHTML}
          </div>
        </div>
      </div>
    `;
  }).join("");

  setTimeout(() => {
    lista.forEach((l, idx) => {
      const ctx = document.getElementById(`chart-${idx}`);
      if (!ctx) return;
      const fechas = l.resumen.diario.fecha.map(f => {
        const d = new Date(f);
        return `${d.getDate()}/${d.getMonth() + 1}`;
      });
      const tmax = l.resumen.diario.tmax;
      const tmin = l.resumen.diario.tmin;
      const lluvia = l.resumen.diario.lluvia;
      const lluviaMax = Math.max(5, ...lluvia) * 1.3;
      const tempMax = Math.max(...tmax) + 3;
      const tempMin = Math.min(...tmin) - 3;
      const chart = new Chart(ctx, {
        type: "line",
        data: {
          labels: fechas,
          datasets: [
            { label: "Tmáx (°C)", data: tmax, borderColor: "#C62828",
              backgroundColor: "rgba(198,40,40,.1)", tension: .3,
              pointRadius: 3, pointBackgroundColor: "#C62828",
              borderWidth: 2, yAxisID: "y", order: 1 },
            { label: "Tmín (°C)", data: tmin, borderColor: "#1565C0",
              backgroundColor: "rgba(21,101,192,.1)", tension: .3,
              pointRadius: 3, pointBackgroundColor: "#1565C0",
              borderWidth: 2, yAxisID: "y", order: 1 },
            { type: "bar", label: "Lluvia (mm)", data: lluvia,
              backgroundColor: "rgba(2,119,189,.55)",
              borderColor: "rgba(2,119,189,.8)", borderWidth: 1,
              yAxisID: "y1", order: 2 },
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: true, position: 'bottom',
              labels: { font: { size: 10 }, boxWidth: 12, padding: 8 } },
            tooltip: { callbacks: { label: (ctx) => {
              const v = ctx.parsed.y;
              if (ctx.dataset.label.includes("Lluvia")) return `Lluvia: ${v.toFixed(1)} mm`;
              return `${ctx.dataset.label}: ${v.toFixed(1)}°C`;
            } } }
          },
          scales: {
            x: { ticks: { font: { size: 9 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
                 grid: { display: false } },
            y: { type: 'linear', position: 'left',
              min: Math.floor(tempMin), max: Math.ceil(tempMax),
              ticks: { font: { size: 9 }, callback: (v) => v + "°" },
              title: { display: true, text: 'Temperatura', font: { size: 10 } },
              grid: { color: 'rgba(0,0,0,.05)' } },
            y1: { type: 'linear', position: 'right',
              min: 0, max: Math.ceil(lluviaMax),
              ticks: { font: { size: 9 }, callback: (v) => v + "mm" },
              title: { display: true, text: 'Lluvia', font: { size: 10 } },
              grid: { drawOnChartArea: false } },
          }
        }
      });
      chartsCreados.push(chart);
    });
  }, 50);
}

function renderTrimestral() {
  const cont = document.getElementById("trimestral");
  cont.innerHTML = DATOS.localidades.map(l => {
    const t = l.tendencia;
    if (!t.disponible) {
      return `<div class="trimestral-card">
        <div class="zona">${l.info.nombre}</div>
        <div class="desc">${t.emoji} ${t.mensaje || 'No disponible'}</div>
      </div>`;
    }
    return `<div class="trimestral-card">
      <div class="zona">${l.info.nombre} <span style="font-weight:400;color:#888;font-size:11px">(${l.info.provincia})</span></div>
      <div class="desc"><span class="icono">${t.emoji}</span>${t.descripcion}</div>
      <div class="rec">💡 ${t.recomendacion}</div>
    </div>`;
  }).join("");
}

function renderPrecios() {
  const precios = DATOS.precios;
  const sec = document.getElementById("precios-section");
  if (!precios || !precios.productos_top || precios.productos_top.length === 0) {
    sec.style.display = "none";
    return;
  }
  sec.style.display = "block";
  document.getElementById("precios-fecha").textContent = "Datos del " + (precios.fecha_str || "—");
  // Resumen
  document.getElementById("precios-resumen").innerHTML = precios.texto_resumen || "";
  // Tabla
  const tbody = document.querySelector("#tabla-precios tbody");
  const formatPrecio = (n) =>
    "$" + Math.round(n).toLocaleString("es-AR").replace(/,/g, ".");
  tbody.innerHTML = precios.productos_top.map(p => {
    let varHtml = '<span class="var-flat">—</span>';
    if (p.variacion !== null && p.variacion !== undefined) {
      const v = p.variacion;
      if (v > 5)       varHtml = `<span class="var-up">↑ ${v.toFixed(0)}%</span>`;
      else if (v < -5) varHtml = `<span class="var-down">↓ ${v.toFixed(0)}%</span>`;
      else             varHtml = `<span class="var-flat">≈ ${v.toFixed(0)}%</span>`;
    }
    const procEnvase = `${p.procedencia} · ${p.envase} ${p.kg_bulto ? Math.round(p.kg_bulto) + 'kg' : ''}`;
    return `
      <tr>
        <td><b>${p.especie}</b> <span style="color:#888">${p.variedad || ''}</span></td>
        <td style="font-size:11.5px;color:#666">${procEnvase}</td>
        <td style="text-align:right"><b>${formatPrecio(p.precio)}</b></td>
        <td style="text-align:center">${varHtml}</td>
      </tr>
    `;
  }).join("");
}

init();
</script>
</body>
</html>
"""


def generar_html(datos: dict, output: str = "dashboard.html"):
    data_json = json.dumps(datos, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__DATOS__", data_json)
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    return output


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    print("=" * 60)
    print("  Generando dashboard HTML — Don Antonio SRL")
    print("=" * 60)
    print("\nRecolectando datos climáticos en paralelo...")
    datos = recolectar_datos()
    print(f"\n→ {len(datos['localidades'])} localidades procesadas.")
    print("→ Generando dashboard.html...")
    out = generar_html(datos)
    full_path = os.path.abspath(out)
    print(f"\n✓ Dashboard generado: {full_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
