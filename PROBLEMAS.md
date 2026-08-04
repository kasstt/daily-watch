# Problemas y quejas

Aca se anota todo lo que no funciona o no gusta. Los chats se pierden, los
archivos no. Si un dia le pedis ayuda a otra IA, pasale este archivo.

Formato: fecha, que paso, estado.
Estados: `abierto`, `en eso`, `resuelto`, `no se va a arreglar`.

Al dia con la **v5.6**.

---

## Abiertos

### 03/08 - compartirlo con otras personas (punto 6 del pedido)
No se programo nada a proposito. Hay que elegir primero el camino: cada uno
con su copia, un solo bot con varias personas adentro, o un bot chico por
persona armado desde una plantilla. Falta la decision del dueno.
Estado: abierto, esperando que elija.

### 03/08 - ver material de profes de otras secciones (punto 7)
Depende del punto 6. Sin cuentas separadas no hay forma de compartir
material sin entregar claves.
Estado: abierto, atado al punto 6.

### 03/08 - falta verlo funcionando en clase
Tres cosas quedaron arregladas en el codigo pero todavia no se vieron con
material de verdad, porque el semestre no arranco:

1. Que el archivo de un adjunto sin extension llegue al chat con su nombre
   y su formato.
2. Que el material que se publica en el menu armado con javascript aparezca
   apenas lo suben.
3. Que el aviso normal de material nuevo traiga el adjunto pegado.

Estado: abierto, esperando la primera semana de clases.

### 03/08 - resuelto en la v5.4: los archivos no llegaban
El panel decia "4 cosas" y el boton contestaba que no habia ningun documento.
Eran dos listas distintas: el contador miraba las novedades anotadas y el
boton miraba solo lo que tenia extension. Ahora las dos cosas salen de
`archivos_del_ramo`, que acepta los enlaces sin extension del tipo
`/archivo/8891` y tambien lo que aparece en el menu escondido.
Ademas, si lo que baja es la pantalla de ingreso disfrazada de archivo, se
avisa en vez de mandar basura.
Estado: resuelto, falta verlo con material de verdad.

### 03/08 - resuelto en la v5.4: dos mensajes y en ingles
Al pedir un recordatorio hablado llegaban dos mensajes, uno era el propio
mensaje repetido en cursiva y el otro tenia una frase en ingles cortada.
Ahora la confirmacion la escribe siempre el codigo, la respuesta cruda de la
IA no se imprime nunca, y hay dos filtros que tiran lo que venga en ingles o
en formato de maquina. Si la IA esta apagada se dice con esas palabras.
Estado: resuelto.

### 03/08 - resuelto en la v5.4: una sola clave de IA
Ahora entran varias claves con orden de preferencia. Si una se queda sin
cupo descansa una hora, si es invalida se marca mala y no se reintenta, si
es la red se reintenta a los pocos minutos. El relevo es callado y siempre
se vuelve a probar desde la primera. En `/estado` se ve como estan, nombradas
"clave 2 de 3", sin mostrar nunca el texto de ninguna.
Estado: resuelto.

### 03/08 - la IA se apago sola en el servidor
Mensaje: "se apago sola tras 5 intentos, la clave no sirve o no tiene
permiso". La clave era la misma que andaba en la computadora.
Se vuelve a prender con `/ia on`. Si no vuelve, clave nueva en
`aistudio.google.com/apikey`.
Estado: abierto, hay que mirarlo la proxima vez que pase.

### 03/08 - dos cosas de la revisada de rutina
Faltan mirar: que pasa con los avisos de plazo cuando una entrega **cambia
de fecha** en la plataforma, y que pasa cuando el **mismo archivo aparece en
las dos plataformas**.
Estado: abierto.

---

## Lo que se cerro en la v5.6

Doce puntos que salieron de usar el bot de verdad. Todos verificados con
`python3 _p18.py`.

| # | Que pasaba | Que se hizo |
|---|---|---|
| 1 | Si cambiabas la clave, el bot fallaba callado y solo hablaba tras tres fallas seguidas | Aviso propio de clave rechazada, una vez por dia, y NO reintenta en bucle para no bloquear la cuenta |
| 2 | El aviso de version solo decia el dia | Ahora dice la hora, y `version.py FECHA` la incluye |
| 3 | Actualizabas y el bot seguia contestando la version vieja | No era el .bat. Era `cancel-in-progress: false` en el flujo: el push quedaba en la cola detras de un trabajo que seguia corriendo con el codigo viejo hasta 5,5 h. Ahora es `true`. Ademas el aviso mandaba y anotaba en el orden inverso |
| 4 | Error de cupo de las claves de IA | Es el limite diario gratis del proveedor, no una falla. Lo que se arreglo es que las ordenes locales funcionen con la IA apagada |
| 5 | Decia que no encontraba archivos de un ramo que si tiene cosas | Ese ramo tenia avisos escritos, no archivos. Al leer los avisos ahora se ve que son |
| 6 | Los avisos escritos del profe eran invisibles | Modulo nuevo `avisos.py`. El bot solo miraba ENLACES y un aviso es texto sin enlace. Un aviso urgente rompe el silencio y suena de madrugada |
| 7 | Pendientes era texto muerto: no se podia abrir, leer la nota ni marcar | Pantalla nueva con una fila por pendiente, ver nota, marcar, posponer y borrar |
| 8 | Borrar, completar o posponer era instantaneo y sin retorno | Aviso del cambio mas boton Deshacer que restaura el estado anterior y desaparece al usarse. Borrar pregunta antes |
| 9 | `/recordar` no funcionaba | Tres fallas: el id era por minuto y dos apuntes se pisaban, no se marcaba `es_tarea: False` y caian en PARA ENTREGAR, y no se guardaba |
| 10 | Para crear un recordatorio habia que escribir comandos | Boton Nuevo recordatorio en la pantalla principal, atajos y opcion Otra hora |
| 11 | Un enlace a la plataforma abre sin pedir login | Es la cookie de sesion del navegador, explicado abajo. No es una falla del bot |
| 12 | Tres veces por dia avisaba que cambio algo sin que hubiera nada | `RE_VOLATIL` mucho mas amplia, detector de paginas que oscilan, dos revisiones seguidas antes de avisar y tope de uno por dia |

## Lo que quedo advertido en la v5.6, no es una falla

- **El cupo de la IA.** El proveedor da una cantidad de pedidos gratis por dia
  por clave. Cuando se agotan, el bot descansa y vuelve solo. Se pueden cargar
  hasta cinco claves. No se pierde nada de lo que vigila: los avisos, los
  archivos y los recordatorios no usan IA.
- **El enlace que abre sin pedir clave.** Es el navegador, que ya tiene la
  sesion abierta. El enlace no lleva usuario ni clave adentro. En una maquina
  ajena pide login normalmente. El riesgo real es dejar la sesion abierta en
  un equipo compartido.
- **`cancel-in-progress` en el flujo de trabajo.** Tiene que quedar en `true`.
  En `false`, un push no toma efecto hasta que termine el trabajo anterior, y
  eso puede tardar horas.

## Resueltos

| Fecha | Problema | Como se resolvio |
|---|---|---|
| 03/08 | avisaba de `Inicio`, `Mis Cursos` y otros del menu | lista `PALABRAS_MENU` |
| 03/08 | clasificaba mal las guias como material | se arreglo `tipo_de()` |
| 03/08 | los cuatro FALTA de `probar_local.py` | no era falla, faltaba cargar los datos, se agrego `secretos.py` |
| 03/08 | un trabajo con 3 PDF llegaba como 4 avisos | ahora se agrupan en uno solo |
| 03/08 | anclaba hasta la pantalla de Ajustes | cuando el texto no cambiaba, la mensajeria devolvia error y el bot mandaba un panel nuevo. Ahora ese caso cuenta como exito |
| 03/08 | los botones tardaban entre 5 y 20 minutos | el bot queda despierto de 07:00 a 02:00 y contesta en un segundo |
| 03/08 | el anclado molestaba igual | se apago del todo, `ANCLAR_PANEL = False` |
| 03/08 | tocar el titulo abria la pagina y habia que bajar el archivo a mano | ahora el bot baja el archivo y te lo deja en el chat |
| 03/08 | los .docx y .pptx se quedaban sin resumen | se les saca el texto solo, sin instalar nada |
| 03/08 | `/revisar` no hacia nada visible | un `pop` metido adentro de un `or` no corria si la primera condicion ya era verdadera |
| 03/08 | el interruptor de la botonera de abajo no funcionaba | esa botonera vive pegada al mensaje que la trajo. Si se borra ese mensaje, se va con el |
| 03/08 | un recordatorio vencido seguia apareciendo | posponer con `dormida_hasta` callaba el aviso pero dejaba la fecha vieja. Ahora se archiva solo |
| 03/08 | el boton de posponer 3 horas era mucho | se agrego uno de 1 hora y quedaron los dos |
| 03/08 | la hora del registro estaba corrida | `fromtimestamp` usa el reloj de la maquina, y en el servidor es UTC. En el chat siempre se habla en hora local |
| 03/08 | la clave nueva de la IA no andaba | las que empiezan con `AQ.` **solo** funcionan en la cabecera, no pegadas en la direccion |
| 03/08 | subio material y el bot no lo detecto | **el menu del ramo se arma con javascript**, no estaba en la pagina. Se agrego `arbol_escondido()` |
| 03/08 | el actualizador devolvia 404 en todos los archivos | al token le faltaba la casilla `repo`. GitHub contesta 404 y no 403 cuando falta permiso. Y se le habia pedido escribir el repositorio a mano, puso la direccion entera |
| 03/08 | el archivo del profesor nunca llegaba al chat | el enlace no tenia extension. Ahora se mira el `Content-Type` de la respuesta |
| 03/08 | "ver material" y "resumen del ramo" daban lo mismo | el plan B del resumen imprimia la lista de material |
| 03/08 | los comandos de `/ayuda` no se podian apretar | estaban adentro de `<code>`, que se copia pero no se toca. Ahora van en texto pelado |
| 03/08 | no se explicaba que hace cada perfil | Ajustes > Perfiles de aviso, y `/perfil` sin nada |
| 03/08 | la animacion pasaba demasiado rapido | tres quejas. Quedo en `ANIM_SEGUNDOS = 6.5` |
| 03/08 | un recordatorio de una hora mandaba avisos cada minuto | se le estaban aplicando los hitos de un perfil de ramo. Ahora `AVISOS_DE_MIS_RECORDATORIOS = [0]`, suena una sola vez |
| 03/08 | la IA decia que no podia hacer recordatorios | ahora traduce a JSON, Python valida y muestra la confirmacion con Dale o No |
| 03/08 | la IA no sabia como funciona el bot | se le metio el manual adentro (`ia.MANUAL`) |
| 03/08 | nunca llegaba el aviso de version nueva | habia una guarda contra el ruido del arranque que se comia justo el primer aviso |
| 03/08 | no habia forma confiable de saber en que version estas | `version.py`, `/version`, y Ajustes > Version y novedades |
| 03/08 | actualizar era largo y a mano | `ACTUALIZAR.bat`: respaldo, parche, permisos y subida, todo de un clic |
| 03/08 | **poner "lunes" un lunes se iba a la semana que viene** | habia un `or 7` que convertia el cero en siete. Ahora si la hora no paso, cae hoy |
| 03/08 | el apartado de recordatorios era tosco y lento | se rehizo entero: dos toques, atajos de 15 min, 1 hora, 3 horas, Hoy 21:00 y Manana 9:00, y cada uno con hecho, +1h y borrar |
| 03/08 | no entendia los minutos escritos de cualquier forma | ahora vale `5m`, `5 min`, `en 5 minutos` |

---

## Lo que se cerro en la v5.5

| fecha | que pasaba | como quedo |
|---|---|---|
| 03/08 | **las clases por videoconferencia se perdian** | el filtro de enlaces tenia `/meeting/` en la lista de ignorados y se comia las salas. Ahora `ignorar()` deja pasar todo lo que `clases.es_sala()` reconoce, y el chat interno se sigue ignorando |
| 03/08 | una clase avisada en un ramo silenciado no llegaba | `clases_nuevas()` corre antes del corte por silencio. Una clase siempre pasa |
| 03/08 | **GitHub apaga el bot solo a los 60 dias sin movimiento** | `salud.py` mira el reloj todos los dias. A los 50 avisa y trata de moverlo solo. Si no puede, deja el boton Despertar el reloj |
| 03/08 | si varias personas usaban el mismo bot, las claves de IA quedaban a la vista | cada uno carga la suya con `/miclave`. Se guarda cifrada, el mensaje se borra al instante y no se muestra en ningun lado |
| 03/08 | compartir era todo o nada | ahora es ramo por ramo y persona por persona. De fabrica no se comparte nada |
| 03/08 | llegaba material repetido de otras secciones | `huella_de_material()` compara sin extension, sin version y sin tildes. Lo repetido se marca y dice de que ramo tuyo lo tenes |
| 03/08 | lo de otras secciones molestaba igual que lo propio | llega silencioso, en una linea, sin botones y sin insistir nunca |

---

## Lo que quedo advertido, no es una falla

- **Las claves ajenas estan cifradas, no son inviolables.** El bot tiene
  que poder abrirlas para usarlas, asi que la llave vive en el mismo lugar
  que el bot. Nadie las ve en el chat ni en la memoria, pero quien tenga
  el control total del repositorio podria sacarlas. Es lo mejor que se
  puede hacer con un bot que necesita usarlas.
- Si se cambia `GH_TOKEN` o `TG_TOKEN` sin tener puesto el secreto
  `CLAVE_COMPARTIR`, las claves guardadas dejan de abrirse y hay que
  volver a cargarlas. Poner `CLAVE_COMPARTIR` evita eso.
- Una clase avisada sin enlace (el profe dijo "es online" y no publico el
  enlace) llega marcada como no confirmada. No es un error del bot.

---

## Como anotar algo

Agrega una linea arriba de todo en **Abiertos**, con la fecha y lo que viste.
Si tenes el mensaje del bot o el registro de GitHub, pegalo abajo.

Ejemplo:

```
### 15/09 - no me aviso de una guia
El profe subio la guia 4 a las 10:00 y me llego recien a las 11:30.
Estado: abierto
```

---

## Ideas para mas adelante

No son problemas, son cosas que quedaron pensadas y sin hacer.

- **Mini App**: una pantalla de verdad adentro del chat, en vez de botones.
  Conviene esperar una o dos semanas de clases y ver que se usa realmente.
- avisar cuando cambia una nota, leyendo la pagina de calificaciones
- detectar el mismo archivo subido a las dos plataformas y avisar una vez
- estadisticas del semestre: que ramo sube mas material, en que dias
- exportar los pendientes a un calendario
- emojis animados propios: la mensajeria los cobra carisimo, descartado por
  ahora

---

## Auditoría de la v5.7 — el bot completo

Revisión línea por línea de los 10.000+ renglones, no solo de lo nuevo.
Cada punto es una falla que estaba y ya está arreglada. Están acá para que
no vuelvan a entrar por la puerta de atrás.

### Las que te hacían perder información

1. **Cortar mensajes a lo bruto.** `texto[:4000]` podía partir el texto al
   medio de un `<b>` o de un `&amp;`. La plataforma entonces rechaza el
   mensaje ENTERO, no la parte cortada. Resultado: el mensaje no llegaba y
   nadie se enteraba. Le pegaba justo al resumen semanal, que es el más largo.
   Ahora `notificar.cortar()` no corta dentro de una etiqueta ni de un
   símbolo, y cierra lo que quedó abierto. Además, si el formato falla, se
   reintenta el mensaje pelado: mejor sin negritas que perdido.
2. **Posponer una entrega del profe la duplicaba.** El botón `+1 hora` le
   cambiaba el id a `mio_<hora>` a CUALQUIER pendiente. La identidad de una
   entrega del profe es su huella: al renombrarla, el bot la perdía de vista y
   en la revisión siguiente la anotaba como nueva. Quedaban dos, y con la
   fecha del profe cambiada. **Nunca re-llavear un pendiente que vino de la
   plataforma.** Ahora solo se duerme el recordatorio.
3. **Los avisos del profe no se archivaban nunca.** Un aviso no tiene fecha
   de entrega, así que nunca entraba en la limpieza. En un semestre la lista
   de Pendientes quedaba inservible. Ahora se archivan solos a los 21 días
   (`DIAS_PARA_ARCHIVAR_AVISOS`), usando el campo nuevo `nacio`.

### Las que te iban a molestar de más

4. **Todo era urgente.** `PALABRAS_URGENTES` tenía "prueba", "entrega",
   "control", "plazo" y "asistencia", que aparecen en casi todos los avisos.
   O sea: todo iba a sonar a las 3 de la mañana. Una alarma que suena siempre
   se apaga, y el día que se apaga te perdés la suspensión de verdad. Ahora
   hay dos niveles: nivel 1 te cambia el día y suena; nivel 2 se marca pero
   espera la mañana. Interruptor: `IMPORTANTES_SUENAN_DE_NOCHE`.
5. **`MINUTOS_PARA_DESHACER` estaba definido y NO se usaba.** El botón
   Deshacer sobrevivía horas. **Una opción de configuración escrita y sin usar
   es un error, no una función pendiente.**
6. **La campanita callaba un ramo dos semanas de un solo toque**, al lado del
   botón "ya está", sin decir hasta cuándo y sin vuelta atrás. Ahora avisa la
   fecha de término y se puede deshacer.

### Las que se veían roto

7. **No se le podía hablar normal.** `if "pendientes" in plano` hacía que
   cualquier frase con esa palabra —"que pendientes tengo?"— se tratara como
   si hubieras apretado el botón. **El teclado fijo se compara por texto
   EXACTO, nunca por subcadena.**
8. **`/avisos` ordenaba por id**, que es `"aviso_" + hash`. Orden de azar.
   Ahora ordena por `nacio`, el más nuevo arriba.
9. **La admiración roja la llevaban todos los avisos**, así que no distinguía
   nada. Ahora es solo para los urgentes de verdad.
10. **Ajustes había perdido la única puerta a "Cuándo te hablo"**, y con ella
    el acceso a `p:dia` y `p:hora`. No había forma de cambiar el día ni la
    hora del resumen. **Toda pantalla necesita al menos un botón que lleve a
    ella; si no, existe pero es inalcanzable.**
11. **El diagnóstico mostraba el diccionario crudo** de la falla.
12. **Botones recortados.** `teclado()` hacía `d[:64]`. Un dato recortado
    apunta a OTRA cosa: el botón hacía algo distinto de lo que decía. **Si no
    cabe, el botón no se pone.**
13. **`sacar_basura` tiraba los mensajes sobrantes de la lista sin borrarlos**
    del chat, así que quedaban ahí para siempre.
14. **`_escribir_local` sin try.** Un disco lleno reventaba la corrida entera
    en la última línea, con todo el trabajo ya hecho.

### Trampas de programación que encontré (valen para cualquier cambio futuro)

- **Una variable local puede tapar un módulo importado.** En
  `avisos_de_plazo` había un local llamado `avisos`, y arriba hay
  `import avisos`. Cualquier `avisos.algo()` dentro de esa función reventaba.
  **Nunca le pongas a una variable el nombre de un módulo.**
- **Agregar un tipo nuevo de deshacer exige una rama nueva en
  `panel._deshacer`.** La cola genérica asume que el id es de una tarea. Mi
  propio deshacer de la campanita pasaba una clave de ramo y creaba un
  pendiente fantasma. Lo cazó `_p19.py`.
- **Una pantalla rota NO se detecta contando filas de botones.** Muchas
  pantallas de solo lectura tienen una sola fila con Volver y están perfectas.
  La señal real es el texto literal `"se rompi"` que devuelve
  `panel.pantalla`.
- **Nunca escribas el número de versión en una prueba.** Comparalo contra
  `VER.VERSION`. Ya rompió dos veces.
- **Un `replacements: 1` no garantiza que el cambio quedó.** Verificá con
  `grep` o volviendo a correr las pruebas.
- **Mandá primero, marcá después.** Nunca pongas la marca de "ya avisé" antes
  de que el envío devuelva un id.
- **Cuidado con las pruebas que miran el código fuente:** los comentarios
  explican cómo era antes, así que contienen el texto viejo a propósito. Hay
  que sacar los comentarios antes de buscar.
