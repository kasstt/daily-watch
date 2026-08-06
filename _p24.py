# -*- coding: utf-8 -*-
"""Tanda 24: lo que pediste en la quinta vuelta, probado uno por uno.

Cada prueba de aca nace de algo que te paso o que pediste:
  - el bot decia "la ayuda no esta disponible" y despues contestaba igual
  - querias apagarlo y prenderlo desde el chat, y que nadie mas pueda
  - buscabas un archivo por su nombre y te contestaba cualquier cosa
  - la sonda dejo tu nombre completo escrito en el informe
  - la sonda pasaba de largo por la pagina de videochat del profe
  - el profe subio una clase por video y el bot no te aviso

Se corre sola, sin internet, sin claves de verdad y sin tocar tu cuenta:
    python3 _p24.py
"""
import os
import subprocess
import sys

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("IA_KEY", "AIzaDePrueba1")
os.environ.setdefault("IA_KEY_2", "AIzaDePrueba2")

import fuentes as CFG
import ia as IA
import notificar as N
import panel as P
import sonda as SO
import version as VER
import watcher as W

FALLOS = []
CARPETA = os.path.dirname(os.path.abspath(__file__)) or "."


def ok(cond, que):
    if cond:
        print("  ok   %s" % que)
    else:
        print("  MAL  %s" % que)
        FALLOS.append(que)


def titulo(t):
    print("\n" + t)
    print("-" * 50)


def filas_de(teclado):
    return (teclado or {}).get("inline_keyboard", [])


mandados = []


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    mandados.append((texto, botones))
    return 100 + len(mandados)


N.enviar = _enviar
N.avisar_boton = lambda ident, texto="": None


class Resp(object):
    """Una respuesta de mentira que sirve para las dos formas de mirar."""

    def __init__(self, texto, url, codigo=200):
        self.text = texto
        self.url = url
        self.status_code = codigo
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.content = texto.encode("utf-8")

    def json(self):
        import json
        return json.loads(self.text)


class Sesion(object):
    def __init__(self, paginas=None, html=u"<html></html>"):
        self.paginas = paginas or {}
        self.html = html
        self.pedidos = []
        self.cookies = {}

    def _elegir(self, url):
        for pedazo, cuerpo in self.paginas.items():
            if pedazo in url:
                return cuerpo
        return self.html

    def get(self, url, **kw):
        self.pedidos.append(url)
        return Resp(self._elegir(url), url)

    def post(self, url, **kw):
        self.pedidos.append(url)
        return Resp(self._elegir(url), url)


# ==================================================================== 1
titulo("1. la ayuda escrita dice siempre lo mismo")

_respuestas = []


def _motor(texto, pdfs, c=None):
    _respuestas.append(texto)
    return "Listo, ya lo mire."


for _n in list(IA.PROVEEDORES):
    IA.PROVEEDORES[_n] = _motor

encendida = {"config": {"ia": True}}
ok(IA.en_palabras(encendida) == "encendida",
   "con todo bien te dice que esta encendida")
ok(IA.se_puede_intentar(encendida) is True, "y ahi si la intenta usar")

apagada = {"config": {"ia": False}}
ok(IA.en_palabras(apagada) == "apagada por vos",
   "si vos la apagaste, te lo dice asi")
ok(IA.se_puede_intentar(apagada) is False, "y no la intenta a escondidas")

dormida = {"config": {"ia": True}}
for c in IA.claves():
    IA._penitencia(dormida, c, "cupo", "quota")
ok(IA.en_palabras(dormida) != "encendida",
   "si se quedo sin cupo, no dice que esta encendida")
ok(IA.disponible(dormida) is False,
   "y el trabajo de fondo no insiste al pedo")
ok(IA.se_puede_intentar(dormida) is True,
   "pero la puerta para vos sigue abierta")
ok(bool(IA.preguntar(dormida, "hola", "libreta de prueba")),
   "pero si vos le hablas, igual te contesta")


# ==================================================================== 2
titulo("2. el boton para reiniciarlo desde el chat")


def vigilante(guardar_revienta=False):
    v = object.__new__(W.Vigilante)
    v.estado = {"novedades": [{"t": "algo"}], "grupos": {"r1": {}}}
    v.guardado = []

    def guardar():
        if guardar_revienta:
            raise IOError("el gist no contesta")
        v.guardado.append(dict(v.estado))
    v.guardar = guardar
    return v


v = vigilante()
del mandados[:]
v.preguntar_si_reinicio()
ok(len(mandados) == 1, "antes de apagarse te pregunta")
ok(getattr(v, "reiniciar_pedido", False) is False, "y todavia no se apaga")

del mandados[:]
v.reiniciarme()
ok(len(v.guardado) == 1, "al confirmar guarda la memoria ANTES de apagarse")
ok(v.reiniciar_pedido is True, "y recien ahi pide el corte")
ok(v.estado.get("novedades") and v.estado.get("grupos"),
   "la memoria queda entera, no se borra nada")

v2 = vigilante(guardar_revienta=True)
del mandados[:]
v2.reiniciarme()
ok(getattr(v2, "reiniciar_pedido", False) is False,
   "si no puede guardar, NO se apaga")
ok(mandados and "No pude guardar" in mandados[0][0],
   "y te lo dice en vez de callarse")

acc = {"texto_diagnostico": lambda: "todo en orden"}
_t, teclado = P.pantalla({}, "p:diag", acc)
filas = filas_de(teclado)
fila = [f for f in filas
        if any(b.get("callback_data") == "a:reiniciar" for b in f)]
ok(len(fila) == 1, "el boton vive en Diagnostico")
ok(fila and len(fila[0]) == 1, "y va solo, lejos de cualquier otro boton")
ok(len(filas) <= 6, "y esa pantalla sigue sin pasarse de 6 filas")


# ==================================================================== 3
titulo("3. la sonda ya no deja escapar tu nombre")

NOMBRE = "Juan Andr\u00e9s Miranda Fuentes"
GRITADO = "JUAN ANDR\u00c9S MIRANDA FUENTES"


def sonda_limpia():
    del SO.TAPAR[:]
    del SO.PALABRAS_TAPADAS[:]
    del SO.LINEAS[:]
    SO._PATRONES.clear()


sonda_limpia()
SO.guardar_secreto(NOMBRE, "TU_NOMBRE")
salida = SO.tapar("ha iniciado sesion como %s, necesita salir" % GRITADO)
ok("MIRANDA" not in salida.upper(), "aunque este todo en mayusculas, lo tapa")

sonda_limpia()
SO.guardar_secreto("Oscar Gutierrez", "UN_PROFE")
ok("scar" not in SO.tapar("\u00f3scar Guti\u00e9rrez"),
   "y aunque le cambien las tildes, tambien")

sonda_limpia()
SO.SALIDA = os.path.join(CARPETA, "_sonda_de_prueba.txt")
SO.escribir("pagina 2: %s" % GRITADO)          # todavia no sabe tu nombre
SO.aprender_nombre("ha iniciado sesion como %s, necesita salir" % GRITADO)
SO.volcar()
escrito = open(SO.SALIDA, encoding="utf-8").read()
ok("MIRANDA" not in escrito.upper(),
   "lo escrito antes de aprenderlo tambien queda tapado")
try:
    os.remove(SO.SALIDA)
except OSError:
    pass
SO.SALIDA = "sonda.txt"

sonda_limpia()
SO.guardar_secreto(NOMBRE, "TU_NOMBRE")
util = SO.tapar("TALLER DE PRUEBA 05-08-2026 12:40")
ok("TALLER DE PRUEBA" in util and "12:40" in util,
   "y lo que si tiene que verse se sigue viendo")


# ==================================================================== 4
titulo("4. la sonda mira mas hondo y no rompe nada")

for malo in ("https://a.cl/salir", "https://a.cl/logout.php",
             "https://a.cl/curso/9999/crear_modulo",
             "https://a.cl/tarea/enviar/3"):
    ok(SO.peligroso(malo), "no abre %s" % malo.split("/", 3)[-1])
for bueno in ("https://a.cl/curso/9999/calendario",
              "https://a.cl/curso/meeting/show/9999",
              "https://a.cl/mod/resource/view.php?id=3"):
    ok(not SO.peligroso(bueno), "si abre %s" % bueno.split("/", 3)[-1])

SECCION = (u'<html><body><a href="/curso/98/material/Semana1.pdf">S1</a>'
           u'<a href="/curso/98/tema/2">Tema 2</a></body></html>')
sonda_limpia()
s = Sesion({"/curso/98/tema/1": SECCION})
nuevos, bajables = SO.mirar_de_paso(W, s, "https://a.cl",
                                    "https://a.cl/curso/98/tema/1",
                                    "PLATAFORMA_A", set())
ok(len(nuevos) == 2, "entra a una seccion y ve lo que cuelga de adentro")
ok(len(bajables) == 1, "y sabe cual de esos se puede bajar")
ok("a.cl" not in "\n".join(SO.LINEAS), "sin escribir la direccion de nadie")


# ==================================================================== 5
titulo("5. las clases por videoconferencia")

VIDEOCHAT = (u'<html><body><table><tbody><tr>'
             u'<td>1</td><td>05-08-2026 12:40:00</td><td>60</td>'
             u'<td>Clase 05 de agosto</td><td>\u00f3scar Guti\u00e9rrez</td>'
             u'<td>123456</td>'
             u'<td><a href="/curso/meeting/entrar/98">Iniciar</a></td>'
             u'</tr></tbody></table></body></html>')

sonda_limpia()
s = Sesion({"/curso/meeting/show/98": VIDEOCHAT})
SO.mirar_reuniones_de(W, s, "https://a.cl",
                      ["https://a.cl/curso/meeting/show/98"], "PLATAFORMA_A")
informe = "\n".join(SO.LINEAS)
ok(any("/meeting/show/98" in p for p in s.pedidos),
   "la sonda ahora si abre la pagina de videochat")
ok("el bot ve 1 reunion" in informe, "y confirma que el bot ve la reunion")
ok("05-08-2026 12:40" in informe, "con la fecha y la hora de verdad")
ok("123456" not in informe, "la clave de la reunion NO queda escrita")
ok("Guti" not in informe, "y el nombre del profe tampoco")

reuniones = W.reuniones_b64(Sesion({"meeting": VIDEOCHAT}), "https://a.cl", "98")
ok(reuniones and len(reuniones) == 1, "el bot lee la tabla del profe")
r = (reuniones or [{}])[0]
ok(r.get("minutos") == 60, "y sabe cuanto dura")
ok(bool(r.get("llave")), "y que tiene clave para entrar")
ok(isinstance(getattr(CFG, "MINUTOS_ANTES_DE_LA_CLASE", None), int),
   "esta puesto cuantos minutos antes te avisa")
ok(getattr(CFG, "MINUTOS_ANTES_DE_LA_CLASE", 0) > 0,
   "y ese aviso previo esta prendido")


# ==================================================================== 6
titulo("6. la plataforma B no se queda muda")

ENTRAR = (u'<html><head><title>Iniciar sesion en el sitio</title></head>'
          u'<body><form action="/login/index.php">'
          u'<input name="logintoken" value="abc"></form></body></html>')
_ramos_b, _avisos_b = W.leer_aula(Sesion(html=ENTRAR), "https://b.cl")
ok(_ramos_b is None,
   "si la plataforma lo devuelve a la puerta, avisa que no pudo mirar")
ok(W._pantalla_de_entrar(ENTRAR) is True, "reconoce la pantalla de entrar")


# ==================================================================== 7
titulo("7. la version y lo que le contas al duenio")

ok(bool(VER.VERSION) and VER.VERSION[0].isdigit(),
   "el numero de version sale del archivo de version, no de aca")
_t, _b = P.pantalla({}, "p:version", {"texto_version": VER.etiqueta})
ok(VER.VERSION in _t, "y es el mismo que se ve en el chat")
ok(len(VER.CAMBIOS) >= 5, "la lista de cambios cuenta varias cosas")
todos = " ".join(str(x) for x in VER.CAMBIOS).lower()
for jerga in ("json", "callback", "except", "quota", "api", "token",
              "commit", "workflow", "http", "cache", "regex", "traceback"):
    ok(jerga not in todos, "la lista de cambios no dice '%s'" % jerga)
ok("reinici" in todos, "le contas del boton para reiniciarlo")
ok("video" in todos, "y de las clases por videoconferencia")


# ==================================================================== 8
titulo("8. las pruebas sueltas de esta vuelta siguen en verde")

for prueba in ("_probar_aula.py", "_probar_nombre.py", "_probar_video.py",
               "_probar_ia_coherente.py", "_probar_reinicio.py",
               "_probar_mensaje_vacio.py", "_probar_sonda_tapado.py",
               "_probar_sonda_hondo.py"):
    ruta = os.path.join(CARPETA, prueba)
    if not os.path.exists(ruta):
        ok(False, "falta la prueba %s" % prueba)
        continue
    r = subprocess.run([sys.executable, ruta], cwd=CARPETA,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    ok(r.returncode == 0, "%s pasa entera" % prueba)


# ==================================================================== fin
print("\n" + "=" * 50)
if FALLOS:
    print("fallaron %d cosas:" % len(FALLOS))
    for f in FALLOS:
        print("  - %s" % f)
    raise SystemExit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
