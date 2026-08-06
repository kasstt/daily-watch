# -*- coding: utf-8 -*-
# Prueba suelta: reproduce lo que mostro la sonda en la plataforma B.
import os, json
os.environ.setdefault("TG_TOKEN", "x")
os.environ.setdefault("TG_CHAT", "1")
import watcher as W

ENTRAR = ('<html><head><title>Iniciar sesion en el sitio</title></head><body>'
          '<form action="/login/index.php" method="post">'
          '<input name="logintoken" value="abc123">'
          '<input name="username"><input name="password" type="password">'
          '</form></body></html>')

COLGADA = ('<html><head><title>Iniciar sesion en el sitio</title></head><body>'
           '<h4>Confirmar</h4><p>Actualmente ha iniciado sesion como Fulano,'
           ' necesita salir antes de entrar con otro usuario.</p>'
           '<a href="/login/logout.php?sesskey=ZZZ9">Cerrar sesion</a>'
           '</body></html>')

TABLERO_VACIO = ('<html><head><title>Area personal</title></head><body>'
                 '<div id="tablero"></div>'
                 '<script>M.cfg = {"sesskey":"K3Y"};</script>'
                 '<a href="/login/logout.php?sesskey=K3Y">Salir</a>'
                 '</body></html>')

TABLERO_CON_RAMOS = ('<html><head><title>Area personal</title></head><body>'
                     '<a href="/course/view.php?id=77">FISICA I</a>'
                     '<a href="/login/logout.php?sesskey=K3Y">Salir</a>'
                     '</body></html>')

RESPUESTA_INTERNA = json.dumps([{"error": False, "data": {"courses": [
    {"id": 501, "fullname": "QUIMICA GENERAL",
     "viewurl": "https://b.cl/course/view.php?id=501"},
    {"id": 502, "fullname": "CURSO NUEVO DEL PROFE",
     "viewurl": "https://b.cl/course/view.php?id=502"}]}}])


class Resp(object):
    def __init__(self, texto, url):
        self.text = texto
        self.url = url
        self.status_code = 200
        self.content = texto.encode("utf-8")

    def json(self):
        return json.loads(self.text)


class SesionFalsa(object):
    """Cada caso decide que contesta cada pagina."""

    def __init__(self, paginas, tras_entrar=None, colgada=False):
        self.paginas = paginas
        self.tras_entrar = tras_entrar or {}
        self.entro = False
        self.colgada = colgada
        self.pedidos = []
        self.cerro_sesion = False

    def _elegir(self, url):
        camino = url.split("b.cl", 1)[-1]
        # Mientras haya una sesion vieja colgada, la plataforma no deja pasar
        # a ninguna pagina de adentro.
        if self.colgada:
            return ENTRAR, camino
        tabla = self.tras_entrar if self.entro else self.paginas
        for llave, cuerpo in tabla.items():
            if camino.startswith(llave):
                return cuerpo, camino
        return ENTRAR, camino

    def get(self, url, **kw):
        self.pedidos.append(url)
        if "logout.php" in url:
            self.cerro_sesion = True
            self.colgada = False
            self.entro = False
            return Resp(ENTRAR, "https://b.cl/login/index.php")
        cuerpo, camino = self._elegir(url)
        final = url if cuerpo is not ENTRAR else "https://b.cl/login/index.php"
        return Resp(cuerpo, final)

    def post(self, url, **kw):
        self.pedidos.append(url)
        if "/lib/ajax/service.php" in url:
            return Resp(RESPUESTA_INTERNA, url)
        if "/login/index.php" in url:
            self.entro = True
            if self.colgada:
                return Resp(COLGADA, "https://b.cl/login/index.php")
            return Resp(self.paginas.get("__respuesta_entrada__", ENTRAR),
                        "https://b.cl/my/")
        return Resp(ENTRAR, url)


W.explorar_ramo = lambda s, base, g: ([], "firma")
BASE = "https://b.cl"
malas = 0


def revisar(titulo, esperado, obtenido):
    global malas
    bien = esperado == obtenido
    if not bien:
        malas += 1
    print("%-4s %s (esperaba %r, obtuve %r)"
          % ("OK" if bien else "MAL", titulo, esperado, obtenido))


# 1. Lo que pasa hoy de verdad: todo devuelve la pantalla de entrar.
s = SesionFalsa({}, tras_entrar={})
revisar("si todo es la pantalla de entrar, NO entro",
        False, W.entrar_aula(s, BASE, "u", "c"))

# 2. Sesion vieja colgada: cierra, vuelve a entrar y recien ahi pasa.
s = SesionFalsa({}, tras_entrar={"/my/": TABLERO_CON_RAMOS}, colgada=True)
revisar("con sesion colgada, cierra y entra", True,
        W.entrar_aula(s, BASE, "u", "c"))
revisar("y de verdad cerro la sesion vieja", True, s.cerro_sesion)

# 3. Entrada buena.
s = SesionFalsa({}, tras_entrar={"/my/": TABLERO_CON_RAMOS})
revisar("entrada buena", True, W.entrar_aula(s, BASE, "u", "c"))

# 4. Leer ramos cuando la pagina si los escribe.
s = SesionFalsa({}, tras_entrar={"/my/": TABLERO_CON_RAMOS})
s.entro = True
grupos, viejos = W.leer_aula(s, BASE)
revisar("lee el ramo escrito en la pagina", ["77"], [g["id"] for g in grupos])

# 5. La pagina se arma sola y no escribe ni un ramo: hay que preguntar adentro.
s = SesionFalsa({}, tras_entrar={"/my/": TABLERO_VACIO})
s.entro = True
grupos, viejos = W.leer_aula(s, BASE)
revisar("pregunta por dentro y encuentra el curso nuevo",
        ["501", "502"], [g["id"] for g in grupos])
revisar("y le pone el nombre correcto",
        "CURSO NUEVO DEL PROFE",
        ([g["nombre"] for g in grupos if g["id"] == "502"] or [""])[0])

# 6. No se pudo abrir nada: tiene que decir "no pude", nunca "cero ramos".
s = SesionFalsa({}, tras_entrar={})
s.entro = True
grupos, viejos = W.leer_aula(s, BASE)
revisar("si no pudo mirar, contesta 'no pude' y no 'cero'", None, grupos)

print("\nresultado: %s" % ("TODO BIEN" if not malas else "%d MALAS" % malas))
raise SystemExit(1 if malas else 0)
