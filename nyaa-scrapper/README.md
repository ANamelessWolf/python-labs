# Nyaa Scrapper

Busca cada episodio de una serie en [nyaa.si](https://nyaa.si) y guarda el magnet link en
`output/<serie en camelCase>.txt`, uno por línea. Si hay varios resultados te pregunta cuál agregar.

## Instalación

```powershell
conda env create -f environment.yml      # crea el entorno "WebScrapper" (compartido con otros scrapers)
copy config\settings.example.json config\settings.json
```

`NYAA.bat` usa rutas absolutas, así que puedes copiarlo a `Z:\bin`.

## Configuración

```json
{
  "SITE": "https://nyaa.si",
  "SERIE": "Thousand-Year Blood War",
  "QUERY": "[ToonsHub] Thousand-Year Blood War SXXEXX [Multi-Subs]",
  "SEASON": [
    { "INDEX": 1, "START": 1, "END": 49 }
  ]
}
```

| Clave | Descripción |
|---|---|
| `SITE` | URL base del sitio |
| `SERIE` | Nombre de la serie; define el archivo de salida (`thousand-YearBloodWar.txt`) |
| `QUERY` | Texto de búsqueda; `SXXEXX` se reemplaza por `S01E01`, `S01E02`, ... |
| `SEASON` | Lista de temporadas: `INDEX` = número de temporada, `START`/`END` = rango de episodios |

## Comandos

| Comando | Qué hace |
|---|---|
| `NYAA` | Usa `config\settings.json`; si hay varios resultados muestra una tabla y pregunta cuál agregar |
| `NYAA -c ruta\otra.json` | Usa otro archivo de configuración |
| `NYAA -a` (o `--auto`) | No pregunta: toma siempre el primer resultado |
| `NYAA -w` (o `--wizard`) | Wizard: pregunta sitio, serie, query, temporada inicial y final (vacía = solo una) y el rango de episodios de cada temporada; guarda `settings.json` y busca. Acepta `-a` |
| `NYAA -q "[ToonsHub] Thousand-Year Blood War S01E01"` | Una sola búsqueda; el magnet elegido se agrega a `output\general.txt`. Acepta `-a` |
| `NYAA -h` | Ayuda con todos los modos, opciones y ejemplos |
| `NYAA --delay 2` | Espera 2 s entre búsquedas (default 1) |

La tabla muestra nombre, tamaño, seeds (▲) y leechers (▼) de cada torrent. Al elegir: escribe el número de la fila,
`Enter` toma la 1 y `0` omite el episodio.

## Estados en consola

| Estado | Significado |
|---|---|
| `[Copied]` | Se guardó el magnet elegido (o el único resultado) |
| `[Saved]` | Uno de los resultados ya está en el archivo (de esta u otra ejecución, p. ej. un batch); no pregunta otra vez |
| `[Skipped]` | Elegiste `0` |
| `[Not Found]` | La búsqueda no tuvo resultados |
| `[Error]` | Falló la petición HTTP |

El archivo nunca se borra: si vuelves a correr con la misma `SERIE` (por ejemplo con otro `QUERY`), los magnets
nuevos se anexan al final, y cada elección se guarda en cuanto la haces (si cancelas con `Ctrl+C` no se pierde lo
ya elegido). Para empezar de cero, borra el `.txt`.
