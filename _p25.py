# -*- coding: utf-8 -*-
"""Tanda 25: las cinco cosas que fallaron en la sexta vuelta.

Cada prueba de aca nace de algo concreto que te paso:
  1. el panel decia que la ayuda de IA no estaba y despues te contestaba bien
  2. buscabas "Semana" y te decia que no lo tenia, pero al pedir todo el ramo
     te llegaba el Semana1.pdf
  3. te agregaron a un ramo nuevo y no aparecia ni en la lista de ramos
  4. un ramo enorme se veia casi vacio y el bot no decia que lo habia mirado
     a medias
  5. el boton de reiniciar apagaba el bot y el bot no volvia

Se corre sola, sin internet, sin claves de verdad y sin tocar tu cuenta:
    python3 _p25.py
"""
import io
import os
import re
import sys

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("IA_KEY", "AIzaDePrueba1")
os.environ.setdefault("IA_KEY_2", "AIzaDePrueba2")

import fuentes as CFG
import ia as IA
import notificar as N
import salud as SA
import sonda as SO
import version as VER
import watcher as W

FALLOS = []
CARPETA = os.path.dirname(os.path.abspath(__file__)) or "."
URL_ARCHIVO = "https://plataforma-de-prueba/curso/9999/archivo/8891"


def ok(cond, que):
    if cond:
        print("  ok   %s" % que)
    else:
        print("  MAL  %s" % que)
        FALLOS.append(que)


def titulo(t):
    print("\n" + t)
    print("-" * 56)


# --------------------------------------------------------------- ayudantes
MANDADOS = []


def _enviar_falso(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append(texto)
    return {"ok": True, "result": {"message_id": 1}}


N.enviar = _enviar_falso


class Resp(object):
    """Una respuesta de mentira, con lo justo para que el codigo la use."""

    def __init__(self, texto="", url="", codigo=200, cabeceras=None):
        self.text = texto
        self.url = url
        self.status_code = codigo
        self.headers = cabeceras or {}
        self.content = texto.encode("utf-8")

    def json(self):
        return {}

    def close(self):
        pass


class RespConNombre(Resp):
    def __init__(self, nombre):
        Resp.__init__(self, "", "", 200,
                      {"Content-Disposition": 'attachment; filename="%s"' % nombre})


class SesionQueSabeElNombre(object):
    """La plataforma sabe como se llama el archivo aunque el enlace no lo diga."""

    def __init__(self, nombre="Semana1.pdf"):
        self.nombre = nombre
        self.pedidos = []

    def head(self, url, **kw):
        self.pedidos.append(url)
        return RespConNombre(self.nombre)

    def get(self, url, **kw):
        self.pedidos.append(url)
        return RespConNombre(self.nombre)


def vigilante_con_un_archivo(nombre_real="Semana1.pdf"):
    v = object.__new__(W.Vigilante)
    v.estado = {
        "arrancado": True,
        "novedades": [{"c": "r1", "u": URL_ARCHIVO, "t": "Descargar",
                       "f": "2026-08-01", "tipo": "archivo"}],
        "grupos": {"r1": {"nombre": "TALLER DE PRUEBA", "fuente": "A",
                          "id": "9999",
                          "url": "https://plataforma-de-prueba/curso/9999"}},
    }
    v.sesiones = {"A": SesionQueSabeElNombre(nombre_real)}
    v.leer_ramo_ahora = lambda clave: []
    v.guardar = lambda: None
    return v


def sin_comentarios(texto):
    """Los comentarios guardan a proposito el texto viejo, asi que no cuentan."""
    texto = re.sub(r'""".*?"""', " ", texto, flags=re.S)
    texto = re.sub(r"'''.*?'''", " ", texto, flags=re.S)
    return "\n".join(l.split("#")[0] for l in texto.split("\n"))


JERGA = ("traceback", "exception", "none", "self.", "watcher.py", "sesskey",
         "logintoken", "workflow", "dispatch", "attributeerror", "{'", '{"')


def sin_jerga(t):
    bajo = str(t or "").lower()
    return [p for p in JERGA if p in bajo]


# ============================================================ 1. el nombre
titulo("1. buscar por nombre encuentra el archivo de verdad")

ficha_real = {"titulo": "Descargar", "url": URL_ARCHIVO, "real": "Semana1.pdf"}
ficha_pelada = {"titulo": "Descargar", "url": URL_ARCHIVO}
ok(W.calza_nombre("Semana", ficha_real),
   "escribir 'Semana' encuentra el archivo que se llama Semana1.pdf")
ok(W.calza_nombre("semana 1", ficha_real),
   "y tambien escribiendolo a medias y en minusculas")
ok(not W.calza_nombre("parcial", ficha_real),
   "pero no encuentra cualquier cosa")
ok(not W.calza_nombre("Semana", ficha_pelada),
   "sin saber el nombre real no lo podia encontrar (asi estaba antes)")

v = vigilante_con_un_archivo()
elegidos, total, _rango = v.filtrar_archivos("r1", alcance="todo", nombre="Semana")
ok(total == 1, "el ramo tiene un solo archivo guardado")
ok(len(elegidos) == 1,
   "y buscando 'Semana' aparece, en vez de decirte que no lo tiene")
ok(v.estado.get("nombres_reales", {}).get(URL_ARCHIVO) == "Semana1.pdf",
   "el nombre queda guardado para la proxima")

v.sesiones["A"].pedidos = []
elegidos2, _t, _r = v.filtrar_archivos("r1", alcance="todo", nombre="semana")
ok(len(elegidos2) == 1, "la segunda vez tambien lo encuentra")
ok(v.sesiones["A"].pedidos == [],
   "y ya no vuelve a molestar a la plataforma preguntando lo mismo")

v3 = vigilante_con_un_archivo()
elegidos3, _t, _r = v3.filtrar_archivos("r1", alcance="todo", nombre="parcial")
ok(not elegidos3, "y si de verdad no esta, no te lo inventa")

v4 = vigilante_con_un_archivo()
v4.recordar_nombre(URL_ARCHIVO, "Semana1.pdf")
fichas = v4.archivos_del_ramo("r1", frescos=False)
ok(fichas and fichas[0].get("real") == "Semana1.pdf",
   "la lista del ramo muestra el nombre con el que llega el archivo")
ok("Semana1" in str(v4.parecidos_a("r1", "seman")),
   "y cuando sugiere parecidos sugiere el nombre real, no 'Descargar'")


# ================================================== 2. el ramo que no salia
titulo("2. un ramo recien inscrito aparece igual en la lista")

PORTADA = ('<html><head><script>var M = {"sesskey":"AAA1"};</script></head>'
           '<body><a href="/course/view.php?id=1111">RAMO VIEJO</a>'
           '</body></html>')


class SesionAula(object):
    def __init__(self):
        self.pidio_la_lista = False

    def get(self, url, **kw):
        return Resp(PORTADA, url)

    def post(self, url, **kw):
        self.pidio_la_lista = True
        return _RespLista()


class _RespLista(Resp):
    def json(self):
        return [{"error": False, "data": {"courses": [
            {"id": 1111, "fullname": "RAMO VIEJO",
             "viewurl": "https://p/course/view.php?id=1111"},
            {"id": 90002, "fullname": "RAMO NUEVO",
             "viewurl": "https://p/course/view.php?id=90002"}]}}]


viejo_explorar = W.explorar_ramo
W.explorar_ramo = lambda s, base, g: ([], "firma")
sesion_aula = SesionAula()
try:
    grupos, _viejos = W.leer_aula(sesion_aula, "https://p")
finally:
    W.explorar_ramo = viejo_explorar

nombres = sorted((g or {}).get("nombre", "") for g in (grupos or []))
ok(sesion_aula.pidio_la_lista,
   "pregunta la lista completa de ramos, no se conforma con la portada")
ok(len(grupos or []) == 2,
   "encuentra los dos ramos: el de siempre y el que te acaban de agregar")
ok("RAMO NUEVO" in nombres, "y el nuevo esta entre ellos")


# =============================================== 3. el ramo mirado a medias
titulo("3. un ramo enorme avisa cuando lo miro a medias")


def html_curso(cuantas):
    partes = ['<html><body>']
    for i in range(cuantas):
        partes.append('<a href="/mod/folder/view.php?id=%d">Carpeta %d</a>'
                      % (900 + i, i))
    partes.append("</body></html>")
    return "".join(partes)


class SesionCurso(object):
    def __init__(self, cuantas=12):
        self.cuantas = cuantas
        self.vistas = []

    def get(self, url, **kw):
        self.vistas.append(url)
        if "course/view.php" in url:
            return Resp(html_curso(self.cuantas), url)
        return Resp("<html><body>nada</body></html>", url)


tope_antes = CFG.PAGINAS_POR_RAMO
W._ULTIMO_PROFUNDO.clear()
W._YA_MIRADAS.clear()
CFG.PAGINAS_POR_RAMO = 4
g_corto = {"id": "90002", "nombre": "FISICA DE PRUEBA",
           "url": "https://p/course/view.php?id=90002"}
s1 = SesionCurso()
W.explorar_ramo(s1, "https://p", g_corto)
ok(g_corto.get("corto") is True,
   "cuando no alcanza a mirar todo, queda anotado que falto")

W._ULTIMO_PROFUNDO.clear()
s2 = SesionCurso()
W.explorar_ramo(s2, "https://p", dict(g_corto))
nuevas = set(s2.vistas) - set(s1.vistas)
ok(bool(nuevas),
   "en la vuelta siguiente abre carpetas que antes no habia abierto")

W._ULTIMO_PROFUNDO.clear()
W._YA_MIRADAS.clear()
CFG.PAGINAS_POR_RAMO = 60
g_entero = {"id": "8807", "nombre": "FISICA DE PRUEBA",
            "url": "https://p/course/view.php?id=8807"}
W.explorar_ramo(SesionCurso(), "https://p", g_entero)
ok(g_entero.get("corto") is False,
   "y cuando alcanza a mirar todo, no te molesta con avisos")
CFG.PAGINAS_POR_RAMO = tope_antes
ok(tope_antes >= 60,
   "el tope de carpetas por ramo alcanza para un ramo grande de verdad")


# ==================================================== 4. la IA no se miente
titulo("4. la IA no dice que esta caida y despues contesta bien")

viejo_descansando = IA._descansando
IA._descansando = lambda estado, c: "sin cupo por ahora"
try:
    encendida = {"config": {"ia": True}}
    frase = IA.en_palabras(encendida)
    puede = IA.se_puede_intentar(encendida)
finally:
    IA._descansando = viejo_descansando

ok(puede, "si le escribis mientras descansa, igual lo intenta")
ok("encendida" in frase.lower(),
   "y la pantalla no te dice que esta caida")
for palabra in ("no disponible", "apagada", "no puedo"):
    ok(palabra not in frase.lower(),
       "la pantalla no dice '%s' mientras el chat contesta bien" % palabra)
ok(not sin_jerga(frase), "y lo dice sin jerga")

apagada = {"config": {"ia": False}}
ok("apagada por vos" in IA.en_palabras(apagada),
   "si vos la apagaste, eso si lo dice claro")
ok(not IA.se_puede_intentar(apagada), "y ahi de verdad no lo intenta")


# ================================================== 5. apagarse y volver
titulo("5. el boton de reiniciar promete volver y vuelve")

ok(hasattr(SA, "relanzar"), "sabe pedirle a GitHub un turno nuevo")

guardado = {}


class RequestsFalso(object):
    codigo = 204

    @classmethod
    def post(cls, url, headers=None, data=None, timeout=None):
        guardado["url"] = url
        guardado["data"] = data or ""
        guardado["headers"] = headers or {}
        return Resp("", url, cls.codigo)


os.environ["GH_TOKEN"] = "llave-de-prueba"
os.environ["GH_REPO"] = "duenio/repo-de-prueba"
os.environ["GH_RAMA"] = "main"
viejo_requests = SA.requests
SA.requests = RequestsFalso
try:
    bien, motivo = SA.relanzar()
    RequestsFalso.codigo = 403
    mal, motivo_mal = SA.relanzar()
finally:
    SA.requests = viejo_requests
    RequestsFalso.codigo = 204

ok(bien, "cuando GitHub dice que si, contesta que si")
ok("actions/workflows" in guardado.get("url", ""),
   "pide el turno nuevo por el camino que corresponde")
ok('"main"' in str(guardado.get("data", "")),
   "y sobre la rama que corresponde")
ok(not mal, "cuando GitHub no lo deja, no miente")
ok("llave" in motivo_mal.lower(), "y lo explica en castellano")
ok("llave-de-prueba" not in motivo_mal, "sin mostrar nunca la llave")
ok(not sin_jerga(motivo_mal), "y sin jerga")

vb = object.__new__(W.Vigilante)
vb.estado = {"arrancado": True}
vb.guardar = lambda: None

MANDADOS[:] = []
W.salud.relanzar = lambda *a, **k: (False, "no tengo la llave de GitHub")
vb.reiniciarme()
ok(not getattr(vb, "reiniciar_pedido", False),
   "si no puede garantizar la vuelta, NO se apaga")
ok(MANDADOS and "no me apago" in MANDADOS[-1].lower(),
   "y te avisa por que sigue despierto")
ok("reinicio_pedido_en" not in vb.estado,
   "y no deja anotado un reinicio que nunca paso")

MANDADOS[:] = []
W.salud.relanzar = lambda *a, **k: (True, "")
vb.reiniciarme()
ok(getattr(vb, "reiniciar_pedido", False) is True,
   "si consigue el turno nuevo, ahi si se apaga")
ok("reinicio_pedido_en" in vb.estado,
   "y deja anotado que se fue por el boton")
ok(MANDADOS and not sin_jerga(MANDADOS[-1]),
   "el aviso de apagado no tiene jerga")

MANDADOS[:] = []
vb.saludar_si_volvi()
ok(MANDADOS and "ya volv" in MANDADOS[0].lower(),
   "al volver te saluda, en vez de volver callado")
ok("reinicio_pedido_en" not in vb.estado, "y borra la anotacion")
MANDADOS[:] = []
vb.saludar_si_volvi()
ok(not MANDADOS, "y no repite el saludo en cada vuelta")

vc = object.__new__(W.Vigilante)
vc.estado = {"arrancado": True}
vc.guardar = lambda: None
MANDADOS[:] = []
vc.saludar_si_volvi()
ok(not MANDADOS, "si nunca lo reiniciaste, no saluda de la nada")


# ============================================ 6. la sonda cuenta por que no
titulo("6. la sonda cuenta por que no pudo entrar")

ok(hasattr(SO, "diagnostico_de_entrada"),
   "la sonda sabe mirar por que se quedo afuera")

PUERTA = ('<html><body><form id="loginform">'
          '<input name="logintoken" value="x">'
          '<input name="password" type="password">'
          '<div class="alert">Datos incorrectos, intente nuevamente</div>'
          '</form></body></html>')


class SesionPuerta(object):
    def get(self, url, **kw):
        return Resp(PUERTA, url)


SO.LINEAS[:] = []
SO.diagnostico_de_entrada(SesionPuerta(), "https://plataforma-de-prueba")
informe = "\n".join(SO.LINEAS)
ok("no pude entrar" in informe.lower(),
   "cuando no puede entrar, el informe lo dice y no queda vacio")
ok("casilla de clave" in informe,
   "y cuenta que la plataforma seguia viva")
ok("Datos incorrectos" in informe,
   "y copia lo que decia la pantalla, que es lo unico que sirve")
ok(len(SO.LINEAS) >= 6, "deja varias lineas, no una sola")

import inspect
firma = str(inspect.signature(SO.diagnostico_de_entrada))
ok("clave" not in firma and "pass" not in firma.lower(),
   "y ni siquiera recibe tu clave, asi que no la puede escribir")
SO.LINEAS[:] = []


# ================================== 7. el cupo de hoy no vuelve "en un rato"
titulo("7. de noche, 'se acabo el cupo de hoy' no se convierte en 'un rato'")

# Este es el que se escapaba: la cuenta de cuando vuelve la IA se decidia
# mirando el reloj (si faltan mas de tres horas, es cosa de manana).  Pasadas
# las nueve de la noche faltan menos de tres horas para el otro dia, asi que
# el bot prometia "vuelve en 150 min" cuando en realidad no volvia hasta el
# dia siguiente.  Se finge esa hora para que la prueba no dependa de cuando
# se corra: hasta ahora pasaba de dia y fallaba de noche, sin avisar por que.
viejo_manana = IA._segundos_hasta_manana
IA._segundos_hasta_manana = lambda: 2 * 3600
try:
    estado_noche = {}
    for c in IA.claves():
        IA._penitencia(estado_noche, c, "cupo",
                       "You exceeded your current quota, requests per day")
    corto = IA.cuando_vuelve(estado_noche)
    detalle = IA._descansando(estado_noche, IA.claves()[0])

    estado_apuro = {}
    for c in IA.claves():
        IA._penitencia(estado_apuro, c, "cupo", "too many requests, slow down")
    corto_apuro = IA.cuando_vuelve(estado_apuro)
finally:
    IA._segundos_hasta_manana = viejo_manana

ok("ma\u00f1ana" in corto,
   "a las diez de la noche sigue diciendo que el cupo vuelve manana")
ok("min" not in corto,
   "y no promete minutos que no le van a alcanzar")
ok("ma\u00f1ana" in detalle,
   "el detalle clave por clave dice lo mismo que el resumen")
ok(not sin_jerga(corto), "y lo dice sin jerga")
ok("ma\u00f1ana" not in corto_apuro,
   "pero si solo fue apuro de un minuto, no exagera diciendo 'manana'")
ok("min" in corto_apuro, "ahi si cuenta los minutos")


# ============================================ 8. la version no va a mano
titulo("8. ninguna prueba tiene el numero de version escrito a mano")

for archivo in sorted(os.listdir(CARPETA)):
    if not archivo.endswith(".py"):
        continue
    if not (archivo.startswith("_p") or archivo.startswith("_probar")):
        continue
    crudo = sin_comentarios(io.open(os.path.join(CARPETA, archivo),
                                    encoding="utf-8").read())
    escrito = ('"%s"' % VER.VERSION in crudo) or ("'%s'" % VER.VERSION in crudo)
    ok(not escrito, "%s compara contra el modulo, no contra un numero" % archivo)

ok(str(VER.VERSION).count(".") == 1, "la version tiene la forma de siempre")
ok(len(getattr(VER, "CAMBIOS", [])) > 0, "y la lista de cambios no esta vacia")


# ==================================================================== fin
print("\n" + "=" * 56)
if FALLOS:
    print("fallaron %d cosas:" % len(FALLOS))
    for f in FALLOS:
        print("  - %s" % f)
    raise SystemExit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
