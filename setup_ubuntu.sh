#!/bin/bash
set -e

echo "=== INSTALACION INVENTARIO PRO ==="
echo ""

# 1. Sistema
echo "[1/4] Instalando dependencias del sistema..."
sudo apt update
sudo apt install -y python3-pip python3-venv python3-kivy libsdl2-dev \
  libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libgles2-mesa-dev

# 2. Entorno virtual
echo "[2/4] Creando entorno virtual..."
python3 -m venv ~/app/venv
source ~/app/venv/bin/activate

# 3. Dependencias Python
echo "[3/4] Instalando dependencias Python..."
pip install --upgrade pip
pip install openpyxl imaplib2 requests python-dotenv Pillow fpdf2

# 4. .env
echo "[4/4] Configurando .env..."
if [ ! -f ~/app/.env ]; then
  cat > ~/app/.env << 'EOF'
APP_EMAIL=tu_correo@gmail.com
APP_EMAIL_PASS=tu_contrasena_app
FILTRO_ASUNTO=
FILTRO_REMITENTE=
EOF
  echo "-> .env creado. Editalo: nano ~/app/.env"
fi

echo ""
echo "=== INSTALACION COMPLETADA ==="
echo ""
echo "Para ejecutar la app:"
echo "  cd ~/app && source venv/bin/activate && python main.py"
echo ""
echo "O crear un acceso directo:"
echo "  echo 'alias inventario=\"cd ~/app && source venv/bin/activate && python main.py\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
echo "  inventario"
