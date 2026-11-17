Quiero crear un aplicación de consola que se conecte a mi cuenta de ytMusic, podemos crear un archivo de configuración. Ahí puedes definir las variables que necesitas para conectarte ya se por API, o por otra forma que creas conveniente.

La idea es tener un formato de playlist en JSON, lo puedes definir en la carpeta de Assets. Ahi estará una playlist con un nombre que le de el usuario. Ejemplo "Radiohead", tomara la playlist de Inputs y la sincronizara con la playlist remota.

Aquí existen dos casos que no exista la playlist, se busca por nombre. Se crea y es un dump de las canciones del JSON a la playlist remota.

Si ya existe se borra y se cambia por el contenido que tiene la playlist en inputs.

Como buscas canción, primero por nombre, artista y album. Como es youtube es dificil que no este, preferir la canción oficial, si no la mas reproducida. Probablemente el album pueda estar vacio, por ejemplo canciones unreleased o reproducidas en vivo o covers. Pero es obligatorio nombre y artista.

En consola se podrá hacer lo siguiente, 
listar playlist de inputs, 
Seleccionar playlist a subir
Sincronizar todas las playlists
Salir

Para este comando, usaremos conda por lo que deberas crear un nuevo ambiente para ytMusic, y usarlo para ejecutar los comandos. El comando se define con un py, pero tendra como capa un bat, para que pueda añadirlo despues a mi bin folder que esta en esta ruta: Z:\bin

Este proyecto python-labs, son muchas apps pequeñas asi que todo lo que trabajes para esta app será bajo la carpeta de yt-music-playlist, en la ruta Z:\dev\py\python-labs\yt-music-playlist

