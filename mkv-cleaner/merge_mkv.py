import os
import sys
import tempfile
import subprocess
from pathlib import Path


def do_merge(file1: str, file2: str, output: str | None) -> None:
    p1 = Path(file1)
    p2 = Path(file2)

    for p in (p1, p2):
        if not p.is_file():
            print(f"Archivo no encontrado: {p}")
            sys.exit(1)

    out_path = Path(output) if output else p1.parent / f"{p1.stem}_merged.mkv"
    if out_path.suffix.lower() != ".mkv":
        out_path = out_path.with_suffix(".mkv")

    print(f"\nCombinando:")
    print(f"  [1] {p1.name}")
    print(f"  [2] {p2.name}")
    print(f"  ->  {out_path}\n")

    # ffmpeg concat demuxer: copia todos los streams sin re-encodear
    # ffmpeg en Windows necesita forward slashes y sin comillas simples escapadas
    s1 = p1.as_posix().replace("'", "\\'")
    s2 = p2.as_posix().replace("'", "\\'")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(f"file '{s1}'\n")
        f.write(f"file '{s2}'\n")
        filelist = f.name

    print(f"[debug] filelist: {filelist}")
    print(open(filelist, encoding="utf-8").read())

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", filelist,
                "-c", "copy",
                str(out_path),
            ],
        )
    except FileNotFoundError:
        os.unlink(filelist)
        print("Error: ffmpeg no encontrado en el PATH.")
        print("Instálalo con:  conda install -c conda-forge ffmpeg")
        sys.exit(1)
    finally:
        if os.path.exists(filelist):
            os.unlink(filelist)

    if result.returncode != 0:
        print(f"Error al combinar los archivos. (código {result.returncode})")
        sys.exit(result.returncode)

    print(f"\nArchivo generado: {out_path.resolve()}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Concatena dos archivos MKV: primero el 1, luego el 2."
    )
    parser.add_argument("file1", help="Primer archivo MKV")
    parser.add_argument("file2", help="Segundo archivo MKV")
    parser.add_argument("-o", "--output", default=None, help="Ruta del archivo de salida (sin .mkv se agrega automático)")
    args = parser.parse_args()

    do_merge(args.file1, args.file2, args.output)
