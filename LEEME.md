# Vigilante

Mira dos plataformas de clase cada pocos minutos y te avisa al chat cuando
aparece algo nuevo. Corre gratis en GitHub, sin computadora prendida.

---

## 1. Que hace

- Avisa de guias, tareas, foros y cualquier archivo nuevo.
- Junta un trabajo con su consigna, su fecha y sus adjuntos en **un solo
  aviso**, no en cinco.
- Le pide a una IA un resumen corto de lo que subieron. Ese resumen aparece
  dentro de una cita con barra al costado. Esa barra significa: **esto lo
  escribio una maquina**. Todo lo de afuera es dato sacado de la plataforma.
- Te recuerda las entregas antes de que venzan, con la insistencia que vos
  elijas por ramo.
- Tiene un panel de botones. No hace falta acordarse de ningun comando.

---

## 2. Los archivos

| Archivo | Para que sirve |
|---|---|
| `watcher.py` | el motor |
| `panel.py` | las pantallas de botones |
| `comandos.py` | los comandos y los toques |
| `notificar.py` | todo lo que sale al chat |
| `ia.py` | los resumenes |
| `almacen.py` | la memoria |
| `fuentes.py` | la configuracion |
| `secretos.py` | lee `mis_datos.txt` cuando corres en tu maquina |
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

### b. En GitHub

1. Crea una cuenta con un apodo. No pongas tu nombre real.
2. Crea un repositorio **publico**. Publico es a proposito: asi los minutos
   son ilimitados. En este codigo no hay nada que te identifique.
3. Sube todos los archivos menos `mis_datos.txt`.
4. En **Settings > Secrets and variables > Actions**, carga uno por uno los
   mismos nombres que estan en `mis_datos.txt`.
5. Anda a **Actions** y prendelo.

---

## 4. Los datos que necesita

| Nombre | Que es | Obligatorio |
|---|---|---|
| `SITE_A_URL` `SITE_A_USER` `SITE_A_PASS` | la plataforma propia | si |
| `SITE_B_URL` `SITE_B_USER` `SITE_B_PASS` | el aula virtual | si |
| `CAL_URL` | el calendario privado de la plataforma A | no |
| `CAL_URL_B` | el calendario privado de la plataforma B | no |
| `TG_TOKEN` `TG_CHAT` | la mensajeria | si |
| `GH_TOKEN` | token clasico con la casilla `gist` | recomendado |
| `GIST_ID` | se llena solo la primera vez | no |
| `IA_KEY` | la clave de la IA | no |

Sin `GH_TOKEN` el bot igual funciona, pero guarda la memoria en el propio
repositorio y solo en forma de huellas, sin texto legible. No perdes avisos,
perdes las notas y los titulos guardados.

Sin `IA_KEY` el bot funciona igual y los avisos salen sin la linea del
cerebro. Nada mas cambia.

---

## 5. El panel

Es un mensaje anclado arriba del chat que se edita a si mismo. El estado
esta escrito adentro de cada boton, asi que sabes donde estas parado sin
abrir nada.

```
Vigilante                       todo en orden
6 ramos - 3 pendientes - 2 nuevas hoy

[ Novedades (2) ]
[ Pendientes (3) ]   [ Semana ]
[ Ramos ]            [ Avisos ]
[ Pausa: no ]        [ Noche: si ]
[ IA: si ]           [ Ajustes ]

actualizado 02:47
```

Abajo del teclado quedan fijos tres atajos: Novedades, Pendientes y Panel.

**Anclado hay uno solo**, el panel, y se ancla una unica vez. Navegar entre
pantallas no manda mensajes nuevos: reescribe ese mismo. Los avisos de
material no se anclan nunca.

---

## 6. Los comandos, por si preferis escribir

```
/panel        abre el panel
/ultimo       lo ultimo que aparecio
/pendientes   que te falta entregar
/semana       los ultimos 7 dias
/resumen ramo calculo    resumen de ese ramo, con IA
/resumen viernes 20:00   cambia el dia y la hora del resumen
/pausa 3      callate 3 horas
/noche        prende o apaga los avisos de madrugada
/estado       diagnostico
/perfil apretado termo   cuanto insistir en ese ramo
/callar calculo          silenciar 14 dias
/revisar      revisa ahora
/recordar viernes 18:00 estudiar
/ia on        prende o apaga los resumenes
/exportar     te manda todo en un archivo
/ayuda
```

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

Ponele `(0, 0)` si lo queres despierto las 24 horas. Sale gratis igual, en
repositorio publico los minutos son ilimitados.

**El bot no ancla nada.** El panel es un mensaje mas: si lo perdes de vista,
escribis `/panel` o tocas el boton de abajo y aparece de nuevo. Si algun dia
quisieras el panel anclado, en `fuentes.py` pones `ANCLAR_PANEL = True`.

---

## 7 bis. Los archivos te llegan al chat

Cuando suben una guia, un trabajo o una presentacion, el bot **baja el
archivo y te lo deja en el chat**, abajo del aviso. No tenes que entrar a la
plataforma solo para bajarlo.

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

- **Lo que se entrega** (tareas, trabajos, informes) dice `✅ hecho`.
- **Lo que solo hay que mirar** (guias, apuntes, presentaciones) dice
  `👀 lo vi`.

Mientras no lo marques, la cosa queda en **Pendientes**, separada en dos
listas: `PARA ENTREGAR` y `SIN REVISAR`. Asi ves de un vistazo que material
te falta abrir.

Si a las 20 horas no marcaste algo, el bot te lo recuerda **una sola vez** y
no insiste mas. Se cambia en `fuentes.py` con `HORAS_PARA_RECORDAR_VISTO`.
Ponele `0` y no te recuerda nunca.

---

## 8. Cosas que conviene saber

- **Silenciar un ramo no lo apaga.** Las entregas con fecha llegan igual, el
  ramo aparece al pie de todos los resumenes con los dias que le quedan, y a
  los 14 dias vuelve solo y te avisa.
- **Nada se declara roto en la primera lectura.** Hacen falta tres
  revisiones seguidas. Las plataformas se reinician solas.
- **Si un ramo desaparece**, el bot distingue tres casos: cambio de
  semestre, baja del ramo, o plataforma rota. Solo te molesta en el segundo.
- **La primera corrida no grita.** Anota todo lo que ya existe y se calla.
  Desde ahi en adelante avisa solo lo nuevo.
- **Las huellas nunca se borran**, ni cuando se archiva un ramo, asi no te
  reanuncia material viejo si repetis una asignatura.

---

## 9. Cuando algo falle

1. Anda a **Actions** en tu repositorio y mira la ultima corrida.
2. Escribile `/estado` al bot.
3. Anota el problema en `PROBLEMAS.md` con la fecha. Los chats se pierden,
   los archivos no.
4. Si vas a pedirle ayuda a otra IA, pasale `INSTRUCCIONES_PARA_LA_IA.md`
   junto con el problema.
