"""
enviar_email_nader.py
Envía por email (vía Resend) los reportes climáticos diarios al
Ing. Agrónomo Claudio Nader, con los PDFs adjuntos.

Uso (desde GitHub Action):
    RESEND_API_KEY=re_xxx python3 enviar_email_nader.py

Lee `reportes_extra` del config.json — para cada reporte adjunta el PDF
correspondiente y arma un email breve.
"""

import base64
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


def construir_html(empresa: dict, cliente: str, reportes: list) -> str:
    """HTML con resumen de qué se manda."""
    bg = empresa.get("color_primario", "#1B5E20")
    accent = empresa.get("color_secundario", "#F9A825")
    fecha_str = _ahora_ar().strftime("%d/%m/%Y")

    filas = ""
    for r in reportes:
        filas += f"""
        <li style="margin:6px 0">
          <b>{r['nombre']}</b><br>
          <span style="font-size:12px;color:#666">
            {', '.join(r['localidades'])}
          </span>
        </li>
        """

    return f"""
    <!DOCTYPE html>
    <html><body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#222">
      <div style="max-width:640px;margin:0 auto;background:#fff">
        <div style="background:linear-gradient(135deg,{bg} 0%,#2E7D32 100%);color:#fff;padding:24px 28px">
          <div style="font-size:22px;font-weight:700">🌦️ Reporte Climático Diario</div>
          <div style="font-size:13px;opacity:.9;margin-top:4px">
            {empresa['nombre']} · Para: {cliente} · {fecha_str}
          </div>
        </div>
        <div style="padding:24px 28px">
          <p style="line-height:1.6;color:#333;font-size:14px">
            Estimado {cliente},
          </p>
          <p style="line-height:1.6;color:#333;font-size:14px">
            Adjuntamos los reportes climáticos del día con pronóstico
            para las próximas 48 hs, próximos 7 días y sugerencias
            agronómicas para cada zona:
          </p>
          <ul style="line-height:1.7;color:#333;font-size:14px;padding-left:22px">
            {filas}
          </ul>
          <p style="line-height:1.6;color:#333;font-size:14px;margin-top:20px">
            Los reportes incluyen alertas de heladas, viento fuerte,
            lluvias intensas y recomendaciones específicas por zona.
          </p>
          <p style="line-height:1.6;color:#555;font-size:13px;margin-top:24px">
            Saludos,<br>
            <b>{empresa['nombre']}</b><br>
            <span style="color:#888;font-size:11px">{empresa.get('web', '')}</span>
          </p>
        </div>
        <div style="background:#fafbfc;padding:16px 28px;border-top:1px solid #eee;font-size:11px;color:#888;line-height:1.6">
          <i>Fuentes: Open-Meteo (ECMWF, GFS-NOAA, ICON-DWD, JMA). Reporte generado automáticamente.</i>
        </div>
      </div>
    </body></html>
    """


def main():
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("❌ Falta la variable de entorno RESEND_API_KEY")
        sys.exit(1)

    cfg = cargar_config()
    empresa = cfg["empresa"]
    reportes = cfg.get("reportes_extra", [])
    if not reportes:
        print("→ No hay reportes_extra en config.json. Nada que mandar.")
        return

    # Agrupar por email_destinatario para mandar 1 mail con todos los adjuntos
    por_destinatario = {}
    for r in reportes:
        dest = r.get("email_destinatario")
        if not dest:
            print(f"⚠️  Reporte '{r['id']}' sin email_destinatario, se omite.")
            continue
        if not os.path.exists(r["salida"]):
            print(f"⚠️  Reporte '{r['id']}' — PDF no existe ({r['salida']}), se omite.")
            continue
        por_destinatario.setdefault(dest, []).append(r)

    if not por_destinatario:
        print("❌ No hay ningún reporte válido con PDF y destinatario.")
        sys.exit(1)

    for destinatario, lista_reportes in por_destinatario.items():
        cliente = lista_reportes[0].get("cliente", destinatario)
        cc = lista_reportes[0].get("email_cc", "")

        # Adjuntos (base64)
        adjuntos = []
        for r in lista_reportes:
            with open(r["salida"], "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            nombre_archivo = os.path.basename(r["salida"])
            adjuntos.append({
                "filename": nombre_archivo,
                "content": b64,
            })

        fecha_str = _ahora_ar().strftime("%d/%m/%Y")
        asunto = f"🌦️ Reporte Climático — {fecha_str} — {empresa['nombre']}"
        # Si hay alertas, marcarlo (opcional — no revisamos ahora, se puede sumar después)

        html = construir_html(empresa, cliente, lista_reportes)

        body = {
            "from": f"{empresa['nombre']} <info@novitsji.com.ar>",
            "to": [destinatario],
            "reply_to": empresa.get("email", destinatario),
            "subject": asunto,
            "html": html,
            "attachments": adjuntos,
            "headers": {
                "List-Unsubscribe": f"<mailto:{empresa.get('email', destinatario)}?subject=Unsubscribe>",
                "X-Entity-Ref-ID": "reporte-clima-nader-diario",
            },
        }
        if cc:
            body["cc"] = [cc]

        print(f"→ Enviando mail a {destinatario}"
              + (f" (cc: {cc})" if cc else "")
              + f" con {len(adjuntos)} PDF(s)...")
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60,
        )
        if resp.status_code in (200, 202):
            data = resp.json()
            print(f"  ✓ Email enviado. ID: {data.get('id', 'N/D')}")
        else:
            print(f"  ❌ Error al enviar: {resp.status_code}")
            print(f"  {resp.text}")
            sys.exit(1)


if __name__ == "__main__":
    main()
