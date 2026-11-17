"""PirateBay Scrapper: busca episodios en un mirror de The Pirate Bay y guarda el magnet link elegido.

Uso:
    python pbay.py                          usa config/settings.json
    python pbay.py -c config/otra.json      usa otro archivo de configuracion
    python pbay.py -a / --auto              no pregunta: toma siempre el primer resultado
    python pbay.py -w / --wizard            configura settings.json paso a paso y busca
    python pbay.py -q "texto"               una sola busqueda; se agrega a output/general.txt
    python pbay.py -h                       ayuda con todos los comandos
    python pbay.py --delay 2                segundos de espera entre busquedas (default 1)
    python pbay.py -q "texto" --json        imprime el resultado como JSON (mensajes a stderr; implica --auto)
"""
import sys

from pbay_app.cli import main

if __name__ == "__main__":
    sys.exit(main())
