import logging
import os
import traceback
import sys
from datetime import datetime

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DIR = os.path.dirname(os.path.abspath(__file__))

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("inventario_pro")
    logger.setLevel(logging.INFO)
    log_file = os.path.join(LOG_DIR, "app.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%d/%m/%Y %H:%M:%S"))
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    return logger

logger = setup_logging()

def guardar_crash(tipo, valor, tb) -> None:
    try:
        ruta = os.path.join(LOG_DIR, "crash_log.txt")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"CRASH {datetime.now()}\n")
            traceback.print_exception(tipo, valor, tb, file=f)
        logger.critical("Crash guardado en %s", ruta)
    except Exception:
        pass

sys.excepthook = guardar_crash
