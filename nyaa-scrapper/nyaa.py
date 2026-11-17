"""Nyaa Scrapper: busca episodios en nyaa.si y guarda el magnet link elegido.

Uso:
    python nyaa.py                          usa config/settings.json
    python nyaa.py -c config/otra.json      usa otro archivo de configuracion
    python nyaa.py -a / --auto              no pregunta: toma siempre el primer resultado
    python nyaa.py -w / --wizard            configura settings.json paso a paso y busca
    python nyaa.py -q "texto"               una sola busqueda; se agrega a output/general.txt
    python nyaa.py -h                       ayuda con todos los comandos
    python nyaa.py --delay 2                segundos de espera entre busquedas (default 1)
    python nyaa.py -q "texto" -ln es        solo resultados cuya pagina mencione el idioma (audio/subs)
    python nyaa.py -q "texto" --json        imprime el resultado como JSON (mensajes a stderr; implica --auto)
"""
import sys

from nyaa_app.cli import main

if __name__ == "__main__":
    sys.exit(main())
