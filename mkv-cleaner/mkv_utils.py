import sys
import json
import subprocess


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
