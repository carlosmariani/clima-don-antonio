"""
enviar_email_extendido.py
Envía el REPORTE EXTENDIDO QUINCENAL por email (vía Resend), adjuntando
el PDF `informes/extendido_hoy.pdf`.

Se ejecuta desde el workflow los días 1 y 15 de cada mes ART.

Uso:
    RESEND_API_KEY=re_xxx python3 enviar_email_extendido.py
"""

import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

TZ_AR = timezone(timedelta(hours=-3))
PDF_PATH = "informes/extendido_hoy.pdf"


def _ahora_ar() -> datetime:
    return datetime.now(TZ_AR).replace(tzinfo=None)


def cargar_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def construir_html(empresa: dict, enso: dict = None) -> str:
    bg = empresa.get("color_primario", "#1B5E20")
    fecha_str = _ahora_ar().strftime("%d/%m/%Y")

    enso_html = ""
    if enso and enso.get("disponible"):
        enso_html = f"""
        <div style="background:#F5F7FA;border-left:4px solid {enso.get('color', '#1B5E20')};
                    padding:14px 18px;margin:16px 0;border-radius:6px">
          <b>{enso['emoji']} Estado climático global</b><br>
          <b>{enso['titulo']}</b> — índice ONI {enso['anomalia']:+.2f}°C
          ({enso['trimestre']}).
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html><body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#222">
      <div style="max-width:640px;margin:0 auto;background:#fff">
        <div style="background:linear-gradient(135deg,{bg} 0%,#2E7D32 100%);color:#fff;padding:24px 28px">
          <div style="font-size:22px;font-weight:700">📊 Reporte Climático Extendido</div>
          <div style="font-size:13px;opacity:.9;margin-top:4px">
            {empresa['nombre']} · Perspectiva 15 días + estacional 3 meses · {fecha_str}
          </div>
        </div>
        <div style="padding:24px 28px">
          <p style="line-height:1.6;color:#333;font-size:14px">
            Adjuntamos el reporte climático extendido correspondiente a esta
            quincena. Incluye:
          </p>
          {enso_html}
          <ul style="line-height:1.7;color:#333;font-size:14px;padding-left:22px">
            <li>Contexto climático global (estado ENSO — El Niño / La Niña) con
                recomendaciones agronómicas por fase.</li>
            <li>Pronóstico detallado a <b>15 días por zona</b>, con gráficos
                (lluvia y temperatura) y métricas resumen.</li>
            <li>Alertas destacadas: heladas, vientos fuertes, calor extremo.</li>
            <li><b>Perspectiva estacional 3 meses</b> por zona
                (temperaturas promedio y lluvia mensual esperada).</li>
          </ul>
          <p style="line-height:1.6;color:#333;font-size:14px;margin-top:20px">
            El reporte diario de precios y clima seguirá llegando normalmente
            todos los días. Este extendido se emite <b>solo los días 1 y 15
            de cada mes</b>.
          </p>
          <p style="line-height:1.6;color:#555;font-size:13px;margin-top:24px">
            Saludos,<br>
            <b>{empresa['nombre']}</b>
          </p>
        </div>
        <div style="background:#fafbfc;padding:16px 28px;border-top:1px solid #eee;font-size:11px;color:#888;line-height:1.6">
          <i>Fuentes: Promedio ensemble ECMWF + GFS-NOAA + ICON-DWD + JMA · NOAA CPC (ONI).
          Reporte generado automáticamente. Información orientativa, no reemplaza el criterio profesional.</i>
        </div>
      </div>
    </body></html>
    """


def main():
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("❌ Falta RESEND_API_KEY")
        sys.exit(1)

    if not os.path.exists(PDF_PATH):
        print(f"❌ No existe el PDF: {PDF_PATH}")
        sys.exit(1)

    cfg = cargar_config()
    empresa = cfg["empresa"]
    destinatario = (cfg.get("precios_mercado_central", {}).get("email_destinatario")
                    or empresa.get("email"))
    if not destinatario:
        print("❌ No hay destinatario configurado")
        sys.exit(1)

    # Estado ENSO opcional (para incluir en el HTML)
    enso = None
    try:
        from clima_enso import obtener_estado_enso
        enso = obtener_estado_enso()
    except Exception as e:
        print(f"⚠️ No se pudo traer ENSO para el HTML: {e}")

    # Adjunto
    with open(PDF_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    nombre = f"reporte_extendido_{_ahora_ar().strftime('%Y%m%d')}.pdf"

    fecha_str = _ahora_ar().strftime("%d/%m/%Y")
    subject = f"📊 Reporte Climático Extendido — {fecha_str}"

    body = {
        "from": f"{empresa['nombre']} <info@novitsji.com.ar>",
        "to": [destinatario],
        "reply_to": empresa.get("email", destinatario),
        "subject": subject,
        "html": construir_html(empresa, enso),
        "attachments": [{"filename": nombre, "content": b64}],
        "headers": {
            "List-Unsubscribe": f"<mailto:{empresa.get('email', destinatario)}?subject=Unsubscribe>",
            "X-Entity-Ref-ID": "reporte-extendido-quincenal",
        },
    }

    print(f"→ Enviando extendido a {destinatario}...")
    resp = requests.post("https://api.resend.com/emails",
                         headers={"Authorization": f"Bearer {api_key}",
                                   "Content-Type": "application/json"},
                         json=body, timeout=60)
    if resp.status_code in (200, 202):
        print(f"  ✓ Enviado. ID: {resp.json().get('id', 'N/D')}")
    else:
        print(f"  ❌ Error {resp.status_code}: {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
