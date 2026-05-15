import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

VERSION_ACTUAL = os.environ.get("APP_VERSION", "3.0.0")
URL_NUEVA_APK  = os.environ.get("UPDATE_URL", "https://tu-servidor.com/app_actualizada.apk")

EMAIL_CONFIG = {
    "remitente":        os.environ.get("APP_EMAIL", ""),
    "password":         os.environ.get("APP_EMAIL_PASS", ""),
    "destinatarios":    [os.environ.get("APP_EMAIL", "")],
    "imap_servidor":    "imap.gmail.com",
    "imap_puerto":      993,
    "asunto_filtro":    os.environ.get("FILTRO_ASUNTO", ""),
    "remitente_filtro": os.environ.get("FILTRO_REMITENTE", ""),
}

def _get_db_path() -> str:
    try:
        from kivy.utils import platform
        if platform == 'android':
            from android.storage import app_storage_path
            import sqlite3
            db = os.path.join(app_storage_path(), "gestion_inventario.db")
            return db
    except Exception:
        pass
    return "gestion_inventario.db"

DB_PATH = _get_db_path()

def _get_export_dir() -> str:
    try:
        from kivy.utils import platform
        if platform == 'android':
            export = "/storage/emulated/0/Download/InventarioPRO"
        else:
            export = os.path.join(str(Path.home()), "Downloads", "InventarioPRO")
        os.makedirs(export, exist_ok=True)
        return export
    except Exception:
        return os.path.dirname(os.path.abspath(__file__))

EXPORT_DIR = _get_export_dir()
