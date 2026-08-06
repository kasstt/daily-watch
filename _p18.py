# -*- coding: utf-8 -*-
"""La tanda de pruebas de la v5.6.

Cubre los doce puntos que aparecieron en las pruebas de uso real:

   1. clave rechazada, aviso una vez por dia y sin insistir
   2. el aviso de version dice la hora
   3. el aviso de version manda PRIMERO y anota despues
   4. la IA sin cupo no rompe las ordenes locales
   5. avisos que no son archivos
   6. los avisos escritos del profe (el agujero grande)
   7. pendientes que se pueden tocar
   8. deshacer, con aviso y con el boton que desaparece
   9. /recordar de verdad
  10. boton para crear recordatorios
  12. el aviso ciego de "cambio algo y no se que"

No toca internet, no necesita claves y no manda un mensaje de verdad.
Se corre con:  python3 _p18.py
"""
import datetime as dt
import os
import sys

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("CLAVE_COMPARTIR", "llave-de-prueba-nada-real")

import avisos as AV          # noqa: E402
import comandos as C         # noqa: E402
import fuentes as CFG        # noqa: E402
import notificar as N        # noqa: E402
import panel as P            # noqa: E402
import version as VER        # noqa: E402
import watcher as W          # noqa: E402

FALLOS = []


def ok(cond, que):
    if cond:
        print("  ok   %s" % que)
    else:
        print("  FALLA %s" % que)
        FALLOS.append(que)


def titulo(t):
    print("\n== %s" % t)


# ------------------------------------------------- el chat, de mentira
MANDADOS = []


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append({"texto": texto, "silencioso": silencioso,
                     "botones": botones})
    return len(MANDADOS)


def _editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    MANDADOS.append({"texto": texto, "silencioso": True, "botones": botones})
    return mensaje_id


def _nada(*a, **k):
    return True


N.enviar = _enviar
N.editar = _editar
N.borrar = _nada
N.anclar = _nada
N.desanclar = _nada
N.avisar_boton = _nada
N.mandar_documento = lambda *a, **k: True
N.mandar_archivo = lambda *a, **k: True
N.publicar_menu = _nada
N.quitar_teclado = _nada


def limpiar():
    del MANDADOS[:]


def ultimo():
    return MANDADOS[-1]["texto"] if MANDADOS else ""


def todo_lo_mandado():
    return "\n".join(m["texto"] for m in MANDADOS)


def filas_de(b):
    if not b:
        return []
    return (b or {}).get("inline_keyboard", [])


def datos_de_botones(b):
    return [x.get("callback_data", "") for fila in filas_de(b) for x in fila]


# OJO: la maquina anda en UTC y el bot en la zona de Chile.
HOY = W.ahora()
CLAVE = "A:1"
OTRA = "A:2"


def bot_de_prueba():
    b = W.Vigilante.__new__(W.Vigilante)
    b.estado = {
        "items": {},
        "grupos": {
            CLAVE: {"nombre": "C\u00c1LCULO INTEGRAL", "emoji": "\U0001F4D8",
                    "fuente": "A", "id": "1", "url": "http://x/curso/1",
                    "visto": "", "cantidad": 0},
            OTRA: {"nombre": "Contabilidad", "emoji": "\U0001F4D8",
                   "fuente": "A", "id": "2", "url": "", "visto": "",
                   "cantidad": 0},
        },
        "tareas": {}, "novedades": [], "avisos": {}, "callados": {},
        "perfiles": {}, "fallas": {}, "ausentes": {}, "archivados": {},
        "config": {}, "avisos_vistos": {}, "deshacer": None,
        "version_avisada": "", "version_desde": "", "aviso_clave": {},
        "fallas_ia": 0, "arrancado": True,
    }
    b.sesiones = {}
    b.bases = {}
    b.cache = {}
    b.modo = "gist"
    b.gist_nuevo = False
    b.guardar = lambda *a, **k: True
    return b


# La pagina de Avisos tal como se ve en la plataforma: un panel con titulo
# "Avisos", dos avisos fijados y NINGUN enlace para bajar.  Por eso el bot
# viejo no veia nada aca.
HTML_AVISOS = """
<html><body>
<div class="panel">
  <div class="panel-heading">Avisos</div>
  <div class="panel-body">
    <div class="aviso-item">
      <h4>Clase subida</h4>
    </div>
    <div class="aviso-item">
      <p>Buenas tardes, escribo para informar que la universidad tomo la
      decision de clases online los dias 3 y 4 de agosto. Saludos.</p>
    </div>
  </div>
</div>
<div class="footer">Ultimo acceso: 03/08/2026 18:28 - 4 visitas</div>
</body></html>
"""


# ============================================================ punto 6
titulo("6. los avisos escritos del profe")

fichas = AV.avisos_de_la_pagina(HTML_AVISOS, "C\u00c1LCULO INTEGRAL")
ok(len(fichas) >= 1, "encuentro avisos en una pagina que no tiene enlaces")

todo = " ".join((f.get("titulo", "") + " " + f.get("texto", "")) for f in fichas)
ok("online" in todo.lower(), "el aviso de clases online aparece")
ok(any(f.get("urgente") for f in fichas),
   "y queda marcado como urgente, asi suena de noche")

ok(AV.urgente("clases online los dias 3 y 4 de agosto"),
   "clases online cuenta como urgente")
ok(AV.urgente("se suspende la clase de manana"), "una suspension es urgente")
ok(AV.urgente("se posterga el certamen"), "un certamen postergado es urgente")
ok(not AV.urgente("buenas tardes, subi el material de la semana"),
   "pero un mensaje comun no lo es")

# La huella es el texto, no el enlace: tiene que aguantar espacios de mas,
# tildes y mayusculas, o el bot te avisa dos veces por lo mismo.
h1 = AV.huella_de_aviso("Clase subida", "la decision de clases online")
h2 = AV.huella_de_aviso("CLASE  SUBIDA", "la decisi\u00f3n de clases   online")
ok(h1 == h2, "la huella no cambia por tildes, espacios ni mayusculas")
ok(h1 != AV.huella_de_aviso("Clase subida", "otra cosa distinta"),
   "pero si cambia el texto, cambia la huella")

ya = {}
ok(len(AV.nuevos(fichas, ya)) == len(fichas), "la primera vez son todos nuevos")
ok(ya == {}, "y nuevos() NO toca la memoria, la anota el bot al mandar")
for f in fichas:
    ya[f["huella"]] = "2026-08-03"
ok(AV.nuevos(fichas, ya) == [], "la segunda vez no hay ninguno nuevo")

ok(AV.avisos_de_la_pagina(None) == [], "con basura devuelve vacio y no revienta")
ok(AV.avisos_de_la_pagina("<html") == [], "con html roto tampoco revienta")

# Y el bot: el primer paso anota lo viejo callado, el segundo si avisa.
b = bot_de_prueba()
ficha = b.estado["grupos"][CLAVE]
limpiar()
mando = b.avisos_nuevos(CLAVE, ficha, fichas)
ok(not mando, "la primera lectura del ramo no te bombardea con lo viejo")
ok(ficha.get("avisos_leidos"), "queda anotado que ya los leyo")
ok(MANDADOS == [], "y no manda nada")

nuevo = AV.avisos_de_la_pagina(
    "<div class='panel'><div class='panel-heading'>Avisos</div>"
    "<div class='aviso-item'><p>Se suspende la evaluacion del viernes, "
    "se reprograma para el lunes siguiente.</p></div></div>",
    "C\u00c1LCULO INTEGRAL")
limpiar()
mando = b.avisos_nuevos(CLAVE, ficha, nuevo)
ok(mando, "un aviso nuevo si se manda")
ok("suspende" in todo_lo_mandado().lower(), "y el texto del aviso va entero")
ok(any(t.get("aviso") for t in b.estado["tareas"].values()),
   "queda en Pendientes para no perderlo")
ok(all(not t.get("es_tarea", True) for t in b.estado["tareas"].values()
       if t.get("aviso")),
   "pero NO como entrega del ramo")
ok(any(n.get("tipo") == "aviso" for n in b.estado["novedades"]),
   "y aparece en novedades como aviso")

limpiar()
ok(not b.avisos_nuevos(CLAVE, ficha, nuevo), "el mismo aviso no se repite")
ok(MANDADOS == [], "de verdad no lo repite")

# Un ramo callado igual recibe el aviso: una suspension no espera.
b2 = bot_de_prueba()
f2 = b2.estado["grupos"][CLAVE]
f2["avisos_leidos"] = True
b2.estado["callados"][CLAVE] = {
    "hasta": (HOY + dt.timedelta(days=5)).strftime("%Y-%m-%d"), "cuenta": 0}
limpiar()
ok(b2.avisos_nuevos(CLAVE, f2, nuevo),
   "un ramo silenciado igual te avisa de una suspension")

ok(b.texto_avisos(), "/avisos contesta algo")
ok("suspende" in b.texto_avisos().lower(), "y muestra el aviso guardado")
ok(bot_de_prueba().texto_avisos(), "sin avisos tambien contesta, sin romperse")


# ============================================================ punto 12
titulo("12. el aviso ciego que aparecia tres veces al dia")

b = bot_de_prueba()
f = b.estado["grupos"][CLAVE]

# Freno 2: la primera revision distinta NO avisa, hacen falta dos.
limpiar()
ok(not b._cambio_sin_nombre(CLAVE, f, "aaa", "bbb"),
   "la primera revision distinta no te molesta")
ok(b._cambio_sin_nombre(CLAVE, f, "bbb", "ccc"),
   "la segunda seguida si avisa")

# Freno 3: y despues no vuelve a avisar el mismo dia.
ok(not b._cambio_sin_nombre(CLAVE, f, "ccc", "ddd"),
   "no avisa dos veces el mismo dia")
ok(not b._cambio_sin_nombre(CLAVE, f, "ddd", "eee"),
   "ni tres veces, que es justo lo que pasaba")

# Freno 1: la pagina que va y viene entre dos estados se calla sola.
b3 = bot_de_prueba()
f3 = b3.estado["grupos"][CLAVE]
b3._cambio_sin_nombre(CLAVE, f3, "uno", "dos")
b3._cambio_sin_nombre(CLAVE, f3, "dos", "tres")
f3["aviso_ciego"] = ""
ok(not b3._cambio_sin_nombre(CLAVE, f3, "tres", "dos"),
   "si la firma ya se vio antes, la pagina se mueve sola")
ok(f3.get("pagina_inquieta"), "y el ramo queda marcado como inquieto")
f3["aviso_ciego"] = ""
ok(not b3._cambio_sin_nombre(CLAVE, f3, "dos", "nueve"),
   "un ramo inquieto no vuelve a dar avisos ciegos")

ok(CFG.HORAS_ENTRE_AVISOS_CIEGOS >= 24, "como maximo uno por dia")
ok(CFG.REVISIONES_PARA_AVISO_CIEGO >= 2, "y hacen falta dos revisiones")

# La firma no se tiene que mover por un reloj o una fecha en la pagina.
uno = W.firma_de_pagina(
    "<div>Guia 3<span>Ultimo acceso: 03/08/2026 18:28</span>"
    "<span>4 visitas</span></div>")
dos = W.firma_de_pagina(
    "<div>Guia 3<span>Ultimo acceso: 04/08/2026 09:11</span>"
    "<span>7 visitas</span></div>")
ok(uno == dos, "la firma ignora el reloj y el contador de visitas")
tres = W.firma_de_pagina("<div>Guia 3<span>Guia 4</span></div>")
ok(uno != tres, "pero si aparece material nuevo, la firma cambia")


# ============================================================ punto 9 y 10
titulo("9 y 10. recordatorios")

b = bot_de_prueba()

# Esto es literalmente lo que se escribio en el chat y no se entendio.
o = b.orden_local("Hazme un recordatorio de levantarme en 2 min")
ok(o and o.get("accion") == "recordar", "entiende el pedido armado, sin IA")
ok(o and "levantar" in (o.get("que") or "").lower(),
   "y saca bien que hay que recordar")
ok(o and not (o.get("que") or "").rstrip().endswith(" en"),
   "sin dejar el 'en' colgando al final")

for frase in ("ponme una alarma para estudiar en 30 minutos",
              "crea un aviso de sacar la ropa en 1 hora",
              "anotame un recordatorio de la prueba el viernes 18:00",
              "necesito un recordatorio para llamar a mi mama en 3 horas"):
    o = b.orden_local(frase)
    ok(o and o.get("accion") == "recordar", "entiende: %s" % frase)

o = b.orden_local("recordame en 2 min levantarme")
ok(o and o.get("accion") == "recordar", "y la forma directa sigue andando")

ok(b.orden_local("hola como andas") is None,
   "una charla comun no se toma como orden")
ok(b.orden_local("") is None, "y con nada no revienta")

ok(b._limpiar_que("de levantarme en") == "levantarme",
   "_limpiar_que saca el relleno de los dos lados")
ok(b._limpiar_que("que estudiar para") == "estudiar", "y el 'que' del principio")
ok(b._limpiar_que("") == "", "con vacio devuelve vacio")

# /recordar: tres cosas estaban mal y se probaban ninguna.
b = bot_de_prueba()
r = C._recordar(b.estado, "20 min sacar la ropa", HOY)
ok(len(b.estado["tareas"]) == 1, "/recordar crea el recordatorio")
una = list(b.estado["tareas"].values())[0]
ok(una["titulo"] == "sacar la ropa", "con el texto justo")
ok(una.get("es_tarea") is False,
   "marcado como TUYO, no como entrega del ramo")
ok(una.get("mio") is True, "y como tuyo")

# Dos en el mismo minuto: antes el segundo borraba al primero.
C._recordar(b.estado, "20 min comprar pan", HOY)
ok(len(b.estado["tareas"]) == 2,
   "dos recordatorios en el mismo minuto NO se pisan")
ok(len(set(b.estado["tareas"].keys())) == 2, "y tienen id distinto")

r = C._recordar(b.estado, "", HOY)
ok("recordar" in r.lower(), "sin nada explica como se usa")
ok(len(b.estado["tareas"]) == 2, "y no crea nada")
r = C._recordar(b.estado, "cualquier cosa sin fecha", HOY)
ok("prob" in r.lower() or "fecha" in r.lower(),
   "sin fecha lo dice con un ejemplo")

ok(("recordar", "guardame un apunte") in C.MENU, "/recordar sigue en el menu")
ok(any(c == "avisos" for c, _ in C.MENU), "/avisos esta en el menu")
ok(any(c == "deshacer" for c, _ in C.MENU), "/deshacer esta en el menu")


# ============================================================ punto 7
titulo("7. pendientes que se pueden tocar")

b = bot_de_prueba()
b.estado["tareas"] = {
    "mio_1": {"grupo": "", "clave": "", "titulo": "lista de compras",
              "url": "", "vence": (HOY + dt.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"),
              "hecho": False, "nota": "pan, leche, yerba", "mio": True,
              "es_tarea": False},
    "t_2": {"grupo": "C\u00c1LCULO INTEGRAL", "clave": CLAVE,
            "titulo": "entregar la guia 3", "url": "http://x/g3",
            "vence": (HOY - dt.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
            "hecho": False, "nota": "", "es_tarea": True},
    "t_3": {"grupo": "", "clave": "", "titulo": "esto ya esta", "url": "",
            "vence": "", "hecho": True, "nota": "", "es_tarea": True},
    "aviso_zz": {"grupo": "C\u00c1LCULO INTEGRAL", "clave": CLAVE,
                 "titulo": "Clases", "url": "", "vence": "", "hecho": False,
                 "nota": "", "es_tarea": False, "aviso": True,
                 "texto": "clases online los dias 3 y 4"},
}

lista = b.pendientes_para_panel()
ids = [x[0] for x in lista]
ok("mio_1" in ids and "t_2" in ids, "la lista trae los pendientes")
ok("t_3" not in ids, "y no trae los que ya estan hechos")
ok(len(lista[0]) == 5, "cada uno viene con sus cinco datos")
ok(ids[0] == "t_2", "lo vencido va primero")
ok(ids[-1] == "aviso_zz", "y lo que no tiene fecha va al final")
ficha_compras = [x for x in lista if x[0] == "mio_1"][0]
ok(ficha_compras[4] is True, "sabe cual tiene nota escrita")

acc = {"pendientes_para_panel": b.pendientes_para_panel,
       "ficha_tarea": lambda i: b.estado["tareas"].get(i),
       "texto_avisos": b.texto_avisos,
       "ahora": W.ahora}

texto, bot = P.pantalla(b.estado, "p:pen", acc)
filas = filas_de(bot)
ok(len(filas) > 1, "la pantalla de Pendientes se dibuja sin romperse")
datos = datos_de_botones(bot)
ok("pv:mio_1" in datos, "cada pendiente tiene su boton para abrirlo")
ok("p:rec" in datos, "y esta el boton de nuevo recordatorio")

texto, bot = P.pantalla(b.estado, "p:ver:mio_1", acc)
ok("pan, leche, yerba" in texto, "al abrirlo se lee la nota entera")
datos = datos_de_botones(bot)
ok("ql:mio_1" in datos, "tiene el boton de ya esta")
ok("qm:mio_1" in datos, "el de posponer")
ok("pn:mio_1" in datos, "el de escribir nota")
ok("pb:mio_1" in datos, "y el de borrar")

texto, bot = P.pantalla(b.estado, "p:ver:aviso_zz", acc)
ok("online" in texto, "un aviso del profe se abre y se lee completo")

texto, bot = P.pantalla(b.estado, "p:ver:no_existe", acc)
ok("ya no" in texto.lower(), "si el pendiente no esta, lo dice tranquilo")

texto, bot = P.pantalla(b.estado, "p:prof", acc)
ok(len(filas_de(bot)) >= 1, "la pantalla de avisos del profe se dibuja")

# Borrar pregunta antes.
aviso, donde = P.toque(b.estado, "pb:mio_1", acc, HOY)
ok(donde == "p:borrar:mio_1", "borrar lleva a la pregunta, no borra de una")
ok("mio_1" in b.estado["tareas"], "y todavia no borro nada")
texto, bot = P.pantalla(b.estado, "p:borrar:mio_1", acc)
ok("lista de compras" in texto, "la pregunta dice cual es")
datos = datos_de_botones(bot)
ok("qx:mio_1" in datos and "p:ver:mio_1" in datos, "con si y con no")

# Escribir nota deja al bot esperando el texto.
P.toque(b.estado, "pn:t_2", acc, HOY)
ok(b.estado.get("esperando_nota") == "t_2", "escribir nota queda esperando")
b.estado.pop("esperando_nota", None)

texto, bot = P.pantalla(bot_de_prueba().estado, "p:pen", acc)
ok(len(filas_de(bot)) >= 1, "sin pendientes tambien se dibuja")


# ============================================================ punto 8
titulo("8. deshacer")

ok(CFG.PERMITIR_DESHACER, "deshacer viene prendido")


def bot_con_uno():
    b = bot_de_prueba()
    b.estado["tareas"] = {
        "mio_9": {"grupo": "", "clave": "", "titulo": "osi", "url": "",
                  "vence": (HOY + dt.timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"),
                  "hecho": False, "nota": "la nota importante", "mio": True,
                  "es_tarea": False}}
    a = {"pendientes_para_panel": b.pendientes_para_panel,
         "ficha_tarea": lambda i: b.estado["tareas"].get(i),
         "texto_avisos": b.texto_avisos, "ahora": W.ahora,
         "tablero": lambda: {"salud": "ok", "ramos": 2, "pendientes": 1,
                             "nuevas": 0, "nuevas_hoy": 0, "ultima": "ahora",
                             "memoria": "", "ia": "", "silenciados": ""},
         "en_pausa": lambda: False, "hoy": W.ahora,
         "lista_ramos": lambda: []}
    return b, a


# ---- borrar y volver atras
b, acc = bot_con_uno()
aviso, donde = P.toque(b.estado, "qx:mio_9", acc, HOY)
ok("mio_9" not in b.estado["tareas"], "el boton borra")
ok("deshacer" in aviso.lower(), "pero AVISA que se puede deshacer")
ok(b.estado.get("deshacer"), "y guarda como estaba antes")
texto, bot = P.pantalla(b.estado, "p:pen", acc)
ok("z:1" in datos_de_botones(bot), "aparece el boton de deshacer")

aviso, donde = P.toque(b.estado, "z:1", acc, HOY)
ok("mio_9" in b.estado["tareas"], "deshacer lo trae de vuelta")
ok(b.estado["tareas"]["mio_9"]["nota"] == "la nota importante",
   "con la nota y todo")
ok(not b.estado.get("deshacer"), "y el boton se apaga")
texto, bot = P.pantalla(b.estado, "p:pen", acc)
ok("z:1" not in datos_de_botones(bot),
   "el boton de deshacer desaparece despues de usarlo")
aviso, donde = P.toque(b.estado, "z:1", acc, HOY)
ok("nada" in aviso.lower(), "y si lo toca igual, contesta tranquilo")

# ---- marcar y volver atras
b, acc = bot_con_uno()
aviso, donde = P.toque(b.estado, "ql:mio_9", acc, HOY)
ok(b.estado["tareas"]["mio_9"]["hecho"] is True, "marcar lo marca")
ok("deshacer" in aviso.lower(), "y avisa")
P.toque(b.estado, "z:1", acc, HOY)
ok(b.estado["tareas"]["mio_9"]["hecho"] is False, "deshacer lo desmarca")

# ---- posponer y volver atras (aca cambia el id, es el caso complicado)
b, acc = bot_con_uno()
antes = b.estado["tareas"]["mio_9"]["vence"]
aviso, donde = P.toque(b.estado, "qm:mio_9", acc, HOY)
ok("mio_9" not in b.estado["tareas"], "al posponer cambia de id")
ok(len(b.estado["tareas"]) == 1, "y sigue habiendo uno solo")
ok("deshacer" in aviso.lower(), "avisa igual")
P.toque(b.estado, "z:1", acc, HOY)
ok(len(b.estado["tareas"]) == 1, "deshacer no deja dos copias")
ok("mio_9" in b.estado["tareas"], "vuelve con el id de antes")
ok(b.estado["tareas"]["mio_9"]["vence"] == antes, "y con la hora de antes")

# ---- desde la pantalla de recordatorios vuelve a la de recordatorios
b, acc = bot_con_uno()
aviso, donde = P.toque(b.estado, "rx:mio_9", acc, HOY)
ok(donde == "p:rec", "desde recordatorios vuelve a recordatorios")
aviso, donde = P.toque(b.estado, "z:1", acc, HOY)
ok(donde == "p:rec", "y deshacer tambien")

# ---- dos que caen en el mismo segundo al posponer
b, acc = bot_con_uno()
choca = HOY + dt.timedelta(hours=6)
b.estado["tareas"]["mio_%d" % int(choca.timestamp())] = {
    "grupo": "", "clave": "", "titulo": "el otro", "url": "",
    "vence": choca.strftime("%Y-%m-%d %H:%M"), "hecho": False, "nota": "",
    "mio": True, "es_tarea": False}
cuantos = len(b.estado["tareas"])
P.toque(b.estado, "qm:mio_9", acc, HOY)
ok(len(b.estado["tareas"]) == cuantos,
   "posponer no se come otro recordatorio que caiga en el mismo minuto")

# El boton de deshacer aparece tambien en la pantalla principal.
b, acc = bot_con_uno()
P.toque(b.estado, "qx:mio_9", acc, HOY)
texto, bot = P.pantalla(b.estado, "p:raiz", acc)
ok("z:1" in datos_de_botones(bot), "y se ve desde la pantalla principal")
ok("p:rec" in datos_de_botones(bot),
   "la pantalla principal tiene el boton de nuevo recordatorio")
ok("p:prof" in datos_de_botones(bot), "y el de avisos del profe")


# ============================================================ punto 2 y 3
titulo("2 y 3. el aviso de version")

ok(":" in VER.FECHA, "la fecha de la version incluye la hora")
ok(VER.VERSION not in ("5.5", "5.4"), "la version subio")
ok(len(VER.CAMBIOS) >= 8, "y trae los cambios escritos")

b = bot_de_prueba()
b.estado["version_avisada"] = ""
limpiar()
b.avisar_version()
ok(MANDADOS, "avisa cuando la version cambio")
salio = todo_lo_mandado()
ok(VER.VERSION in salio, "dice que version es")
ok("entr\u00f3" in salio or "entro" in salio, "y a que hora entro")
ok(b.estado.get("version_avisada") == VER.VERSION, "despues de mandar, anota")
ok(b.estado.get("version_desde"), "y guarda desde cuando")

limpiar()
b.avisar_version()
ok(MANDADOS == [], "y no lo repite en cada vuelta")

# Lo importante del punto 3: si el mensaje NO sale, no se puede anotar como
# avisado, porque entonces nunca mas lo intenta y vos te quedas sin saber.
b2 = bot_de_prueba()
b2.estado["version_avisada"] = ""
viejo = N.enviar
N.enviar = lambda *a, **k: None
try:
    b2.avisar_version()
finally:
    N.enviar = viejo
ok(b2.estado.get("version_avisada") != VER.VERSION,
   "si el mensaje no sale, NO lo marca como avisado")
limpiar()
b2.avisar_version()
ok(MANDADOS, "y lo vuelve a intentar en la vuelta siguiente")


# ============================================================ punto 1
titulo("1. la clave cambiada")

b = bot_de_prueba()
f = {"clave": "A", "nombre": "plataforma A", "emoji": "\U0001F4D8"}
limpiar()
b._aviso_de_clave(f)
salio = todo_lo_mandado()
ok(salio, "cuando la plataforma rechaza la clave, te avisa")
ok("clave" in salio.lower() or "contrase" in salio.lower(),
   "y nombra la clave")
ok("bloque" in salio.lower(), "avisa del riesgo de que se bloquee la cuenta")

limpiar()
b._aviso_de_clave(f)
ok(MANDADOS == [], "pero avisa UNA vez por dia, no insiste")


# ============================================================ punto 4
titulo("4. la IA sin cupo")

# Con la IA apagada, un pedido de recordatorio tiene que andar igual: eso es
# lo que fallaba cuando se acabo el cupo de las claves.
b = bot_de_prueba()
o = b.orden_local("Hazme un recordatorio de levantarme en 2 min")
ok(o and o.get("accion") == "recordar",
   "con la IA apagada el recordatorio se entiende igual")
ok(CFG.IA.get("descanso_cupo_minutos", 0) > 0, "hay descanso por falta de cupo")
ok(len(CFG.IA.get("claves_env", [])) >= 3, "y se pueden poner varias claves")


# ============================================================ nada viejo roto
titulo("nada de lo viejo se rompio")

b = bot_de_prueba()
acc = b._acciones()
for k in ("tablero", "hoy", "ahora", "texto_pendientes", "texto_novedades",
          "pendientes_para_panel", "texto_avisos", "ficha_tarea",
          "dibujar_panel", "abrir_panel", "lista_ramos"):
    ok(k in acc, "el panel sigue teniendo %s" % k)

for donde in ("p:raiz", "p:ramos", "p:rec", "p:avisos", "p:nov", "p:pen",
              "p:sem", "p:ayuda", "p:ajustes", "p:prof", "p:mas"):
    texto, bot = P.pantalla(b.estado, donde, acc)
    # Si algo revienta, pantalla() devuelve UNA sola fila con Volver.
    ok(len(filas_de(bot)) >= 1 and "rompi" not in texto,
       "la pantalla %s se dibuja bien" % donde)

ok(len(P.ATAJOS_RECORDAR) >= 3, "siguen los atajos de recordar")
aviso, donde = P.toque(b.estado, "r:15m", acc, HOY)
ok(b.estado.get("esperando_rec"), "el atajo de 15 min sigue andando")
b.estado.pop("esperando_rec", None)
aviso, donde = P.toque(b.estado, "r:otra", acc, HOY)
ok("recordame" in aviso.lower(), "y 'otra hora' explica como escribirlo")


# --------------------------------------------------------------- final
print("\n" + "-" * 50)
if FALLOS:
    print("%d cosas fallaron:" % len(FALLOS))
    for x in FALLOS:
        print("  - %s" % x)
    sys.exit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
