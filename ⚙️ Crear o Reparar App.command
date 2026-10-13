#!/bin/bash
# ⚙️ Crear o Reparar App — Don Antonio SRL
#
# Crea (o vuelve a crear) la app "Clima Don Antonio" en el Escritorio,
# apuntando a ESTA carpeta (la del repo de GitHub, donde está este archivo).
# Es seguro correrlo cuantas veces quieras.

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║   ⚙️   Clima Don Antonio — instalación / reparación      ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""

DESK="$HOME/Desktop"
PROYECTO="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$DESK/Clima Don Antonio.app"
export PROYECTO

if [ ! -f "$PROYECTO/config.json" ]; then
    echo "  ❌ Este archivo tiene que estar dentro de la carpeta del proyecto."
    read -p "  (Apretá Enter para cerrar) " _
    exit 1
fi

# Verificar PNG fuente del icono
PNG_FUENTE=""
[ -f "$PROYECTO/AppIcon.png" ] && PNG_FUENTE="$PROYECTO/AppIcon.png"
[ -z "$PNG_FUENTE" ] && [ -f "$PROYECTO/logo.png" ] && PNG_FUENTE="$PROYECTO/logo.png"

# Siempre se crea de cero: así la app apunta a la carpeta correcta
# aunque el proyecto se haya mudado (antes estaba en el Escritorio).
MODO="CREAR"
if [ -d "$APP_PATH" ]; then
    echo "  ⓘ La app ya existe — se vuelve a crear apuntando a:"
    rm -rf "$APP_PATH"
else
    echo "  ⓘ Se crea la app apuntando a:"
fi
echo "     $PROYECTO"
echo ""

# ===== GENERAR ICONO (siempre se necesita) =====
TMP_DIR="/tmp/clima_build_$$"
rm -rf "$TMP_DIR"; mkdir -p "$TMP_DIR"

ICON_OK=false
if [ -n "$PNG_FUENTE" ]; then
    echo "  → Generando icono nativo (iconutil)..."
    ICONSET="$TMP_DIR/AppIcon.iconset"
    mkdir -p "$ICONSET"
    for s in 16 32 128 256 512; do
        sips -z $s $s "$PNG_FUENTE" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null 2>&1
        s2=$((s * 2))
        sips -z $s2 $s2 "$PNG_FUENTE" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1
    done
    if iconutil -c icns "$ICONSET" -o "$TMP_DIR/AppIcon.icns" 2>/dev/null; then
        ICON_OK=true
        echo "    ✓ Icono generado"
    else
        echo "    ⚠️  iconutil falló"
    fi
else
    echo "  ⚠️  No se encontró AppIcon.png ni logo.png"
fi

# ===== MODO: CREAR APP =====
if [ "$MODO" = "CREAR" ]; then
    cd "$TMP_DIR" || exit 1
    TMP_SCPT="$TMP_DIR/source.applescript"
    TMP_APP="$TMP_DIR/Clima Don Antonio.app"

    cat > "$TMP_SCPT" <<'APPLESCRIPT'
on run
	-- Traer la app al frente: en macOS nuevos los carteles quedaban escondidos detrás de otras ventanas
	activate
	set proyectoPath to "__PROYECTO__"
	set logPath to (POSIX path of (path to home folder)) & "Library/Logs/ClimaDonAntonio.log"

	try
		do shell script "test -d " & quoted form of proyectoPath
	on error
		display dialog "No se encontró la carpeta del proyecto:" & return & proyectoPath with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
		return
	end try

	set pythonPath to ""
	repeat with cand in {"/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"}
		try
			do shell script "test -x " & quoted form of (cand as string)
			set pythonPath to (cand as string)
			exit repeat
		end try
	end repeat
	if pythonPath is "" then
		display dialog "Python no está instalado." & return & return & "Ejecutá '1️⃣ Instalar (primera vez).command' en la carpeta del proyecto." with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
		return
	end if

	try
		-- Lista (no botones): un cartel de macOS admite como máximo 3 botones
		set eleccion to choose from list {"Dashboard", "Precios MCBA", "PDF Cliente"} with title "Clima Don Antonio" with prompt "¿Qué querés hacer?" default items {"Dashboard"} OK button name "Abrir" cancel button name "Cancelar"
	on error errMsg
		display dialog "No se pudo mostrar el menú." & return & return & errMsg with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
		return
	end try

	if eleccion is false then return
	set accion to item 1 of eleccion

	set cdCmd to "cd " & quoted form of proyectoPath & " && "

	-- Traer la última versión de GitHub (sin molestar si no hay internet).
	-- Antes se descartan los archivos que genera GitHub solo (dashboard, PDF del día),
	-- para que no choquen con los que bajan.
	try
		do shell script cdCmd & "git checkout -- dashboard.html index.html precios_hoy.pdf informes/precios_hoy.pdf informes/precios_hoy_resumen.json informes/extendido_hoy.pdf informes/reporte_abapo.pdf informes/reporte_tucuman.pdf informes/por_zona .last_email_date .last_email_extendido_date .last_email_nader_date >/dev/null 2>&1; GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=15 pull --ff-only -q >> " & quoted form of logPath & " 2>&1"
	end try

	-- Tras renombrado de botones para que entren más opciones
	if accion is "Dashboard" then
		set dialogPID to do shell script "(osascript -e 'display dialog \"Actualizando datos del clima…\\n\\nPuede tardar 30 segundos.\" with title \"Clima Don Antonio\" buttons {\"Cerrar\"} giving up after 60 with icon note' >/dev/null 2>&1 &) ; echo $!"
		try
			do shell script cdCmd & quoted form of pythonPath & " generar_dashboard.py >> " & quoted form of logPath & " 2>&1"
			do shell script "kill " & dialogPID & " 2>/dev/null; true"
			do shell script cdCmd & "open dashboard.html"
		on error errMsg
			do shell script "kill " & dialogPID & " 2>/dev/null; true"
			try
				do shell script cdCmd & "test -f dashboard.html && open dashboard.html"
				display dialog "No se pudieron actualizar los datos. Se abre la última versión disponible." with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
			on error
				display dialog "No se pudo generar el dashboard." & return & return & "Detalle: " & errMsg with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
			end try
		end try
		return
	end if

	if accion is "Precios MCBA" then
		-- Siempre regenera para tener el del día. Si falla, abre el último disponible.
		set dialogPID to do shell script "(osascript -e 'display dialog \"Consultando precios del Mercado Central…\\n\\nTarda 30-60 segundos.\" with title \"Clima Don Antonio\" buttons {\"Cerrar\"} giving up after 90 with icon note' >/dev/null 2>&1 &) ; echo $!"
		try
			do shell script cdCmd & quoted form of pythonPath & " generar_precios.py >> " & quoted form of logPath & " 2>&1"
			do shell script "kill " & dialogPID & " 2>/dev/null; true"
			-- Abrir el PDF más reciente generado
			set ultimoPDF to do shell script cdCmd & "ls -t informes/precios_mcba_*.pdf 2>/dev/null | head -1"
			if ultimoPDF is not "" then
				do shell script cdCmd & "open " & quoted form of ultimoPDF
			else
				do shell script cdCmd & "open informes/"
			end if
		on error errMsg
			do shell script "kill " & dialogPID & " 2>/dev/null; true"
			-- Si falla, abrir el último disponible si lo hay
			try
				do shell script cdCmd & "test -f informes/precios_hoy.pdf && open informes/precios_hoy.pdf"
				display dialog "No se pudieron obtener los precios de hoy. Se abre el último PDF disponible." with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
			on error
				display dialog "No se pudieron obtener los precios." & return & return & "Detalle: " & errMsg with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
			end try
		end try
		return
	end if

	if accion is "PDF Cliente" then
		-- Primero le pregunto qué tipo de PDF quiere: clima o precios
		try
			set tipoPdf to button returned of (display dialog "¿Qué tipo de informe querés generar para el cliente?" buttons {"Cancelar", "Precios MCBA", "Clima"} default button "Clima" with title "Clima Don Antonio" with icon note)
			if tipoPdf is "Cancelar" then return
		on error
			return
		end try

		try
			set clienteRespuesta to display dialog "¿Para qué cliente es el informe?" & return & "(Dejá vacío para informe genérico)" with title "Clima Don Antonio" default answer "" buttons {"Cancelar", "Siguiente"} default button "Siguiente" with icon note
			if button returned of clienteRespuesta is "Cancelar" then return
			set cliente to text returned of clienteRespuesta
		on error
			return
		end try

		-- Si eligió Precios, genero el PDF de precios y termino
		if tipoPdf is "Precios MCBA" then
			set dialogPID to do shell script "(osascript -e 'display dialog \"Generando informe de precios para \" & " & quoted form of cliente & " & \"…\\n\\nTarda 30-60 segundos.\" with title \"Clima Don Antonio\" buttons {\"Cerrar\"} giving up after 90 with icon note' >/dev/null 2>&1 &) ; echo $!"
			set clienteArg to ""
			if cliente is not "" then set clienteArg to "--cliente " & quoted form of cliente
			set cmdPrecios to cdCmd & quoted form of pythonPath & " generar_precios.py " & clienteArg & " >> " & quoted form of logPath & " 2>&1"
			try
				do shell script cmdPrecios
				do shell script "kill " & dialogPID & " 2>/dev/null; true"
				set ultimoPDF to do shell script cdCmd & "ls -t informes/precios_mcba_*.pdf 2>/dev/null | head -1"
				if ultimoPDF is not "" then do shell script cdCmd & "open " & quoted form of ultimoPDF
			on error errMsg
				do shell script "kill " & dialogPID & " 2>/dev/null; true"
				display dialog "Hubo un error generando el PDF de precios." & return & return & errMsg with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
			end try
			return
		end if

		-- Si eligió Clima, sigue el flujo normal de zonas + extendido

		try
			set zonasOpt to choose from list {"Todas las zonas (informe completo)", "Una zona específica", "Varias zonas (elegir cuáles)"} with title "Clima Don Antonio" with prompt "¿Qué zonas incluir?" default items {"Todas las zonas (informe completo)"} OK button name "Siguiente" cancel button name "Cancelar"
			if zonasOpt is false then return
			set zonasOpt to item 1 of zonasOpt
		on error
			return
		end try

		set zonasArg to ""
		if zonasOpt is not "Todas las zonas (informe completo)" then
			set listaCmd to cdCmd & quoted form of pythonPath & " -c \"import json; cfg=json.load(open('config.json')); print('|'.join(l['nombre'] + ' (' + l['provincia'] + ')' for l in cfg['localidades']))\""
			set listaRaw to do shell script listaCmd
			set AppleScript's text item delimiters to "|"
			set zonasList to text items of listaRaw
			set AppleScript's text item delimiters to ""

			if zonasOpt is "Una zona específica" then
				try
					set zonaSel to choose from list zonasList with title "Clima Don Antonio" with prompt "¿De qué zona querés generar el informe?" OK button name "Generar" cancel button name "Cancelar"
					if zonaSel is false then return
					set zonaTxt to item 1 of zonaSel
					set AppleScript's text item delimiters to " ("
					set nombreZona to item 1 of (text items of zonaTxt)
					set AppleScript's text item delimiters to ""
					set zonasArg to "--localidad " & quoted form of nombreZona
				on error
					return
				end try
			else
				try
					set zonasSel to choose from list zonasList with title "Clima Don Antonio" with prompt "¿Qué zonas? (Cmd + click para varias)" OK button name "Generar" cancel button name "Cancelar" with multiple selections allowed
					if zonasSel is false then return
					set nombres to {}
					repeat with z in zonasSel
						set AppleScript's text item delimiters to " ("
						set end of nombres to item 1 of (text items of (z as string))
						set AppleScript's text item delimiters to ""
					end repeat
					set AppleScript's text item delimiters to ","
					set nombresStr to nombres as string
					set AppleScript's text item delimiters to ""
					set zonasArg to "--localidades " & quoted form of nombresStr
				on error
					return
				end try
			end if
		end if

		try
			set tipoBtn to button returned of (display dialog "¿Qué tipo de informe?" & return & return & "• ESTÁNDAR: 15 días + tendencia trimestral" & return & "• EXTENDIDO: análisis trimestral mes a mes detallado" buttons {"Cancelar", "Estándar", "Extendido"} default button "Estándar" with title "Clima Don Antonio" with icon note)
			if tipoBtn is "Cancelar" then return
		on error
			return
		end try
		set extArg to ""
		if tipoBtn is "Extendido" then set extArg to "--extendido"

		set dialogPID to do shell script "(osascript -e 'display dialog \"Generando el informe…\\n\\nTarda entre 30 y 60 segundos.\" with title \"Clima Don Antonio\" buttons {\"Cerrar\"} giving up after 90 with icon note' >/dev/null 2>&1 &) ; echo $!"

		set clienteArg to ""
		if cliente is not "" then set clienteArg to "--cliente " & quoted form of cliente

		set cmd to cdCmd & quoted form of pythonPath & " generar_informe.py " & clienteArg & " " & zonasArg & " " & extArg & " >> " & quoted form of logPath & " 2>&1"

		try
			do shell script cmd
			do shell script "kill " & dialogPID & " 2>/dev/null; true"
			set ultimoPDF to do shell script cdCmd & "ls -t informes/*.pdf 2>/dev/null | head -1"
			if ultimoPDF is not "" then
				do shell script cdCmd & "open " & quoted form of ultimoPDF
			else
				do shell script cdCmd & "open informes/"
			end if
		on error errMsg
			do shell script "kill " & dialogPID & " 2>/dev/null; true"
			display dialog "Hubo un error generando el informe." & return & return & "Detalle: " & errMsg with icon caution buttons {"OK"} default button 1 with title "Clima Don Antonio"
		end try
	end if
end run
APPLESCRIPT
    # Poner la ruta real del proyecto dentro de la app
    perl -pi -e 's/__PROYECTO__/$ENV{PROYECTO}/g' "$TMP_SCPT"

    echo "  → Compilando .app..."
    osacompile -o "$TMP_APP" "$TMP_SCPT" 2>&1 >/dev/null
    if [ ! -d "$TMP_APP" ]; then
        echo "  ❌ Error al compilar la app"
        cd /; rm -rf "$TMP_DIR"
        read -p "  (Apretá Enter para cerrar) " _
        exit 1
    fi

    # Identificador de la app: macOS nuevos no abren bien una app sin él
    /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string ar.com.semdonantonio.clima" "$TMP_APP/Contents/Info.plist" 2>/dev/null \
      || /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier ar.com.semdonantonio.clima" "$TMP_APP/Contents/Info.plist"

    # Aplicar el icono ANTES de mover
    if [ "$ICON_OK" = true ]; then
        cp "$TMP_DIR/AppIcon.icns" "$TMP_APP/Contents/Resources/applet.icns"
        cp "$TMP_DIR/AppIcon.icns" "$TMP_APP/Contents/Resources/AppIcon.icns"
        /usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AppIcon" "$TMP_APP/Contents/Info.plist" 2>/dev/null
        /usr/libexec/PlistBuddy -c "Set :CFBundleIconName AppIcon" "$TMP_APP/Contents/Info.plist" 2>/dev/null
    fi

    # Mover al Escritorio
    mv "$TMP_APP" "$APP_PATH"
    echo "    ✓ App instalada en el Escritorio"
fi

# ===== MODO: REPARAR ICONO (también se ejecuta tras CREAR) =====
if [ "$ICON_OK" = true ] && [ -d "$APP_PATH" ]; then
    cp "$TMP_DIR/AppIcon.icns" "$APP_PATH/Contents/Resources/applet.icns" 2>/dev/null
    cp "$TMP_DIR/AppIcon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null
    /usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AppIcon" "$APP_PATH/Contents/Info.plist" 2>/dev/null
    /usr/libexec/PlistBuddy -c "Set :CFBundleIconName AppIcon" "$APP_PATH/Contents/Info.plist" 2>/dev/null

    # Guardar copia del .icns en el proyecto
    cp "$TMP_DIR/AppIcon.icns" "$PROYECTO/AppIcon.icns"
fi

# ===== Refresh agresivo del icono =====
echo "  → Forzando refresh del icono..."
xattr -cr "$APP_PATH" 2>/dev/null
touch "$APP_PATH"
touch "$APP_PATH/Contents/Info.plist"
touch "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null
touch "$APP_PATH/Contents/Resources/applet.icns" 2>/dev/null

rm -rf "$HOME/Library/Caches/com.apple.iconservices."* 2>/dev/null
rm -rf "$HOME/Library/Caches/com.apple.dock.iconcache" 2>/dev/null

# Re-firmar AL FINAL (clave para que el icono persista)
echo "  → Firmando la app..."
codesign --force --deep --sign - "$APP_PATH" 2>/dev/null

# Reiniciar Dock + Finder
killall Dock 2>/dev/null
killall Finder 2>/dev/null

# Truco: mover/traer para forzar reindex
TEMP_HOLDING="$DESK/.clima_temp_$$"
mkdir -p "$TEMP_HOLDING"
mv "$APP_PATH" "$TEMP_HOLDING/Clima Don Antonio.app" 2>/dev/null
sleep 1
mv "$TEMP_HOLDING/Clima Don Antonio.app" "$APP_PATH" 2>/dev/null
rmdir "$TEMP_HOLDING" 2>/dev/null

# Registrar la app en macOS para que el doble click la abra
LSREG="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
[ -x "$LSREG" ] && "$LSREG" -f "$APP_PATH" 2>/dev/null

cd /
rm -rf "$TMP_DIR"

# Borrar archivos viejos del Escritorio
[ -f "$DESK/🌤 Clima Don Antonio.command" ] && rm -f "$DESK/🌤 Clima Don Antonio.command"

echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║   ✅  Listo                                               ║"
echo "  ║                                                          ║"
echo "  ║   Si el icono igual no se ve después de unos segundos:   ║"
echo "  ║                                                          ║"
echo "  ║   Método manual a prueba de balas:                       ║"
echo "  ║   1. Abrí AppIcon.png con doble click (Vista Previa)     ║"
echo "  ║   2. Cmd+A → Cmd+C (copiar)                              ║"
echo "  ║   3. Click sobre Clima Don Antonio.app (un solo click)   ║"
echo "  ║   4. Cmd+I (Obtener información)                         ║"
echo "  ║   5. Click en el icono chico arriba a la izquierda       ║"
echo "  ║   6. Cmd+V (pegar)                                       ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  (Esta ventana se cerrará en 10 segundos)"
sleep 10
exit 0
