import os
import re
import shutil
from pathlib import Path

# ==============================
# CONFIGURACIÓN
# ==============================

DIRECTORIO = r"G:\Vuze\The Pixar-Disney Animations Collection (1995-2024)"

# Cambia entre regex según el formato

# Formato: 1940 - Fantasia
# REGEX = r"^\s*(?P<year>\d{4})\s*-\s*(?P<title>.+?)\s*$"

# Formato: 1995.Toy.Story.1080p...
REGEX = r"^(?P<year>\d{4})\.(?P<title>.+?)(?=\.(?:\d{3,4}p|\d{3,4}x\d{3,4}|BDRip|WEBRip|BluRay|x264|x265|DTS|AAC|HDR|DV|HEVC|$))"

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v"}

# 🔥 Modo simulación
DRY_RUN = False  # True = solo muestra cambios, False = mueve archivos


# ==============================
# FUNCIÓN PRINCIPAL
# ==============================

def organizar_videos(directorio: str):
    base_path = Path(directorio)

    if not base_path.exists():
        print(f"❌ El directorio no existe: {directorio}")
        return

    print(f"\n📂 Procesando: {directorio}")
    print(f"🧪 DRY_RUN: {'ON' if DRY_RUN else 'OFF'}\n")

    for archivo in base_path.iterdir():
        if not archivo.is_file():
            continue

        if archivo.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        nombre_sin_ext = archivo.stem

        match = re.match(REGEX, nombre_sin_ext)

        if not match:
            print(f"⚠️ No coincide con regex: {archivo.name}")
            continue

        year = match.group("year").strip()
        title = match.group("title").strip()

        # Reemplazar puntos por espacios (para formato tipo Toy.Story)
        title = title.replace(".", " ")

        # Limpiar caracteres inválidos para carpetas
        title = limpiar_nombre(title)

        carpeta_nombre = f"{title} ({year})"
        carpeta_path = base_path / carpeta_nombre
        destino = carpeta_path / archivo.name

        print(f"➡️ {archivo.name}")
        print(f"   📁 Carpeta destino: {carpeta_nombre}")

        if destino.exists():
            print(f"   ⚠️ Ya existe destino, se omite\n")
            continue

        if DRY_RUN:
            print(f"   🧪 [DRY RUN] No se mueve archivo\n")
            continue

        # Crear carpeta
        carpeta_path.mkdir(exist_ok=True)

        # Mover archivo
        shutil.move(str(archivo), str(destino))

        print(f"   ✅ Movido\n")


# ==============================
# UTILIDAD PARA LIMPIAR NOMBRE
# ==============================

def limpiar_nombre(nombre: str) -> str:
    """
    Elimina caracteres inválidos para nombres de carpeta en Windows.
    """
    return re.sub(r'[<>:"/\\|?*]', '', nombre)


# ==============================
# EJECUCIÓN
# ==============================

if __name__ == "__main__":
    organizar_videos(DIRECTORIO)