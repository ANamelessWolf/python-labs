import sys
import json
import subprocess
import argparse
import os
from pathlib import Path


def get_tracks(input_file: str) -> list[dict]:
    result = subprocess.run(
        ["mkvmerge", "-J", input_file],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print(f"Error al leer el archivo: {result.stderr}")
        sys.exit(1)

    data = json.loads(result.stdout)
    return data.get("tracks", [])


def list_audio_tracks(tracks: list[dict]) -> list[dict]:
    audio_tracks = [t for t in tracks if t.get("type") == "audio"]
    if not audio_tracks:
        print("No se encontraron pistas de audio en el archivo.")
        sys.exit(1)

    print("\nPistas de audio disponibles:")
    for i, track in enumerate(audio_tracks):
        props = track.get("properties", {})
        lang = props.get("language", "und")
        codec = track.get("codec", "desconocido")
        track_id = track.get("id")
        print(f"  [{i}] Audio - {lang} - {codec}  (track id: {track_id})")

    return audio_tracks


def select_track(audio_tracks: list[dict], track_index: int | None) -> dict:
    if track_index is not None:
        if track_index < 0 or track_index >= len(audio_tracks):
            print(f"Índice {track_index} fuera de rango. Hay {len(audio_tracks)} pistas de audio.")
            sys.exit(1)
        return audio_tracks[track_index]

    while True:
        try:
            choice = int(input(f"\nElige el número de pista [0-{len(audio_tracks) - 1}]: "))
            if 0 <= choice < len(audio_tracks):
                return audio_tracks[choice]
            print("Número fuera de rango. Intenta de nuevo.")
        except ValueError:
            print("Entrada inválida. Ingresa un número entero.")


def build_output_path(input_file: str, track: dict) -> str:
    p = Path(input_file)
    props = track.get("properties", {})
    lang = props.get("language", "und")
    codec = track.get("codec", "unknown").replace("/", "-")
    return str(p.parent / f"{p.stem}_audio_{lang}_{codec}{p.suffix}")


def run_mkvmerge(input_file: str, track_id: int, output_file: str) -> None:
    cmd = ["mkvmerge", "-o", output_file, "-a", str(track_id), input_file]
    print(f"\nEjecutando: {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True, encoding="utf-8")
    if result.returncode not in (0, 1):  # 1 = warnings, still ok
        print("mkvmerge terminó con errores.")
        sys.exit(result.returncode)
    print(f"\nArchivo generado: {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Selecciona una pista de audio de un archivo MKV y genera un nuevo archivo con solo esa pista."
    )
    parser.add_argument("input", help="Ruta al archivo .mkv de entrada")
    parser.add_argument(
        "--track",
        type=int,
        default=None,
        metavar="N",
        help="Índice de la pista de audio a conservar (modo no interactivo)",
    )
    args = parser.parse_args()

    input_file = args.input
    if not Path(input_file).is_file():
        print(f"Archivo no encontrado: {input_file}")
        sys.exit(1)

    tracks = get_tracks(input_file)
    audio_tracks = list_audio_tracks(tracks)
    selected = select_track(audio_tracks, args.track)

    track_id = selected["id"]
    output_file = build_output_path(input_file, selected)
    run_mkvmerge(input_file, track_id, output_file)

    answer = input("\nDo you want to replace the original file? [y/N]: ").strip().lower()
    if answer == "y":
        os.replace(output_file, input_file)
        print(f"Original file replaced: {input_file}")
    else:
        print("Both files kept.")


if __name__ == "__main__":
    main()
