# -*- coding: utf-8 -*-
# Prueba suelta: la pagina de videoconferencias, tal como viene en la realidad.
import os
import datetime as dt
os.environ.setdefault("TG_TOKEN", "x")
os.environ.setdefault("TG_CHAT", "1")
import watcher as W
import notificar as N

PAGINA = u'''<html><body>
<h1>Videochat - Listado de reuniones</h1>
<table><thead><tr><th>N\u00b0</th><th>Hora inicio</th><th>Duraci\u00f3n (min)</th>
<th>Tema</th><th>Anfitri\u00f3n</th><th>Clave</th><th>Acciones</th></tr></thead>
<tbody><tr>
<td>1</td><td>05-08-2026 12:40:00</td><td>60</td>
<td>Clase 05 de agosto - Taller empr</td><td>\u00f3scar Guti\u00e9rrez</td>
<td>123456</td><td><a href="/curso/meeting/entrar/9999">Iniciar</a></td>
</tr></tbody></table></body></html>'''

BASE = "https://a.cl"
malas = []
mandados = []


def revisar(titulo, condicion, detalle=""):
    if not condicion:
        malas.append(titulo)
    print("%-4s %s%s" % ("OK" if condicion else "MAL", titulo,
                         "" if condicion else "  <- " + str(detalle)))


class Resp(object):
    def __init__(self, texto, url):
        self.text = texto
        self.url = url


class SesionFalsa(object):
    def __init__(self, html=PAGINA, revienta=False):
        self.html = html
        self.revienta = revienta
        self.pedidos = []

    def get(self, url, **kw):
        self.pedidos.append(url)
        if self.revienta:
            raise IOError("sin red")
        return Resp(self.html, url)


def enviar_falso(texto, silencioso=False, botones=None, teclado_fijo=False):
    mandados.append(texto)
    return 100 + len(mandados)


def enviar_roto(texto, silencioso=False, botones=None, teclado_fijo=False):
    mandados.append(texto)
    return None


def reloj(cuando):
    W.ahora = lambda: cuando


def vigilante():
    """Un vigilante pelado, sin memoria en disco ni red."""
    v = object.__new__(W.Vigilante)
    v.estado = {}
    v.guardar = lambda: None
    v.nombre_de = lambda clave: "TALLER DE PRUEBA"
    v.en_silencio = lambda: False
    return v


ZONA = W.ZONA


def momento(anio, mes, dia, hh, mm):
    f = dt.datetime(anio, mes, dia, hh, mm)
    return f.replace(tzinfo=ZONA) if ZONA else f


N.enviar = enviar_falso
RAMO = {"id": "9999", "nombre": "TALLER DE PRUEBA"}

# ---------------------------------------------------------------- 1. leer
filas = W.reuniones_b64(SesionFalsa(), BASE, "9999")
revisar("encuentra la reuni\u00f3n de la p\u00e1gina", filas and len(filas) == 1, filas)
if filas:
    r = filas[0]
    revisar("con la hora exacta", r["cuando"].strftime("%Y-%m-%d %H:%M") == "2026-08-05 12:40",
            r["cuando"])
    revisar("con la duraci\u00f3n", r["minutos"] == 60, r["minutos"])
    revisar("con el tema", r["tema"].startswith("Clase 05 de agosto"), r["tema"])
    revisar("con la clave de entrada", r["llave"] == "123456", r["llave"])
    revisar("con el bot\u00f3n de entrar", r["enlace"].endswith("/curso/meeting/entrar/9999"),
            r["enlace"])

# --------------------------------------------- 2. si no se puede mirar, None
revisar("si no puede abrir la p\u00e1gina dice 'no pude', no 'no hay'",
        W.reuniones_b64(SesionFalsa(revienta=True), BASE, "9999") is None)

# ------------------------------------------------------- 3. avisa al aparecer
reloj(momento(2026, 8, 5, 10, 0))
v = vigilante()
del mandados[:]
cuantas = v.mirar_reuniones("r1", RAMO, SesionFalsa(), BASE)
revisar("avisa la clase apenas la ve", cuantas == 1, cuantas)
revisar("y el aviso trae la clave", mandados and "123456" in mandados[0])
revisar("y trae la hora en cristiano", mandados and "12:40" in mandados[0], mandados[:1])
revisar("y dice que va a recordarlo antes",
        mandados and "10 minutos antes" in mandados[0], mandados[:1])

# ------------------------------------------------------- 4. no repite el aviso
del mandados[:]
revisar("no vuelve a avisar la misma clase",
        v.mirar_reuniones("r1", RAMO, SesionFalsa(), BASE) == 0)
revisar("y no manda nada", not mandados, mandados)

# ------------------------------- 5. si el mensaje no sale, no la da por avisada
N.enviar = enviar_roto
v2 = vigilante()
del mandados[:]
v2.mirar_reuniones("r1", RAMO, SesionFalsa(), BASE)
quedo = list(v2.estado.get("reuniones", {}).values())
revisar("si el mensaje no sale, la clase NO queda marcada", not quedo, quedo)
N.enviar = enviar_falso

# ------------------------------------------------ 6. el recordatorio, a tiempo
reloj(momento(2026, 8, 5, 12, 10))
del mandados[:]
revisar("media hora antes todav\u00eda no recuerda", v.recordar_reuniones() == 0)

reloj(momento(2026, 8, 5, 12, 31))
del mandados[:]
revisar("nueve minutos antes s\u00ed recuerda", v.recordar_reuniones() == 1)
revisar("y el recordatorio trae la clave",
        mandados and "123456" in mandados[0], mandados[:1])
del mandados[:]
revisar("y no recuerda dos veces", v.recordar_reuniones() == 0)

# ------------------------------------------- 7. una clase terminada no molesta
reloj(momento(2026, 8, 6, 9, 0))
v3 = vigilante()
del mandados[:]
revisar("la clase de ayer no se avisa",
        v3.mirar_reuniones("r1", RAMO, SesionFalsa(), BASE) == 0)
revisar("y no manda nada", not mandados, mandados)

# ------------------------------------ 8. la memoria no crece para siempre
reloj(momento(2026, 8, 9, 9, 0))
v.recordar_reuniones()
revisar("lo viejo se borra solo de la memoria",
        not v.estado.get("reuniones"), v.estado.get("reuniones"))

print("\nresultado: %s" % ("TODO BIEN" if not malas else "%d MALAS" % len(malas)))
raise SystemExit(1 if malas else 0)
