# Instrucciones para la proxima IA

Si estas leyendo esto, sos una IA a la que le pidieron cambiar este bot.
Lee todo antes de tocar una linea. El dueno no programa: si le entregas algo
roto, no lo va a poder arreglar solo.

---

## 1. Que es esto

Un bot que vigila dos plataformas de clase y avisa por chat cuando aparece
material nuevo. Corre en GitHub Actions cada 5 minutos. Sin servidor.

**Trabaja con el usuario en castellano rioplatense, directo, sin adornos.
Dale la conclusion y los pasos, no el proceso.**

---

## 2. Reglas que no se rompen

1. **Anonimato.** El repositorio es publico. En el codigo no puede aparecer
   el nombre del usuario, el de su universidad, el de las plataformas, ni
   ninguna direccion. Todo eso vive en los Secrets. Antes de entregar,
   busca esas palabras en todos los archivos.
2. **La IA no toca datos.** Los resumenes rellenan una sola parte del aviso,
   la cita con barra. Fechas, nombres, enlaces y plazos los pone el codigo,
   siempre. Una IA que inventa una fecha de entrega cuesta una nota.
3. **Nada revienta hacia afuera.** `notificar.py` e `ia.py` capturan todo.
   Si la IA falla, el aviso sale igual sin la cita. Si el chat falla, el bot
   sigue guardando.
4. **No entregues codigo pegado en el chat.** Entrega archivos para
   descargar. Ya hubo un `SyntaxError` por copiar y pegar mal.
5. **Nunca le pidas que pegue un token en el chat.** Van a `mis_datos.txt` y
   a los Secrets.
6. **No reintentar el login en bucle.** Una de las plataformas bloquea la
   cuenta tras varios intentos fallidos.

---

## 3. Los archivos y quien hace que

| Archivo | Responsabilidad | No hace |
|---|---|---|
| `fuentes.py` | configuracion | logica |
| `almacen.py` | memoria en gist, respaldo en repo | avisos |
| `ia.py` | resumenes | armar mensajes |
| `notificar.py` | mandar, editar, formatear | decidir |
| `panel.py` | dibujar pantallas de botones | leer plataformas |
| `comandos.py` | interpretar toques y comandos | dibujar |
| `watcher.py` | el motor y la clase `Vigilante` | todo lo de arriba |

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
- ramos de semestres anteriores: `POST /async/main/oldCourses`
- los modulos internos son anclas `#mod_<nombre>` en la misma pagina, no
  paginas aparte
- **no hay captcha activo.** El bloque que lo invocaba esta comentado en el
  javascript. Ya se verifico.

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
```

**Las huellas nunca se borran**, ni al archivar un ramo. Si el usuario
repite una asignatura, no se le reanuncia el material viejo.

---

## 6. Decisiones tomadas y por que

No las revuelvas sin preguntar. Cada una salio de un problema real.

| Decision | Motivo |
|---|---|
| primera corrida muda | si no, el primer dia le llegan 200 avisos |
| `CONFIRMAR_FALLA = 3` | las plataformas se reinician solas |
| un aviso por trabajo, no por archivo | un trabajo con 3 PDF es una cosa sola |
| resumen solo en la cita | separa lo que dijo la maquina de lo que dice la plataforma |
| animacion solo a pedido | si trabaja solo, no hay nadie mirando |
| silenciar caduca a los 14 dias | el miedo real es perderse algo por un toque |
| plazos suenan siempre | ni la pausa ni el silencio ni la madrugada los frenan |
| gist privado, no cifrado | perder la clave era peor, y git guarda el historial |
| repositorio publico | minutos ilimitados, y aca no hay nada privado |

---

## 7. Errores que ya se cometieron

No los repitas.

| Error | Como se arreglo |
|---|---|
| falsos positivos: `Inicio`, `Mis Cursos`, `Portada` | lista `PALABRAS_MENU` y el parametro `propia=` |
| `tipo_de()` clasificaba mal | busca la extension en `href` y en el texto por separado, no en la concatenacion |
| login incompleto en modo `b64` | van los dos campos de clave |
| se dio por hecho que habia captcha | no lo hay, estaba comentado |
| se recomendo cifrar la memoria sin decir los contras | se cambio por el gist |
| el usuario no cargaba las variables de entorno | se agrego `secretos.py` y un corte con mensaje claro |

---

## 7 bis. Decisiones tomadas que no hay que revertir sin preguntar

| Decision | Donde | Por que |
|---|---|---|
| El bot no ancla nada | `ANCLAR_PANEL = False` en `fuentes.py` | cada anclada deja un cartelito en el chat y ensucia |
| Ventana despierta 07:00 a 02:00 | `DESPIERTO = (7, 2)` en `fuentes.py` | asi los botones contestan en un segundo. `(0, 0)` seria 24 horas |
| Los archivos se mandan al chat | `ADJUNTAR = True`, `mandar_adjuntos()` en `watcher.py` | para no entrar a la plataforma solo a bajar un PDF |
| Material y tareas se marcan distinto | `botones_tarjeta()` | lo que se entrega dice "hecho", lo que solo se mira dice "lo vi" |
| Un solo recordatorio por cosa sin ver | `HORAS_PARA_RECORDAR_VISTO = 20` | empujoncito, no alarma |
| Word y PowerPoint se leen sin dependencias | `_texto_de_office()` en `ia.py` | son zip con XML. Los `.doc` y `.ppt` viejos no tienen arreglo |

## 8. Si te piden cambiar el proveedor de IA

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

Si la IA falla 5 veces seguidas se apaga sola. `/ia on` la vuelve a prender.

---

## 9. Antes de entregar cualquier cambio

1. Compila todos los archivos.
2. Busca las palabras identificables en todo el repositorio.
3. Prueba sin conexion lo que se pueda.
4. Entrega un zip, no codigo pegado.
5. Anota lo que cambiaste al final de `PROBLEMAS.md`.
