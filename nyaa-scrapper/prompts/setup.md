Quiero crear un aplicación de consola que actue como webscrapper en el sitio https://nyaa.si, la información de busqueda en la pagina se hace por url.

Ejemplo: el archivo de configuración define los siguiente:

```json
{
  "SITE": "https://nyaa.si",
  "SERIE": "Thousand-Year Blood War",
  "QUERY": "[ToonsHub] Thousand-Year Blood War SXXEXX [Multi-Subs]",
  "SEASON": [
    { "INDEX": 1, "START": 1, "END": 49 },
  ]
}
```

Significa que usara el query `[ToonsHub] Thousand-Year Blood War SXXEXX [Multi-Subs]`, el valor SXXEXX se cambia por S01, ya que solo hay un registro de index y E01-E49.

La url de busqueda para el primer valor queda como: 
https://nyaa.si/?f=0&c=0_0&q=%5BToonsHub%5D+Thousand-Year+Blood+War+S01E01+%5BMulti-Subs%5D
La segunda:
https://nyaa.si/?f=0&c=0_0&q=%5BToonsHub%5D+Thousand-Year+Blood+War+S01E02+%5BMulti-Subs%5D

Y así será sucesivamente.

Por cada pagina se busca el elemento, de la columna link el contenido del botón magnetic link
Este bloque es en la página

```html
<td class="text-center">
    <a href="/download/1902510.torrent"><i class="fa fa-fw fa-download"></i></a>
    <a href="magnet:?xt=urn:btih:5ec6cbf69c8c6d90eee994d9bc35d289c1c4f3df&amp;dn=%5BToonsHub%5D%20BLEACH%20Thousand-Year%20Blood%20War%20S01E01-S01E13%20Cour%201%201080p%20AMZN%20WEB-DL%20DDP2.0%20H.264%20%28BLEACH%3A%20Sennen%20Kessen-hen%2C%20Multi-Subs%29%20%5BBATCH%5D&amp;tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&amp;tr=udp%3A%2F%2Fopen.stealth.si%3A80%2Fannounce&amp;tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&amp;tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&amp;tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce"><i class="fa fa-fw fa-magnet"></i></a>
</td>
```

Solo me intera el primer registro del resultado de la busqueda el href con el magnet link, para ese ejemplo sería

```
magnet:?xt=urn:btih:5ec6cbf69c8c6d90eee994d9bc35d289c1c4f3df&dn=%5BToonsHub%5D%20BLEACH%20Thousand-Year%20Blood%20War%20S01E01-S01E13%20Cour%201%201080p%20AMZN%20WEB-DL%20DDP2.0%20H.264%20%28BLEACH%3A%20Sennen%20Kessen-hen%2C%20Multi-Subs%29%20%5BBATCH%5D&tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&tr=udp%3A%2F%2Fopen.stealth.si%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce
```

Cada magnetic link se deja en la carpeta output Z:\dev\py\python-labs\nyaa-scrapper\output uno por línea
El archivo se llamara como el nombre del campo SERIE, todo en camel case con extensión .txt

Para este ejemplo será:
thousand-YearBloodWar.txt

Crea un environment en CONDA para WebScrapper, ese ambiente se usará para scripts similares

El comando se define con un py, pero tendra como capa un bat, para que pueda añadirlo despues a mi bin folder que esta en esta ruta: Z:\bin, agregar formato de colores en los reportes de consola, ahí puedes ser creativo para mostrar estos datos.

Por ejemplo mostrar algo así
Thousand-Year Blood War
    Episode 1: [ToonsHub] BLEACH Thousand-Year Blood War - S01E01 (JAP 2160p 4K x264 AAC) [Multi-Subs] [Copied]
    Episode 2: [ToonsHub] BLEACH Thousand-Year Blood War - S02E02 (JAP 2160p 4K x264 AAC) [Multi-Subs] [Not Found]
    ....

Este proyecto python-labs, son muchas apps pequeñas asi que todo lo que trabajes para esta app será bajo la carpeta de nyaa-scrapper, en la ruta Z:\dev\py\python-labs\nyaa-scrapper. 

Si tienes una duda consultame antes de comenzar a desarrollar el comando de consola.

