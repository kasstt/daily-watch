# -*- coding: utf-8 -*-
"""Tanda 20: la segunda auditoria, hecha desde cero y sin creerle a nadie.

Cada prueba de aca corresponde a una falla que estaba VIVA en la 5.7, aunque
el informe anterior diera el tema por cerrado. Todas fallan con el codigo de
la 5.7 y pasan con el de la 5.8.

Se corre sola, sin internet, sin claves de verdad y sin tocar tu cuenta:
    python3 _p20.py
"""
import os
import shutil
import tempfile

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("CLAVE_COMPARTIR", "llave-de-prueba-nada-real")

import datetime as dt

import almacen as A
import avisos as AV
import clases as CL
import comandos as C
import compartir as CO
import fuentes as CFG
import notificar as N
import panel as P
import salud as SA
import version as VER
import watcher as W

# Se guardan de verdad ANTES de reemplazar la mensajeria por falsa, porque
# justo estas dos son parte de lo que se esta probando.
CORTAR_AVISANDO_DE_VERDAD = N.cortar_avisando
ENLACE_DE_VERDAD = N.enlace

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
AVISOS_DE_BOTON = []
PANELES = []
REDIBUJADAS = []
ENVIO_FALLA = {"si": False}


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append({"texto": texto, "silencioso": silencioso,
                     "botones": botones})
    if ENVIO_FALLA["si"]:
        return None            # la mensajeria contesto que no, como en la vida real
    return len(MANDADOS)


def _editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    MANDADOS.append({"texto": texto, "botones": botones, "edito": mensaje_id})
    return mensaje_id


def _borrar(mid):
    BORRADOS.append(mid)
    return True


def _avisar_boton(consulta_id, texto=""):
    AVISOS_DE_BOTON.append(texto or "")
    return True


def _nada(*a, **k):
    return None


N.enviar = _enviar
N.editar = _editar
N.borrar = _borrar
N.anclar = _nada
N.desanclar = _nada
N.avisar_boton = _avisar_boton
N.mandar_documento = _nada
N.mandar_archivo = _nada
N.publicar_menu = _nada
N.quitar_teclado = _nada


def limpiar():
    del MANDADOS[:]
    del BORRADOS[:]
    del AVISOS_DE_BOTON[:]
    del PANELES[:]
    del REDIBUJADAS[:]
    ENVIO_FALLA["si"] = False


def ultimo():
    return MANDADOS[-1]["texto"] if MANDADOS else ""


def todo_lo_mandado():
    return "\n".join(m["texto"] or "" for m in MANDADOS)


def sin_comentarios(nombre):
    """El codigo sin comentarios. Los comentarios cuentan como era ANTES, asi
    que buscar texto con ellos adentro da falsas alarmas."""
    salida = []
    with open(nombre, "r", encoding="utf-8") as f:
        for linea in f:
            cortada = linea.split("#", 1)[0]
            salida.append(cortada)
    return "\n".join(salida)


HOY = W.ahora()
CLAVE = "A:1"
OTRA = "A:2"


def bot_de_prueba(nombre_ramo="C\u00c1LCULO INTEGRAL"):
    b = W.Vigilante.__new__(W.Vigilante)
    b.estado = {
        "items": {}, "grupos": {
            CLAVE: {"nombre": nombre_ramo, "emoji": "\U0001F4D8",
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
    acc["dibujar_panel"] = lambda donde=None, mid=None: PANELES.append(donde)
    acc["abrir_panel"] = lambda *a, **k: None
    acc["redibujar_tarjeta"] = lambda idt=None, mid=None: REDIBUJADAS.append(idt)
    return acc


def tarea_mia(b, idt="mio_1", horas=-1.0, titulo_t="estudiar"):
    """Un recordatorio tuyo que ya paso, asi el aviso corresponde ahora."""
    f = HOY + dt.timedelta(hours=horas)
    b.estado["tareas"][idt] = {
        "titulo": titulo_t, "vence": f.strftime("%Y-%m-%d %H:%M"),
        "mio": True, "clave": CLAVE, "hecho": False,
        "grupo": b.estado["grupos"][CLAVE]["nombre"],
        "nacio": HOY.strftime("%Y-%m-%d %H:%M"),
    }
    return idt


# ===================================================================== 1
titulo("1. el recordatorio de una entrega tiene que llegar de verdad")

b = bot_de_prueba()
idt = tarea_mia(b)
limpiar()
revento = ""
try:
    b.avisos_de_plazo()
except Exception as e:
    revento = type(e).__name__
ok(not revento, "revisar los plazos no se cae (se cayo con %s)" % (revento or "nada"))
ok(len(MANDADOS) == 1, "llega el aviso del recordatorio")
ok("0" in b.estado["avisos"].get(idt, []),
   "y queda anotado para no repetirlo")

# la vuelta completa tiene que pasar por TODOS los pasos, no cortarse en el
# primero que falle
b2 = bot_de_prueba()
b2.revisar_todo = lambda *a, **k: None
b2.procesar_agenda = lambda *a, **k: None
pasos = []
for paso in ("podar_memoria", "olvidar_recordatorios_viejos", "recordar_sin_ver",
             "resumen_periodico", "latido", "revisar_reloj"):
    setattr(b2, paso, (lambda p: (lambda *a, **k: pasos.append(p)))(paso))
tarea_mia(b2)
limpiar()
b2.una_vuelta()
ok(len(pasos) == 6, "la vuelta llega hasta el final (%d de 6 pasos)" % len(pasos))


# ===================================================================== 2
titulo("2. si el mensaje no sale, no se marca como avisado")

b = bot_de_prueba()
idt = tarea_mia(b)
limpiar()
ENVIO_FALLA["si"] = True
b.avisos_de_plazo()
ok(len(MANDADOS) == 1, "lo intento")
ok("0" not in b.estado["avisos"].get(idt, []),
   "no lo anota como avisado, asi lo reintenta en la vuelta siguiente")

ENVIO_FALLA["si"] = False
limpiar()
b.avisos_de_plazo()
ok(len(MANDADOS) == 1, "y en la vuelta siguiente el aviso si llega")
ok("0" in b.estado["avisos"].get(idt, []), "ahora si queda anotado")

# lo mismo con una clase por videoconferencia
b = bot_de_prueba()
novedad = [{"titulo": "Clase de hoy", "url": "http://x/a",
            "descripcion": "nos vemos en https://meet.google.com/abc-defg-hij"}]
limpiar()
ENVIO_FALLA["si"] = True
b.clases_nuevas(CLAVE, "C\u00e1lculo", novedad)
ok(len(MANDADOS) == 1, "intenta avisar la clase")
ok(not b.estado["clases_avisadas"],
   "una clase que no se pudo avisar no queda marcada como avisada")
ENVIO_FALLA["si"] = False
limpiar()
b.clases_nuevas(CLAVE, "C\u00e1lculo", novedad)
ok(len(MANDADOS) == 1 and b.estado["clases_avisadas"],
   "al reintentar, la clase llega y recien ahi se marca")


# ===================================================================== 3
titulo("3. de madrugada solo suena lo que te cambia el dia")

ficha_floja = CL.detectar("Repaso", "",
                          "la clase pasada fue por videoconferencia")
ok(bool(ficha_floja), "detecta que el texto habla de una clase")
ok(not CL.prioritaria(ficha_floja),
   "pero sin enlace NO es de las que te despiertan")

b = bot_de_prueba()
b.en_silencio = lambda: True
limpiar()
b.clases_nuevas(CLAVE, "C\u00e1lculo",
                [{"titulo": "Repaso", "url": "http://x/a",
                  "descripcion": "la clase pasada fue por videoconferencia"}])
ok(len(MANDADOS) == 1, "igual te lo avisa")
ok(MANDADOS[-1]["silencioso"] is True,
   "pero de madrugada entra sin sonido")

b = bot_de_prueba()
b.en_silencio = lambda: True
limpiar()
b.clases_nuevas(CLAVE, "C\u00e1lculo",
                [{"titulo": "Clase online", "url": "http://x/b",
                  "descripcion": "entren a https://meet.google.com/abc-defg-hij"}])
ok(len(MANDADOS) == 1 and MANDADOS[-1]["silencioso"] is False,
   "una clase con enlace de verdad si te despierta")


# ===================================================================== 4
titulo("4. las palabras se buscan completas, no adentro de otra")

ok(not AV.urgente("tomate una foto del pizarron y subila"),
   "'tomate' ya no se confunde con 'tome'")
ok(not AV.urgente("vamos a tomar la asistencia manana"),
   "'tomar asistencia' no es una urgencia de madrugada")
ok(not AV.importante("les comparto mis apuntes tomados en clase"),
   "un apunte compartido no se marca como importante")
ok(AV.urgente("se suspende la clase de manana"),
   "una suspension sigue siendo urgente")
ok(AV.urgente("clases online el dia 3"), "una clase online sigue siendo urgente")
ok(AV.importante("hay prueba el lunes"), "una prueba sigue siendo importante")
ok(AV.importante("recuerden las entregas del informe"),
   "tambien en plural")


# ===================================================================== 5
titulo("5. un nombre con signos raros no rompe el mensaje")

FEO = 'C\u00e1lculo <b>3</b> & "Fisica"'
b = bot_de_prueba(nombre_ramo=FEO)
tarea_mia(b, idt="mio_9", horas=5.0, titulo_t="informe")
texto = b.texto_pendientes()
ok("<b>3</b>" not in texto, "el nombre del ramo no se manda con formato crudo")
ok("&lt;b&gt;3&lt;/b&gt;" in texto, "va escapado, se lee tal cual lo escribio el profe")

diag = b.texto_diagnostico()
ok("<b>3</b>" not in diag, "la pantalla de diagnostico tambien lo escapa")

sucio = ENLACE_DE_VERDAD("abrir", 'https://x/a"onmouseover="malo')
ok('a"onmouseover' not in sucio,
   "una direccion con comillas no parte el enlace en dos")
ok(sucio.count('"') == 2, "el enlace queda con sus dos comillas y nada mas")


# ===================================================================== 6
titulo("6. un mensaje que no entra se corta AVISANDO")

largo = "hola " + ("a" * 6000)
c = CORTAR_AVISANDO_DE_VERDAD(largo)
ok(len(c) <= N.LARGO_MAXIMO, "entra en un solo mensaje")
ok(c.endswith(N.AVISO_DE_CORTE), "y te dice que le falta el final")
ok(CORTAR_AVISANDO_DE_VERDAD("corto") == "corto", "un texto corto no se toca")

fuente_n = sin_comentarios("notificar.py")
ok("cortar_avisando" in fuente_n.split("def enviar", 1)[-1][:600],
   "el que manda los mensajes usa el corte que avisa")


# ===================================================================== 7
titulo("7. los botones viejos explican, no se cuelgan")

b = bot_de_prueba()
acc = acc_de_prueba(b)
idt = tarea_mia(b, idt="mio_5", horas=3.0)
antes = b.estado["tareas"][idt]["vence"]


def novedades_falsas(datos):
    def _n(offset, espera=0):
        return datos
    return _n


limpiar()
N.novedades = novedades_falsas([{
    "update_id": 1,
    "callback_query": {"id": "c1", "from": {"id": "9999"},
                       "data": "dormir1:" + idt,
                       "message": {"message_id": 55}},
}])
C.atender(b.estado, acc, HOY)
ok(b.estado["tareas"][idt]["vence"] != antes,
   "el boton de +1 hora ahora si mueve el recordatorio")
ok(REDIBUJADAS == [idt], "y redibuja la tarjeta, no el panel encima")
ok(PANELES == [], "no le tapa el mensaje con el panel")
ok(any("1 hora" in a for a in AVISOS_DE_BOTON),
   "te contesta que te lo recuerda en una hora")

limpiar()
N.novedades = novedades_falsas([{
    "update_id": 2,
    "callback_query": {"id": "c2", "from": {"id": "9999"},
                       "data": "vieja:cosa:que:ya:no:existe",
                       "message": {"message_id": 56}},
}])
C.atender(b.estado, acc, HOY)
ok(PANELES == [], "un boton de una version vieja no redibuja nada")
ok(AVISOS_DE_BOTON and AVISOS_DE_BOTON[-1].strip(),
   "pero contesta algo, asi no queda el relojito girando")
ok("viejo" in " ".join(AVISOS_DE_BOTON).lower(),
   "y le explica que el boton es de un mensaje viejo")

ok(P.reconoce("p:raiz"), "el panel reconoce sus propias pantallas")
ok(not P.reconoce("vieja:cosa"), "y no reconoce lo que no es suyo")


# ===================================================================== 8
titulo("8. el 'Dale' de un pedido viejo no ejecuta el pedido nuevo")

b = bot_de_prueba()
acc = acc_de_prueba(b)
marca_vieja = b.nueva_marca_de_propuesta(
    {"accion": "recordar", "que": "lo viejo",
     "cuando": (HOY + dt.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")})
marca_nueva = b.nueva_marca_de_propuesta(
    {"accion": "recordar", "que": "lo nuevo",
     "cuando": (HOY + dt.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")})
ok(marca_vieja != marca_nueva, "cada pedido tiene su propia marca")

limpiar()
salida = b.confirmar_propuesta(True, marca_vieja)
ok("anterior" in (salida or "").lower(),
   "apretar el 'Dale' viejo no hace nada y te lo explica")
ok(not b.estado.get("tareas"), "y no guarda el pedido equivocado")

salida = b.confirmar_propuesta(True, marca_nueva)
ok(any("lo nuevo" in str(t.get("titulo", ""))
       for t in b.estado.get("tareas", {}).values()),
   "el 'Dale' del pedido de verdad si funciona")

fuente_c = sin_comentarios("comandos.py")
ok("prop:si" in fuente_c and "marca" in fuente_c.split("prop:si", 1)[-1][:400],
   "el boton viaja con la marca de su pedido")


# ===================================================================== 9
titulo("9. la memoria no crece para siempre")

b = bot_de_prueba()
dias = int(CFG.DIAS_PARA_PODAR_HUELLAS)
viejo = (HOY - dt.timedelta(days=dias + 30)).strftime("%Y-%m-%d %H:%M")
reciente = HOY.strftime("%Y-%m-%d %H:%M")
b.estado["items"] = {"h_vieja": viejo, "h_nueva": reciente}

tope = int(CFG.PENDIENTES_CERRADOS_GUARDADOS)
for i in range(tope + 5):
    b.estado["tareas"]["vieja_%d" % i] = {
        "titulo": "cerrada %d" % i, "hecho": True,
        "nacio": (HOY - dt.timedelta(days=tope + 5 - i)).strftime("%Y-%m-%d %H:%M"),
    }
abierta = tarea_mia(b, idt="mio_abierta", horas=48.0)

b.podar_memoria()
ok("h_vieja" not in b.estado["items"], "una huella de hace mas de un ano se va")
ok("h_nueva" in b.estado["items"], "la de esta semana se queda")
cerradas = [k for k, t in b.estado["tareas"].items() if t.get("hecho")]
ok(len(cerradas) == tope, "quedan %d pendientes cerrados, no mas" % tope)
ok(abierta in b.estado["tareas"], "lo que todavia no hiciste no se toca")
ok("vieja_0" not in b.estado["tareas"] and "vieja_%d" % (tope + 4) in b.estado["tareas"],
   "se van los mas antiguos y quedan los ultimos")
ok("podar_memoria" in sin_comentarios("watcher.py").split("def una_vuelta", 1)[-1][:400],
   "y la poda se hace en cada vuelta, sola")


# ==================================================================== 10
titulo("10. la memoria del disco no queda partida al medio")

carpeta = tempfile.mkdtemp()
guardado = A.ARCHIVO_LOCAL
try:
    A.ARCHIVO_LOCAL = os.path.join(carpeta, "estado", "visto.json")
    A._escribir_local({"items": {"a": "1"}})
    ok(os.path.isfile(A.ARCHIVO_LOCAL), "la memoria queda guardada")
    ok(not os.path.isfile(A.ARCHIVO_LOCAL + ".nuevo"),
       "y no deja archivos a medio escribir dando vueltas")
    leido = A._leer_local()
    ok(leido.get("items", {}).get("a") == "1", "se puede volver a leer")
    ok(not A.memoria_rota(), "y no se considera rota")

    with open(A.ARCHIVO_LOCAL, "w", encoding="utf-8") as f:
        f.write('{"items": {"a": ')      # cortada, como si se hubiera cortado la corrida
    A._leer_local()
    ok(A.memoria_rota(),
       "si la memoria quedo ilegible, el bot lo sabe y puede decirlo")

    os.remove(A.ARCHIVO_LOCAL)
    A._leer_local()
    ok(not A.memoria_rota(),
       "pero la primera vez, sin archivo, no es una falla")
finally:
    A.ARCHIVO_LOCAL = guardado
    shutil.rmtree(carpeta, ignore_errors=True)


# ==================================================================== 11
titulo("11. si se queda sin memoria, lo dice")

b = bot_de_prueba()
b.modo = "repo"
limpiar()
b._avisar_memoria("gist")
ok(len(MANDADOS) == 1, "avisa que paso a la copia de respaldo")
texto = ultimo()
ok("gist" not in texto.lower() and "json" not in texto.lower(),
   "sin nombres de archivos ni palabras de programador")

limpiar()
b._avisar_memoria("repo")
ok(len(MANDADOS) == 0, "no lo repite cada cinco minutos")

b = bot_de_prueba()
b.modo = "nada"
limpiar()
b._avisar_memoria("gist")
ok(len(MANDADOS) == 1 and "repita" in ultimo(),
   "si no pudo guardar nada, te avisa que podria repetirse algo")

b = bot_de_prueba()
b.modo = "gist"
limpiar()
b._avisar_memoria("gist")
ok(len(MANDADOS) == 0, "cuando todo anda bien no molesta")


# ==================================================================== 12
titulo("12. la hora es la de tu ciudad, no la de la maquina")

ok(SA._ahora().tzinfo is not None,
   "el vigilante del reloj usa hora con zona")
ok(CO._ahora().tzinfo is not None,
   "compartir tambien fecha con hora de tu ciudad")
fuente_s = sin_comentarios("salud.py")
ok("utcnow" not in fuente_s, "ya no queda ninguna hora sin zona en salud")
fuente_co = sin_comentarios("compartir.py")
# La unica hora sin zona que queda es el respaldo de adentro del propio
# ayudante, para cuando la maquina no trae la lista de zonas horarias.
ok(fuente_co.count("dt.datetime.now()") == 1,
   "ni en compartir queda una fecha suelta con la hora de la maquina")


# ==================================================================== 13
titulo("13. el reloj de GitHub no puede matar una corrida a medias")

wf = ""
for ruta in (".github/workflows/watch.yml", ".github/workflows/watcher.yml"):
    if os.path.isfile(ruta):
        with open(ruta, encoding="utf-8") as f:
            wf = f.read()
        break
ok(bool(wf), "encuentro el archivo del reloj")
sin_notas = "\n".join(l.split("#", 1)[0] for l in wf.splitlines())
ok("cancel-in-progress: true" not in sin_notas,
   "un turno programado ya no corta al que esta trabajando")
ok("schedule" in sin_notas.split("cancel-in-progress", 1)[-1][:120],
   "pero al actualizar a mano si se corta el viejo")


# ==================================================================== 14
titulo("14. la version quedo al dia")

ok(VER.VERSION > "5.7", "la version subio (dice %s)" % VER.VERSION)
ok(len(VER.CAMBIOS) >= 5, "y trae la lista de que cambio")
todos = " ".join(VER.CAMBIOS).lower()
for jerga in ("utcnow", "callback", "json", "except", "gist", "timezone"):
    ok(jerga not in todos, "la lista de cambios no dice '%s'" % jerga)


# ==================================================================== fin
print("\n" + "=" * 50)
if FALLOS:
    print("fallaron %d cosas:" % len(FALLOS))
    for f in FALLOS:
        print("  - %s" % f)
    raise SystemExit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
