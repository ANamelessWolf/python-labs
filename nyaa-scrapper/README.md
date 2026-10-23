# Nyaa Scrapper

Busca cada episodio de una serie en [nyaa.si](https://nyaa.si) y guarda el magnet link del **primer resultado**
en `output/<serie en camelCase>.txt`, uno por línea.

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
| `NYAA` | Usa `config\settings.json` |
| `NYAA -c ruta\otra.json` | Usa otro archivo de configuración |
| `NYAA --delay 2` | Espera 2 s entre búsquedas (default 1) |

## Estados en consola

| Estado | Significado |
|---|---|
| `[Copied]` | Se encontró y se guardó el magnet |
| `[Saved]` | El magnet ya estaba en el archivo de una ejecución anterior; no se repite |
| `[Duplicate]` | El primer resultado es el mismo magnet de un episodio anterior (p. ej. un batch); no se repite en el archivo |
| `[Not Found]` | La búsqueda no tuvo resultados |
| `[Error]` | Falló la petición HTTP |

El archivo de salida nunca se borra: si vuelves a correr con la misma `SERIE` (por ejemplo con otro `QUERY`),
los magnets nuevos se anexan al final. Para empezar de cero, borra el `.txt`.
