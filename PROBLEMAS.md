# Problemas y quejas

Aca se anota todo lo que no funciona o no gusta. Los chats se pierden, los
archivos no. Si un dia le pedis ayuda a otra IA, pasale este archivo.

Formato: fecha, que paso, estado.
Estados: `abierto`, `en eso`, `resuelto`, `no se va a arreglar`.

Al dia con la **v5.4**.

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
