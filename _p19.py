# -*- coding: utf-8 -*-
"""Tanda 19: la auditoria de la v5.7.

Cada prueba de aca corresponde a una falla REAL que encontre revisando el bot
completo. La idea no es que pasen hoy: es que si alguien manana vuelve a
romper una de estas cosas, salte al toque y no se entere el usuario primero.

Se corre sola, sin internet y sin tocar tu cuenta:
    python3 _p19.py
"""
import os

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("CLAVE_COMPARTIR", "llave-de-prueba-nada-real")

import datetime as dt

import almacen as A
import avisos as AV
import comandos as C
import fuentes as CFG
import notificar as N
import panel as P
import version as VER
import watcher as W

# ------------------------------------------------------------------ ojo
# Estas dos son justo LO QUE SE ESTA PROBANDO, asi que las guardo de verdad
# ANTES de reemplazar las funciones de la mensajeria por falsas.
CORTAR_DE_VERDAD = N.cortar
TECLADO_DE_VERDAD = N.teclado

FALLOS = []


def ok(cond, que):
    if cond:
        print("  ok   %s" % que)
    else:
        print("  MAL  %s" % que)
        FALLOS.append(que)


def titulo(t):
    print("\n" + t)
    print("-" * 50)


# ------------------------------------------------- mensajeria de mentira
MANDADOS = []
BORRADOS = []


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append({"texto": texto, "silencioso": silencioso,
                     "botones": botones})
    return len(MANDADOS)


def _editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    MANDADOS.append({"texto": texto, "botones": botones, "edito": mensaje_id})
    return mensaje_id


def _borrar(mid):
    BORRADOS.append(mid)
    return True


def _nada(*a, **k):
    return None


N.enviar = _enviar
N.editar = _editar
N.borrar = _borrar
N.anclar = _nada
N.desanclar = _nada
N.avisar_boton = _nada
N.mandar_documento = _nada
N.mandar_archivo = _nada
N.publicar_menu = _nada
N.quitar_teclado = _nada


def limpiar():
    del MANDADOS[:]
    del BORRADOS[:]


def ultimo():
    return MANDADOS[-1]["texto"] if MANDADOS else ""


def todo_lo_mandado():
    return "\n".join(m["texto"] or "" for m in MANDADOS)


def filas_de(b):
    return (b or {}).get("inline_keyboard", [])


def datos_de_botones(b):
    return [d.get("callback_data", "")
            for fila in filas_de(b) for d in fila]


def fuente(nombre):
    """Lee un archivo del proyecto como texto, para las pruebas de codigo."""
    with open(nombre, "r", encoding="utf-8") as f:
        return f.read()


HOY = W.ahora()
CLAVE = "A:1"
OTRA = "A:2"


def bot_de_prueba():
    b = W.Vigilante.__new__(W.Vigilante)
    b.estado = {
        "items": {}, "grupos": {
            CLAVE: {"nombre": "C\u00c1LCULO INTEGRAL", "emoji": "\U0001F4D8",
                    "fuente": "A", "id": "1", "url": "http://x/curso/1",
                    "visto": "", "cantidad": 0},
            OTRA: {"nombre": "F\u00cdSICA", "emoji": "\U0001F4D8",
                   "fuente": "A", "id": "2", "url": "http://x/curso/2",
                   "visto": "", "cantidad": 0},
        },
        "archivados": {}, "ausentes": {}, "avisos": {}, "tareas": {},
        "perfiles": {}, "callados": {}, "novedades": [], "pendientes_ia": [],
        "config": {}, "fallas": {}, "tg_offset": 0, "avisos_vistos": {},
        "deshacer": None, "personas": {}, "clases_avisadas": {},
        "version_avisada": VER.VERSION, "version_desde": "",
        "aviso_clave": {}, "basura": [], "de_afuera": [],
    }
    b.sesiones = {}
    b.bases = {}
    b.cache = {}
    b.modo = "gist"
    b.gist_nuevo = False
    b.guardar = lambda *a, **k: None
    return b


def acc_de_prueba(b):
    acc = dict(b._acciones())
    acc["dibujar_panel"] = lambda *a, **k: None
    acc["abrir_panel"] = lambda *a, **k: None
    acc["redibujar_tarjeta"] = lambda *a, **k: None
    return acc


# ===================================================================== 1
titulo("1. cortar un mensaje largo sin romperlo")

largo = "<b>" + ("a" * 5000) + "</b>"
c = CORTAR_DE_VERDAD(largo, largo=4000)
ok(len(c) <= 4000 + 20, "respeta el tope")
ok(c.endswith("</b>"), "cierra la negrita que qued\u00f3 abierta")
ok(c.count("<") == c.count(">"), "no deja un < suelto")

# el corte cae justo dentro de una etiqueta
feo = ("x" * 3995) + '<a href="http://largo/muy/largo">hola</a>'
c2 = CORTAR_DE_VERDAD(feo, largo=4000)
ok("<a href=\"http" not in c2 or c2.endswith("</a>"),
   "no corta por la mitad de una etiqueta")

# el corte cae dentro de un &amp;
feo2 = ("y" * 3997) + "&amp;" + ("z" * 100)
c3 = CORTAR_DE_VERDAD(feo2, largo=4000)
ok("&am" not in c3[-4:], "no corta por la mitad de un &s\u00edmbolo;")

corto = "hola <b>che</b>"
ok(CORTAR_DE_VERDAD(corto) == corto, "un texto corto no se toca")
ok(N.sin_etiquetas("<b>ho</b>la") == "hola", "sin_etiquetas pela el formato")

# ===================================================================== 2
titulo("2. un bot\u00f3n nunca puede apuntar a otra cosa")

limpiar()
largo_dato = "p:r:" + ("Q" * 90)
t = TECLADO_DE_VERDAD([[("malo", largo_dato), ("bueno", "p:raiz")]])
datos = datos_de_botones(t)
ok(largo_dato not in datos, "el bot\u00f3n que no cabe NO se pone")
ok("p:raiz" in datos, "el bot\u00f3n que s\u00ed cabe se queda")
ok(all(len(d.encode("utf-8")) <= 64 for d in datos),
   "ninguno pasa de 64 bytes")
ok(largo_dato[:64] not in datos, "y no lo recorta, que era lo peligroso")
vacio = TECLADO_DE_VERDAD([[("malo", largo_dato)]])
ok(vacio is None, "si no queda ning\u00fan bot\u00f3n, no manda teclado vac\u00edo")

# ===================================================================== 3
titulo("3. dos niveles de aviso: qu\u00e9 te despierta y qu\u00e9 no")

ok(AV.urgente("se suspende la clase de manana"), "suspensi\u00f3n = urgente")
ok(AV.urgente("clases online el dia 3 y 4"), "clase online = urgente")
ok(AV.urgente("se posterga el certamen"), "postergaci\u00f3n = urgente")
ok(AV.urgente("cambio de sala para el jueves"), "cambio de sala = urgente")

ok(not AV.urgente("hay prueba el lunes"), "'prueba' sola NO te despierta")
ok(not AV.urgente("recuerden la entrega del informe"),
   "'entrega' sola NO te despierta")
ok(not AV.urgente("la asistencia es obligatoria"),
   "'asistencia' sola NO te despierta")

ok(AV.importante("hay prueba el lunes"), "pero 'prueba' s\u00ed es importante")
ok(AV.importante("recuerden la entrega"), "y 'entrega' tambi\u00e9n")
ok(not AV.importante("se suspende la clase"),
   "lo urgente no cuenta dos veces")

ok(AV.prioridad({"urgente": True}) == "urgente", "prioridad urgente")
ok(AV.prioridad({"importante": True}) == "importante", "prioridad importante")
ok(AV.prioridad({}) == "comun", "prioridad com\u00fan")

# ===================================================================== 4
titulo("4. la pantalla 'Cu\u00e1ndo te hablo' volvi\u00f3 a tener puerta")

b = bot_de_prueba()
acc = acc_de_prueba(b)

_txt, bo = P.pantalla(b.estado, "p:ajustes", acc)
ok("p:avisos" in datos_de_botones(bo), "desde Ajustes se llega a p:avisos")

_txt, bo = P.pantalla(b.estado, "p:avisos", acc)
d = datos_de_botones(bo)
ok("p:dia" in d, "y desde ahi al d\u00eda del resumen")
ok("p:hora" in d, "y a la hora del resumen")

# nadie puede quedar sin puerta de entrada
PUERTAS = ["p:avisos", "p:dia", "p:hora", "p:pen", "p:prof"]
todas = set()
for donde in ("p:raiz", "p:ajustes", "p:mas", "p:avisos", "p:pen", "p:rec"):
    _t, _b = P.pantalla(b.estado, donde, acc)
    todas.update(datos_de_botones(_b))
for p in PUERTAS:
    ok(p in todas, "alguien lleva a %s" % p)

# ===================================================================== 5
titulo("5. el bot\u00f3n Deshacer se vence")

import time as _t

b = bot_de_prueba()
P._guardar_deshacer(b.estado, "listo", "x1", {"titulo": "algo"}, "marqu\u00e9")
ok(bool(P._fila_deshacer(b.estado)), "recien hecho, el bot\u00f3n est\u00e1")

minutos = getattr(CFG, "MINUTOS_PARA_DESHACER", 30)
b.estado["deshacer"]["cuando"] = _t.time() - (minutos * 60 + 120)
ok(not P._fila_deshacer(b.estado), "pasado el rato, el bot\u00f3n desaparece")

r, _donde = P._deshacer(b.estado)
ok("hace rato" in r, "y si insist\u00eds te dice que ya pas\u00f3")
ok(b.estado.get("deshacer") is None, "y limpia el estado")

# ===================================================================== 6
titulo("6. posponer una entrega del profe NO la duplica")

b = bot_de_prueba()
acc = acc_de_prueba(b)
vence = (HOY + dt.timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
idt = W.huella("tarea", CLAVE, "http://x/tarea/9")
b.estado["tareas"][idt] = {
    "grupo": "C\u00c1LCULO INTEGRAL", "clave": CLAVE, "titulo": "Informe 2",
    "url": "http://x/tarea/9", "vence": vence, "hecho": False, "nota": "",
    "es_tarea": True}

limpiar()
aviso, _donde = P.toque(b.estado, "qm:" + idt, acc, HOY)
tareas = b.estado["tareas"]
ok(idt in tareas, "la entrega conserva su identidad")
ok(not any(k.startswith("mio_") for k in tareas),
   "no se le invent\u00f3 un id de recordatorio propio")
ok(tareas[idt]["vence"] == vence, "la fecha del profe NO se toc\u00f3")
ok(bool(tareas[idt].get("dormida_hasta")), "solo se durmi\u00f3 el recordatorio")
ok(len(tareas) == 1, "sigue habiendo UNA sola entrega")
ok("no la toqu" in aviso, "y te lo dice con todas las letras")

# un recordatorio TUYO s\u00ed se mueve de hora
mio = "mio_%d" % int(HOY.timestamp())
b.estado["tareas"] = {mio: {
    "grupo": "", "clave": "", "titulo": "llamar", "url": "",
    "vence": HOY.strftime("%Y-%m-%d %H:%M"), "hecho": False, "nota": "",
    "mio": True, "es_tarea": False}}
P.toque(b.estado, "rm:" + mio, acc, HOY)
ok(not any(t.get("vence") == HOY.strftime("%Y-%m-%d %H:%M")
           for t in b.estado["tareas"].values()),
   "pero un recordatorio tuyo s\u00ed cambia de hora")

# ===================================================================== 7
titulo("7. los recordatorios hablados no se pisan ni se disfrazan")

b = bot_de_prueba()
cuando = (HOY + dt.timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M")
b.ejecutar_plan({"accion": "recordar", "cuando": cuando, "que": "levantarme"})
b.ejecutar_plan({"accion": "recordar", "cuando": cuando, "que": "otra cosa"})
mios = [t for t in b.estado["tareas"].values() if t.get("mio")]
ok(len(b.estado["tareas"]) == 2, "dos pedidos del mismo minuto = dos apuntes")
ok(all(t.get("mio") for t in mios), "los dos quedan marcados como tuyos")
ok(all(t.get("es_tarea") is False for t in mios),
   "y NINGUNO es una entrega de un ramo")

texto = b.texto_pendientes()
ok("SIN REVISAR" in texto.upper(), "aparecen en SIN REVISAR")
ok("PARA ENTREGAR" not in texto.upper(),
   "y no se cuelan en PARA ENTREGAR")

# ===================================================================== 8
titulo("8. el diagn\u00f3stico no muestra c\u00f3digo crudo")

b = bot_de_prueba()
b.estado["fallas"][CLAVE] = {"veces": 3, "desde": "2026-08-01 10:00",
                            "motivo": "no pude entrar"}
texto = b.texto_diagnostico()
ok("{" not in texto, "no aparece una llave de diccionario")
ok("'veces'" not in texto, "no aparece el nombre interno del campo")
ok("C\u00c1LCULO INTEGRAL" in texto, "dice el nombre del ramo")
ok("no pude entrar" in texto, "y dice qu\u00e9 pas\u00f3")

# ===================================================================== 9
titulo("9. /avisos en orden de fecha y la admiraci\u00f3n donde va")

b = bot_de_prueba()
b.estado["tareas"] = {
    "aviso_zzzz": {"grupo": "C\u00c1LCULO INTEGRAL", "clave": CLAVE,
                   "titulo": "viejo", "texto": "buenas tardes, saludos",
                   "aviso": True, "hecho": False, "es_tarea": False,
                   "nacio": "2026-08-01 09:00"},
    "aviso_aaaa": {"grupo": "F\u00cdSICA", "clave": OTRA,
                   "titulo": "nuevo", "texto": "se suspende la clase",
                   "aviso": True, "hecho": False, "es_tarea": False,
                   "nacio": "2026-08-04 18:00"},
}
texto = b.texto_avisos()
ok(texto.index("F\u00cdSICA") < texto.index("C\u00c1LCULO"),
   "el m\u00e1s nuevo va arriba, aunque el id diga otra cosa")
lineas = [l for l in texto.split("\n") if "F\u00cdSICA" in l]
ok(any("\u2757" in l for l in lineas), "el urgente lleva admiraci\u00f3n")
lineas = [l for l in texto.split("\n") if "C\u00c1LCULO" in l]
ok(not any("\u2757" in l for l in lineas),
   "y el saludo com\u00fan NO la lleva")

# ==================================================================== 10
titulo("10. los avisos del profe se archivan solos")

b = bot_de_prueba()
dias = getattr(CFG, "DIAS_PARA_ARCHIVAR_AVISOS", 21)
viejo = (HOY - dt.timedelta(days=dias + 2)).strftime("%Y-%m-%d %H:%M")
b.estado["tareas"] = {
    "aviso_1": {"grupo": "C", "clave": CLAVE, "titulo": "viejo",
                "aviso": True, "hecho": False, "es_tarea": False,
                "nacio": viejo},
    "aviso_2": {"grupo": "C", "clave": CLAVE, "titulo": "sin fecha",
                "aviso": True, "hecho": False, "es_tarea": False},
}
limpiar()
b.olvidar_recordatorios_viejos()
ok(b.estado["tareas"]["aviso_1"]["hecho"] is True,
   "un aviso de hace %d d\u00edas se archiva" % (dias + 2))
ok(not MANDADOS, "y se archiva callado, sin molestarte")
ok(b.estado["tareas"]["aviso_2"].get("hecho") is False,
   "uno sin fecha no se archiva de una")
ok(bool(b.estado["tareas"]["aviso_2"].get("nacio")),
   "le pone fecha para contar desde hoy")

# ==================================================================== 11
titulo("11. la campanita avisa y se puede deshacer")

b = bot_de_prueba()
acc = acc_de_prueba(b)
limpiar()
_r, _c = C._boton_de_tarjeta(b.estado, "basta:" + CLAVE, acc, HOY)
ok(CLAVE in b.estado["callados"], "silencia el ramo")
d = b.estado.get("deshacer") or {}
ok(d.get("que") == "callar", "deja un deshacer del tipo correcto")
mensaje = todo_lo_mandado()
ok("deshacer" in mensaje.lower(), "te dice que se puede deshacer")
ok("/" in mensaje, "y te dice hasta qu\u00e9 fecha")

r, _donde = P._deshacer(b.estado)
ok(CLAVE not in b.estado["callados"], "al deshacer, el ramo vuelve a hablar")
ok("aviso" in r.lower() or "vuelve" in r.lower(), "y te lo confirma")
ok(not any(k == CLAVE for k in b.estado["tareas"]),
   "y NO qued\u00f3 un pendiente fantasma con la clave del ramo")

# marcar hecho tambien se deshace
b = bot_de_prueba()
acc = acc_de_prueba(b)
b.estado["tareas"]["t1"] = {"grupo": "C", "clave": CLAVE, "titulo": "algo",
                            "hecho": False, "es_tarea": True, "vence": ""}
C._boton_de_tarjeta(b.estado, "hecho:t1", acc, HOY)
ok(b.estado["tareas"]["t1"]["hecho"] is True, "marca como hecho")
ok((b.estado.get("deshacer") or {}).get("que") == "listo",
   "y deja el deshacer puesto")
P._deshacer(b.estado)
ok(b.estado["tareas"]["t1"]["hecho"] is False, "y se puede volver atr\u00e1s")

# ==================================================================== 12
titulo("12. se le puede hablar normal al bot (revisi\u00f3n del c\u00f3digo)")

# Saco los comentarios antes de mirar: los comentarios EXPLICAN cómo era
# antes, asi que contienen el texto viejo a proposito y daban falsa alarma.
src_crudo = fuente("comandos.py")
src = "\n".join(l for l in src_crudo.split("\n")
                if not l.strip().startswith("#"))
ok('"pendientes" in plano' not in src,
   "ya no alcanza con que la palabra aparezca en la frase")
ok('"novedades" in plano' not in src, "idem novedades")
ok('"panel" in plano' not in src, "idem panel")
ok('plano in ("pendientes"' in src, "ahora pide el texto exacto del bot\u00f3n")

# ==================================================================== 13
titulo("13. /deshacer redibuja el panel (revisi\u00f3n del c\u00f3digo)")

ok("P._deshacer(estado)[0]" not in src, "ya no tira la pantalla que devuelve")
ok("r, donde = P._deshacer(estado)" in src, "ahora la usa para redibujar")

# ==================================================================== 14
titulo("14. guardar no se lleva la corrida puesta")

real = A._escribir_local


def _revienta(*a, **k):
    raise IOError("disco lleno de prueba")


try:
    A._escribir_local = _revienta
    r = A.guardar({"version": A.VERSION, "items": {}}, "repo")
    ok(r == "nada", "si el disco falla, avisa y sigue viva")
finally:
    A._escribir_local = real

chico = A.reducir({"version": 2, "version_desde": "2026-08-04 19:00",
                   "version_avisada": "5.7", "items": {}})
ok(chico.get("version_desde") == "2026-08-04 19:00",
   "la memoria chica se acuerda DESDE CU\u00c1NDO es esta versi\u00f3n")
ok(chico.get("version_avisada") == "5.7", "y cu\u00e1l avis\u00f3")

# ==================================================================== 15
titulo("15. los mensajes viejos se borran de verdad")

b = bot_de_prueba()
futuro = _t.time() + 9999
b.estado["basura"] = [[1000 + i, futuro] for i in range(80)]
limpiar()
C.sacar_basura(b.estado)
ok(len(b.estado["basura"]) == 60, "la cola queda en 60")
ok(len(BORRADOS) == 20, "y los 20 que sobraban se borraron del chat")

# ==================================================================== 16
titulo("16. no se rompi\u00f3 nada de lo viejo")

# OJO: una pantalla rota NO se detecta contando filas de botones. Muchas
# pantallas de solo lectura tienen una sola fila con Volver y estan perfectas.
# La senal de verdad es el texto del error que devuelve panel.pantalla.
b = bot_de_prueba()
acc = acc_de_prueba(b)
PANTALLAS = ["p:raiz", "p:ramos", "p:rec", "p:pen", "p:ajustes", "p:mas",
             "p:avisos", "p:dia", "p:hora", "p:nov", "p:sem", "p:ayuda",
             "p:perfiles", "p:version", "p:prof", "p:diag", "p:comp",
             "p:afuera", "p:clases"]
for donde in PANTALLAS:
    texto, bo = P.pantalla(b.estado, donde, acc)
    roto = "se rompi" in texto
    ok(not roto and bool(texto) and bool(filas_de(bo)),
       "la pantalla %s se dibuja" % donde)

for nombre, fn in (("novedades", b.texto_novedades),
                   ("pendientes", b.texto_pendientes),
                   ("semana", b.texto_semana),
                   ("avisos", b.texto_avisos),
                   ("version", b.texto_version)):
    ok(bool(fn()), "texto_%s contesta algo" % nombre)

ok(len(C.MENU) >= 22, "el men\u00fa de comandos sigue completo")
ok(bool(VER.VERSION) and "." in VER.VERSION, "hay una versi\u00f3n puesta")
ok(VER.VERSION in b.texto_version(), "y el bot la informa")

# un aviso urgente de punta a punta
b = bot_de_prueba()
ficha = b.estado["grupos"][CLAVE]
ficha["avisos_leidos"] = True
limpiar()
mando = b.avisos_nuevos(CLAVE, ficha, [{
    "titulo": "Clases online", "texto": "la universidad decidio clases online "
                                       "los dias 3 y 4 de agosto",
    "huella": "abc123", "urgente": True, "importante": False}])
ok(mando, "un aviso urgente nuevo se manda")
ok("online" in todo_lo_mandado(), "y dice de qu\u00e9 se trata")
tarea = b.estado["tareas"].get("aviso_abc123") or {}
ok(bool(tarea.get("nacio")), "queda anotado con fecha de nacimiento")
ok(tarea.get("es_tarea") is False, "y no como entrega")

# ===================================================================== fin
print("\n" + "=" * 50)
if FALLOS:
    print("%d cosas fallaron:" % len(FALLOS))
    for f in FALLOS:
        print(" - %s" % f)
    raise SystemExit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
