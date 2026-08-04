# -*- coding: utf-8 -*-
"""Clases por videoconferencia.

Son pocas veces al semestre, pero son las que no se pueden perder: si el
profesor avisa por la plataforma que la clase de manana es por video y vos
no entraste ese dia, perdiste la clase entera.

Las dos plataformas avisan distinto.  La plataforma A lo suele poner como
un aviso o como un enlace suelto dentro del ramo.  La plataforma B lo pone
como una actividad de sala virtual.  Aca no se distingue: se busca el
enlace de la reunion venga de donde venga, y si aparece, se avisa fuerte.

Este archivo no toca internet ni la memoria.  Son funciones puras, para
que se puedan probar sin plataforma y sin claves.
"""
import re

# ------------------------------------------------------------- las salas
# clave -> (como se muestra, lista de pedazos que aparecen en la direccion)
SALAS = [
    ("meet", "Meet", ("meet.google.com",)),
    ("zoom", "Zoom", ("zoom.us/j/", "zoom.us/my/", "zoom.us/s/", "zoom.us/w/",
                      ".zoom.us/j/", "zoom.com/j/")),
    ("teams", "Teams", ("teams.microsoft.com/l/meetup-join",
                        "teams.microsoft.com/l/meeting",
                        "teams.live.com/meet", "teams.microsoft.us/l/meetup-join")),
    ("meet_viejo", "Meet", ("hangouts.google.com/call",)),
    ("webex", "Webex", ("webex.com/meet", "webex.com/j.php", ".webex.com/")),
    ("jitsi", "Jitsi", ("meet.jit.si", "jitsi.")),
    ("bbb", "Sala virtual", ("/bigbluebutton/", "bbb.", "/b/", "greenlight")),
    ("aula_sala", "Sala virtual", ("mod/bigbluebuttonbn", "mod/zoom",
                                   "mod/collaborate", "mod/teamsmeeting",
                                   "mod/webexactivity", "mod/jitsi",
                                   "mod/msteams", "mod/virtualclass")),
    ("skype", "Skype", ("join.skype.com",)),
    ("whereby", "Whereby", ("whereby.com/",)),
    ("gotomeet", "GoToMeeting", ("gotomeet.me", "gotomeeting.com/join")),
    ("bluejeans", "BlueJeans", ("bluejeans.com/",)),
    ("chime", "Chime", ("chime.aws/",)),
    ("discord", "Discord", ("discord.gg/", "discord.com/invite")),
]

# Una direccion suelta escrita en el texto del aviso, sin ser un enlace.
RE_URL_EN_TEXTO = re.compile(r"(?:https?://|www\.)[^\s<>\"')\]]{4,300}", re.I)

# Palabras que, sin enlace, igual delatan que la clase es por video.  Sirven
# para el segundo caso: el profesor avisa hoy y recien manda el enlace
# despues.  Ese aviso tambien vale.
PALABRAS_CLASE = [
    "videoconferencia", "video conferencia", "videollamada", "video llamada",
    "clase online", "clase on line", "clase en linea", "clase virtual",
    "clase remota", "clase por video", "clase sincronica", "catedra online",
    "sala virtual", "sala de reunion", "reunion virtual", "link de la clase",
    "enlace de la clase", "enlace de la reunion", "link de la reunion",
    "nos conectamos", "nos vemos por", "sesion virtual", "sesion online",
    "transmision en vivo", "clase por meet", "clase por zoom",
    "clase por teams", "por videoconferencia", "modalidad online",
    "modalidad remota", "modalidad virtual", "telematica",
]

# Palabras que dicen que la clase NO va: tambien hay que avisarlas, porque
# ir al aula al pedo es igual de caro que perderse la clase.
PALABRAS_SUSPENSION = [
    "se suspende", "suspendida", "suspension de clases", "sin clases",
    "no habra clase", "no hay clase", "queda sin efecto", "se reprograma",
    "cambio de sala", "cambio de horario", "cambio de fecha",
]

# Como se ve en el chat.
EMOJI = "\U0001F3A5"           # camarita
EMOJI_SUSPENSION = "\u26A0\uFE0F"


def _sin_tildes(t):
    reemplazos = (("\u00e1", "a"), ("\u00e9", "e"), ("\u00ed", "i"),
                  ("\u00f3", "o"), ("\u00fa", "u"), ("\u00fc", "u"),
                  ("\u00f1", "n"), ("\u00c1", "a"), ("\u00c9", "e"),
                  ("\u00cd", "i"), ("\u00d3", "o"), ("\u00da", "u"),
                  ("\u00d1", "n"))
    t = str(t or "").lower()
    for de, a in reemplazos:
        t = t.replace(de, a)
    return " ".join(t.split())


def marca_de(url):
    """De una direccion saca como se llama la sala.  Vacio si no es una."""
    bajo = str(url or "").lower()
    if not bajo:
        return ""
    for _clave, nombre, pedazos in SALAS:
        for p in pedazos:
            if p in bajo:
                # "/b/" es muy corto y engancha cualquier cosa, asi que solo
                # vale si ademas la direccion habla de una sala.
                if p == "/b/" and not any(x in bajo for x in
                                          ("bbb", "bigbluebutton", "greenlight")):
                    continue
                return nombre
    return ""


def es_sala(url):
    return bool(marca_de(url))


def enlaces_de_video(*textos):
    """Todas las direcciones de sala que aparecen escritas en estos textos.
    Sin repetir y en el orden en que se leen."""
    salida, vistos = [], set()
    for t in textos:
        for cruda in RE_URL_EN_TEXTO.findall(str(t or "")):
            u = cruda.rstrip(".,;:)\u00bb\"'")
            if not u.lower().startswith("http"):
                u = "https://" + u
            if not es_sala(u) or u in vistos:
                continue
            vistos.add(u)
            salida.append(u)
    return salida


def habla_de_clase(*textos):
    """True si el texto dice que hay clase por video aunque no haya enlace."""
    bolsa = _sin_tildes(" ".join(str(t or "") for t in textos))
    return any(p in bolsa for p in PALABRAS_CLASE)


def habla_de_suspension(*textos):
    bolsa = _sin_tildes(" ".join(str(t or "") for t in textos))
    return any(p in bolsa for p in PALABRAS_SUSPENSION)


def detectar(titulo="", url="", descripcion=""):
    """Mira una cosa encontrada en la plataforma y decide si es una clase.

    Devuelve None si no tiene nada que ver, o una ficha:
        {"clase": True, "sala": "Meet", "enlace": "...", "enlaces": [...],
         "suspension": False, "seguro": True}

    "seguro" es True cuando hay un enlace de sala de verdad.  Cuando solo
    hay palabras, es False: se avisa igual, pero mas flojito, porque puede
    ser el profesor hablando de la clase pasada.
    """
    titulo = str(titulo or "")
    url = str(url or "")
    descripcion = str(descripcion or "")

    enlaces = enlaces_de_video(url, titulo, descripcion)
    # La direccion propia de la actividad tambien cuenta, aunque no aparezca
    # escrita adentro del texto.
    if es_sala(url) and url not in enlaces:
        enlaces.insert(0, url)

    suspendida = habla_de_suspension(titulo, descripcion)
    palabras = habla_de_clase(titulo, descripcion)

    if not enlaces and not palabras and not suspendida:
        return None
    if suspendida and not enlaces and not palabras:
        # Una suspension a secas igual se avisa, pero no es una clase.
        return {"clase": False, "sala": "", "enlace": "", "enlaces": [],
                "suspension": True, "seguro": True}

    sala = ""
    for e in enlaces:
        sala = marca_de(e)
        if sala:
            break
    return {"clase": True, "sala": sala or "videoconferencia",
            "enlace": enlaces[0] if enlaces else "",
            "enlaces": enlaces, "suspension": suspendida,
            "seguro": bool(enlaces)}


def prioritaria(ficha):
    """Una clase con enlace se avisa siempre, aunque el ramo este callado y
    aunque sea de madrugada.  Perderse una clase no se arregla despues."""
    if not ficha:
        return False
    return bool(ficha.get("seguro")) and (ficha.get("clase") or ficha.get("suspension"))


def titulo_del_aviso(ficha):
    if not ficha:
        return ""
    if ficha.get("suspension") and not ficha.get("clase"):
        return "%s <b>Aviso del profesor</b>" % EMOJI_SUSPENSION
    if ficha.get("suspension"):
        return "%s <b>Cambio en la clase por video</b>" % EMOJI_SUSPENSION
    return "%s <b>Clase por %s</b>" % (EMOJI, ficha.get("sala") or "video")


def lineas_del_aviso(ficha, ramo="", titulo="", cuando="", escapar=None,
                     enlace=None):
    """Las lineas del aviso, ya listas para mandar.

    escapar y enlace son las funciones del modulo de mensajeria.  Se pasan
    de afuera para que este archivo se pueda probar solo.
    """
    esc = escapar or (lambda t: str(t or ""))
    lin = enlace or (lambda t, u: "%s (%s)" % (t, u))

    salida = [titulo_del_aviso(ficha)]
    if ramo:
        salida.append("Ramo: <b>%s</b>" % esc(ramo))
    if titulo:
        salida.append(esc(titulo))
    if cuando:
        salida.append("\U0001F550 %s" % esc(cuando))
    for i, u in enumerate(ficha.get("enlaces", [])[:3]):
        etiqueta = "Entrar a %s" % (marca_de(u) or "la sala")
        if i:
            etiqueta += " (%d)" % (i + 1)
        salida.append("\U0001F517 " + lin(etiqueta, u))
    if not ficha.get("seguro"):
        salida.append("<i>Lo le\u00ed del texto del profesor, todav\u00eda no hay "
                      "enlace publicado.</i>")
    if ficha.get("suspension"):
        salida.append("<i>Ojo que el mensaje habla de suspender, reprogramar "
                      "o cambiar algo. Le\u00e9lo entero antes de moverte.</i>")
    return salida
