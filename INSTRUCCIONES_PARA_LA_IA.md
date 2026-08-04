# Instrucciones para la proxima IA

Si estas leyendo esto, sos una IA a la que le pidieron cambiar este bot.
Lee todo antes de tocar una linea. El dueno no programa: si le entregas algo
roto, no lo va a poder arreglar solo.

Al dia con la **v5.4**.

### Lo que cambio en la v5.5 (leelo antes de tocar nada)

Tres archivos nuevos y ninguno depende de `watcher.py`, para que no haya
importaciones circulares:

- **`clases.py`**: detecta clases por videoconferencia. Es puro texto, no
  toca la red ni la memoria. `detectar(titulo, url, descripcion)` devuelve
  una ficha o `None`. `seguro=True` solo cuando hay un enlace de sala de
  verdad. Ojo: `/meeting/` sigue en `CFG.IGNORAR` para el chat interno,
  pero `watcher.ignorar()` ahora deja pasar cualquier cosa que
  `clases.es_sala()` reconozca. Si sacas eso, se pierden las clases.
- **`salud.py`**: el reloj de GitHub. La plataforma apaga los trabajos
  automaticos a los 60 dias sin movimiento, asi que a los 50 avisa y trata
  de moverlo solo escribiendo `estado/latido.txt`. Las funciones puras
  (`dias_quieto`, `hay_que_avisar`, `texto_del_aviso`) se prueban sin red.
  `revisar()` acepta `consultar_fn` y `tocar_fn` justamente para eso.
- **`compartir.py`**: compartir material, permisos por ramo, duplicados y
  el cifrado de las claves ajenas. **Nunca agregues un campo a
  `CAMPOS_QUE_SALEN` sin pensarlo dos veces**, esa lista es lo unico que
  separa el material publico de los datos privados. `revisar_fuga()` tiene
  que devolver siempre una lista vacia.

Reglas nuevas que no se rompen:

- **De fabrica no se comparte nada.** `COMPARTIR_DE_FABRICA = []`. Cada
  ramo lo abre el usuario a mano, persona por persona.
- **Lo de otras secciones es de segunda.** Llega silencioso, en una linea,
  sin botones y sin insistencia. No genera pendientes ni entra en el
  sistema de recordatorios. No le agregues un boton de "ya lo vi" ni de
  silenciar, lo pidio explicitamente.
- **Las claves ajenas nunca se muestran.** Ni en el chat, ni en `/estado`,
  ni en los registros. `resumen_de_claves()` solo dice cuantas hay.
- **Las clases rompen el silencio del ramo.** `clases_nuevas()` se llama
  antes del corte por `callado()` en `_avisar`. Si lo mueves despues, un
  ramo silenciado se come la clase.

Pantallas nuevas del panel: `p:mas`, `p:comp`, `p:per:<id>`, `p:clases`,
`p:afuera`. Botones nuevos: `tc:<id>:<ramo>`, `tq:<id>`, `a:tocar`,
`a:reloj`, `a:cerrar_compartir`. Comandos nuevos: `/clases`, `/compartir`,
`/afuera`, `/reloj`, `/miclave`.

El workflow ahora pasa `GH_REPO`, `GH_RAMA` y `CLAVE_COMPARTIR`. Si
`CLAVE_COMPARTIR` no esta, `compartir.py` arma la llave con `GH_TOKEN` mas
`TG_TOKEN`, asi que funciona igual, pero si el usuario cambia el token las
claves guardadas dejan de abrirse. Conviene que ponga el secreto.

---

### Lo que cambio en la v5.4

- **Archivos de un ramo**: todo pasa por `Vigilante.archivos_del_ramo`, que
  junta lo anotado en la memoria con lo que hay ahora en la plataforma,
  incluido el menu escondido. `cuantos_archivos` cuenta con esa misma
  funcion, asi que el numero del panel y el del boton no pueden discrepar.
  Si cambias una, cambia la otra.
- **Tres alcances**: `semana`, `mes` y `todo`, con los dias en
  `CFG.DIAS_DE_ALCANCE`. Los botones son `a:baj:<clave>:<alcance>` y la clave
  lleva dos puntos adentro, por eso se parte con `rpartition`.
- **La IA no cuenta nada**: solo traduce el pedido a JSON con la accion
  `buscar_archivos`. `validar_orden` resuelve el ramo, filtra y arma la
  confirmacion con numeros propios. Todo texto que ve el usuario lo escribe
  Python.
- **Filtros de salida**: `ia._parece_ingles` y `ia._parece_json` tiran la
  respuesta antes de que llegue al chat. No los saques.
- **Anillo de claves**: `ia.claves()` arma la lista desde `CFG.IA["claves_env"]`
  y desde `IA_KEYS`. `ia._pedir(estado, texto, pdfs)` es la unica puerta a los
  proveedores, que ahora reciben la clave como parametro. La penitencia vive
  en `estado["ia_claves"]` y se borra sola si cambias la clave, porque se
  guarda una huella. **Ninguna clave puede aparecer en un registro ni en el
  chat**, se las nombra "clave 2 de 3". El apagado por 5 fallas es por clave.
- **Pantallas**: dos botones por fila, seis filas como maximo y `Volver`
  solo en la ultima.
- **Pruebas**: `_p16.py` corre sin internet y cubre los puntos 1, 2, 3, 4 y 5.

---

## 1. Que es esto

Un bot que vigila dos plataformas de clase y avisa por chat cuando aparece
material nuevo. Corre en GitHub Actions. Sin servidor.

**Trabaja con el usuario en castellano rioplatense, directo, sin adornos.
Dale la conclusion y los pasos, no el proceso.** Nada de rayas largas ni de
punto y coma en los textos que el va a leer.

---

## 2. Reglas que no se rompen

1. **Anonimato.** El repositorio es publico. En el codigo no puede aparecer
   el nombre del usuario, el de su universidad, el de las plataformas, ni
   ninguna direccion. Todo eso vive en los Secrets. Antes de entregar,
   busca esas palabras en todos los archivos.
2. **La IA no toca datos.** Los resumenes rellenan una sola parte del aviso,
   la cita con barra. Fechas, nombres, enlaces y plazos los pone el codigo,
   siempre. Una IA que inventa una fecha de entrega cuesta una nota.
3. **La IA propone, Python dispone.** Para las ordenes habladas la IA solo
   devuelve un JSON. El programa lo valida, arma la confirmacion con datos
   propios y recien ejecuta si el usuario toca **Dale**. Esto es un pedido
   explicito y repetido del dueno, no lo cambies.
4. **Nada revienta hacia afuera.** `notificar.py` e `ia.py` capturan todo.
   Si la IA falla, el aviso sale igual sin la cita. Si el chat falla, el bot
   sigue guardando.
5. **No entregues codigo pegado en el chat.** Entrega archivos para
   descargar. Ya hubo un `SyntaxError` por copiar y pegar mal.
6. **Nunca le pidas que edite un archivo de configuracion a mano**, ni que
   pegue un token en el chat. El programa pregunta por pantalla y guarda
   solo. Ya se rompio el actualizador por pedirle que escribiera una linea.
7. **No reintentar el login en bucle.** Una de las plataformas bloquea la
   cuenta tras varios intentos fallidos.
8. **Detectar material nuevo es la razon de ser del bot.** Si eso falla, no
   sirve nada de lo demas. Cualquier cambio que toque la deteccion se prueba
   dos veces.

---

## 3. Los archivos y quien hace que

| Archivo | Responsabilidad | No hace |
|---|---|---|
| `fuentes.py` | configuracion | logica |
| `version.py` | numero de version, titulo, cambios, que probar | todo lo demas |
| `almacen.py` | memoria en gist, respaldo en repo | avisos |
| `ia.py` | resumenes, charla, traducir ordenes a JSON | decidir o ejecutar |
| `notificar.py` | mandar, editar, formatear | decidir |
| `panel.py` | dibujar pantallas de botones | leer plataformas |
| `comandos.py` | interpretar toques, comandos y fechas | dibujar |
| `watcher.py` | el motor y la clase `Vigilante` | todo lo de arriba |
| `actualizar.py` | respaldo, parche, permisos y subida a GitHub | correr el bot |

Si vas a agregar algo, ponelo en la capa que corresponde. El motor no debe
saber como se ve un mensaje.

---

## 4. Como se conecta a cada plataforma

### Modo `b64`, plataforma propia

```python
s.get(base + "/session/login")
s.post(base + "/session/do_login", data={
    "username": usuario,
    "real-password": clave,                          # en claro, OBLIGATORIO
    "password": base64.b64encode(clave.encode()).decode(),
})
# entraste si  "/session/login" not in r.url
```

**Los dos campos de clave viajan juntos.** Mandar solo uno da
"contrasena invalida". Ya se cometio ese error.

- lista de ramos: `GET /cursos`, elementos con `data-courseid`
- adentro de un ramo: `GET /curso/<id>`
- modulos: `GET /curso/<id>/modulo/<idModulo>`
- adjuntos: `/curso/<id>/modulo/<mid>/archivo/<fid>`
- ramos de semestres anteriores: `POST /async/main/oldCourses`
- **no hay captcha activo.** El bloque que lo invocaba esta comentado en el
  javascript. Ya se verifico.

**El hallazgo mas importante de todo el proyecto.** El menu de material de
esa plataforma **no esta en el HTML**, se arma con javascript:

```javascript
var arbol = JSON.parse('[ ... ]');
$('#myTree').on('selected.fu.tree', function (event, data) {
    location.href = base + "/curso/<id>/modulo/" + data.target.id;
});
```

Por eso el bot se perdio material real durante dos parches. La solucion vive
en `watcher.py`: `RE_ARBOL_JS`, `_texto_js`, `_aplanar_arbol` y
`arbol_escondido(html, base, id_ramo)`. **Si un dia un ramo aparece vacio,
mira primero ahi.**

### Modo `aula`, plataforma educativa estandar

```python
r0 = s.get(base + "/login/index.php")
token = sopa.find("input", {"name": "logintoken"})["value"]
s.post(base + "/login/index.php",
       data={"anchor": "", "logintoken": token,
             "username": usuario, "password": clave})
```

- portada `GET /my/`
- ramos: enlaces con `/course/view.php?id=`
- actividades: `li.activity.modtype_<tipo>` con `.instancename`
- archivos: `pluginfile.php`

### Bajar archivos

No alcanza con mirar la extension del enlace. Hay adjuntos publicados como
`/archivo/8891`, sin extension en ningun lado. Por eso existen
`parece_descarga()`, `es_bajable()` con plan B, `nombre_de_archivo()` que
mira el `Content-Type` de la respuesta, y `extension_de_tipo()`.

---

## 5. La memoria

Vive en un **gist privado**. `GH_TOKEN` tiene que ser un token **clasico**
con la casilla `gist`. Los tokens de permisos finos no manejan gists, esto
ya se comprobo.

Si el gist falla, `almacen.guardar()` escribe en `estado/visto.json` pero
pasado por `reducir()`, que deja solo huellas. El repositorio es publico, ahi
no puede haber texto legible.

Claves de huella, en `watcher.huella()`:

```
item   -> huella("item", clave_de_ramo, url, titulo en minusculas sin tildes)
grupo  -> huella("grupo", clave_de_fuente, id_del_ramo)
tarea  -> huella("tarea", clave_de_ramo, url)
plazo  -> huella("plazo", uid del calendario)
arbol  -> huella("arbol", ...)   el menu escondido en javascript
```

**Las huellas nunca se borran**, ni al archivar un ramo. Si el usuario
repite una asignatura, no se le reanuncia el material viejo.

Una tarea propia del usuario se guarda asi, con la clave
`mio_<timestamp>`:

```python
{"grupo": "", "clave": "", "titulo": "...", "url": "",
 "vence": "%Y-%m-%d %H:%M", "hecho": False, "nota": "", "mio": True}
```

---

## 6. Las ordenes habladas, como funcionan

Esto es lo mas delicado que hay. El circuito completo:

1. Llega texto sin barra. `comandos.atender` lo manda a
   `watcher.proponer(texto)`.
2. `watcher._contexto_orden()` arma el contexto: la hora de ahora, los ramos
   y los pendientes.
3. `ia.interpretar(estado, texto, contexto)` le pide a la IA **solo un
   JSON**. `ia._json_de()` limpia las comillas de bloque y corta entre la
   primera llave y la ultima.
4. `watcher.validar_orden(orden)` revisa que la accion exista, que la fecha
   sea futura y razonable, que el ramo exista. Devuelve `(plan, texto)`.
   **Las fechas y los plazos los calcula Python**, no se copian de la IA.
5. Se manda la confirmacion con `Dale` y `No`. Vence a los 30 minutos.
6. `watcher.confirmar_propuesta(si=True)` llama a `ejecutar_plan(plan)`.

Contrato JSON, cerrado:

```
{"accion":"recordar","cuando":"AAAA-MM-DD HH:MM","que":"texto corto"}
{"accion":"pausa","horas":3}
{"accion":"seguir"}
{"accion":"callar","ramo":"nombre"}
{"accion":"perfil","perfil":"suave|normal|apretado|diario","ramo":"o vacio"}
{"accion":"revisar"}
{"accion":"resumen","ramo":"nombre"}
{"accion":"hecho","tarea":"titulo o parte del titulo"}
{"accion":"noche"}
{"accion":"ninguna"}
```

Si agregas una accion, tocas cuatro lugares: `ia.ORDEN_ACCION`,
`watcher.validar_orden`, `watcher.ejecutar_plan` y las pruebas.

`ia.MANUAL` es el manual del bot en criollo, pegado adentro del pedido de
charla. Por eso la IA sabe contestar dudas de uso. **Si cambias como
funciona algo, actualiza el MANUAL**, o la IA va a explicar algo que ya no
existe.

---

## 7. Interpretar fechas: `comandos.cuando(texto, ahora)`

Devuelve `(fecha, resto)`. Entiende `20m`, `3h`, `2d`, `5 minutos`,
`2 horas`, `hoy 21:00`, `manana 09:00`, `lunes 18:45` y `HH:MM` pelado.
`RELLENO` saca las muletillas del principio (`en`, `el`, `este`, `de`...).

**El error mas caro de esta funcion**, ya cometido:

```python
falta = (DIAS.index(uno) - ahora.weekday()) % 7 or 7   # MAL
```

Ese `or 7` convierte el cero en siete, asi que nombrar el dia de hoy siempre
saltaba a la semana siguiente. Lo correcto es dejar el cero y solo saltar si
la hora ya paso. **Un `or` sobre un cero legitimo se come el caso mas
comun.**

---

## 8. Decisiones tomadas y por que

No las revuelvas sin preguntar. Cada una salio de un problema real.

| Decision | Motivo |
|---|---|
| primera corrida muda | si no, el primer dia le llegan 200 avisos |
| `CONFIRMAR_FALLA = 3` | las plataformas se reinician solas |
| un aviso por trabajo, no por archivo | un trabajo con 3 PDF es una cosa sola |
| resumen solo en la cita | separa lo que dijo la maquina de lo que dice la plataforma |
| animacion solo a pedido, y lenta (`ANIM_SEGUNDOS = 6.5`) | si va rapido parece que va a explotar. Se lo quejo tres veces |
| silenciar caduca a los 14 dias | el miedo real es perderse algo por un toque |
| plazos suenan siempre | ni la pausa ni el silencio ni la madrugada los frenan |
| gist privado, no cifrado | perder la clave era peor, y git guarda el historial |
| repositorio publico | minutos ilimitados, y aca no hay nada privado |
| el bot no ancla nada (`ANCLAR_PANEL = False`) | cada anclada deja un cartelito y ensucia |
| ventana despierta 07:00 a 02:00 (`DESPIERTO = (7, 2)`) | asi los botones contestan en un segundo. **Ya se cerro, no vuelvas a ofrecer ampliarla** |
| los archivos se mandan al chat | para no entrar a la plataforma solo a bajar un PDF |
| material y tareas se marcan distinto | lo que se entrega dice "hecho", lo que solo se mira dice "lo vi" |
| un solo recordatorio por cosa sin ver | empujoncito, no alarma |
| `AVISOS_DE_MIS_RECORDATORIOS = [0]` | un apunte propio suena **una vez**. Los perfiles son para las entregas de la plataforma |
| recordatorios de dos toques | escribir la fecha a mano es lento y se escribe mal |
| Word y PowerPoint se leen sin dependencias | son zip con XML. Los `.doc` y `.ppt` viejos no tienen arreglo |
| el aviso de version no se borra | es el unico mensaje que tiene que quedar |

---

## 9. Errores que ya se cometieron

No los repitas.

| Error | Como se arreglo |
|---|---|
| falsos positivos: `Inicio`, `Mis Cursos`, `Portada` | lista `PALABRAS_MENU` y el parametro `propia=` |
| `tipo_de()` clasificaba mal | busca la extension en `href` y en el texto por separado |
| login incompleto en modo `b64` | van los dos campos de clave |
| se dio por hecho que habia captcha | no lo hay, estaba comentado |
| **el menu de material se armaba con javascript** | `arbol_escondido()`. Se perdio material real |
| enlace de descarga sin extension | `parece_descarga()`, `nombre_de_archivo()` por `Content-Type` |
| dos botones que devolvian lo mismo | el plan B de `resumen_ramo` imprimia la lista de material |
| comandos dentro de `<code>` | en la mensajeria eso se copia pero **no se toca**. Van en texto pelado |
| `or 7` sobre el dia de hoy | ver el punto 7 |
| hitos de perfil aplicados a un apunte propio | `AVISOS_DE_MIS_RECORDATORIOS` |
| una guarda contra el ruido del arranque se comia el primer aviso de version | se saco el porton de `avisar_version` |
| `pop` adentro de un `or` | si la primera condicion es verdadera, el `pop` no corre |
| posponer no movia la fecha | `dormida_hasta` calla pero deja la fecha vieja |
| `fromtimestamp` en los registros | usa el reloj de la maquina, que en Actions es UTC |
| se le pidio editar la configuracion a mano | el programa pregunta y guarda solo |
| token sin `repo` | GitHub contesta **404**, no 403. Parecia archivo perdido y era permiso |
| clave nueva de IA en la direccion | las `AQ.` **solo** andan en la cabecera `x-goog-api-key` |
| se recomendo cifrar la memoria sin decir los contras | se cambio por el gist |
| el usuario no cargaba las variables de entorno | `secretos.py` y un corte con mensaje claro |
| se referencio una funcion antes de escribirla | despues de escribir una llamada nueva, buscala para confirmar que existe |

---

## 10. Si te piden cambiar el proveedor de IA

Todo esta en `ia.py`. Hay dos motores: `_gemini` y `_compatible`. El segundo
sirve para cualquier servicio que hable el formato de OpenAI, que hoy son
casi todos.

Para mudarse:

```python
IA = {"proveedor": "compatible",
      "modelo": "el-que-sea",
      "url": "https://el-servicio/v1", ...}
```

Y cambiar `IA_KEY`. Nada mas. Ojo con una diferencia real: solo el modo
`gemini` se traga un PDF entero. Con `compatible`, el PDF se convierte a
texto con `pypdf` antes de mandarlo, y un PDF escaneado no da texto. En ese
caso `resumir()` devuelve `None` y el aviso sale sin la cita, que es
exactamente lo que tiene que pasar. **No inventes un resumen.**

Si la IA falla 5 veces seguidas se apaga sola. `/ia on` la vuelve a prender,
y `/estado` dice el motivo por el que se apago.

---

## 11. El actualizador

`actualizar.py` hace cuatro pasos: **[1]** respaldo, **[2]** buscar el zip
mas nuevo en Descargas y aplicarlo, **[3]** verificar el token, **[4]**
subir a GitHub por la API de contenidos.

- Busca el parche en Descargas, incluso adentro de OneDrive.
- `FUERA` es la lista de lo que nunca se sube: claves, `estado`, `respaldos`,
  `__pycache__`.
- Con `workflow` en el token dispara la corrida al toque. Sin eso, hay que
  esperar al reloj.
- **Nunca le pidas al usuario que escriba `GH_REPO` a mano.** Ya paso: puso
  la direccion entera y todo devolvia 404. `normalizar_repo()` y
  `elegir_repo()` existen por eso.

---

## 12. Las pruebas

Corren sin conexion y sin claves reales.

```
python3 -m py_compile watcher.py comandos.py panel.py fuentes.py version.py \
    ia.py actualizar.py secretos.py notificar.py almacen.py
python3 _p12.py    # deteccion, anclas, arbol, configuracion
python3 _p13.py    # arbol javascript, archivos sin extension, material vs resumen
python3 _p14.py    # ayuda apretable, perfiles, ordenes habladas, version
python3 _p15.py   # fechas, minutos, pantalla de recordatorios
python3 _p16.py    # archivos por alcance, ordenes habladas, anillo de claves
python3 _p17.py    # clases por video, reloj de GitHub, compartir y cifrado
```

El truco para probar sin red: `bot = W.Vigilante.__new__(W.Vigilante)`, se
le enchufan a mano las cosas que necesita, y se reemplaza `W.N.enviar` por
una funcion que guarda en una lista. A `P.pantalla` se le pasa un
diccionario de acciones falso.

**En las pruebas no hardcodees el numero de version**, usa `VER.VERSION`. Ya
se rompieron cinco pruebas por eso, la ultima en la v5.5.

**La maquina de GitHub anda en UTC y el bot en la zona del usuario.** Si en
una prueba usas `datetime.now()`, el "hoy" se te va un dia y las fechas
fallan sin motivo. Usa siempre `HOY = W.ahora()`.

**El silencio de un ramo se guarda como `%Y-%m-%d`, sin hora.** Si en una
prueba le pones hora, `callado()` no lo lee y la prueba miente.

---

## 13. Antes de entregar cualquier cambio

1. Compila todos los archivos.
2. Corre las cuatro pruebas.
3. Busca las palabras identificables en todo lo que vas a entregar.
4. **Sube `version.py`**: numero nuevo, titulo, y los cambios en criollo.
   Si no lo haces, el usuario no se entera de nada.
5. Entrega un zip **solo con los archivos que se reemplazan**, nunca codigo
   pegado.
6. Anota lo que cambiaste en `PROBLEMAS.md`.
7. Antes de armar un parche, fijate si el anterior esta puesto. Ya paso que
   el usuario mandara una carpeta sin aplicar el parche previo.
