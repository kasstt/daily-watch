# -*- coding: utf-8 -*-
"""Los avisos escritos que publica el profesor.

Esto resuelve el agujero mas grande que tenia el bot: hasta ahora solo miraba
ENLACES.  Un aviso del profesor no es un enlace, es texto pelado dentro de un
tablero que dice "Avisos".  Por eso se perdian cosas como

    "la universidad tomo la decision de clases online los dias 3 y 4"

que es justo la clase de informacion que no se puede perder.

Este modulo NO toca la red, NO toca la memoria y NO importa nada del bot.
Solo recibe el html de una pagina y devuelve fichas.  Asi se puede probar
entero en seco.
"""
import hashlib
import re
import unicodedata

try:
    from bs4 import BeautifulSoup
except Exception:                                   # pragma: no cover
    BeautifulSoup = None


# ------------------------------------------------------------------ palabras
# Como se llama el tablero de avisos en las dos plataformas y en sus temas
# visuales.  Se compara sin tildes y en minusculas.
TITULOS_DE_TABLERO = (
    "avisos", "aviso", "anuncios", "anuncio", "novedades", "noticias",
    "comunicados", "comunicado", "informaciones", "informacion importante",
    "tablon de anuncios", "tablero de avisos", "cartelera", "mensajes",
    "anuncios recientes", "avisos recientes", "ultimas noticias",
    "foro de novedades", "novedades del curso", "anuncios del curso",
)

# Clases y identificadores que usan las plataformas para el mismo cajon.
SELECTORES = (
    "[class*='aviso']", "[id*='aviso']",
    "[class*='anuncio']", "[id*='anuncio']",
    "[class*='novedad']", "[id*='novedad']",
    "[class*='news']", "[id*='news']",
    "[class*='announce']", "[id*='announce']",
    "[class*='comunicado']",
    ".block_news_items", ".forumpost", ".post-content-container",
)

# Un aviso con estas palabras cambia tu semana.  Estos suenan y no esperan.
# Los avisos tienen DOS niveles, y la diferencia importa de verdad.
#
# Antes habia una lista sola, y adentro estaban "prueba", "entrega",
# "control", "plazo" y "asistencia".  Esas palabras aparecen en casi todos
# los avisos de la facultad, asi que practicamente TODO salia urgente y todo
# iba a sonar a las 3 de la manana.  Un despertador que suena siempre se
# apaga, y el dia que se apaga te perdes la suspension de verdad.
#
# NIVEL 1 (urgente): te cambia el dia. Donde o cuando es la clase, o si hay
# clase. Esto rompe el silencio y suena de noche.
PALABRAS_URGENTES = (
    "se suspende", "suspension", "suspendida", "suspendido", "suspenden",
    "se cancela", "cancelada", "cancelado", "cancelacion", "cancelan",
    "no habra clases", "no hay clases", "sin clases", "no se dictara",
    "no se realizara", "queda sin efecto",
    "se posterga", "postergada", "postergado", "postergacion",
    "se aplaza", "aplazada", "aplazado", "se reprograma", "reprogramada",
    "reprogramado", "cambio de fecha", "se cambio la fecha", "nueva fecha",
    "se adelanta",
    "clases online", "clase online", "modalidad online", "modalidad remota",
    "videoconferencia", "por meet", "por zoom", "clase virtual",
    "paro", "toma", "feriado", "suspende actividades",
    "emergencia", "alerta",
    "cambio de sala", "cambio de horario", "nuevo horario", "cambio de sede",
)

# NIVEL 2 (importante): habla de fechas o de notas, pero no cambia nada de
# golpe. Te lo marco y lo pongo arriba, pero NO te despierto por esto.
# Se puede cambiar con IMPORTANTES_SUENAN_DE_NOCHE en fuentes.py.
PALABRAS_IMPORTANTES = (
    "certamen", "prueba", "evaluacion", "examen", "control", "solemne",
    "interrogacion", "disertacion", "presentacion",
    "plazo", "entrega", "ultimo dia", "fecha limite", "vence",
    "obligatorio", "obligatoria", "asistencia",
    "inscripcion", "nota", "calificacion",
)

# Texto de adorno que aparece en todos los tableros y no es un aviso.
RUIDO = (
    "agregar aviso", "nuevo aviso", "editar", "eliminar", "ver mas",
    "ver todos", "mostrar mas", "ocultar", "no hay avisos",
    "sin avisos", "no existen avisos", "aun no hay", "agregar un nuevo tema",
    "anadir un nuevo tema", "suscribirse", "rss", "marcar como leido",
    "buscar", "filtrar", "cerrar", "volver", "siguiente", "anterior",
    "avisos", "anuncios", "novedades", "noticias", "comunicados",
)

EMOJI = "\U0001F4E3"
EMOJI_URGENTE = "\u2757"

LARGO_MINIMO = 12
LARGO_MAXIMO = 1200
TOPE_POR_PAGINA = 25


# ------------------------------------------------------------------ ayudantes
def _sin_tildes(texto):
    """Minusculas y sin tildes, para poder comparar sin sorpresas."""
    t = unicodedata.normalize("NFKD", str(texto or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def _apretado(texto):
    """Un solo espacio entre palabras y sin espacios en los bordes."""
    return " ".join(str(texto or "").split())


def _es_titulo_de_tablero(texto):
    plano = _sin_tildes(_apretado(texto)).strip(" :\u00b7-\u2022|")
    if not plano or len(plano) > 40:
        return False
    return any(plano == t or plano.startswith(t + " ") or plano == t + "s"
               for t in TITULOS_DE_TABLERO)


def es_ruido(texto):
    """Adorno del tablero, botones y textos de relleno."""
    plano = _sin_tildes(_apretado(texto)).strip(" :\u00b7-\u2022|.")
    if not plano:
        return True
    if plano in RUIDO:
        return True
    # Una sola palabra corta casi nunca es un aviso de verdad.
    if len(plano) < LARGO_MINIMO and " " not in plano:
        return True
    return False


def urgente(texto):
    """Nivel 1: te cambia el dia. Suena aunque sea de madrugada."""
    plano = _sin_tildes(texto)
    return any(p in plano for p in PALABRAS_URGENTES)


def importante(texto):
    """Nivel 2: habla de fechas o notas, pero no te despierta.

    Devuelve False si ya es urgente, asi un aviso no cuenta en los dos
    niveles a la vez y no se marca dos veces.
    """
    if urgente(texto):
        return False
    plano = _sin_tildes(texto)
    return any(p in plano for p in PALABRAS_IMPORTANTES)


def prioridad(ficha):
    """urgente / importante / comun, para ordenar y para decidir el sonido."""
    if ficha.get("urgente"):
        return "urgente"
    if ficha.get("importante"):
        return "importante"
    return "comun"


def huella_de_aviso(titulo, texto=""):
    """La identidad de un aviso es su TEXTO, no su enlace: no tiene enlace.

    Se normaliza fuerte para que un espacio de mas, una tilde que el profesor
    corrigio o un cambio de mayusculas no lo hagan parecer un aviso nuevo.
    Esto es lo que evita que te avise dos veces por lo mismo.
    """
    crudo = _sin_tildes(_apretado("%s %s" % (titulo or "", texto or "")))
    crudo = re.sub(r"[^a-z0-9 ]+", " ", crudo)
    crudo = " ".join(crudo.split())
    return hashlib.sha256(crudo.encode("utf-8", "ignore")).hexdigest()[:16]


# ------------------------------------------------------------------ el parser
def _pedazos_del_cajon(cajon):
    """Parte un tablero en avisos sueltos.

    Las plataformas los separan de cuatro formas distintas: en <li>, en <p>,
    en filas de tabla, o con una linea punteada que en el html es un <hr> o
    un div con borde.  Se prueban en orden y se usa la primera que de mas de
    un pedazo, porque eso significa que acerto.
    """
    for selector in ("li", "tr", "p", "article",
                     "[class*='item']", "[class*='post']", "[class*='entry']"):
        try:
            encontrados = cajon.select(selector)
        except Exception:
            continue
        textos = []
        for e in encontrados:
            # Si un pedazo contiene a otro del mismo tipo, el de afuera es el
            # contenedor y no un aviso.  Se queda solo el de adentro.
            try:
                if e.select(selector):
                    continue
            except Exception:
                pass
            t = _apretado(e.get_text(" "))
            if t and not es_ruido(t):
                textos.append(t)
        if len(textos) >= 2:
            return textos
        if len(textos) == 1:
            guardado = textos
    entero = _apretado(cajon.get_text(" "))
    if entero and not es_ruido(entero):
        return [entero]
    try:
        return guardado
    except NameError:
        return []


def _cajones_por_titulo(sopa):
    """Busca un encabezado que diga Avisos y devuelve la caja que lo sigue."""
    cajones = []
    etiquetas = ["h1", "h2", "h3", "h4", "h5", "h6", "legend", "caption",
                 "th", "strong", "b", "span", "div", "a"]
    for tag in sopa.find_all(etiquetas):
        try:
            texto = tag.get_text(" ")
        except Exception:
            continue
        if not _es_titulo_de_tablero(texto):
            continue
        # Primero el hermano de al lado, que es el caso normal.
        siguiente = None
        try:
            for h in tag.next_siblings:
                if getattr(h, "get_text", None) and _apretado(h.get_text(" ")):
                    siguiente = h
                    break
        except Exception:
            siguiente = None
        if siguiente is not None:
            cajones.append(siguiente)
            continue
        # Si no hay hermano, el tablero es el padre y el titulo va adentro.
        padre = getattr(tag, "parent", None)
        if padre is not None:
            cajones.append(padre)
    return cajones


def avisos_de_la_pagina(html, titulo_ramo=""):
    """Devuelve las fichas de los avisos escritos que hay en una pagina.

    Cada ficha es:
        {"titulo", "texto", "huella", "urgente"}

    Nunca revienta: si algo sale mal devuelve una lista vacia, porque es
    mejor no avisar que cortar la revision de todos los ramos.
    """
    if not html or BeautifulSoup is None:
        return []
    try:
        sopa = BeautifulSoup(html, "html.parser")
        for basura in sopa(["script", "style", "noscript", "nav", "footer"]):
            basura.decompose()
    except Exception:
        return []

    cajones = _cajones_por_titulo(sopa)
    for selector in SELECTORES:
        try:
            cajones.extend(sopa.select(selector))
        except Exception:
            continue

    fichas, vistas = [], set()
    nombre_ramo = _sin_tildes(_apretado(titulo_ramo))
    for cajon in cajones:
        if cajon is None:
            continue
        try:
            pedazos = _pedazos_del_cajon(cajon)
        except Exception:
            continue
        for texto in pedazos:
            if len(texto) < LARGO_MINIMO:
                continue
            texto = texto[:LARGO_MAXIMO]
            # El nombre del ramo suelto no es un aviso.
            if nombre_ramo and _sin_tildes(texto) == nombre_ramo:
                continue
            h = huella_de_aviso("", texto)
            if h in vistas:
                continue
            vistas.add(h)
            fichas.append({
                "titulo": _titulo_corto(texto),
                "texto": texto,
                "huella": h,
                "urgente": urgente(texto),
                "importante": importante(texto),
            })
            if len(fichas) >= TOPE_POR_PAGINA:
                return _sin_contenidos(fichas)
    return _sin_contenidos(fichas)


def _sin_contenidos(fichas):
    """Saca las fichas que son solo el contenedor de otras.

    Pasa seguido: el tablero entero entra como un aviso gigante que contiene
    a los tres avisos de verdad.  Si el texto de una ficha contiene entero el
    texto de otra, la grande se tira.
    """
    if len(fichas) < 2:
        return fichas
    largos = sorted(fichas, key=lambda x: len(x["texto"]))
    salida = []
    for i, ficha in enumerate(largos):
        chico = _sin_tildes(ficha["texto"])
        contiene_otro = False
        for otro in largos[:i]:
            plano = _sin_tildes(otro["texto"])
            if len(plano) >= LARGO_MINIMO and plano in chico:
                contiene_otro = True
                break
        if not contiene_otro:
            salida.append(ficha)
    return salida


def _titulo_corto(texto):
    """La primera oracion, para usarla de titulo en la lista de pendientes."""
    limpio = _apretado(texto)
    corte = re.split(r"(?<=[.!?])\s", limpio, maxsplit=1)[0]
    if len(corte) > 90 or len(corte) < 8:
        corte = limpio[:90]
    return corte.rstrip(" .,:;\u00b7-") or limpio[:90]


# ------------------------------------------------------------------ el mensaje
def titulo_del_aviso(ficha):
    marca = EMOJI_URGENTE if ficha.get("urgente") else EMOJI
    return "%s Aviso del profe" % marca


def lineas_del_aviso(ficha, ramo="", url="", escapar=None, enlace=None):
    """Arma el mensaje que llega al chat.

    Se le pasan `escapar` y `enlace` desde afuera para que este modulo no
    dependa de la mensajeria y se pueda probar solo.
    """
    esc = escapar or (lambda x: x)
    lineas = ["%s" % titulo_del_aviso(ficha)]
    if ramo:
        lineas.append("<b>%s</b>" % esc(ramo))
    texto = ficha.get("texto", "")
    lineas.append(esc(texto if len(texto) <= 700 else texto[:700] + "..."))
    if ficha.get("urgente"):
        lineas.append("<i>Esto puede cambiarte la semana, leelo.</i>")
    if url and enlace:
        lineas.append(enlace("abrir el ramo", url))
    return "\n".join(lineas)


def nuevos(fichas, ya_avisadas):
    """Los avisos que todavia no te mande.

    `ya_avisadas` es el diccionario que vive en la memoria, huella -> fecha.
    No lo modifica: eso lo hace el bot despues de mandar el mensaje, asi si
    el mensaje no sale se vuelve a intentar.
    """
    guardadas = ya_avisadas or {}
    return [f for f in (fichas or []) if f.get("huella") not in guardadas]
