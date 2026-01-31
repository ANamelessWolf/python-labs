import os
import sys
import subprocess

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a"}

def convert_to_flac(input_dir, output_dir):
    if not os.path.isdir(input_dir):
        print(f"❌ Carpeta de entrada no válida: {input_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        name, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            continue

        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, f"{name}.flac")

        print(f"🎵 Convirtiendo: {filename} → {name}.flac")

        command = [
            "ffmpeg",
            "-y",               # sobrescribe si existe
            "-i", input_path,
            "-vn",              # sin video
            "-acodec", "flac",
            output_path
        ]

        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"⚠️ Error al convertir {filename}")

    print("✅ Conversión finalizada")

def main():
    if len(sys.argv) != 3:
        print("Uso:")
        print("  python convertToFlac.py <carpeta_entrada> <carpeta_salida>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    convert_to_flac(input_dir, output_dir)

if __name__ == "__main__":
    main()
