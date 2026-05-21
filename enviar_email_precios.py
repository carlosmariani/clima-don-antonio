"""
enviar_email_precios.py
Envía un email vía Resend con resumen de precios + link al PDF público.

Uso (desde GitHub Action):
    RESEND_API_KEY=re_xxx python3 enviar_email_precios.py

Lee:
  - config.json para destinatario
  - informes/precios_hoy_resumen.json (generado por generar_precios.py)

Email tiene:
  - HTML con resumen ejecutivo del día
  - Tabla simple de precios destacados
  - Mini-tabla del clima de mañana + alertas críticas si hay
  - Link grande "📄 Ver PDF completo"
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

TZ_AR = timezone(timedelta(hours=-3))


def _ahora_ar() -> datetime:
    return datetime.now(TZ_AR).replace(tzinfo=None)


def cargar_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_resumen(path: str = "informes/precios_hoy_resumen.json") -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def construir_html(empresa: dict, resumen: dict, url_pdf: str) -> str:
    """Genera el HTML del email con resumen visual."""
    fecha_str = resumen.get("fecha_str", "")
    n_total = resumen.get("n_cotizaciones", 0)
    productos_top = resumen.get("productos_top", [])
    # Compatibilidad: aceptar tanto clima_48h (nuevo) como clima_manana (viejo)
    clima = resumen.get("clima_48h") or resumen.get("clima_manana", [])
    alertas_clima = [c for c in clima if c.get("alerta")]
    alertas_7d = resumen.get("alertas_7d") or resumen.get("alertas_15d", [])

    # Estilos inline (algunos clientes de email no soportan <style>)
    bg = "#1B5E20"
    accent = "#F9A825"
    rojo = "#C62828"
    naranja = "#EF6C00"

    productos_html = ""
    for p in productos_top[:8]:  # top 8 productos
        var_str = ""
        if p.get("variacion") is not None:
            v = p["variacion"]
            if v > 5:
                var_str = f' <span style="color:{rojo}">↑ {v:+.0f}%</span>'
            elif v < -5:
                var_str = f' <span style="color:#2E7D32">↓ {v:+.0f}%</span>'
        productos_html += f"""
          <tr>
            <td style="padding:6px 10px;border-bottom:1px solid #eee">
              <b>{p['especie'].capitalize()}</b> {p.get('variedad', '')}
              <br><span style="font-size:11px;color:#888">{p.get('procedencia', '')} · {p.get('envase', '')} {p.get('kg_bulto', 0):.0f}kg</span>
            </td>
            <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right">
              <b>${p['precio']:,.0f}</b>{var_str}
            </td>
          </tr>
        """.replace(",", ".")

    alerta_box = ""
    if alertas_clima:
        items = "".join(
            f"<li><b>{c['zona']}</b> ({c['provincia']}): {c['alerta']}</li>"
            for c in alertas_clima
        )
        alerta_box = f"""
        <div style="background:#FFEBEE;border-left:4px solid {rojo};padding:14px 18px;margin:16px 0;border-radius:4px">
          <b style="color:{rojo}">⚠️ Alertas críticas para mañana</b>
          <ul style="margin:6px 0 0 0;padding-left:20px;color:#5D4037">{items}</ul>
        </div>
        """

    # Banner amarillo si los datos están atrasados (MCBA no publicó hoy)
    aviso_atraso = ""
    dias_atraso = resumen.get("dias_atraso", 0)
    if dias_atraso >= 1:
        if dias_atraso == 1:
            txt = (f"<b>Datos del día anterior ({fecha_str}).</b> "
                   "El Mercado Central aún no publicó los datos de hoy.")
        else:
            txt = (f"<b>Datos atrasados — última publicación: {fecha_str}</b> "
                   f"(hace {dias_atraso} días). El MCBA puede tardar al cambiar de "
                   "mes o por feriados. Se actualiza automáticamente.")
        aviso_atraso = f"""
        <div style="background:#FFF8E1;border-left:4px solid {accent};padding:14px 18px;margin:16px 0;border-radius:4px;color:#5D4037">
          ⚠️ {txt}
        </div>
        """

    clima_filas = ""
    for c in clima:
        bg_row = "#FFF3E0" if c.get("alerta") else "#fff"
        # Si no hay datos de pasado mañana, usar mañana como fallback
        tmax_p = c.get("tmax_pasado", c.get("tmax", 0))
        tmin_p = c.get("tmin_pasado", c.get("tmin", 0))
        lluvia_p = c.get("lluvia_pasado", c.get("lluvia_mm", 0))
        clima_filas += f"""
        <tr style="background:{bg_row}">
          <td style="padding:5px 8px;border-bottom:1px solid #eee">
            <b>{c['zona']}</b><br><span style="font-size:10px;color:#888">{c['provincia']}</span>
          </td>
          <td style="padding:5px 6px;border-bottom:1px solid #eee;text-align:center">{c.get('tmax', 0):.0f}°</td>
          <td style="padding:5px 6px;border-bottom:1px solid #eee;text-align:center">{c.get('tmin', 0):.0f}°</td>
          <td style="padding:5px 6px;border-bottom:1px solid #eee;text-align:center">{c.get('lluvia_mm', 0):.0f} mm</td>
          <td style="padding:5px 6px;border-bottom:1px solid #eee;text-align:center;border-left:2px solid #0D47A1">{tmax_p:.0f}°</td>
          <td style="padding:5px 6px;border-bottom:1px solid #eee;text-align:center">{tmin_p:.0f}°</td>
          <td style="padding:5px 6px;border-bottom:1px solid #eee;text-align:center">{lluvia_p:.0f} mm</td>
        </tr>
        """

    # === Sección de alertas próximos 7 días ===
    alertas_7d_html = ""
    n_total_alertas_7d = sum(len(z.get("alertas", [])) for z in alertas_7d)
    if n_total_alertas_7d > 0:
        # Aplanar y ordenar por fecha
        meses_es = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may",
                    6: "jun", 7: "jul", 8: "ago", 9: "sep",
                    10: "oct", 11: "nov", 12: "dic"}
        filas_plano = []
        for z in alertas_7d:
            for a in z.get("alertas", []):
                filas_plano.append({
                    "fecha": a.get("fecha", ""),
                    "zona": z.get("zona", ""),
                    "provincia": z.get("provincia", ""),
                    "tipo": a.get("tipo", ""),
                    "icono": a.get("icono", ""),
                    "detalle": a.get("detalle", ""),
                    "severidad": a.get("severidad", "MEDIA"),
                })
        sev_orden = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
        filas_plano.sort(key=lambda r: (r["fecha"],
                                          sev_orden.get(r["severidad"], 9)))

        filas_html = ""
        for r in filas_plano:
            try:
                f_dt = datetime.strptime(r["fecha"], "%Y-%m-%d")
                f_str = f"{f_dt.day:02d}/{meses_es[f_dt.month]}"
            except Exception:
                f_str = r["fecha"]
            if r["severidad"] == "ALTA":
                bg_row = "#FFEBEE"
                sev_html = f'<span style="color:{rojo};font-weight:700">ALTA</span>'
            elif r["severidad"] == "MEDIA":
                bg_row = "#FFF3E0"
                sev_html = f'<span style="color:{naranja};font-weight:700">MEDIA</span>'
            else:
                bg_row = "#fff"
                sev_html = '<span style="color:#888">BAJA</span>'

            filas_html += f"""
            <tr style="background:{bg_row}">
              <td style="padding:5px 8px;border-bottom:1px solid #eee;text-align:center;white-space:nowrap"><b>{f_str}</b></td>
              <td style="padding:5px 8px;border-bottom:1px solid #eee">
                <b>{r['zona']}</b><br><span style="font-size:10px;color:#888">{r['provincia']}</span>
              </td>
              <td style="padding:5px 8px;border-bottom:1px solid #eee">{r['icono']} {r['tipo']}</td>
              <td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:11px">{r['detalle']}</td>
              <td style="padding:5px 8px;border-bottom:1px solid #eee;text-align:center;font-size:11px">{sev_html}</td>
            </tr>
            """

        alertas_7d_html = f"""
          <h3 style="color:{bg};font-size:15px;margin:24px 0 8px 0;padding-left:10px;border-left:4px solid {accent}">
            ⚠️ Alertas en los próximos 7 días
          </h3>
          <p style="font-size:12px;color:#555;margin:0 0 8px 0">
            <b>{n_total_alertas_7d} alerta{'s' if n_total_alertas_7d != 1 else ''}</b>
            detectada{'s' if n_total_alertas_7d != 1 else ''} en
            {len(alertas_7d)} zona{'s' if len(alertas_7d) != 1 else ''}.
          </p>
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead>
              <tr style="background:#0D47A1;color:#fff">
                <th style="padding:6px 8px;text-align:center">Fecha</th>
                <th style="padding:6px 8px;text-align:left">Zona</th>
                <th style="padding:6px 8px;text-align:left">Tipo</th>
                <th style="padding:6px 8px;text-align:left">Detalle</th>
                <th style="padding:6px 8px;text-align:center">Sev.</th>
              </tr>
            </thead>
            <tbody>{filas_html}</tbody>
          </table>
        """

    html = f"""
    <!DOCTYPE html>
    <html><body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#222">
      <div style="max-width:640px;margin:0 auto;background:#fff">
        <!-- Header -->
        <div style="background:linear-gradient(135deg,{bg} 0%,#2E7D32 100%);color:#fff;padding:24px 28px">
          <div style="font-size:22px;font-weight:700">📊 Precios del Mercado Central</div>
          <div style="font-size:13px;opacity:.9;margin-top:4px">
            {empresa['nombre']} · {fecha_str}
          </div>
        </div>

        <!-- Cuerpo -->
        <div style="padding:24px 28px">
          {aviso_atraso}
          {alerta_box}

          <p style="line-height:1.6;color:#333;font-size:14px">
            {resumen.get('texto_resumen', 'Informe de precios del día.')}
          </p>

          <!-- Top productos -->
          <h3 style="color:{bg};font-size:15px;margin:20px 0 8px 0;padding-left:10px;border-left:4px solid {accent}">
            Precios destacados (referencia Salta/Jujuy o Buenos Aires)
          </h3>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead>
              <tr style="background:{bg};color:#fff">
                <th style="padding:8px 10px;text-align:left">Producto</th>
                <th style="padding:8px 10px;text-align:right">$ Medio (bulto)</th>
              </tr>
            </thead>
            <tbody>{productos_html}</tbody>
          </table>

          <!-- Clima 48hs -->
          <h3 style="color:{bg};font-size:15px;margin:24px 0 8px 0;padding-left:10px;border-left:4px solid {accent}">
            🌤️ Clima — próximas 48 hs
          </h3>
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead>
              <tr style="background:#0D47A1;color:#fff">
                <th style="padding:6px 8px;text-align:left" rowspan="2">Zona</th>
                <th style="padding:4px 8px;text-align:center;border-bottom:1px solid #fff" colspan="3">Mañana</th>
                <th style="padding:4px 8px;text-align:center;border-left:2px solid #fff;border-bottom:1px solid #fff" colspan="3">Pasado</th>
              </tr>
              <tr style="background:#0D47A1;color:#fff;font-size:11px">
                <th style="padding:4px 6px;text-align:center">Máx</th>
                <th style="padding:4px 6px;text-align:center">Mín</th>
                <th style="padding:4px 6px;text-align:center">Lluvia</th>
                <th style="padding:4px 6px;text-align:center;border-left:2px solid #fff">Máx</th>
                <th style="padding:4px 6px;text-align:center">Mín</th>
                <th style="padding:4px 6px;text-align:center">Lluvia</th>
              </tr>
            </thead>
            <tbody>{clima_filas}</tbody>
          </table>

          {alertas_7d_html}

          <!-- Botón PDF -->
          <div style="text-align:center;margin:30px 0 10px 0">
            <a href="{url_pdf}" style="background:{bg};color:#fff;padding:14px 30px;text-decoration:none;border-radius:6px;font-weight:600;display:inline-block;font-size:15px">
              📄 Ver / descargar PDF completo
            </a>
            <div style="margin-top:8px;font-size:12px;color:#888">
              Para reenviarlo a tus clientes, también podés copiar este link:<br>
              <a href="{url_pdf}" style="color:{bg};word-break:break-all">{url_pdf}</a>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div style="background:#fafbfc;padding:18px 28px;border-top:1px solid #eee;font-size:11px;color:#888;line-height:1.6">
          <b>{empresa['nombre']}</b> — {empresa.get('rubro', '')}<br>
          {empresa.get('web', '')} · {empresa.get('email', '')}<br>
          <i>Fuente de precios: Mercado Central de Buenos Aires (mercadocentral.gob.ar). Pronóstico climático: Open-Meteo (modelos ECMWF, GFS-NOAA, ICON-DWD).</i>
        </div>
      </div>
    </body></html>
    """
    return html


def main():
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("❌ Falta la variable de entorno RESEND_API_KEY")
        sys.exit(1)

    cfg = cargar_config()
    empresa = cfg["empresa"]
    cfg_p = cfg["precios_mercado_central"]
    destinatario = cfg_p.get("email_destinatario") or empresa.get("email")
    if not destinatario:
        print("❌ Sin destinatario configurado")
        sys.exit(1)

    resumen = cargar_resumen()
    if not resumen:
        print("❌ No se encontró informes/precios_hoy_resumen.json. "
              "Corré primero generar_precios.py")
        sys.exit(1)

    # URL pública del PDF (servida por GitHub Pages)
    url_pdf = ("https://carlosmariani.github.io/clima-don-antonio/"
               "precios_hoy.pdf")

    fecha_str = resumen.get("fecha_str", _ahora_ar().strftime("%d/%m/%Y"))
    asunto = f"📊 Precios MCBA — {fecha_str}"
    clima_e = (resumen.get("clima_48h")
               or resumen.get("clima_manana", []))
    hay_alerta_48h = any(c.get("alerta") for c in clima_e)
    n_alertas_7d = sum(len(z.get("alertas", []))
                        for z in (resumen.get("alertas_7d")
                                   or resumen.get("alertas_15d", [])))
    if hay_alerta_48h:
        asunto = f"⚠️ {asunto} (alerta climática 48hs)"
    elif n_alertas_7d > 0:
        asunto = f"⚠️ {asunto} ({n_alertas_7d} alerta"\
                 f"{'s' if n_alertas_7d != 1 else ''} próximos 7 días)"

    html = construir_html(empresa, resumen, url_pdf)

    print(f"→ Enviando email a {destinatario}...")
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Don Antonio SRL <info@novitsji.com.ar>",
            "to": [destinatario],
            "reply_to": empresa.get("email", destinatario),
            "subject": asunto,
            "html": html,
        },
        timeout=30,
    )

    if resp.status_code in (200, 202):
        data = resp.json()
        print(f"✓ Email enviado. ID: {data.get('id', 'N/D')}")
    else:
        print(f"❌ Error al enviar: {resp.status_code}")
        print(resp.text)
        sys.exit(1)


if __name__ == "__main__":
    main()
