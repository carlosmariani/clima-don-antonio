#!/bin/bash
# Don Antonio SRL - Instalación inicial
# Instala las librerías de Python que usa el proyecto. Se hace una sola vez por Mac
# (o cuando cambia requirements.txt).

cd "$(dirname "$0")"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  PRevisor del Clima — Don Antonio SRL"
echo "  INSTALACIÓN (solo se hace una vez)"
echo "════════════════════════════════════════════════════════════"
echo ""

# Mismo orden de búsqueda que usa la app "Clima Don Antonio"
PY=""
for CAND in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$CAND" ] && "$CAND" --version >/dev/null 2>&1; then
        PY="$CAND"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "⚠️  Python no está instalado en tu Mac."
    echo ""
    echo "Para instalarlo:"
    echo "  1. Abrí esta dirección en tu navegador:"
    echo "     https://www.python.org/downloads/"
    echo "  2. Descargá la versión para macOS y ejecutá el instalador"
    echo "  3. Volvé a abrir este archivo cuando termine"
    echo ""
    echo "(Apretá Enter para cerrar)"
    read
    exit 1
fi

echo "✓ Python detectado: $("$PY" --version)  ($PY)"
echo ""
echo "Instalando librerías necesarias (esto puede tardar un par de minutos)..."
echo ""

instalar() {
    "$PY" -m pip install --user "$@" -r requirements.txt > /tmp/clima_pip.log 2>&1
}
OK=false
if instalar; then
    OK=true
elif grep -q "externally-managed" /tmp/clima_pip.log; then
    # Python de Homebrew: pide este permiso extra para instalar librerías
    instalar --break-system-packages && OK=true
fi
tail -5 /tmp/clima_pip.log

if [ "$OK" = true ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "✓ Instalación completada correctamente."
    echo ""
    echo "Ahora podés:"
    echo "  • Doble click en '⚙️ Crear o Reparar App.command' para tener"
    echo "    la app 'Clima Don Antonio' en el Escritorio"
    echo "════════════════════════════════════════════════════════════"
else
    echo ""
    echo "❌ Hubo un error en la instalación. Mostrame esta ventana."
fi

echo ""
echo "(Apretá Enter para cerrar esta ventana)"
read
