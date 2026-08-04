# Vigilante

Mira dos plataformas de clase cada pocos minutos y te avisa al chat cuando
aparece algo nuevo. Corre gratis en GitHub, sin computadora prendida.

Version de este documento: **v5.3**

---

## 1. Que hace

- Avisa de guias, tareas, foros y cualquier archivo nuevo.
- Junta un trabajo con su consigna, su fecha y sus adjuntos en **un solo
  aviso**, no en cinco.
- Te baja el archivo y te lo deja en el chat, listo para abrir.
- Le pide a una IA un resumen corto de lo que subieron. Ese resumen aparece
  dentro de una cita con barra al costado. Esa barra significa: **esto lo
  escribio una maquina**. Todo lo de afuera es dato sacado de la plataforma.
- Te recuerda las entregas antes de que venzan, con la insistencia que vos
  elijas por ramo.
- **Le hablas normal y hace cosas.** Le decis "recordame en 5 minutos sacar
  la ropa" y el programa te muestra una confirmacion antes de tocar nada.
- **Le preguntas dudas de uso** y contesta, porque la IA tiene adentro el
  manual del bot.
- Tiene un panel de botones. No hace falta acordarse de ningun comando.
- Se actualiza de un clic con `ACTUALIZAR.bat` y te avisa cuando hay version
  nueva.

---

## 2. Los archivos

| Archivo | Para que sirve |
|---|---|
| `watcher.py` | el motor |
| `panel.py` | las pantallas de botones |
| `comandos.py` | los comandos y los toques |
| `notificar.py` | todo lo que sale al chat |
| `ia.py` | los resumenes, la charla y las ordenes habladas |
| `almacen.py` | la memoria |
| `fuentes.py` | la configuracion |
| `version.py` | el numero de version y la lista de novedades |
| `secretos.py` | lee `mis_datos.txt` cuando corres en tu maquina |
| `actualizar.py` | aplica el parche, respalda y sube todo a GitHub |
| `ACTUALIZAR.bat` | el doble clic que llama al de arriba |
| `probar_local.py` | la prueba antes de subir |
| `mis_datos.txt` | tus claves. **NUNCA se sube** |
| `.github/workflows/watch.yml` | la agenda de GitHub |
| `PROBLEMAS.md` | donde anotas lo que no te gusta |

Para que funcione en GitHub hacen falta todos menos `mis_datos.txt`.

---

## 3. Puesta en marcha

### a. En tu computadora primero

1. Instala Python 3.11 o mas nuevo.
2. Abre la terminal en esta carpeta y escribi:
   ```
   pip install -r requirements.txt
   ```
3. Abri `mis_datos.txt` y completa lo que puedas. Con `TG_TOKEN` y
   `TG_CHAT` ya alcanza para probar.
4. Corre:
   ```
   python probar_local.py
   ```
   Te va a mandar mensajes de prueba y decir que anda y que no.

Consejo: **no tengas la carpeta adentro de OneDrive.** Sincroniza mientras
el programa escribe y se pisan los archivos. Mejor algo corto como `C:/bot`.

### b. En GitHub

1. Crea una cuenta con un apodo. No pongas tu nombre real.
2. Crea un repositorio **publico**. Publico es a proposito: asi los minutos
   son ilimitados. En este codigo no hay nada que te identifique.
3. Sube todos los archivos menos `mis_datos.txt`.
4. En **Settings > Secrets and variables > Actions**, carga uno por uno los
   mismos nombres que estan en `mis_datos.txt`.
5. Anda a **Actions** y prendelo.
6. Si te quedo el workflow de ejemplo que trae GitHub ("Python Package using
   Conda"), borralo. El unico que sirve es `watch.yml`.

---

## 3 bis. Actualizar de un clic

Cuando te llegue un parche en zip:

1. Guarda el zip en Descargas. **No lo descomprimas.**
2. Doble clic en `ACTUALIZAR.bat`.
3. El programa hace cuatro cosas solo:
   - **[1]** copia todo lo que tenes hoy a la carpeta `respaldos`
   - **[2]** busca el zip mas nuevo en Descargas y reemplaza los archivos
   - **[3]** revisa que el token tenga permiso
   - **[4]** sube todo a GitHub
4. En un rato te llega al chat el aviso **version nueva** con la lista de
   cambios. Ese mensaje no se borra solo.

Si te pide el token, seguile los pasos que muestra por pantalla. **Nunca
tenes que editar un archivo a mano.** Si algo sale mal, en `respaldos` esta
la version anterior completa.

Para ver en que version estas: **Ajustes > Version y novedades**, o escribi
`/version`.

---

## 4. Los datos que necesita

| Nombre | Que es | Obligatorio |
|---|---|---|
| `SITE_A_URL` `SITE_A_USER` `SITE_A_PASS` | la plataforma propia | si |
| `SITE_B_URL` `SITE_B_USER` `SITE_B_PASS` | el aula virtual | si |
| `CAL_URL` | el calendario privado de la plataforma A | no |
| `CAL_URL_B` | el calendario privado de la plataforma B | no |
| `TG_TOKEN` `TG_CHAT` | la mensajeria | si |
| `GH_TOKEN` | token clasico con `gist`, `repo` y `workflow` | recomendado |
| `GH_REPO` `GH_RAMA` | a donde sube el actualizador. Se llenan solos | no |
| `GIST_ID` | se llena solo la primera vez | no |
| `IA_KEY` | la clave de la IA | no |

Sin `GH_TOKEN` el bot igual funciona, pero guarda la memoria en el propio
repositorio y solo en forma de huellas, sin texto legible. No perdes avisos,
perdes las notas y los titulos guardados.

Sin `IA_KEY` el bot funciona igual y los avisos salen sin la linea del
cerebro. Lo que si perdes son las ordenes habladas y la charla. El resto,
incluida la pantalla de recordatorios, anda igual.

**Sobre las casillas del token:** `gist` es para la memoria, `repo` es para
que el actualizador pueda subir, y `workflow` es para que la corrida arranque
al toque en vez de esperar al reloj. Si le falta `repo`, GitHub contesta
**404** y no "prohibido", asi que no te confundas: 404 casi siempre es
permiso, no archivo perdido.

**Sobre la clave de la IA:** las claves nuevas empiezan con `AQ.` y **solo
funcionan mandadas en la cabecera**, no pegadas en la direccion. El bot ya lo
hace bien. Si la IA se apaga sola, sacate una nueva en
`aistudio.google.com/apikey` y prendela con `/ia on`.

---

## 5. El panel

Un mensaje que se edita a si mismo. El estado esta escrito adentro de cada
boton, asi que sabes donde estas parado sin abrir nada.

```
Vigilante                       todo en orden
6 ramos - 3 pendientes - 2 nuevas hoy

[ Pendientes (3) ]   [ Recordar ]
[ Novedades (2) ]    [ Semana ]
[ Ramos ]            [ Avisos ]
[ Pausa: no ]        [ Noche: si ]
[ IA: si ]           [ Ajustes ]

actualizado 02:47
```

En **Ajustes** tenes: Revisar ahora, Ayuda, Perfiles de aviso, Version y
novedades, Atajos de abajo, Diagnostico y Exportar todo.

Navegar entre pantallas no manda mensajes nuevos, reescribe ese mismo.

**Los atajos de abajo son un interruptor.** En Ajustes > Atajos de abajo los
prendes o los apagas. Ojo con una cosa rara de la mensajeria: esa botonera
vive pegada al mensaje que la trajo, asi que si borras ese mensaje, la
botonera se va con el.

---

## 5 bis. Recordatorios, la pantalla nueva

Boton **Recordar** en la primera fila del panel. Son **dos toques**:

1. Elegis cuando: `15 min`, `1 hora`, `3 horas`, `Hoy 21:00` o `Manana 9:00`.
2. Escribis que te recuerdo. Listo, queda anotado.

No tenes que escribir ninguna fecha. Abajo te lista los que tenes vivos, y
cada uno trae su propia fila con tres botones:

- **hecho**, lo saca de la lista
- **+1h**, lo corre una hora
- **tacho**, lo borra

Si preferis escribir, `/recordar` sigue andando y ahora entiende mucho mas:

```
/recordar 5m sacar la ropa
/recordar en 20 minutos llamar
/recordar 3h estudiar
/recordar hoy 21:00 leer
/recordar manana 09:00 imprimir
/recordar lunes 18:45 entregar
```

**Si nombras el dia de hoy y la hora todavia no paso, es hoy.** Antes se iba
a la semana que viene, ya esta arreglado.

Tus recordatorios suenan **una sola vez**, a la hora que pediste. No es una
alarma que insiste. Los que ya pasaron se archivan solos.

---

## 5 ter. Hablarle sin comandos

Le escribis en castellano y hace cosas:

```
recordame en 5 minutos sacar la ropa
callate 3 horas
no me avises mas de calculo
quiero que me insistas mas con termo
revisa ahora
ya entregue el informe
```

**La IA solo traduce, el programa decide.** Antes de tocar nada te llega una
confirmacion armada por el codigo:

```
Confirmame esto
Recordatorio: sacar la ropa
Cuando: hoy a las 20:05 (en 5 minutos)
Suena una sola vez.
Estos datos los resolvi yo, no la IA.
[ Dale ]   [ No ]
```

Esa fecha la calculo Python, no la IA. Si la IA entendio cualquier cosa, lo
ves antes de que pase y tocas **No**.

Tambien le podes preguntar como funciona el bot y te contesta, porque tiene
el manual adentro. Para todo esto la IA tiene que estar prendida (`/ia on`).

---

## 6. Los comandos, por si preferis escribir

En `/ayuda` la lista sale **apretable**: tocas el comando y se manda solo.

```
/panel        abre el panel
/pendientes   que te falta entregar
/ultimo       lo ultimo que aparecio
/semana       los ultimos 7 dias
/recordar     abre la pantalla de recordatorios
/resumen ramo calculo    resumen de ese ramo, con IA
/resumen viernes 20:00   cambia el dia y la hora del resumen
/pausa 3      callate 3 horas
/noche        prende o apaga los avisos de madrugada
/estado       diagnostico, incluye la version
/perfil       muestra los perfiles y como cambiarlos
/perfil apretado termo   cuanto insistir en ese ramo
/callar calculo          silenciar 14 dias
/revisar      revisa ahora
/ia on        prende o apaga la IA
/atajos       prende o apaga la botonera de abajo
/limpiar      borra la basura del chat
/version      en que version estas y que trae
/exportar     te manda todo en un archivo
/ayuda
```

---

## 6 bis. Cuanto te insiste cada perfil

Se elige por ramo, en **Ajustes > Perfiles de aviso** o con `/perfil`.

| Perfil | Te avisa |
|---|---|
| `suave` | 3 dias antes y 12 horas antes |
| `normal` | 3 dias, 1 dia y 3 horas antes (el que viene puesto) |
| `apretado` | 7 dias, 3 dias, 1 dia, 6 horas, 2 horas y 30 minutos antes |
| `diario` | una vez por dia hasta la entrega |

Ojo, esto es para las entregas de la plataforma. **Tus recordatorios propios
suenan una sola vez** y no siguen ningun perfil.

---

## 7. Cuanto tarda en contestar

De **7 de la manana a 2 de la madrugada el bot esta despierto de corrido**,
escuchando el chat. En esa franja los botones contestan en un segundo.

De 2 a 7 duerme y solo se asoma cada 10 minutos para revisar. Si tocas un
boton a esa hora, el toque no se pierde, queda en la cola y se ejecuta
cuando despierta. Por eso el panel siempre dice a que hora se actualizo.

Para cambiar la franja, en `fuentes.py`:

```python
DESPIERTO = (7, 2)     # de las 7 a las 2 de la madrugada
```

Un detalle util: en el registro de GitHub las horas salen en hora del
servidor, que no es la tuya. En el chat siempre te habla en tu hora.

Cuando la IA esta pensando vas a ver una animacion con puntos y frases que
van cambiando. Es a proposito, para que se note que esta trabajando. La
velocidad se toca en `fuentes.py` con `ANIM_SEGUNDOS`.

---

## 7 bis. Los archivos te llegan al chat

Cuando suben una guia, un trabajo o una presentacion, el bot **baja el
archivo y te lo deja en el chat**, abajo del aviso. No tenes que entrar a la
plataforma solo para bajarlo.

Tambien anda cuando el enlace **no dice la extension**. Hay plataformas que
publican los adjuntos con una direccion pelada. El bot igual se da cuenta de
que hay algo para bajar y le pone el nombre y la extension que corresponde.

Si un aviso viejo se quedo sin sus archivos, entra al ramo y toca
**Mandame los archivos**.

Tres cosas que conviene saber:

1. **En el chat no ocupa lugar en tu telefono.** El archivo vive en la nube
   de la mensajeria. Recien se baja cuando vos lo tocas.
2. **Si te queda pesado**, en Ajustes de Telegram, Datos y almacenamiento,
   Uso de almacenamiento, le decis que borre lo descargado a los 3 dias.
   Aunque se borre de tu telefono, el archivo sigue en la nube y lo volves a
   abrir cuando quieras.
3. **Si algo no llega**, el enlace del aviso sigue ahi. Nunca perdes la cosa,
   en el peor caso la abris en la pagina como siempre.

Se puede ajustar en `fuentes.py`:

```python
ADJUNTAR = True              # ponelo en False y solo te manda el enlace
ADJUNTOS_POR_AVISO = 5       # cuantos archivos manda por novedad
PESO_ADJUNTO_MB = 45         # el tope de la mensajeria es 50
```

---

## 7 ter. Marcar que ya lo viste

Cada aviso trae un boton:

- **Lo que se entrega** (tareas, trabajos, informes) dice `hecho`.
- **Lo que solo hay que mirar** (guias, apuntes, presentaciones) dice `lo vi`.

Mientras no lo marques, la cosa queda en **Pendientes**, separada en dos
listas: `PARA ENTREGAR` y `SIN REVISAR`. Asi ves de un vistazo que material
te falta abrir.

Si a las 20 horas no marcaste algo, el bot te lo recuerda **una sola vez** y
no insiste mas. Se cambia en `fuentes.py` con `HORAS_PARA_RECORDAR_VISTO`.
Ponele `0` y no te recuerda nunca.

En cada aviso tambien hay `1h` y `3h` para posponer, y un boton de silencio
para ese ramo.

---

## 7 quater. Ramos y material

En **Ramos** elegis uno y tenes dos botones que hacen cosas distintas:

- **Ver material**: la lista completa de lo que hay, ordenada por cajones
  (para entregar, guias, apuntes, foros). Es un indice.
- **Resumen del ramo**: lo que la IA entendio de todo eso, en cuatro lineas.
  Es una opinion.

Uno te dice **que hay**, el otro te dice **de que se trata**.

Hay plataformas que arman el menu del ramo con javascript, o sea que la
lista no esta escrita en la pagina. El bot igual la encuentra. Si aun asi un
ramo aparece vacio, anotalo en `PROBLEMAS.md`.

---

## 8. Cosas que conviene saber

- **Silenciar un ramo no lo apaga.** Las entregas con fecha llegan igual, el
  ramo aparece al pie de todos los resumenes con los dias que le quedan, y a
  los 14 dias vuelve solo y te avisa.
- **Nada se declara roto en la primera lectura.** Hacen falta tres
  revisiones seguidas. Las plataformas se reinician solas.
- **Si un ramo desaparece**, el bot distingue tres casos: cambio de
  semestre, baja del ramo, o plataforma rota. Solo te molesta en el segundo.
- **Si te sacan de un ramo, te avisa.**
- **La primera corrida no grita.** Anota todo lo que ya existe y se calla.
  Desde ahi en adelante avisa solo lo nuevo.
- **Las huellas nunca se borran**, ni cuando se archiva un ramo, asi no te
  reanuncia material viejo si repetis una asignatura.
- **El chat se limpia solo.** Tus mensajes se borran a los 5 segundos y la
  basura del bot a los 25. Los avisos de material, los plazos y el aviso de
  version nueva **no se borran nunca**.

---

## 9. Cuando algo falle

1. Escribile `/estado` al bot. Ahi ves la version, la memoria, la IA y el
   motivo si algo esta apagado.
2. Anda a **Actions** en tu repositorio y mira la ultima corrida.
3. Anota el problema en `PROBLEMAS.md` con la fecha. Los chats se pierden,
   los archivos no.
4. Si vas a pedirle ayuda a otra IA, pasale `INSTRUCCIONES_PARA_LA_IA.md`
   junto con el problema.
