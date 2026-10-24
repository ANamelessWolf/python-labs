# PirateBay Scrapper

Busca cada episodio de una serie en un mirror de The Pirate Bay (p. ej. `https://thepiratebay.bond`) y guarda el
magnet link en `output/<serie en camelCase>.txt`, uno por línea. Si hay varios resultados te pregunta cuál agregar.

## Instalación

Usa el mismo entorno conda que `nyaa-scrapper`:

```powershell
conda env create -f ..\nyaa-scrapper\environment.yml     # solo si aún no existe "WebScrapper"
copy config\settings.example.json config\settings.json
```

`PBAY.bat` usa rutas absolutas, así que puedes copiarlo a `Z:\bin`.

## Configuración

```json
{
  "SITE": "https://thepiratebay.bond",
  "SERIE": "Helluva Boss",
  "QUERY": "Helluva Boss SXXEXX",
  "SEASON": [
    { "INDEX": 3, "START": 1, "END": 8 }
  ]
}
```

| Clave | Descripción |
|---|---|
| `SITE` | URL del mirror; si se cae, cámbialo por otro |
| `SERIE` | Nombre de la serie; define el archivo de salida (`helluvaBoss.txt`) |
| `QUERY` | Texto de búsqueda; `SXXEXX` se reemplaza por `S03E01`, `S03E02`, ... |
| `SEASON` | Lista de temporadas: `INDEX` = número de temporada, `START`/`END` = rango de episodios |

La búsqueda queda como `https://thepiratebay.bond/search/Helluva%20Boss%20S03E01/1/99/0`.

## Comandos

| Comando | Qué hace |
|---|---|
| `PBAY` | Usa `config\settings.json`; si hay varios resultados muestra una tabla y pregunta cuál agregar |
| `PBAY -c ruta\otra.json` | Usa otro archivo de configuración |
| `PBAY -a` (o `--auto`) | No pregunta: toma siempre el primer resultado |
| `PBAY -w` (o `--wizard`) | Wizard: pregunta sitio, serie, query, temporada inicial y final (vacía = solo una) y el rango de episodios de cada temporada; guarda `settings.json` y busca. Acepta `-a` |
| `PBAY -q "Helluva Boss S03E01"` | Una sola búsqueda; el magnet elegido se agrega a `output\general.txt`. Acepta `-a` |
| `PBAY -h` | Ayuda con todos los modos, opciones y ejemplos |
| `PBAY --delay 2` | Espera 2 s entre búsquedas (default 1) |

La tabla muestra nombre, tamaño, seeds (▲) y leechers (▼) de cada torrent. Al elegir: escribe el número de la fila, `Enter` toma la 1 y `0` omite el episodio.

## Estados en consola

| Estado | Significado |
|---|---|
| `[Copied]` | Se guardó el magnet elegido (o el único resultado) |
| `[Saved]` | Uno de los resultados ya estaba en el archivo de una ejecución anterior; no pregunta otra vez |
| `[Skipped]` | Elegiste `0` |
| `[Not Found]` | La búsqueda no tuvo resultados |
| `[Error]` | Falló la petición HTTP |

El archivo nunca se borra: los magnets nuevos se anexan al final, y cada elección se guarda en cuanto la haces
(si cancelas con `Ctrl+C` no se pierde lo ya elegido). Para empezar de cero, borra el `.txt`.
