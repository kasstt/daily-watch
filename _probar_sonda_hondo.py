# -*- coding: utf-8 -*-
# Prueba suelta: la sonda mira mas hondo y no se saltea la pagina de videochat.
# Sin internet: la pagina viene de aca adentro.
import os
os.environ.setdefault("TG_TOKEN", "x")
os.environ.setdefault("TG_CHAT", "1")

import watcher as W
import sonda as S

BASE = "https://a.cl"
ETIQUETA = "PLATAFORMA_A"
malas = []

VIDEOCHAT = u'''<html><body>
<h1>Videochat - Listado de reuniones</h1>
<table><thead><tr><th>N\u00b0</th><th>Hora inicio</th><th>Duraci\u00f3n (min)</th>
<th>Tema</th><th>Anfitri\u00f3n</th><th>Clave</th><th>Acciones</th></tr></thead>
<tbody><tr>
<td>1</td><td>05-08-2026 12:40:00</td><td>60</td>
<td>Clase 05 de agosto - Taller empr</td><td>\u00f3scar Guti\u00e9rrez</td>
<td>123456</td><td><a href="/curso/meeting/entrar/9999">Iniciar</a></td>
</tr></tbody></table></body></html>'''

SECCION = u'''<html><body><div class="contenido">
<a href="/curso/9999/material/Semana1.pdf">Semana 1</a>
<a href="/curso/9999/tema/2">Tema 2</a>
<a href="/salir">Cerrar sesi\u00f3n</a>
</div></body></html>'''


def revisar(titulo, condicion, detalle=""):
    if not condicion:
        malas.append(titulo)
    print("%-4s %s%s" % ("OK" if condicion else "MAL", titulo,
                         "" if condicion else "  <- " + str(detalle)))


class Resp(object):
    """Sirve para las dos formas de mirar: la de la sonda y la del bot."""

    def __init__(self, texto, url):
        self.text = texto
        self.url = url
        self.status_code = 200
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.content = texto.encode("utf-8")


class SesionFalsa(object):
    def __init__(self, paginas):
        self.paginas = paginas
        self.pedidos = []

    def get(self, url, **kw):
        self.pedidos.append(url)
        for pedazo, html in self.paginas.items():
            if pedazo in url:
                return Resp(html, url)
        return Resp(u"<html><body>nada</body></html>", url)


def limpiar():
    del S.LINEAS[:]
    del S.TAPAR[:]
    del S.PALABRAS_TAPADAS[:]
    S._PATRONES.clear()


def informe():
    return "\n".join(S.LINEAS)


# ============================ 1. lo que no se abre ni por casualidad
for malo in ("https://a.cl/salir", "https://a.cl/logout.php",
             "https://a.cl/curso/9999/crear_modulo",
             "https://a.cl/curso/borrar/12", "https://a.cl/tarea/enviar/3"):
    revisar("no abre %s" % malo.replace(BASE, ""), S.peligroso(malo), malo)

for bueno in ("https://a.cl/curso/9999", "https://a.cl/curso/meeting/show/9999",
              "https://a.cl/curso/9999/calendario",
              "https://a.cl/mod/resource/view.php?id=3"):
    revisar("s\u00ed abre %s" % bueno.replace(BASE, ""), not S.peligroso(bueno), bueno)

# ============================ 2. abrir una seccion y ver lo que cuelga
limpiar()
s = SesionFalsa({"/curso/9999/tema/1": SECCION})
vistos = set()
nuevos, bajables = S.mirar_de_paso(W, s, BASE, BASE + "/curso/9999/tema/1",
                                   ETIQUETA, vistos)
revisar("encuentra los enlaces de adentro", len(nuevos) == 3, nuevos)
revisar("y reconoce cu\u00e1l se puede bajar",
        len(bajables) == 1 and "Semana1.pdf" in bajables[0], bajables)
revisar("y lo deja escrito en el informe",
        "Semana1.pdf" in informe(), informe()[-200:])
revisar("y tapa la direcci\u00f3n de la plataforma",
        "a.cl" not in informe(), informe()[:200])

# ================= 3. la pagina de videochat, leida como la lee el bot
limpiar()
s = SesionFalsa({"/curso/meeting/show/9999": VIDEOCHAT})
S.mirar_reuniones_de(W, s, BASE, [BASE + "/curso/meeting/show/9999"], ETIQUETA)
salida = informe()
revisar("la sonda ahora abre la p\u00e1gina de videochat",
        any("/meeting/show/9999" in p for p in s.pedidos), s.pedidos)
revisar("y dice que el bot ve la reuni\u00f3n",
        "el bot ve 1 reunion" in salida, salida)
revisar("con la fecha y hora de verdad",
        "05-08-2026 12:40" in salida, salida)
revisar("y con la duraci\u00f3n", "60 min" in salida, salida)
revisar("la clave de la reuni\u00f3n NO se escribe en el informe",
        "123456" not in salida, salida)
revisar("pero avisa que la reuni\u00f3n tiene clave", "clave: si" in salida, salida)
revisar("y tambi\u00e9n vuelca c\u00f3mo est\u00e1 armada la p\u00e1gina",
        "como esta armada" in salida, salida)

# ================= 4. si el bot NO puede leerla, la sonda lo grita
limpiar()


class SesionRota(SesionFalsa):
    def get(self, url, **kw):
        self.pedidos.append(url)
        if "/meeting/show/" in url:
            raise IOError("sin red")
        return Resp(u"<html></html>", url)


s = SesionRota({})
S.mirar_reuniones_de(W, s, BASE, [BASE + "/curso/meeting/show/9999"], ETIQUETA)
revisar("si el bot no puede leerla, queda avisado",
        "NO PUDO LEER" in informe() or "reviento" in informe(), informe())

# ================= 5. un ramo sin videochat no inventa nada
limpiar()
S.mirar_reuniones_de(W, SesionFalsa({}), BASE, [], ETIQUETA)
revisar("sin videochat, lo dice y sigue",
        "no tiene pagina de videochat" in informe(), informe())

print("\nresultado: %s" % ("TODO BIEN" if not malas else "%d MALAS" % len(malas)))
raise SystemExit(1 if malas else 0)
