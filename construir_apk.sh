#!/bin/bash
cd ~/app
source venv/bin/activate
echo "Iniciando build del APK..."
echo "Esto tarda 30-60 minutos. No cierres el terminal."
buildozer android debug 2>&1 | tee ~/app/build.log
echo ""
echo "=== BUILD FINALIZADO ==="
ls -la ~/app/bin/*.apk 2>/dev/null || echo "APK no encontrado"
