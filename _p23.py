# -*- coding: utf-8 -*-
"""Tanda 23: lo que fallaba de verdad en tu telefono y en tu repositorio.

Cada prueba de aca nace de algo que te paso:
  - apretabas /compartir y el bot se quedaba mudo
  - buscabas un archivo por su nombre exacto y decia que no habia nada
  - la IA decia "sin cupo" para siempre, aunque estrenaras claves
  - la sonda trabajaba un rato largo y se caia justo al final
  - tu memoria se estaba publicando en un repositorio abierto

Se corre sola, sin internet, sin claves de verdad y sin tocar tu cuenta:
    python3 _p23.py
"""
import io
import os

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("CLAVE_COMPARTIR", "llave-de-prueba-nada-real")

import fuentes as CFG
import ia as IA
import notificar as N
import panel as P
import sonda as SO
import version as VER
import watcher as W

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
DOCS = []


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append({"texto": texto, "silencioso": silencioso,
                     "botones": botones})
    return len(MANDADOS)


def _editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    MANDADOS.append({"texto": texto, "botones": botones, "edito": mensaje_id})
    return mensaje_id


def _mandar_documento(nombre, datos, leyenda="", silencioso=True,
                      responde_a=None):
    DOCS.append({"nombre": nombre, "datos": datos, "leyenda": leyenda})
    return len(DOCS)


def _nada(*a, **k):
    return None


def _cerrar(texto="", botones=None):
    MANDADOS.append({"texto": texto, "silencioso": True, "botones": botones})
    return len(MANDADOS)


N.enviar = _enviar
N.editar = _editar
N.borrar = _nada
N.anclar = _nada
N.desanclar = _nada
N.avisar_boton = _nada
N.mandar_documento = _mandar_documento
N.mandar_archivo = _nada
N.publicar_menu = _nada
N.quitar_teclado = _nada


def limpiar():
    del MANDADOS[:]
    del DOCS[:]


def todo_lo_mandado():
    return "\n".join(m["texto"] or "" for m in MANDADOS)


def sin_comentarios(nombre):
    """El codigo sin comentarios: los comentarios cuentan como era ANTES."""
    salida = []
    with io.open(nombre, "r", encoding="utf-8") as f:
        for linea in f:
            salida.append(linea.split("#", 1)[0])
    return "\n".join(salida)


CLAVE = "A:1"


def bot_de_prueba(nombre_ramo="C\u00c1LCULO INTEGRAL"):
    b = W.Vigilante.__new__(W.Vigilante)
    b.estado = {
        "items": {}, "grupos": {
            CLAVE: {"nombre": nombre_ramo, "emoji": "\U0001F4D8",
                    "fuente": "A", "id": "1", "url": "http://x/curso/1",
                    "visto": "", "cantidad": 0},
        },
        "archivados": {}, "ausentes": {}, "avisos": {}, "tareas": {},
        "perfiles": {}, "callados": {}, "novedades": [], "pendientes_ia": [],
        "config": {}, "fallas": {}, "tg_offset": 0, "avisos_vistos": {},
        "deshacer": None, "personas": {}, "clases_avisadas": {},
        "version_avisada": VER.VERSION, "version_desde": "",
        "aviso_clave": {}, "basura": [], "de_afuera": [], "desconocidos": {},
    }
    b.sesiones = {}
    b.bases = {}
    b.cache = {}
    b.modo = "gist"
    b.gist_nuevo = False
    b.guardar = lambda *a, **k: None
    b.animar = lambda t: (_nada, _cerrar)
    # Nada de red en las pruebas: lo "de ahora" viene vacio.
    b.leer_ramo_ahora = lambda clave: []
    b.comprobar_dudosos = lambda clave, faltan: []
    return b


def acc_de_prueba(b):
    acc = dict(b._acciones())
    acc["dibujar_panel"] = lambda donde=None, mid=None: None
    acc["abrir_panel"] = lambda *a, **k: None
    acc["redibujar_tarjeta"] = lambda idt=None, mid=None: None
    return acc


# ===================================================================== 1
titulo("1. la sonda ya no se cae al final del trabajo")

VISITADOS = []
SALIDA_REAL = SO.SALIDA


def _entrar_falso(s, base, usuario, clave):
    return True


def _leer_falso(s, base):
    # Las plataformas devuelven una LISTA de ramos.  Antes la sonda la
    # trataba como fichero y reventaba justo aca.
    return ([{"id": "97852", "nombre": "RAMO DE PRUEBA",
              "url": base + "/curso/97852", "items": [], "firma": "x"}],
            ["12345"])


def _informe_falso(W_, CFG_, s, base, ficha, etiqueta):
    VISITADOS.append(ficha.get("nombre"))


ADAPTADORES_REALES = W.ADAPTADORES
INFORME_REAL = SO.informe_de_ramo
AULA_REAL = SO.probar_aula
PROFUNDO = (getattr(CFG, "MINUTOS_EXPLORACION_PROFUNDA", 0),
            getattr(CFG, "PROFUNDIDAD", 1),
            getattr(CFG, "PAGINAS_POR_RAMO", 14))

W.ADAPTADORES = {"b64": (_entrar_falso, _leer_falso),
                 "aula": (_entrar_falso, _leer_falso)}
SO.informe_de_ramo = _informe_falso
SO.probar_aula = lambda *a, **k: None
SO.SALIDA = "/tmp/sonda_de_prueba.txt"
for fuente in CFG.FUENTES:
    os.environ[fuente["env_url"]] = "https://plataforma-de-prueba.local"
    os.environ[fuente["env_user"]] = "alguien"
    os.environ[fuente["env_pass"]] = "algo"

se_cayo = ""
try:
    SO.main()
except Exception as e:
    se_cayo = "%s: %s" % (type(e).__name__, e)

ok(not se_cayo, "la sonda termina entera cuando la plataforma le da la lista")
ok(len(VISITADOS) >= 1, "y alcanza a mirar los ramos que encontro")
ok(os.path.isfile("/tmp/sonda_de_prueba.txt"), "y deja su informe escrito")

W.ADAPTADORES = ADAPTADORES_REALES
SO.informe_de_ramo = INFORME_REAL
SO.probar_aula = AULA_REAL
SO.SALIDA = SALIDA_REAL
(CFG.MINUTOS_EXPLORACION_PROFUNDA, CFG.PROFUNDIDAD,
 CFG.PAGINAS_POR_RAMO) = PROFUNDO
for fuente in CFG.FUENTES:
    for nombre in (fuente["env_url"], fuente["env_user"], fuente["env_pass"]):
        os.environ.pop(nombre, None)


# ===================================================================== 2
titulo("2. buscar por nombre encuentra lo que escribiste")

FICHA = {"titulo": "Gu\u00eda N\u00b03 resuelta",
         "url": "http://x/pluginfile/guia3_resuelta.pdf",
         "cuando": "2026-07-01"}

ok(W.calza_nombre("Gu\u00eda N\u00b03 resuelta.pdf", FICHA),
   "el nombre completo, con tilde y con el final, encuentra el archivo")
ok(W.calza_nombre("guia 3", FICHA), "dos palabras sueltas tambien")
ok(W.calza_nombre("resuelta guia", FICHA), "y no importa el orden")
ok(W.calza_nombre("guia3_resuelta", FICHA),
   "tambien si escribis el nombre con el que baja el archivo")
ok(not W.calza_nombre("laboratorio", FICHA),
   "pero no trae cualquier cosa: lo que no calza, no calza")
ok(not W.calza_nombre("guia 4 resuelta", FICHA),
   "y la guia 4 no puede traerte la guia 3")

b = bot_de_prueba()
b.estado["novedades"] = [{"c": CLAVE, "u": FICHA["url"], "t": FICHA["titulo"],
                         "f": "2026-07-01", "tipo": "archivo"},
                        {"c": CLAVE, "u": "http://x/pluginfile/programa.pdf",
                         "t": "Programa del curso", "f": "2026-03-02",
                         "tipo": "archivo"}]
elegidos, total, rango = b.filtrar_archivos(
    CLAVE, "todo", nombre="Gu\u00eda N\u00b03 resuelta.pdf", frescos=False)
ok(len(elegidos) == 1 and elegidos[0]["url"] == FICHA["url"],
   "y el filtro devuelve ese archivo y no los otros")

parecidos = b.parecidos_a(CLAVE, "guia 4 resuelta")
ok(parecidos and "resuelta" in " ".join(parecidos).lower(),
   "si te equivocas por poco, propone lo mas parecido que tiene")

limpiar()
b.pedir_archivos(CLAVE, "todo", nombre="guia 4 resuelta")
salida = todo_lo_mandado()
ok("parecido" in salida.lower(),
   "y cuando no encuentra nada no te deja a oscuras: te dice que si tiene")


# ===================================================================== 3
titulo("3. la IA prueba todos los modelos antes de rendirse")


class RespIA(object):
    def __init__(self, codigo, cuerpo):
        self.status_code = codigo
        self._cuerpo = cuerpo
        self.text = ""

    def json(self):
        return self._cuerpo


class RequestsFalso(object):
    def __init__(self, respuestas):
        self.respuestas = respuestas
        self.pedidos = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.pedidos.append(url)
        i = min(len(self.pedidos) - 1, len(self.respuestas) - 1)
        return self.respuestas[i]


SIN_CUPO = {"error": {
    "message": "You exceeded your current quota, please check your plan "
               "and billing details.",
    "details": [{"violations": [{"quotaValue": "0"}]}]}}
BUENA = {"candidates": [{"content": {"parts": [{"text": "resumen de prueba"}]}}]}

REQ_REAL = IA.requests
CLAVE_IA = {"clave": "AIzaDePrueba1234567890", "nombre": "IA_KEY",
            "modelo": CFG.IA["modelo"], "proveedor": "gemini", "url": ""}

IA._MODELO_QUE_ANDA.clear()
falso = RequestsFalso([RespIA(429, SIN_CUPO), RespIA(200, BUENA)])
IA.requests = falso
try:
    contesto = IA._gemini("hola", [], dict(CLAVE_IA))
except Exception as e:
    contesto = "se cayo: %s" % type(e).__name__
ok(contesto == "resumen de prueba",
   "si al primer modelo no le queda cupo, contesta igual con el de repuesto")
ok(len(falso.pedidos) >= 2, "o sea que de verdad prueba mas de un modelo")

IA._MODELO_QUE_ANDA.clear()
falso2 = RequestsFalso([RespIA(429, SIN_CUPO)])
IA.requests = falso2
try:
    IA._gemini("hola", [], dict(CLAVE_IA))
    aviso = "contesto igual"
except IA.SinCupo:
    aviso = "sin cupo"
except Exception as e:
    aviso = type(e).__name__
ok(aviso == "sin cupo",
   "recien cuando ninguno tiene lugar dice que se quedo sin cupo")
ok(len(falso2.pedidos) >= 2, "y antes de decirlo los probo a todos")

IA.requests = REQ_REAL
IA._MODELO_QUE_ANDA.clear()

motivo = IA._motivo(RespIA(429, SIN_CUPO), "modelo-de-prueba")
ok("cupo gratis" in motivo and "modelo-de-prueba" in motivo,
   "cuando el modelo no tiene NADA de cupo lo dice, en vez de mandarte a esperar")
ok("(clave)" in IA.sin_la_clave("fallo con AIzaSyABCDEFGHIJKLMNOP"),
   "y ningun pedazo de clave puede colarse en un mensaje")


# ===================================================================== 4
titulo("4. un apuro de un minuto ya no apaga la IA todo el dia")

ok(not IA._es_cupo_del_dia("You exceeded your current quota, please check "
                           "your plan and billing details."),
   "el rechazo comun ya no cuenta como 'se acabo lo de hoy'")
ok(not IA._es_cupo_del_dia("too many requests, slow down"),
   "ni 'vas muy rapido'")
ok(IA._es_cupo_del_dia("Quota exceeded: generate requests per day per project"),
   "pero el limite del dia si se reconoce")
ok(IA._es_cupo_del_dia("limite por dia alcanzado"),
   "tambien dicho en castellano")


# ===================================================================== 5
titulo("5. ninguna orden se queda sin respuesta visible")

b2 = bot_de_prueba()
b2.acc = acc_de_prueba(b2)

limpiar()
N.ULTIMO_MANDADO = 900
b2.estado["panel_id"] = 100
b2.dibujar_panel("p:raiz")
ok(MANDADOS and not MANDADOS[-1].get("edito"),
   "si el panel quedo tapado arriba, manda uno nuevo abajo")

limpiar()
N.ULTIMO_MANDADO = 100
b2.estado["panel_id"] = 100
b2.dibujar_panel("p:raiz")
ok(MANDADOS and MANDADOS[-1].get("edito") == 100,
   "y si el panel es lo ultimo del chat, lo redibuja sin llenarte de mensajes")
ok(b2.panel_tapado(100) is False, "sabe cuando el panel esta a la vista")
N.ULTIMO_MANDADO = 900
ok(b2.panel_tapado(100) is True, "y sabe cuando quedo enterrado")
N.ULTIMO_MANDADO = 0

estado_roto = {"config": {}}
texto, botones = P.pantalla(estado_roto, "p:nov",
                            {"texto_novedades": lambda: 1 / 0})
ok("ZeroDivision" not in texto and "Exception" not in texto,
   "una pantalla rota no le muestra el nombre del error al dueno")
ok("prob" in texto.lower() or "avisame" in texto.lower(),
   "le dice que hacer, no lo deja mirando")
ok(bool(estado_roto.get("ultimo_error_panel")),
   "pero el detalle queda anotado para el diagnostico")
ok("dibujando esto (%s)" not in sin_comentarios("panel.py"),
   "y ese mensaje ya no se arma con el nombre tecnico")


# ===================================================================== 6
titulo("6. tu memoria no se publica en un repositorio abierto")

wf = ""
for ruta in (os.path.join(".github", "workflows", "watch.yml"),
             os.path.join(".github", "workflows", "watcher.yml")):
    if os.path.isfile(ruta):
        wf = io.open(ruta, encoding="utf-8").read()
        break
ok(bool(wf), "encuentro el archivo del reloj")
sin_notas = "\n".join(l.split("#", 1)[0] for l in wf.splitlines())
ok("estado/visto.json" in sin_notas,
   "el reloj sigue teniendo su copia de respaldo de la memoria")
ok("repository.private" in sin_notas,
   "pero solo la guarda si el repositorio es privado, para no publicar lo tuyo")

ignorados = io.open(".gitignore", encoding="utf-8").read()
ok("visto.json" in ignorados and "estado/" in ignorados,
   "y la memoria esta en la lista de lo que nunca se sube")


# ===================================================================== 7
titulo("7. lo que le contas al dueno")

primero = str(VER.CAMBIOS[0]).lower()
ok("importante" in primero, "lo primero de la lista es lo mas importante")
ok(any("mudo" in str(c).lower() or "silencio" in str(c).lower()
       for c in VER.CAMBIOS),
   "le contas que se arreglaron los silencios")
ok(len(VER.CAMBIOS) >= 5, "y cuenta varias cosas, no una")
todos = " ".join(str(x) for x in VER.CAMBIOS).lower()
for jerga in ("json", "callback", "except", "quota", "api", "token",
              "commit", "workflow", "http", "cache"):
    ok(jerga not in todos, "la lista de cambios no dice '%s'" % jerga)


# ==================================================================== fin
print("\n" + "=" * 50)
if FALLOS:
    print("fallaron %d cosas:" % len(FALLOS))
    for f in FALLOS:
        print("  - %s" % f)
    raise SystemExit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
