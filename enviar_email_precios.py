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
from datetime import datetime

import requests


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
    clima = resumen.get("clima_manana", [])
    alertas_clima = [c for c in clima if c.get("alerta")]

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

    clima_filas = ""
    for c in clima:
        bg_row = "#FFF3E0" if c.get("alerta") else "#fff"
        alerta_celda = c.get("alerta") or '<span style="color:#888">—</span>'
        clima_filas += f"""
        <tr style="background:{bg_row}">
          <td style="padding:5px 8px;border-bottom:1px solid #eee">
            <b>{c['zona']}</b><br><span style="font-size:10px;color:#888">{c['provincia']}</span>
          </td>
          <td style="padding:5px 8px;border-bottom:1px solid #eee;text-align:center">{c.get('tmax', 0):.0f}°</td>
          <td style="padding:5px 8px;border-bottom:1px solid #eee;text-align:center">{c.get('tmin', 0):.0f}°</td>
          <td style="padding:5px 8px;border-bottom:1px solid #eee;text-align:center">{c.get('lluvia_mm', 0):.0f} mm</td>
          <td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:11px">{alerta_celda}</td>
        </tr>
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

          <!-- Clima mañana -->
          <h3 style="color:{bg};font-size:15px;margin:24px 0 8px 0;padding-left:10px;border-left:4px solid {accent}">
            🌤️ Clima previsto para mañana
          </h3>
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead>
              <tr style="background:#0D47A1;color:#fff">
                <th style="padding:6px 8px;text-align:left">Zona</th>
                <th style="padding:6px 8px;text-align:center">Tmáx</th>
                <th style="padding:6px 8px;text-align:center">Tmín</th>
                <th style="padding:6px 8px;text-align:center">Lluvia</th>
                <th style="padding:6px 8px;text-align:left">Alerta</th>
              </tr>
            </thead>
            <tbody>{clima_filas}</tbody>
          </table>

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

    fecha_str = resumen.get("fecha_str", datetime.now().strftime("%d/%m/%Y"))
    asunto = f"📊 Precios MCBA — {fecha_str}"
    if any(c.get("alerta") for c in resumen.get("clima_manana", [])):
        asunto = f"⚠️ {asunto} (alerta climática)"

    html = construir_html(empresa, resumen, url_pdf)

    print(f"→ Enviando email a {destinatario}...")
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Don Antonio SRL <onboarding@resend.dev>",
            "to": [destinatario],
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
