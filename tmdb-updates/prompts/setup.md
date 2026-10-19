Quiero crear un aplicación de consola que se revise mis librerías y me diga si hay noticias de las series o peliculas, se utilizará el API de The Movie Database, se tendra un archivo de configuración en config/settings.json, ahí se tendrán las rutas en el nodo MEDIA uno para series y otro para movies.

La idea es tener un archivo de JSON que indique que series estan incompletas y cuales estan terminadas, si una serie esta terminada, ya no entra al proceso de busqueda de updates. Si la serie esta incompleta, se buscará que temporada se tienen actualmente y cuales episodios ya estan disponibles para esta. Ejemplo:

Se tiene la serie de South Park, en M:\TV\South Park, ahí cada temporada se guarda como "Season 1" o a veces "Season 01". Cada Season es una carpeta y en cada carpeta hay archivos, nos interesan para la busqueda. Que tengan el formato SXXEXX, con ese valor podemos identificar si se tiene el capitulo de la serie en la carpeta. Si el archivo no tiene ese formato se agregará un TAG NAMING_ERROR en el reporte de esa temporada que esa serie tiene formato incorrecto y debe arreglarse a mano.

Si la carpeta tiene correcto, se validará que el numero de episodios que tenga la serie coincida con el que dice The movie database, se puede hacer una petición de la serie y obtener todos los datos de ella.

Ahora si la temporada esta completa coinicide con lo de movie database, le agregamos el TAG en el reporte de COMPLETE, 
Si la temporada esta incompleta, se agrega INCOMPLETE
Si la temporada no existe en la carpeta de la serie se pone MISSING

En este escaneo general se verá
El comando podra ser `TMDB status -tv`

Bad Apples [Released] INCOMPLETE
Skins [Ended] OK
...
South Park [Returning Series]
    Season 01 COMPLETE
    Season 02 NAMING_ERROR
    Season 03 COMPLETE
    Season 04 MISSING
    Season 05 INCOMPLETE
    ...
Steven Universe [Ended] INCOMPLETE


Ahora si se pide el detalle de la serie digamos South PARK, nos puede listar en arbol, que capitulos faltan por serie, cual estan proximos por Ejemplo:

El comando podra ser `TMDB status -sn "South Park"`
South Park
    Season 01 COMPLETE
    Season 02 NAMING_ERROR
    Season 03 COMPLETE
    Season 04 MISSING
    Season 05 INCOMPLETE
        S01E01 OK
        S01E02 MISSING (Released on October 10th 2026)
        S01E03 AVAILABLE ON November 12th 2026
        S01E04 AVAILABLE ON November 12th 2026

Tambien se tendra un comando para ver que capitulos de la serie estan por salir, para eso se usará

El comando podra ser `TMDB updates`, seleccionara de las Seasons con TAG INCOMPLETE, aquellas donde exista un MISSING o un AVAILABLE ON. En un rango de fechas del usando como base el dia actual, el rango inicial será dia actual menos dos meses en el pasado y el final la fecha más una semana

Otro comando para listar las series que tengo
El comando podra ser `TMDB list`, Las muestra en lista sin el detalle de temporada y el tag de serie que es el Status de la serie que tiene el API de TMDB, [Released], [Ended], [Returning Series], etc.

Para ejecutar un scan completo que genera la lista que consultan los otros comandos se usará
El comando podra ser `TMDB scan`, las series que esten en el archivo de consulta como [Ended] y COMPLETE, no se vuelven a escanear con el API, a menos que se ejecute con `TMDB scan`.

Se guardara en la serie el tmdbId, por ejemplo un 1198654. Esto es por que si se selecciona mal la serie, se pueda editar en el JSON del resultado del scan y asignar uno correcto.

Para arreglar la serie, se usará el comando `TMDB fix -sn "South Park"`, con esto jalará la información de metadatos correctos, usara el tmdbId en lugar del nombre de la carpeta de la serie

Si sequiere actualizar solo una serie se puede correr el comando `TMDB scan -sn "South Park"`

Por el momento nos concentraremos solo en las series y no en las peliculas, para las peliculas pensaba mostrar aquellas que tengan trilogias pendientes.

Crea un environment en CONDA para TMDB

El comando se define con un py, pero tendra como capa un bat, para que pueda añadirlo despues a mi bin folder que esta en esta ruta: Z:\bin, se tendra un menu interactivo y formato de colores en los reportes de consola, ahí puedes ser creativo para mostrar estos datos.

Este proyecto python-labs, son muchas apps pequeñas asi que todo lo que trabajes para esta app será bajo la carpeta de tmdb-updates, en la ruta Z:\dev\py\python-labs\tmdb-updates. 

Si tienes una duda consultame antes de comenzar a desarrollar el comando de consola.

