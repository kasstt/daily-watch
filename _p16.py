# -*- coding: utf-8 -*-
"""Quinta tanda de pruebas: archivos, ordenes habladas y anillo de claves.

Todo esto corre SIN internet y sin tocar la plataforma.  Se arma un bot de
mentira, se le reemplaza el mensajero y se mira que salga por el chat.

    python3 _p16.py
"""
import datetime as dt
import os
import sys

os.environ.setdefault("TG_TOKEN", "de-mentira")
os.environ.setdefault("TG_CHAT", "1")

import fuentes as CFG          # noqa: E402
import version as VER          # noqa: E402
import notificar as N          # noqa: E402
import ia as IA                # noqa: E402
import watcher as W            # noqa: E402
import panel as P              # noqa: E402
import comandos as C           # noqa: E402

FALLOS = []


def ok(cond, que):
    print("  %s %s" % ("ok  " if cond else "MAL ", que))
    if not cond:
        FALLOS.append(que)


def titulo(t):
    print("\n== %s" % t)


# ------------------------------------------------------ mensajero falso
MANDADOS = []


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append({"texto": texto, "botones": botones})
    return len(MANDADOS)


def _editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    MANDADOS.append({"texto": texto, "botones": botones})
    return True


def _documento(nombre, datos, leyenda="", silencioso=True, responde_a=None):
    MANDADOS.append({"texto": "[documento] " + nombre, "botones": None})
    return True


N.enviar = _enviar
N.editar = _editar
N.mandar_documento = _documento
N.mandar_archivo = lambda n, c, l="": _documento(n, c, l)
N.borrar = lambda *a, **k: None
N.avisar_boton = lambda *a, **k: None


def limpiar():
    del MANDADOS[:]


def ultimo():
    return MANDADOS[-1]["texto"] if MANDADOS else ""


def datos_de_botones(b):
    if not b or "inline_keyboard" not in b:
        return []
    return [x["callback_data"] for fila in b["inline_keyboard"] for x in fila]


def filas_de(b):
    return (b or {}).get("inline_keyboard", [])


# ------------------------------------------------------ bot de mentira
# OJO: el reloj de la maquina puede estar en otro huso.  Se usa el mismo
# reloj que usa el bot, si no las fechas se van un dia para adelante.
HOY = W.ahora()


def cuando(dias):
    return (HOY - dt.timedelta(days=dias)).strftime("%Y-%m-%d %H:%M")


CLAVE = "A:1"


def novedades_de_prueba():
    n = []
    for i in range(4):
        n.append({"c": CLAVE, "g": "Calculo Integral", "t": "Guia %d" % (i + 1),
                  "u": "https://plataforma/curso/1/archivo/%d" % (100 + i),
                  "f": cuando(i), "tipo": "archivo"})
    for i in range(4):
        n.append({"c": CLAVE, "g": "Calculo Integral", "t": "Apunte %d.pdf" % i,
                  "u": "https://plataforma/curso/1/apunte%d.pdf" % i,
                  "f": cuando(i + 1), "tipo": "archivo"})
    n.append({"c": CLAVE, "g": "Calculo Integral", "t": "Programa del ramo.pdf",
              "u": "https://plataforma/curso/1/programa.pdf",
              "f": cuando(200), "tipo": "archivo"})
    n.append({"c": CLAVE, "g": "Calculo Integral", "t": "Aviso del profesor",
              "u": "https://plataforma/curso/1/foro/9",
              "f": cuando(2), "tipo": "foro"})
    return n


def bot_de_prueba():
    b = W.Vigilante.__new__(W.Vigilante)
    b.estado = {
        "grupos": {CLAVE: {"nombre": "Calculo Integral", "emoji": "\U0001F4D8",
                           "fuente": "A", "id": "1", "url": "", "visto": "",
                           "cantidad": 10}},
        "novedades": novedades_de_prueba(),
        "tareas": {}, "items": {}, "avisos": {}, "fallas": {},
        "config": {"ia": True},
    }
    b.sesiones = {}
    b.bases = {}
    b.cache = {}
    b.modo = "gist"
    b.guardar = lambda: None
    return b


# ============================================================ punto 1
titulo("punto 1: los archivos de la plataforma")
bot = bot_de_prueba()

contador = bot.cuantos_archivos(CLAVE)
elegidos, total, rango = bot.filtrar_archivos(CLAVE, "todo", frescos=False)
ok(contador == 9, "el contador ve los 9 archivos, tambien los sin extension")
ok(contador == len(elegidos),
   "el contador y el boton cuentan lo mismo (%d y %d)" % (contador, len(elegidos)))

semana, _, rango_semana = bot.filtrar_archivos(CLAVE, "semana", frescos=False)
mes, _, _ = bot.filtrar_archivos(CLAVE, "mes", frescos=False)
ok(len(semana) == 8, "la ultima semana trae 8")
ok(len(mes) == 8, "el ultimo mes trae 8")
ok(len(elegidos) > len(mes), "todo el ramo trae mas que el ultimo mes")
ok("desde" in rango_semana, "el rango se dice en criollo: %s" % rango_semana)

por_nombre, _, _ = bot.filtrar_archivos(CLAVE, "todo", nombre="programa",
                                        frescos=False)
ok(len(por_nombre) == 1 and "Programa" in por_nombre[0]["titulo"],
   "buscar por nombre encuentra el programa del ramo")

solo_pdf, _, _ = bot.filtrar_archivos(CLAVE, "todo", tipo="pdf", frescos=False)
ok(len(solo_pdf) == 5, "filtrar por tipo pdf deja 5")

limpiar()
bot.pedir_archivos(CLAVE, "todo", nombre="termodinamica")
ok(len(MANDADOS) == 1, "cuando no hay nada igual contesta una vez")
ok("no encontr" in ultimo(), "dice que no encontro, no se queda callado")
ok("todo el ramo" in ultimo(), "y dice en que rango busco")

limpiar()
bot.pedir_archivos(CLAVE, "semana")
ok(len(MANDADOS) == 1, "pedir la semana contesta una sola vez")
ok("Encontr" in ultimo() and "8" in ultimo(),
   "con 8 archivos primero muestra el conteo")
# El boton de confirmar ahora lleva pegada la marca del pedido, para que el
# "Dale" de una pregunta vieja no ejecute el pedido nuevo.  Por eso se mira
# el comienzo del dato y no el dato completo: lo que importa es que el boton
# de aceptar este ahi.
ok(any(d.startswith("prop:si") for d in datos_de_botones(MANDADOS[-1]["botones"])),
   "y espera que toques Mandalos")
ok(bot.estado.get("propuesta", {}).get("plan", {}).get("accion") == "mandar_archivos",
   "la propuesta queda guardada para cuando confirmes")
ok("no la IA" in ultimo(), "avisa que los numeros los conto el programa")

limpiar()
bot.accion("baj:%s:todo" % CLAVE)
ok(len(MANDADOS) == 1, "el boton baj: con clave que tiene dos puntos anda igual")

limpiar()
bot.pedir_archivos(CLAVE, "todo", nombre="programa")
ok("Encontr" not in ultimo(),
   "con un solo archivo no molesta con la confirmacion")


# ============================================================ punto 2
titulo("punto 2: las ordenes habladas")
bot = bot_de_prueba()
bot.estado["config"]["ia"] = False      # la IA apagada, tiene que andar igual
limpiar()
bot.proponer("recordame en 2 min que six seven viene a la casa")
ok(len(MANDADOS) == 1, "una orden, un solo mensaje (llegaron %d)" % len(MANDADOS))
ok(any(d.startswith("prop:si") for d in datos_de_botones(MANDADOS[-1]["botones"])),
   "la confirmacion viene con botones")
ok(not IA._parece_ingles(ultimo()), "la confirmacion no tiene ingles")
ok(not ultimo().strip().startswith("<i>"),
   "no te devuelve tu propio mensaje en cursiva")
ok("six seven" in ultimo(), "te dice que va a guardar, con tus palabras")

limpiar()
cierre = bot.confirmar_propuesta(True)
ok(bool(cierre and cierre.strip()), "despues de aceptar llega el cierre")
ok(not IA._parece_ingles(cierre or ""), "el cierre tampoco viene en ingles")
ok(any(t.get("mio") for t in bot.estado["tareas"].values()),
   "y el recordatorio queda guardado")
ok(any(":" in (t.get("vence") or "") for t in bot.estado["tareas"].values()),
   "con la hora exacta anotada")

limpiar()
bot.proponer("que onda la vida")
ok(len(MANDADOS) == 1, "si no es orden y la IA esta apagada, igual contesta")
ok("IA" in ultimo() or "ia" in ultimo(),
   "y avisa que la IA esta apagada con esas palabras")

ok(IA._parece_ingles("2026-08-03 20:01 in 2 minutes with the reminder"),
   "el filtro reconoce una respuesta en ingles")
ok(not IA._parece_ingles("Te lo recuerdo hoy a las 20:01"),
   "y no se come una respuesta en castellano")
ok(IA._parece_json('{"accion":"recordar"}'), "el filtro reconoce un JSON crudo")


# ============================================================ punto 3
titulo("punto 3: varias claves con relevo")
for v in list(CFG.IA["claves_env"]):
    os.environ.pop(v, None)
os.environ["IA_KEY"] = "clave-una"
os.environ["IA_KEY_2"] = "clave-dos"
os.environ["IA_KEY_3"] = "clave-tres"

USADAS = []
COMO_ESTA = {"clave-una": "cupo", "clave-dos": "mala", "clave-tres": "bien"}


def motor_falso(texto, pdfs, c=None):
    USADAS.append(c["clave"])
    como = COMO_ESTA.get(c["clave"], "bien")
    if como == "cupo":
        raise IA.SinCupo("sin cupo")
    if como == "mala":
        raise IA.ClaveMala("no sirve")
    if como == "caida":
        raise IA.SeCayo("se cayo")
    return "contesto " + c["clave"]


IA.PROVEEDORES["gemini"] = motor_falso
IA.PROVEEDORES["compatible"] = motor_falso

ok(len(IA.claves()) == 3, "lee las tres claves en orden")

estado = {}
del USADAS[:]
salida = IA._pedir(estado, "hola")
ok(salida == "contesto clave-tres", "salta sola hasta la que anda")
ok(USADAS == ["clave-una", "clave-dos", "clave-tres"], "probo en orden")
ok(estado["ia_clave_en_uso"] == "clave 3 de 3", "anota cual esta usando")

del USADAS[:]
IA._pedir(estado, "hola de nuevo")
ok(USADAS == ["clave-tres"], "las que estan en penitencia ni se prueban")

como_van = IA.como_van_las_claves(estado)
ok("clave-una" not in como_van and "clave-dos" not in como_van,
   "el estado no muestra ninguna clave de verdad")
ok("sin cupo" in como_van and "mala" in como_van,
   "pero si dice por que estan en penitencia")

# se le termina el descanso a la primera y vuelve sola
estado["ia_claves"]["IA_KEY"]["hasta"] = 0
COMO_ESTA["clave-una"] = "bien"
del USADAS[:]
salida = IA._pedir(estado, "otra vez")
ok(salida == "contesto clave-una", "siempre vuelve a la primera cuando se recupera")
ok(USADAS == ["clave-una"], "y no molesta a las otras")

# la clave mala no se reintenta nunca sola
ok("mala" in IA._descansando(estado, IA.claves()[1]),
   "la clave invalida queda marcada y no se reintenta")

# sin ninguna clave sana no hay IA, y se avisa
COMO_ESTA["clave-una"] = "cupo"
COMO_ESTA["clave-tres"] = "cupo"
estado["ia_claves"] = {}
estado["config"] = {"ia": True}
try:
    IA._pedir(estado, "y ahora")
    quedo = False
except Exception:
    quedo = True
ok(quedo, "cuando no queda ninguna, avisa con un error claro")
ok(estado.get("ia_sin_claves") is True, "y lo deja anotado")
ok(IA.disponible(estado) is False, "con todas descansando la IA no esta disponible")

os.environ.pop("IA_KEY", None)
os.environ.pop("IA_KEY_2", None)
os.environ.pop("IA_KEY_3", None)
ok(IA.disponible({}) is False, "sin ninguna clave cargada tampoco")
ok(IA.como_van_las_claves({}) == "ninguna cargada", "y lo dice en criollo")


# ============================================================ punto 4
titulo("punto 4: la animacion")
ok(CFG.ANIM_SEGUNDOS >= 9.0, "la animacion es mas lenta que antes")
ok(CFG.ANIM_CADA_FRASE >= 5, "las frases cambian mas lento que los puntos")
ok("ANIM_SEGUNDOS" in open("watcher.py", encoding="utf-8").read(),
   "el bot usa el numero de la configuracion, no uno propio")


# ============================================================ punto 5
titulo("punto 5: las pantallas")
bot = bot_de_prueba()
acc = bot._acciones()

texto, botones = P.pantalla(bot.estado, "p:r:" + CLAVE, acc)
filas = filas_de(botones)
ok(len(filas) <= 6, "la pantalla del ramo tiene %d filas" % len(filas))
ok(all(len(f) <= 3 for f in filas), "ninguna fila pasa de tres botones")
ok(filas[-1][0]["callback_data"].startswith("p:"), "Volver va en la ultima fila")
datos = datos_de_botones(botones)
for alcance in ("semana", "mes", "todo"):
    ok("a:baj:%s:%s" % (CLAVE, alcance) in datos, "esta el boton de %s" % alcance)
ok("p:busc:" + CLAVE in datos, "esta el boton de buscar por nombre")

texto, botones = P.pantalla(bot.estado, "p:busc:" + CLAVE, acc)
ok(bot.estado.get("esperando_busqueda") == CLAVE,
   "al entrar al buscador queda esperando lo que escribas")

texto, botones = P.pantalla(bot.estado, "p:ajustes", acc)
filas = filas_de(botones)
ok(len(filas) <= 6, "Ajustes tiene %d filas" % len(filas))
ok(all(len(f) <= 3 for f in filas), "Ajustes no pasa de tres por fila")

texto, botones = P.pantalla(bot.estado, "p:avisos", acc)
ok(len(filas_de(botones)) <= 6, "Avisos tambien entra en la pantalla")

texto, botones = P.pantalla(bot.estado, "p:ramos", acc)
ok(all(len(f) <= 3 for f in filas_de(botones)), "los ramos van de a dos por fila")


# ============================================================ version
titulo("version")
ok(bool(VER.VERSION) and "." in VER.VERSION,
   "la version esta puesta y dice %s" % VER.VERSION)
ok(len(VER.CAMBIOS) > 5 and len(VER.A_PROBAR) > 3, "los cambios estan escritos")
texto = bot.texto_version()
ok(VER.VERSION in texto, "la pantalla de version usa VER.VERSION")


# ============================================================ cierre
print("\n" + "-" * 50)
if FALLOS:
    print("fallaron %d cosas:" % len(FALLOS))
    for f in FALLOS:
        print("  - " + f)
    sys.exit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)