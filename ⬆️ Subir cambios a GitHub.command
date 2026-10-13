#!/bin/bash
# ⬆️ Subir cambios a GitHub — Don Antonio SRL
#
# Esta carpeta ES el repo de GitHub (clima-don-antonio). Este script:
#   1. Descarta los archivos que GitHub genera solo (dashboard, PDF del día),
#   2. trae lo último de GitHub,
#   3. sube tus cambios (config.json, scripts, etc.).
# Nunca sube CLAUDE.md ni los PDF de clientes (están en .gitignore).

cd "$(dirname "$0")" || exit 1

echo "============================================================"
echo "  📤 Subir cambios a GitHub (clima-don-antonio)"
echo "============================================================"
echo ""

if [ ! -d .git ]; then
    echo "❌ Esta carpeta no es el repo de GitHub."
    echo "   Usá la carpeta ~/Proyectos/clima-don-antonio"
    read -p "Presioná Enter para cerrar..."
    exit 1
fi

# Archivos que actualiza GitHub Actions solo: nunca se suben desde la Mac
GENERADOS=(dashboard.html index.html precios_hoy.pdf
           informes/precios_hoy.pdf informes/precios_hoy_resumen.json
           informes/extendido_hoy.pdf informes/reporte_abapo.pdf
           informes/reporte_tucuman.pdf informes/por_zona
           .last_email_date .last_email_extendido_date .last_email_nader_date)

echo "→ Descartando archivos que genera GitHub (dashboard y PDF del día)..."
git checkout -- "${GENERADOS[@]}" 2>/dev/null
echo ""

echo "→ Trayendo lo último de GitHub..."
if ! git pull --rebase --autostash; then
    echo ""
    echo "❌ No se pudo traer lo último de GitHub (¿sin internet o un conflicto?)."
    echo "   Sacale una captura a esta ventana y pasásela a Claude."
    read -p "Presioná Enter para cerrar..."
    exit 1
fi
echo ""

if [ -z "$(git status --porcelain)" ]; then
    echo "ℹ️  No hay cambios tuyos para subir. Todo está igual que en GitHub."
    echo ""
    read -p "Presioná Enter para cerrar..."
    exit 0
fi

echo "→ Cambios que se van a subir:"
git status --short
echo ""

git add -A

# Control de seguridad: el repo es PÚBLICO
PROBLEMAS=""
while IFS= read -r F; do
    case "$F" in
        CLAUDE.md|*/CLAUDE.md) PROBLEMAS="$PROBLEMAS\n   • $F (guía privada)";;
        informes/informe_clima_*|informes/precios_mcba_*) PROBLEMAS="$PROBLEMAS\n   • $F (PDF de cliente)";;
    esac
done < <(git -c core.quotepath=off diff --cached --name-only)
if git diff --cached -U0 | grep '^+' | grep -qiE '@(gmail|yahoo|hotmail|outlook|live)\.'; then
    PROBLEMAS="$PROBLEMAS\n   • hay una dirección de mail personal en los cambios (va en los Secrets de GitHub)"
fi
if [ -n "$PROBLEMAS" ]; then
    git reset -q
    echo "❌ No subo nada: el repo es público y esto no debería publicarse:"
    echo -e "$PROBLEMAS"
    echo ""
    read -p "Presioná Enter para cerrar..."
    exit 1
fi

read -p "Contá en pocas palabras qué cambiaste (o Enter para seguir): " MSG
[ -z "$MSG" ] && MSG="Cambios desde la Mac"

git commit -q -m "$MSG"
echo ""
echo "→ Subiendo a GitHub..."
if git push; then
    echo ""
    echo "✓ Cambios subidos correctamente."
    echo "  Las automatizaciones de GitHub ya usan la versión nueva."
else
    echo ""
    echo "❌ Falló la subida. Puede faltar iniciar sesión en GitHub en esta Mac."
    echo "   Tus cambios quedaron guardados acá; sacale una captura a esta ventana."
fi

echo ""
read -p "Presioná Enter para cerrar..."
