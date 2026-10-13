# 📘 Cómo usar el PRevisor del Clima

Guía simple para usar el sistema. **No necesitás saber programar.**

---

## 🗂️ Dónde está cada cosa

- **En GitHub** (`carlosmariani/clima-don-antonio`) está la versión que vale. Ahí corren solas las
  automatizaciones: el dashboard web, los PDF de precios y los mails. Funcionan aunque las Macs estén apagadas.
- **En la Mac** el proyecto está en **`~/Proyectos/clima-don-antonio`** (tu carpeta de usuario → Proyectos).
  Es una copia del repo de GitHub: se actualiza sola cada vez que usás la app.
- Los **PDF que hacés para clientes** quedan en la carpeta `informes/` de la Mac y **no se suben** a GitHub
  (el repo es público).

---

## 🚀 En una Mac nueva (una sola vez)

1. Doble click en **`1️⃣ Instalar (primera vez).command`** → instala las librerías de Python.
2. Doble click en **`⚙️ Crear o Reparar App.command`** → crea la app **Clima Don Antonio** en el Escritorio.

> Si un `.command` no abre con doble click: click derecho → **Abrir** → **Abrir**. Solo la primera vez.

---

## 🌤 Uso diario: la app "Clima Don Antonio"

Doble click en la app del Escritorio y elegís:

| Botón | Qué hace |
|---|---|
| **Dashboard** | Actualiza el clima de las 10 zonas y lo abre en el navegador |
| **Precios MCBA** | Baja los precios del Mercado Central y abre el PDF |
| **PDF Cliente** | Te pregunta cliente, zonas y tipo (estándar o extendido) y arma el PDF |

El dashboard también está en internet: https://carlosmariani.github.io/clima-don-antonio/

---

## ⚙️ Cambiar localidades, umbrales, productos, etc.

1. Abrí **`config.json`** con TextEdit, cambiá lo que quieras y guardá.
2. Doble click en **`⬆️ Subir cambios a GitHub.command`** para que las automatizaciones usen el cambio.

Ese script nunca sube la guía `CLAUDE.md`, los PDF de clientes ni direcciones de mail personales.

---

## ✉️ A quién le llegan los mails

Las direcciones **no están en el código** (el repo es público): están guardadas como *Secrets* en GitHub,
en *Settings → Secrets and variables → Actions*:

| Secret | Para qué |
|---|---|
| `EMAIL_DESTINATARIO` | Tu casilla: mail diario de precios, extendido quincenal y copia del de Nader |
| `EMAIL_NADER` | Casilla del Ing. Claudio Nader (reportes de Abapó y Tucumán) |
| `RESEND_API_KEY` | Clave del servicio que manda los mails |

Para cambiar un destinatario, editás el Secret en GitHub. No hace falta tocar archivos.

---

## 🆘 Si algo no funciona

- **Aparece un error**: sacale una captura a la ventana y pasásela a Claude.
- **No tengo internet**: el sistema necesita internet para bajar el clima y los precios.
- **El detalle de qué hizo la app** queda en `~/Library/Logs/ClimaDonAntonio.log`.

---

## 📁 Archivos del proyecto

| Archivo | Para qué sirve |
|---|---|
| `1️⃣ Instalar (primera vez).command` | Instala lo necesario en una Mac nueva |
| `⚙️ Crear o Reparar App.command` | Crea la app del Escritorio (o la arregla) |
| `⬆️ Subir cambios a GitHub.command` | Sube a GitHub lo que cambiaste en la Mac |
| `config.json` | Localidades, datos de la empresa, umbrales y productos |
| `informes/` | PDF generados (los de clientes quedan solo en la Mac) |
| `.github/workflows/` | Las automatizaciones de GitHub |
| Lo demás (`.py`) | El motor del sistema, no lo toques |
