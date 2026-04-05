import sys
import argparse
from pathlib import Path
from select_audio import do_select
from remove_audio import do_remove


def choose_mode() -> str:
    print("\nSelecciona una operación:")
    print("  [1] Seleccionar pista de audio (conservar una)")
    print("  [2] Eliminar pista de audio (conservar el resto)")
    while True:
        try:
            choice = int(input("\nOpción [1/2]: "))
            if choice in (1, 2):
                return "select" if choice == 1 else "remove"
            print("Opción inválida. Elige 1 o 2.")
        except ValueError:
            print("Entrada inválida. Ingresa 1 o 2.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gestiona las pistas de audio de un archivo MKV."
    )
    parser.add_argument("input", help="Ruta al archivo .mkv de entrada")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Modo eliminar: quita una pista de audio y conserva el resto",
    )
    parser.add_argument(
        "--track",
        type=int,
        default=None,
        metavar="N",
        help="Índice de la pista de audio (modo no interactivo)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Reemplaza el archivo original con el resultado (sin preguntar)",
    )
    args = parser.parse_args()

    input_file = args.input
    if not Path(input_file).is_file():
        print(f"Archivo no encontrado: {input_file}")
        sys.exit(1)

    # Determinar modo
    if args.remove:
        mode = "remove"
    elif args.track is not None:
        mode = "select"
    else:
        mode = choose_mode()

    if mode == "select":
        do_select(input_file, args.track, args.replace)
    else:
        do_remove(input_file, args.track, args.replace)


if __name__ == "__main__":
    main()
