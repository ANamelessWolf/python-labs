Crea un scrapper que visite el sitio https://www.setlist.fm, busque un concierto por banda y fecha del evento. Usara una interfaz de consola, similar a otros proyectos como nyaa-scrapper y yt-music-playlist

Ejemplo el comando será similar a "SetListFM" -b "Gorillaz" -d "11/20/2026"

Donde 
-b b:band band=Gorillaz
-d d:event date in format dd/mm/yyyy

La url que debería elegir es
https://www.setlist.fm/setlist/gorillaz/2026/autodromo-hermanos-rodriguez-corona-stage-mexico-city-mexico-6b741226.html

Lo puedes hacer con API, si es que existe uno para setlist, si es necesario hago una cuenta y generamos una API key, si no visitando el sitio y extrayendo la
información.

La salida será de esta manera.


Gorillaz Setlist
Corona Stage at Autódromo Hermanos Rodríguez, Mexico City, Mexico
Tour: The Mountain Tour

Songs list

The Mountain / The Mountain
Tomorrow Comes Today / Gorillaz


Donde el formato de las canciones será 
Song / Album


Si se agrega la opción de --json, se imprimirá con el siguiente formato

{
  "name": "Gorillaz Corona Stage 2026",
  "description": "Gorillaz The Mountain Tour at Corona Stage at Autódromo Hermanos Rodríguez, Mexico City, Mexico",
  "privacy": "PUBLIC",
  "songs": [
    { "title": "The Mountain", "artist": "Gorillaz", "album": "The Mountain" },
    { "title": "Tomorrow Comes Today", "artist": "Gorillaz", "album": "Gorillaz" },
  ]
}

Otro comando será listar eventos de una banda por año "SetListFM" -b "Gorillaz" -y "2026"

[11/26/2026] Gorillaz at Estadio Mario Alberto Kempes, Córdoba, Argentina 
[11/20/2026] Gorillaz at Corona Capital 2026

Con JSON sera de esta manera

{
  "band": "Gorillaz",
  "year": "2026",
  "Tour": [
    { "title": "Gorillaz at Estadio Mario Alberto Kempes, Córdoba, Argentina", "venue": "Estadio Mario Alberto Kempes, Córdoba, Argentina", "url": "https://www.setlist.fm/setlist/gorillaz/2026/autodromo-hermanos-rodriguez-corona-stage-mexico-city-mexico-6b741226.html" },
    { "title": "Gorillaz at Corona Capital 2026", "venue": "Autódromo Hermanos Rodríguez, Mexico City, Mexico", "url": "https://www.setlist.fm/setlist/gorillaz/2026/autodromo-hermanos-rodriguez-corona-stage-mexico-city-mexico-6b741226.html" },
  ]
}

Usa colores similares a los otros proyectos de scrapper, y crea un bat para los comandos.