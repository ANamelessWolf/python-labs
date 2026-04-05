import os
from pathlib import Path

# =========================
# CONFIGURACIÓN
# =========================
DIRECTORIO = r"M:\\Anime\\Rainbow (2010)"
SERIE = "Rainbow"
TEMPORADA = 1
DRY_RUN = False  # True = solo muestra cambios, False = renombra

# Extensiones válidas de video
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v"}


def is_video_file(file_path: Path) -> bool:
    return file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS


def build_new_name(season: int, episode: int, series_name: str, extension: str) -> str:
    return f"S{season:02d}E{episode:02d} {series_name}{extension}"


def rename_files(directory: str, series_name: str, season: int, dry_run: bool = True) -> None:
    base_path = Path(directory)

    if not base_path.exists():
        raise FileNotFoundError(f"El directorio no existe: {directory}")

    if not base_path.is_dir():
        raise NotADirectoryError(f"La ruta no es un directorio: {directory}")

    files = [item for item in base_path.iterdir() if is_video_file(item)]
    files.sort(key=lambda x: x.name.lower())

    if not files:
        print("No se encontraron archivos de video para renombrar.")
        return

    print(f"Directorio: {base_path}")
    print(f"Serie: {series_name}")
    print(f"Temporada: {season:02d}")
    print(f"Modo simulación: {dry_run}")
    print("-" * 60)

    for index, old_file in enumerate(files, start=1):
        new_name = build_new_name(season, index, series_name, old_file.suffix)
        new_file = old_file.with_name(new_name)

        print(f"{old_file.name}  ->  {new_name}")

        if not dry_run:
            if new_file.exists():
                print(f"  [SKIP] Ya existe: {new_name}")
                continue

            old_file.rename(new_file)

    print("-" * 60)
    print("Proceso terminado.")


if __name__ == "__main__":
    rename_files(
        directory=DIRECTORIO,
        series_name=SERIE,
        season=TEMPORADA,
        dry_run=DRY_RUN
    )