import re
import sys
from pathlib import Path

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v", ".ts"}

# Ejemplo soportado:
# S01E01 Hot Tub.en.avi
# S01E01 Something.es.mkv
PATTERN = re.compile(
    r"^(S\d{2}E\d{2})\s+(.+?)\.([a-z]{2,5})$",
    re.IGNORECASE
)


def is_video_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS


def build_new_name(stem: str, ext: str) -> str | None:
    match = PATTERN.match(stem)
    if not match:
        return None

    episode_code = match.group(1).upper()
    episode_title = match.group(2).strip()
    language_code = match.group(3).upper()

    return f"{episode_code} - {language_code} - {episode_title}{ext}"


def rename_files(directory: Path, dry_run: bool = True) -> None:
    if not directory.exists():
        raise FileNotFoundError(f"No existe la carpeta: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"La ruta no es una carpeta: {directory}")

    files = sorted(
        [item for item in directory.iterdir() if is_video_file(item)],
        key=lambda p: p.name.lower()
    )

    if not files:
        print("No se encontraron archivos de video.")
        return

    print(f"Carpeta: {directory}")
    print(f"Modo simulación: {dry_run}")
    print("-" * 70)

    for old_file in files:
        new_name = build_new_name(old_file.stem, old_file.suffix)

        if not new_name:
            print(f"SKIP  | No coincide con el patrón: {old_file.name}")
            continue

        new_file = old_file.with_name(new_name)

        if old_file.name == new_name:
            print(f"OK    | Ya está correcto: {old_file.name}")
            continue

        if new_file.exists():
            print(f"SKIP  | Ya existe destino: {new_name}")
            continue

        print(f"RENAME| {old_file.name} -> {new_name}")

        if not dry_run:
            old_file.rename(new_file)

    print("-" * 70)
    print("Proceso terminado.")


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python rename_versions.py <carpeta> [--apply]")
        print("")
        print("Ejemplo:")
        print(r'  python rename_versions.py "D:\Anime\Season 01" --apply')
        sys.exit(1)

    directory = Path(sys.argv[1])
    dry_run = "--apply" not in sys.argv

    rename_files(directory, dry_run=dry_run)


if __name__ == "__main__":
    main()