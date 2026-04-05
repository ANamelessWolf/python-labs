import sys
import os
import subprocess
from pathlib import Path
from mkv_utils import get_tracks, list_audio_tracks


def select_track(audio_tracks: list[dict], track_index: int | None) -> dict:
    if track_index is not None:
        if track_index < 0 or track_index >= len(audio_tracks):
            print(f"Índice {track_index} fuera de rango. Hay {len(audio_tracks)} pistas de audio.")
            sys.exit(1)
        return audio_tracks[track_index]

    while True:
        try:
            choice = int(input(f"\nElige el número de pista a conservar [0-{len(audio_tracks) - 1}]: "))
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


def do_select(input_file: str, track_index: int | None, replace: bool) -> None:
    tracks = get_tracks(input_file)
    audio_tracks = list_audio_tracks(tracks)
    selected = select_track(audio_tracks, track_index)

    track_id = selected["id"]
    output_file = build_output_path(input_file, selected)
    run_mkvmerge(input_file, track_id, output_file)

    if replace:
        os.replace(output_file, input_file)
        print(f"Archivo original reemplazado: {input_file}")
    elif track_index is None:  # modo interactivo
        answer = input("\n¿Deseas reemplazar el archivo original? [y/N]: ").strip().lower()
        if answer == "y":
            os.replace(output_file, input_file)
            print(f"Archivo original reemplazado: {input_file}")
        else:
            print("Ambos archivos conservados.")
    else:
        print("Ambos archivos conservados.")
