# Generador-Manual-de-Letra-de-Canciones

Con este programa se puede generar la letra de canciones pulsando manualmente el inicio de las
letras guardadas en txt, obteniendo así un vídeo mp4 de las letras generadas.

Tú escuchas la canción y pulsas **ESPACIO** justo cuando empieza cada línea de la letra. Al
terminar, el programa guarda los tiempos (JSON) y genera el video con el mismo estilo del
generador automático:

* Al inicio, el **título grande y al centro**.
* **Derecha (blanco):** lo que viene — máximo 2 líneas; una línea de una sola palabra
  (el "Jesús" de un coro) aparece sola.
* **Izquierda (amarillo):** lo que se está cantando. Al empezar cada parte, el texto se desplaza
  de derecha a izquierda y se vuelve amarillo.

No usa reconocimiento de voz ni GPU: los tiempos son exactamente los que marcas.

## Instalación (una sola vez)

Requiere Python 3.9 o superior (en Windows, Python 3.12 funciona bien).

```
py -3.12 -m pip install -r requirements.txt
```

## Uso

1. Pon en la carpeta `canciones/` el audio y la letra **con el mismo nombre**:
   `Tómalo - Hillsong.mp3` y `Tómalo - Hillsong.txt`.
2. En VS Code pulsa **Ctrl+Shift+B** (o escribe `py -3.12 marcar.py` en la terminal).
3. Elige el MP3 en la ventana que aparece. Si hay un `.txt` con el mismo nombre se usa solo;
   si no, te pide la letra.
4. Se abre una página en el navegador. Pulsa **ESPACIO** para iniciar la canción y luego
   **ESPACIO** cada vez que empiece la línea que aparece a la derecha.
5. Al terminar la canción (o con el botón **Terminar y generar video**) se crean junto al audio:
   * `Tómalo - Hillsong_letra.letra.json` — los tiempos marcados
   * `Tómalo - Hillsong_letra.mp4` — el video

También funciona con rutas: `py -3.12 marcar.py "ruta\cancion.mp3" "ruta\letra.txt"`.

### Teclas

| Tecla | Acción |
|---|---|
| **Espacio** | iniciar la canción · luego, marcar el inicio de la siguiente línea |
| **Shift** | borrar la última marca (por si pulsaste antes de tiempo o de más) |
| P | pausa / continuar |
| ← | retroceder 5 s (borra las marcas de ese tramo para volver a marcarlas) |
| Enter | *(opcional)* marcar el fin de una parte antes de un instrumental, para que el texto no se quede en pantalla |
| botón ↺ en una línea | rehacer desde esa línea (vuelve 3 s antes y sigue sonando) |

En la parte de arriba puedes:
* **Velocidad 0,9× o 0,75×** para marcar con más calma (los tiempos guardados son los reales).
* **Adelanto** (0,15 s por defecto): se resta a cada marca para compensar el tiempo de reacción.
* Cambiar el **título** que aparece al inicio del video.

### Corregir una canción ya marcada

Vuelve a abrirla con Ctrl+Shift+B: la página carga los tiempos guardados. Pulsa **↺** en la
línea desde la que quieras corregir, márcala de nuevo y pulsa **Terminar y generar video**.
(Si cambiaste el texto del `.txt`, se empieza de cero.)

Para rehacer solo el video con los tiempos guardados (sin marcar), usa la tarea
*Rehacer solo el video* o `py -3.12 marcar.py --solo-video`.

## Formato de la letra (.txt)

* Una línea de texto = una parte que se marca con ESPACIO.
* Una línea en blanco o un marcador como `[Coro]` separa estrofas (en el video, la estrofa
  nueva empieza en una página nueva). Esas líneas no se marcan.
* Escribe la letra completa tal como se canta, repitiendo los coros.

```
[Verso 1]
Tu amor me sostiene en la tormenta
Tu paz me guarda cada día

[Coro]
Jesús
Santo, santo, santo es el Señor
```

## Opciones

`--titulo "..."`, `--resolucion 1920x1080`, `--fps 30`, `--tamano-letra 1.2` (letra más grande
si cabe), `--solo-video`, `--no-abrir` (no abre el navegador; muestra la dirección en la terminal).

## Cómo funciona

`marcar.py` abre un pequeño servidor solo en tu computador (127.0.0.1) que muestra la página,
reproduce el audio y recibe tus marcas. No necesita internet. Al terminar escribe el JSON y genera
el MP4 con ffmpeg (incluido en `imageio-ffmpeg`), con el audio original de la canción.

El JSON tiene el mismo formato que el del generador automático, así que también lo puede usar
ese programa (`--desde-json`).

## Pruebas

```
py -3.12 -m unittest discover -s generador_manual/tests -t .
```
