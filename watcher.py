# -*- coding: utf-8 -*-
"""El motor.  Mira las plataformas, guarda lo que ya vio, avisa lo nuevo y
atiende el chat.

Dos ideas de fondo:

1. Nada se declara roto en la primera lectura.  Las plataformas se
   reinician solas, y un susto pasajero no tiene que despertarte.
2. El bot solo hace teatro cuando hay alguien mirando.  Si vos pediste algo,
   te muestra en que anda.  Si trabaja solo a las 4 de la tarde, trabaja
   callado y manda la tarjeta terminada.
"""
import datetime as dt
import hashlib
import json
import os
import re
import threading
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    import secretos
    secretos.cargar(silencioso=True)
except Exception:
    pass

import almacen
import avisos
import clases
import comandos
import compartir
import fuentes as CFG
import salud
import version as VER
import ia as IA
import notificar as N
import panel as P

try:
    from zoneinfo import ZoneInfo
    ZONA = ZoneInfo(CFG.ZONA_HORARIA)
except Exception:
    ZONA = None

DIAS_LARGOS = ["lunes", "martes", "mi\u00e9rcoles", "jueves", "viernes",
               "s\u00e1bado", "domingo"]
DIAS_CORTOS = ["lun", "mar", "mi\u00e9", "jue", "vie", "s\u00e1b", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


# =====================================================================
#  utilidades
# =====================================================================
def ahora():
    return dt.datetime.now(ZONA) if ZONA else dt.datetime.now()


def reloj():
    return ahora().strftime("%H:%M:%S")


def log(*a):
    print(reloj(), *a, flush=True)


def en_ventana(t):
    """True si a esta hora el bot tiene que estar despierto escuchando."""
    inicio, cierre = CFG.DESPIERTO
    if inicio == cierre:
        return True
    if inicio < cierre:
        return inicio <= t.hour < cierre
    return t.hour >= inicio or t.hour < cierre


def cuanto_vivir(t):
    """Segundos que le quedan a este turno.

    Despierto: hasta que cierre la ventana, con el tope que aguanta un
    trabajo seguido.  Dormido: un ratito nada mas.
    """
    if not en_ventana(t):
        return CFG.MINUTOS_DORMIDO * 60
    cierre = t.replace(hour=CFG.DESPIERTO[1], minute=0, second=0, microsecond=0)
    if cierre <= t:
        cierre += dt.timedelta(days=1)
    falta = (cierre - t).total_seconds()
    return max(60.0, min(falta, CFG.HORAS_MAXIMAS * 3600))


# Hay plataformas que no ponen la extension en ningun lado: el enlace es
# algo como /curso/97/modulo/302/archivo/8891 y el texto es el nombre del
# documento pelado.  Antes eso se descartaba y el archivo nunca llegaba.
PISTAS_DESCARGA = ("/archivo/", "/archivos/", "/adjunto", "/descargar",
                   "/download", "/getfile", "/verarchivo", "/bajar",
                   "pluginfile.php", "forcedownload", "file.php",
                   "/documento/", "/fichero",
                   # Una de las dos plataformas publica cada archivo como una
                   # actividad con numero, sin extension y sin ninguna de las
                   # pistas de arriba.  Sin esto, un ramo lleno de material
                   # contestaba "no encontre archivos".
                   "/mod/resource/", "resource/view.php",
                   "draftfile.php", "/mod_resource/")

# Enlaces que NO son un archivo pero adentro tienen los archivos: hay que
# entrar igual aunque el enlace no repita el numero del ramo.
PISTAS_DE_ACTIVIDAD = ("/mod/", "/modulo/", "/actividad", "/recurso",
                       "/seccion", "/section", "/tema/", "/unidad",
                       "/carpeta", "/folder/", "view.php")

TIPOS_DE_ARCHIVO = (("pdf", ".pdf"), ("msword", ".doc"),
                    ("wordprocessingml", ".docx"), ("ms-excel", ".xls"),
                    ("spreadsheetml", ".xlsx"), ("ms-powerpoint", ".ppt"),
                    ("presentationml", ".pptx"), ("opendocument.text", ".odt"),
                    ("opendocument.spreadsheet", ".ods"),
                    ("opendocument.presentation", ".odp"),
                    ("zip", ".zip"), ("rar", ".rar"), ("7z", ".7z"),
                    ("csv", ".csv"), ("rtf", ".rtf"), ("plain", ".txt"),
                    ("jpeg", ".jpg"), ("png", ".png"), ("mp4", ".mp4"))


def parece_descarga(url, titulo=""):
    """True si el enlace huele a descarga aunque no diga la extension."""
    bajo = str(url or "").lower()
    return any(p in bajo for p in PISTAS_DESCARGA)


def extension_de_tipo(content_type):
    """De 'application/pdf' saca '.pdf'."""
    t = (content_type or "").lower().split(";")[0]
    for pista, ext in TIPOS_DE_ARCHIVO:
        if pista in t:
            return ext
    return ""


def es_bajable(url, titulo=""):
    """True si esto parece un archivo y no una pagina."""
    bajo = str(url or "").lower().split("?")[0]
    texto = str(titulo or "").lower()
    for ext in getattr(CFG, "ADJUNTAR_EXTENSIONES", []):
        if bajo.endswith(ext) or texto.endswith(ext):
            return True
    return parece_descarga(url, titulo)


def nombre_de_archivo(respuesta, url, titulo="archivo"):
    """El nombre con el que llega el archivo al chat."""
    from urllib.parse import unquote
    cd = respuesta.headers.get("Content-Disposition", "") if respuesta is not None else ""
    m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
    if m:
        return unquote(m.group(1).strip())[:80]
    cola = unquote(str(url or "").split("?")[0].rstrip("/").split("/")[-1])
    if cola and "." in cola:
        return cola[:80]
    ext = ""
    for e in getattr(CFG, "ADJUNTAR_EXTENSIONES", []):
        if str(url or "").lower().split("?")[0].endswith(e):
            ext = e
            break
    if not ext and respuesta is not None:
        # el enlace no dice nada, pero el servidor si: le preguntamos que
        # clase de archivo mando y le ponemos la extension que corresponde
        ext = extension_de_tipo(respuesta.headers.get("Content-Type", ""))
    limpio_titulo = re.sub(r"[\\/:*?\"<>|]", " ", limpio(titulo))[:70].strip() or "archivo"
    if ext and limpio_titulo.lower().endswith(ext):
        return limpio_titulo
    return limpio_titulo + ext


def huella(*partes):
    return hashlib.sha256("|".join(str(p) for p in partes).encode("utf-8")).hexdigest()[:16]


def limpio(t):
    return " ".join(str(t or "").split())


def pelado(t):
    return comandos.pelado(t)


def _sin_final(t):
    """Saca el final del nombre ('.pdf', '.docx') si lo trae."""
    t = str(t or "").strip()
    punto = t.rfind(".")
    if punto > 0 and len(t) - punto <= 6:
        return t[:punto]
    return t


def _solo_letras(t):
    """'Gu\u00eda N\u00b03.pdf' queda como 'guia n 3 pdf'.  Deja letras y numeros
    separados por espacios, asi los signos raros no arruinan la busqueda."""
    plano = pelado(t)
    return " ".join("".join(c if c.isalnum() else " " for c in plano).split())


def calza_nombre(pedido, ficha):
    """\u00bfEs este el archivo que pediste?

    El dueno escribe el nombre como lo ve en la pantalla: con tildes, con
    'N\u00b0', con el punto y el final, o solo dos palabras sueltas.  Antes se
    comparaba el texto tal cual y por eso escribir el nombre completo no
    encontraba nada.  Ahora alcanza con que esten todas las palabras, en
    cualquier orden, y se mira tambien el nombre con el que baja."""
    pedido = _solo_letras(_sin_final(pedido))
    if not pedido:
        return True
    ficha = ficha or {}
    cola = str(ficha.get("url") or "").split("?")[0].rstrip("/").split("/")[-1]
    donde = (_solo_letras(ficha.get("titulo", "")) + " "
             + _solo_letras(_sin_final(cola))).strip()
    if pedido in donde:
        return True
    return all(p in donde for p in pedido.split())


def fecha_linda(f):
    return "%s %d %s %02d:%02d" % (DIAS_CORTOS[f.weekday()], f.day,
                                   MESES[f.month - 1], f.hour, f.minute)


def leer_fecha(t):
    if not t:
        return None
    for formato in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            f = dt.datetime.strptime(t, formato)
            return f.replace(tzinfo=ZONA) if ZONA else f
        except ValueError:
            continue
    return None


def sesion():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                      "Accept-Language": "es-CL,es;q=0.9"})
    return s


# =====================================================================
#  clasificar lo que se encuentra
# =====================================================================
EXTENSIONES = r"(pdf|docx?|pptx?|xlsx?|zip|rar|txt|csv|jpe?g|png|mp4)"


def ignorar(href):
    """True si el enlace no vale la pena.  Ojo: un ancla suelta (#tab) no
    sirve, pero una direccion de verdad con un ancla al final SI."""
    h = (href or "").strip().lower()
    if not h or h in ("#", "/"):
        return True
    if h.startswith("#") or h.startswith("javascript:") or h.startswith("mailto:"):
        return True
    # Una sala de videoconferencia NUNCA se ignora, aunque caiga en la lista
    # de arriba.  La lista tiene "/meeting/" para saltear el chat interno de
    # la plataforma, y ese filtro se estaba comiendo las clases por video.
    if getattr(CFG, "AVISAR_CLASES", True) and clases.es_sala(h):
        return False
    limpio_h = h.split("#")[0]
    return any(x in limpio_h for x in CFG.IGNORAR)


def es_menu(texto):
    return pelado(texto) in [pelado(x) for x in CFG.PALABRAS_MENU]


def tipo_de(href, texto):
    h = (href or "").lower()
    t = pelado(texto)
    if re.search(r"\." + EXTENSIONES + r"(\?|$)", h) or re.search(r"\." + EXTENSIONES + r"$", t):
        return "archivo"
    if parece_descarga(h, texto):
        return "archivo"
    if "foro" in h or "forum" in h or "foro" in t:
        return "foro"
    if any(p in h for p in CFG.PALABRAS_TAREA) or any(p in t for p in CFG.PALABRAS_TAREA):
        return "tarea"
    return "material"


def icono(tipo):
    return {"tarea": "\U0001F4DD", "foro": "\U0001F4AC",
            "archivo": "\U0001F4C4"}.get(tipo, "\U0001F4CE")


# Muchas plataformas no usan enlaces de verdad: cuelgan la direccion de un
# onclick o de un atributo data-*.  Antes eso era invisible para el bot.
ATRIBUTOS_CON_URL = ("data-href", "data-url", "data-src", "data-file",
                     "data-archivo", "data-download", "data-link", "data-ruta")
RE_URL_EN_JS = re.compile(
    r"""(?:href|src|url|open|location(?:\.href)?)\s*[=(]\s*['"]([^'"]{4,300})['"]""", re.I)
RE_URL_SUELTA = re.compile(r"""['"]((?:https?://|/)[^'"\s]{4,300})['"]""")


def _urls_del_tag(tag):
    """Saca direcciones escondidas en atributos data-* y en el onclick."""
    salida = []
    try:
        for att in ATRIBUTOS_CON_URL:
            v = (tag.get(att) or "").strip()
            if len(v) > 3:
                salida.append(v)
        js = " ".join([(tag.get("onclick") or ""), (tag.get("data-action") or "")])
        if js.strip():
            for m in RE_URL_EN_JS.finditer(js):
                salida.append(m.group(1))
            if not salida:
                for m in RE_URL_SUELTA.finditer(js):
                    salida.append(m.group(1))
    except Exception:
        return []
    return salida


def cosas_de_la_pagina(html, base, propia=None):
    """Saca de una pagina todo lo que parezca material.  Mira los enlaces
    normales, los que estan escondidos en atributos o en el onclick, y las
    fichas de actividad de la plataforma educativa."""
    sopa = BeautifulSoup(html, "html.parser")
    salida, vistos = [], set()

    def sumar(texto, href, tag=None, pista="", descripcion=None):
        texto = limpio(texto)
        if not texto or len(texto) < 3 or es_menu(texto):
            return
        if ignorar(href):
            return
        try:
            url = urljoin(base, href.strip())
        except Exception:
            return
        if not url.lower().startswith(("http://", "https://")):
            return
        if propia and url.rstrip("/") == propia.rstrip("/"):
            return
        if url in vistos:
            return
        vistos.add(url)
        if descripcion is None:
            descripcion = _descripcion_cerca(tag) if tag is not None else ""
        salida.append({"titulo": texto[:160], "url": url,
                       "tipo": tipo_de(pista + " " + href, texto),
                       "descripcion": descripcion})

    for a in sopa.find_all("a"):
        texto = a.get_text(" ")
        href = (a.get("href") or "").strip()
        if href:
            sumar(texto, href, tag=a)
        for u in _urls_del_tag(a):
            sumar(texto, u, tag=a)

    # Botones, filas de tabla y cajas que se comportan como enlaces.
    for tag in sopa.find_all(["button", "tr", "li", "div", "td", "span", "i", "img"]):
        urls = _urls_del_tag(tag)
        if not urls:
            continue
        texto = limpio(tag.get_text(" "))
        if not texto:
            texto = limpio(tag.get("title") or tag.get("alt") or "")
        for u in urls:
            sumar(texto, u, tag=tag, pista=" ".join(tag.get("class", [])))

    for li in sopa.select("li.activity"):
        nombre = li.select_one(".instancename")
        a = li.find("a", href=True)
        if not nombre or not a:
            continue
        try:
            url = urljoin(base, a["href"])
        except Exception:
            continue
        if url in vistos:
            continue
        vistos.add(url)
        clases = " ".join(li.get("class", []))
        resumen = li.select_one(".activity-description, .contentafterlink, .summary")
        salida.append({"titulo": limpio(nombre.get_text(" "))[:160], "url": url,
                       "tipo": tipo_de(clases, nombre.get_text(" ")),
                       "descripcion": limpio(resumen.get_text(" "))[:4000] if resumen else ""})
    return salida


def _descripcion_cerca(a):
    """El texto que el profesor escribio al lado del enlace.  Muchas veces
    ahi esta la consigna entera y la fecha de entrega."""
    try:
        caja = a.find_parent(["li", "div", "td", "article"])
        if not caja:
            return ""
        texto = limpio(caja.get_text(" "))
        propio = limpio(a.get_text(" "))
        texto = texto.replace(propio, " ", 1)
        return limpio(texto)[:4000]
    except Exception:
        return ""


# ------------------------------------------------- huella de una pagina
# Sirve para el ultimo seguro: si la pagina cambio pero no supe decir en
# que, igual te aviso.  Le saco relojes, numeros largos y fichas de sesion
# para que no cambie sola cada vez que se carga.
# Esta lista quedo corta y era la causa de los avisos de "cambio algo y no
# se que" cuando en la pagina no habia cambiado nada: alcanzaba con un
# "hace 2 horas" o un contador de visitas para que la firma diera distinta
# en cada revision.  Todo lo que se mueve solo tiene que estar aca.
RE_VOLATIL = re.compile(
    # relojes
    r"\d{1,2}:\d{2}(:\d{2})?"
    # numeros largos, identificadores y fichas de sesion
    r"|\d{5,}|sesskey|csrf|token|jsessionid|nonce|utm_[a-z]+"
    # "hace 2 horas", "en 5 minutos", "3 dias atras"
    r"|hace\s+\w+\s+(?:segundos?|minutos?|horas?|dias?|semanas?|meses?|anos?)"
    r"|en\s+\d+\s+(?:segundos?|minutos?|horas?)"
    r"|\d+\s+(?:segundos?|minutos?|horas?)\s+(?:atras|antes)"
    # ultimo acceso, ultima modificacion, contadores de gente conectada
    r"|ultim[oa]s?\s+(?:acceso|conexion|ingreso|visita|modificacion|"
    r"actualizacion|entrada)"
    r"|\d+\s+(?:visitas?|vistas?|conectados?|en\s+linea)"
    # el saludo con tu nombre y las fechas escritas
    r"|bienvenid[oa]s?"
    r"|\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{2,4}"
    r"|\d{4}-\d{2}-\d{2}", re.I)


def firma_de_pagina(html):
    try:
        sopa = BeautifulSoup(html, "html.parser")
        for t in sopa(["script", "style", "noscript"]):
            t.decompose()
        texto = pelado(limpio(sopa.get_text(" ")))
        texto = RE_VOLATIL.sub(" ", texto)
        return huella("pag", " ".join(texto.split()))
    except Exception:
        return ""


RE_FECHA_TEXTO = re.compile(
    r"(\d{1,2})\s*(?:de\s+)?(ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic)"
    r"[a-z]*\s*(?:de\s+)?(\d{4})?(?:[^\d]{0,12}(\d{1,2}):(\d{2}))?", re.I)
RE_FECHA_NUM = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?:[^\d]{0,12}(\d{1,2}):(\d{2}))?")


def fecha_en_texto(texto, hoy):
    """Busca una fecha de entrega escrita en la descripcion.
    Devuelve datetime o None.  Ante la duda, None: es preferible no saber
    a inventar un plazo."""
    if not texto:
        return None
    corto = texto[:1200]
    m = RE_FECHA_TEXTO.search(corto)
    if m:
        dia = int(m.group(1))
        mes = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
               "sep", "oct", "nov", "dic"].index(m.group(2).lower()[:3].replace("set", "sep")) + 1
        anio = int(m.group(3)) if m.group(3) else hoy.year
        h = int(m.group(4)) if m.group(4) else 23
        mi = int(m.group(5)) if m.group(5) else 55
    else:
        m = RE_FECHA_NUM.search(corto)
        if not m:
            return None
        dia, mes = int(m.group(1)), int(m.group(2))
        anio = int(m.group(3) or hoy.year)
        if anio < 100:
            anio += 2000
        h = int(m.group(4)) if m.group(4) else 23
        mi = int(m.group(5)) if m.group(5) else 55
    try:
        f = dt.datetime(anio, mes, dia, min(h, 23), min(mi, 59))
        f = f.replace(tzinfo=ZONA) if ZONA else f
    except ValueError:
        return None
    if f < hoy - dt.timedelta(days=30) or f > hoy + dt.timedelta(days=400):
        return None
    return f


# =====================================================================
#  recorrer un ramo por dentro
# =====================================================================
# La portada del ramo no siempre muestra lo que subieron.  Muchas veces la
# actividad nueva es una pagina aparte y el archivo esta adentro.  Asi que
# entro un nivel mas, pero solo dentro del mismo ramo y con tope.
_ULTIMO_PROFUNDO = {}


# Hay plataformas que ni siquiera escriben los enlaces: dejan la lista del
# material en una variable de JavaScript y el navegador arma el arbol solo.
# Sin esto, el bot ve la pagina del ramo vacia aunque este llena.
RE_ARBOL_JS = re.compile(
    r"""var\s+arbol\s*=\s*JSON\.parse\(\s*(['"])(.*?)\1\s*\)""", re.S)


def _texto_js(crudo):
    """Deshace los escapes de una cadena escrita adentro de JavaScript."""
    try:
        return json.loads('"' + crudo.replace('"', '\\"') + '"')
    except Exception:
        return (crudo.replace("\\'", "'").replace('\\"', '"')
                     .replace("\\/", "/").replace("\\\\", "\\"))


def _aplanar_arbol(nodos, salida):
    if isinstance(nodos, dict):
        nodos = [nodos]
    if not isinstance(nodos, list):
        return
    for n in nodos:
        if not isinstance(n, dict):
            continue
        idn = str(n.get("id") or n.get("ID") or "").strip()
        nombre = limpio(str(n.get("name") or n.get("nombre") or ""))
        if idn and idn != "-1" and nombre:
            salida.append((idn, nombre, str(n.get("type") or "")))
        for hijos in ("children", "items", "hijos", "nodes", "data"):
            if n.get(hijos):
                _aplanar_arbol(n[hijos], salida)


def arbol_escondido(html, base, id_ramo):
    """Saca el material que la pagina guarda en JavaScript en vez de enlazarlo."""
    salida = []
    m = RE_ARBOL_JS.search(html or "")
    if not m:
        return salida
    try:
        datos = json.loads(_texto_js(m.group(2)) or "[]")
    except Exception:
        return salida
    planos = []
    _aplanar_arbol(datos, planos)
    for idn, nombre, clase in planos:
        if str(clase).lower() in ("folder", "branch", "carpeta"):
            continue                       # una carpeta no es material
        url = "%s/curso/%s/modulo/%s" % (base.rstrip("/"), id_ramo, idn)
        salida.append({"titulo": nombre[:180], "url": url,
                       "tipo": tipo_de(url, nombre), "descripcion": ""})
    return salida


def _toca_profundo(id_ramo, firma_raiz, vacio=False):
    """Entrar adentro de cada actividad en cada vuelta seria maltratar la
    plataforma.  Entro cuando la portada cambio, y cada tanto igual.

    Y entro SIEMPRE si en la portada no se ve ni un archivo: un ramo que
    parece vacio es justo el que hay que mirar por dentro.  Sin esto, el
    material que vive adentro de una actividad tardaba horas en aparecer
    aunque estuviera publicado hace dias."""
    if vacio:
        _ULTIMO_PROFUNDO[id_ramo] = {"firma": firma_raiz, "t": time.time()}
        return True
    minutos = getattr(CFG, "MINUTOS_EXPLORACION_PROFUNDA", 20)
    ficha = _ULTIMO_PROFUNDO.get(id_ramo)
    if (ficha is None or ficha.get("firma") != firma_raiz
            or time.time() - ficha.get("t", 0) >= minutos * 60):
        _ULTIMO_PROFUNDO[id_ramo] = {"firma": firma_raiz, "t": time.time()}
        return True
    return False


def _es_del_ramo(url, base, id_ramo):
    u = (url or "").lower()
    if not u.startswith(base.rstrip("/").lower()):
        return False
    rid = str(id_ramo or "")
    if rid and rid in u:
        return True
    # Hay una plataforma que no repite el numero del ramo en el enlace de cada
    # actividad.  Como este enlace salio de la pagina de ESTE ramo, si tiene
    # pinta de actividad hay que entrar: si no, el material que vive adentro
    # de una actividad no se ve nunca.
    return any(p in u for p in PISTAS_DE_ACTIVIDAD)


def explorar_ramo(s, base, g):
    """Devuelve (items, firma).  items=None significa 'no pude leer', que no
    es lo mismo que 'no hay nada'."""
    tope = getattr(CFG, "PAGINAS_POR_RAMO", 14)
    hondo = getattr(CFG, "PROFUNDIDAD", 1)
    raiz = g["url"]
    try:
        html = s.get(raiz, timeout=CFG.ESPERA_RED).text
    except Exception:
        return None, ""

    firmas = [firma_de_pagina(html)]
    # Los avisos del profesor son TEXTO suelto, no enlaces, asi que no los
    # agarra nada de lo de abajo.  Hay que leerlos aparte.
    g["avisos"] = avisos.avisos_de_la_pagina(html, g.get("nombre", ""))
    items = {}
    for it in cosas_de_la_pagina(html, base, propia=raiz):
        items.setdefault(it["url"], it)
    # el material que vive en el JavaScript de la pagina
    escondido = arbol_escondido(html, base, g.get("id"))
    for it in escondido:
        items.setdefault(it["url"], it)
    if escondido:
        firmas.append(huella("arbol", *sorted(x["url"] + x["titulo"] for x in escondido)))

    hay_material = any(es_bajable(it["url"], it.get("titulo", ""))
                       for it in items.values())
    if hondo <= 0 or not _toca_profundo(str(g.get("id")), firmas[0],
                                        vacio=not hay_material):
        return list(items.values()), huella("firma", *firmas)

    vistas = {raiz}
    # las secciones del JavaScript se miran siempre primero: ahi esta lo bueno
    cola = [(it["url"], 1) for it in escondido]
    cola += [(it["url"], 1) for it in items.values()
            if _es_del_ramo(it["url"], base, g.get("id"))
            and not es_bajable(it["url"], it["titulo"])]
    while cola and len(vistas) < tope:
        url, nivel = cola.pop(0)
        if url in vistas:
            continue
        vistas.add(url)
        try:
            dentro = s.get(url, timeout=CFG.ESPERA_RED).text
        except Exception:
            continue
        firmas.append(firma_de_pagina(dentro))
        for a in avisos.avisos_de_la_pagina(dentro, g.get("nombre", "")):
            if all(a["huella"] != x["huella"] for x in g["avisos"]):
                g["avisos"].append(a)
        for it in cosas_de_la_pagina(dentro, base, propia=url):
            if it["url"] in items:
                continue
            items[it["url"]] = it
            if (nivel < hondo and not es_bajable(it["url"], it["titulo"])
                    and _es_del_ramo(it["url"], base, g.get("id"))):
                cola.append((it["url"], nivel + 1))
    return list(items.values()), huella("firma", *sorted(firmas))


# =====================================================================
#  las dos plataformas
# =====================================================================
def entrar_b64(s, base, usuario, clave):
    import base64 as b64
    s.get(base + "/session/login", timeout=CFG.ESPERA_RED)
    r = s.post(base + "/session/do_login",
               data={"username": usuario, "real-password": clave,
                     "password": b64.b64encode(clave.encode()).decode()},
               headers={"Referer": base + "/session/login"},
               timeout=CFG.ESPERA_RED)
    return "/session/login" not in r.url


def _ramos_b64(s, base, viejos=False):
    salida = []
    try:
        if viejos:
            html = s.post(base + "/async/main/oldCourses", timeout=CFG.ESPERA_RED).text
        else:
            html = s.get(base + "/cursos", timeout=CFG.ESPERA_RED).text
    except Exception:
        return None
    for d in BeautifulSoup(html, "html.parser").select("[data-courseid]"):
        cid = d.get("data-courseid")
        if not cid:
            continue
        salida.append({"id": str(cid),
                       "nombre": limpio(d.get("data-coursename") or ("curso " + str(cid))),
                       "url": base + "/curso/" + str(cid)})
    return salida


def leer_b64(s, base):
    activos = _ramos_b64(s, base)
    if activos is None:
        return None, []
    for g in activos:
        g["items"], g["firma"] = explorar_ramo(s, base, g)
    viejos = _ramos_b64(s, base, viejos=True) or []
    return activos, [x["id"] for x in viejos]


RE_HORA_REUNION = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})[\sT]+(\d{1,2}):(\d{2})")


def _entero(t):
    numeros = re.findall(r"\d+", str(t or ""))
    return int(numeros[0]) if numeros else 0


def reuniones_b64(s, base, id_ramo):
    """Las clases por videoconferencia que el ramo tiene programadas.

    Esta pagina no publica archivos ni avisos escritos, asi que el explorador
    la dejaba pasar como un enlace cualquiera. Adentro estaba la clase por
    video con su hora y su clave: justo lo unico que no se puede perder.

    Devuelve None si no se pudo mirar, para no confundir "no hay reuniones"
    con "no llegue a mirar".
    """
    url = base + "/curso/meeting/show/" + str(id_ramo)
    try:
        html = s.get(url, timeout=CFG.ESPERA_RED).text or ""
    except Exception:
        return None
    if not html:
        return None
    salida = []
    for fila in BeautifulSoup(html, "html.parser").select("tr"):
        celdas = [limpio(c.get_text(" ")) for c in fila.select("td")]
        if len(celdas) < 3:
            continue
        donde = None
        for i, c in enumerate(celdas):
            if RE_HORA_REUNION.search(c):
                donde = i
                break
        if donde is None:
            continue
        m = RE_HORA_REUNION.search(celdas[donde])
        dia, mes, anio, hh, mm = (int(x) for x in m.groups())
        try:
            cuando = dt.datetime(anio, mes, dia, hh, mm)
        except ValueError:
            continue
        if ZONA:
            cuando = cuando.replace(tzinfo=ZONA)
        resto = celdas[donde + 1:]
        minutos = _entero(resto[0]) if resto else 0
        tema = (resto[1] if len(resto) > 1 else "") or "Clase por videoconferencia"
        anfitrion = resto[2] if len(resto) > 2 else ""
        llave = ""
        for c in resto[3:]:
            pelado_c = c.replace(" ", "")
            if pelado_c.isdigit() and 3 <= len(pelado_c) <= 12:
                llave = pelado_c
                break
        enlace = ""
        for a in fila.select("a[href]"):
            destino = urljoin(base, a["href"])
            if destino != url:
                enlace = destino
                break
        salida.append({"cuando": cuando,
                       "minutos": minutos or 60,
                       "tema": tema[:120],
                       "anfitrion": anfitrion[:80],
                       "llave": llave,
                       "enlace": enlace,
                       "pagina": url})
    return salida


CAMINOS_DE_RAMOS = ("/my/", "/my/courses.php", "/user/profile.php",
                    "/calendar/view.php?view=month")


def _pantalla_de_entrar(html):
    """La segunda plataforma contesta "todo bien" aunque te haya echado: la
    pantalla de entrar viaja con el mismo codigo que una pagina buena, asi que
    hay que reconocerla por lo que trae adentro."""
    bajo = (html or "").lower()
    if 'name="logintoken"' in bajo and 'name="password"' in bajo:
        return True
    if "loginform" in bajo and 'name="password"' in bajo:
        return True
    return "iniciar sesi" in bajo and "logout.php" not in bajo


def _cerrar_sesion_colgada(s, base, html):
    """Si quedo una sesion vieja abierta, la plataforma no deja pasar: muestra
    "ya iniciaste sesion" y espera que elijas. El bot se comia esa pantalla
    como si fuera clave equivocada y despues no leia ni un ramo."""
    m = re.search(r"logout\.php\?sesskey=([A-Za-z0-9]+)", html or "")
    if not m:
        return False
    try:
        s.get(base + "/login/logout.php?sesskey=" + m.group(1),
              timeout=CFG.ESPERA_RED)
    except Exception:
        return False
    return True


def _adentro_del_aula(s, base):
    """Preguntar de verdad, pidiendo paginas que solo se ven estando adentro."""
    for camino in ("/my/", "/user/profile.php"):
        try:
            r = s.get(base + camino, timeout=CFG.ESPERA_RED)
        except Exception:
            continue
        html = r.text or ""
        if "login/index.php" in (r.url or "") or _pantalla_de_entrar(html):
            continue
        return True, html
    return False, ""


def entrar_aula(s, base, usuario, clave):
    """Entra y COMPRUEBA que entro.

    Que la plataforma conteste bien no prueba nada: contesta igual de bien
    cuando lo que manda es la pantalla de entrar. Dar por buena esa respuesta
    es lo que dejaba al dueno sin una plataforma entera y sin enterarse.
    """
    for intento in (1, 2):
        try:
            r0 = s.get(base + "/login/index.php", timeout=CFG.ESPERA_RED)
        except Exception:
            return False
        ficha = BeautifulSoup(r0.text, "html.parser").find("input", {"name": "logintoken"})
        datos = {"anchor": "", "username": usuario, "password": clave}
        if ficha:
            datos["logintoken"] = ficha.get("value", "")
        try:
            r = s.post(base + "/login/index.php", data=datos,
                       headers={"Referer": base + "/login/index.php"},
                       timeout=CFG.ESPERA_RED)
        except Exception:
            return False
        adentro, _ = _adentro_del_aula(s, base)
        if adentro:
            return True
        # Una sola vez: cerrar la sesion colgada y volver a probar. Insistir
        # mas veces puede terminar con la cuenta bloqueada.
        if intento == 1 and _cerrar_sesion_colgada(s, base, r.text or ""):
            continue
        return False
    return False


def _ramos_en_html(base, html):
    grupos, vistos = [], set()
    for a in BeautifulSoup(html or "", "html.parser").select(
            'a[href*="/course/view.php?id="]'):
        m = re.search(r"id=(\d+)", a["href"])
        if not m or m.group(1) in vistos:
            continue
        nombre = limpio(a.get_text(" ")) or ("curso " + m.group(1))
        vistos.add(m.group(1))
        grupos.append({"id": m.group(1), "nombre": nombre[:120],
                       "url": urljoin(base, a["href"])})
    return grupos


def _ramos_por_dentro(s, base, html):
    """El mismo camino que usa la pagina para pedirse sus ramos.

    La pantalla principal ya no viene escrita: se arma sola en el navegador,
    asi que mirar el dibujo devolvia cero ramos aunque estuvieran todos.
    """
    m = re.search(r"sesskey[\"']?\s*[:=]\s*[\"']([A-Za-z0-9]+)", html or "")
    if not m:
        return []
    cuerpo = [{"index": 0,
               "methodname":
                   "core_course_get_enrolled_courses_by_timeline_classification",
               "args": {"offset": 0, "limit": 100, "classification": "all",
                        "sort": "fullname"}}]
    try:
        r = s.post(base + "/lib/ajax/service.php?sesskey=" + m.group(1),
                   json=cuerpo, timeout=CFG.ESPERA_RED)
        datos = r.json()
    except Exception:
        return []
    salida, vistos = [], set()
    for tanda in (datos if isinstance(datos, list) else [datos]):
        if not isinstance(tanda, dict) or tanda.get("error"):
            continue
        for c in ((tanda.get("data") or {}).get("courses") or []):
            cid = str(c.get("id") or "")
            if not cid or cid in vistos:
                continue
            vistos.add(cid)
            salida.append({
                "id": cid,
                "nombre": (limpio(c.get("fullname") or "") or ("curso " + cid))[:120],
                "url": c.get("viewurl") or (base + "/course/view.php?id=" + cid)})
    return salida


def leer_aula(s, base):
    """Busca los ramos por varios caminos, no por uno solo.

    Devolver una lista vacia cuando en realidad no se pudo mirar es la peor
    respuesta posible: se parece a "no hay nada nuevo". Por eso, si ninguna
    pagina se dejo abrir, esto contesta "no pude" y el bot avisa.
    """
    grupos, vistos, alguna_abrio = [], set(), False
    for camino in CAMINOS_DE_RAMOS:
        try:
            html = s.get(base + camino, timeout=CFG.ESPERA_RED).text
        except Exception:
            continue
        if _pantalla_de_entrar(html):
            continue
        alguna_abrio = True
        for g in _ramos_en_html(base, html):
            if g["id"] not in vistos:
                vistos.add(g["id"])
                grupos.append(g)
        if not grupos:
            for g in _ramos_por_dentro(s, base, html):
                if g["id"] not in vistos:
                    vistos.add(g["id"])
                    grupos.append(g)
        if grupos:
            break
    if not alguna_abrio:
        return None, []
    for g in grupos:
        g["items"], g["firma"] = explorar_ramo(s, base, g)
    return grupos, []


ADAPTADORES = {"b64": (entrar_b64, leer_b64), "aula": (entrar_aula, leer_aula)}


# =====================================================================
#  agenda de plazos
# =====================================================================
def _fecha_ical(v):
    for formato in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            f = dt.datetime.strptime(v, formato)
            if formato.endswith("Z"):
                f = f.replace(tzinfo=dt.timezone.utc)
                return f.astimezone(ZONA) if ZONA else f
            return f.replace(tzinfo=ZONA) if ZONA else f
        except ValueError:
            continue
    return None


def enlaces_de_agenda():
    """Los calendarios configurados. Puede haber uno por plataforma.

    Acepta una variable sola o una lista, y dentro de cada variable, varios
    enlaces separados por coma. Si no hay ninguno, el bot funciona igual."""
    nombres = CFG.ENV_AGENDA
    if isinstance(nombres, str):
        nombres = [nombres]
    salida = []
    for nombre in nombres:
        crudo = os.environ.get(nombre, "").strip()
        for pedazo in crudo.replace("\n", ",").split(","):
            pedazo = pedazo.strip()
            if pedazo.startswith("http"):
                salida.append((nombre, pedazo))
    return salida


def leer_agenda():
    eventos = []
    for nombre, url in enlaces_de_agenda():
        # Un calendario caido no puede tumbar al otro.
        try:
            eventos.extend(_leer_un_calendario(nombre, url))
        except Exception as e:
            log("[i] no pude leer la agenda %s: %s" % (nombre, type(e).__name__))
    return eventos


def _leer_un_calendario(nombre, url):
    try:
        crudo = requests.get(url, timeout=CFG.ESPERA_RED).text
    except Exception:
        return []

    eventos, actual = [], None
    for linea in crudo.replace("\r\n ", "").replace("\r\n", "\n").split("\n"):
        if linea.startswith("BEGIN:VEVENT"):
            actual = {}
        elif linea.startswith("END:VEVENT") and actual is not None:
            if actual.get("vence") and actual.get("titulo"):
                eventos.append(actual)
            actual = None
        elif actual is not None:
            campo, _, valor = linea.partition(":")
            campo = campo.split(";")[0].upper()
            if campo == "SUMMARY":
                actual["titulo"] = limpio(valor)[:160]
            elif campo == "DESCRIPTION":
                actual["descripcion"] = limpio(valor)[:4000]
            elif campo == "UID":
                # El origen va pegado al identificador: dos plataformas
                # distintas pueden usar el mismo numero para cosas distintas.
                actual["uid"] = nombre + ":" + valor.strip()
            elif campo in ("DTSTART", "DTEND"):
                f = _fecha_ical(valor.strip())
                if f and (campo == "DTSTART" or not actual.get("vence")):
                    actual["vence"] = f
            elif campo == "URL":
                actual["url"] = valor.strip()
    return eventos


# =====================================================================
#  archivos: rangos, tipos y pesos.  Todo esto lo calcula el programa,
#  la IA no cuenta ni mide nada.
# =====================================================================
GRUPOS_DE_TIPO = {
    "pdf": (".pdf",),
    "doc": (".doc", ".docx", ".odt", ".rtf"),
    "ppt": (".ppt", ".pptx", ".odp"),
    "xls": (".xls", ".xlsx", ".ods", ".csv"),
}


def de_este_tipo(tipo, nombre, url):
    """"todos los pdf de contabilidad": esto decide si entra o no."""
    tipo = (tipo or "todo").strip().lower()
    puntas = GRUPOS_DE_TIPO.get(tipo)
    if not puntas:
        return True
    bolsa = (nombre or "").lower() + " " + (url or "").lower().split("?")[0]
    return any(p in bolsa for p in puntas)


def _dia_de(texto):
    try:
        return dt.datetime.strptime(str(texto or "").strip()[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def rango_de_fechas(alcance=None, desde="", hasta=""):
    """Devuelve (desde, hasta) como dias.  desde None = todo el ramo."""
    hoy = ahora().date()
    d, h = _dia_de(desde), _dia_de(hasta) or hoy
    if d:
        return d, h
    alcance = str(alcance or getattr(CFG, "ALCANCE_POR_DEFECTO", "semana")).lower()
    dias = getattr(CFG, "DIAS_DE_ALCANCE", {}).get(alcance, 7)
    if not dias:
        return None, h
    return hoy - dt.timedelta(days=dias), h


def rango_lindo(d, h):
    """Como se lee el rango en el chat.  Nunca se dice un rango que no se uso."""
    if not d:
        return "de todo el ramo"
    fin = "hoy" if h >= ahora().date() else h.strftime("%d/%m")
    return "desde el %s hasta %s" % (d.strftime("%d/%m"), fin)


def peso_lindo(cuanto):
    cuanto = int(cuanto or 0)
    if cuanto >= 1024 * 1024:
        return "%d MB" % max(1, int(round(cuanto / (1024.0 * 1024.0))))
    return "%d KB" % max(1, int(round(cuanto / 1024.0)))


# =====================================================================
#  el vigilante
# =====================================================================
class Vigilante(object):

    def __init__(self):
        self.estado, self.modo, gist_nuevo = almacen.cargar()
        self.estado["_chat"] = os.environ.get("TG_CHAT", "").strip()
        self.gist_nuevo = gist_nuevo
        self.sesiones = {}
        self.bases = {}          # la direccion de cada plataforma, ya resuelta
        self.cache = {}          # pantallas ya calculadas, ver _memo
        self.acc = self._acciones()

    # ---------------------------------------------------------- guardar
    def guardar(self):
        antes = self.modo
        self.modo = almacen.guardar(self.estado, self.modo)
        self._avisar_memoria(antes)

    def _avisar_memoria(self, antes):
        """Quedarse sin memoria es la falla mas cara de este bot: si no puede
        anotar lo que ya te mando, te lo repite o lo pierde.  Y callarse no es
        opcion, porque un bot mudo se parece demasiado a un bot sin noticias.
        Se avisa una vez cada doce horas para no convertirlo en ruido."""
        perdida = self.modo == "nada"
        respaldo = self.modo == "repo" and antes == "gist"
        ilegible = almacen.memoria_rota()
        if not perdida and not respaldo and not ilegible:
            return

        cuando = time.time()
        ultimo = 0.0
        try:
            ultimo = float(self.estado.get("aviso_memoria") or 0)
        except (TypeError, ValueError):
            ultimo = 0.0
        if cuando - ultimo < 12 * 3600:
            return
        self.estado["aviso_memoria"] = cuando

        if perdida:
            texto = ("\u26A0\uFE0F <b>No pude guardar lo que revis\u00e9</b>\n"
                     "Sigo mirando tus ramos y te voy a avisar igual, pero por "
                     "ahora no logro anotar lo que ya te mand\u00e9, as\u00ed que "
                     "puede que te repita alg\u00fan aviso.\n"
                     "Si esto sigue ma\u00f1ana, conviene revisar la conexi\u00f3n "
                     "del bot.")
        elif respaldo:
            texto = ("\u26A0\uFE0F <b>Estoy usando mi copia de respaldo</b>\n"
                     "Mi memoria de siempre no me responde, as\u00ed que anoto "
                     "todo en la copia. Vas a seguir recibiendo los avisos "
                     "igual; te lo digo para que sepas por qu\u00e9 podr\u00eda "
                     "repetirse alguno.")
        else:
            texto = ("\u26A0\uFE0F <b>Arranqu\u00e9 sin recordar lo anterior</b>\n"
                     "No pude leer lo que ten\u00eda anotado, as\u00ed que empec\u00e9 "
                     "la cuenta de nuevo. Puede que te avise cosas que ya "
                     "hab\u00edas visto durante el pr\u00f3ximo d\u00eda.")
        try:
            N.enviar(texto)
        except Exception as e:
            log("[!] no pude avisar el problema de memoria: %s" % e)

    # ---------------------------------------------------------- ayudas
    def cfg(self):
        return self.estado.setdefault("config", {})

    def en_pausa(self):
        fin = leer_fecha(self.cfg().get("pausa_hasta"))
        if not fin:
            return False
        if ahora() >= fin:
            self.cfg()["pausa_hasta"] = None
            return False
        return True

    def en_silencio(self):
        if not self.cfg().get("noche", True) or not CFG.SILENCIO:
            return False
        h = ahora().hour
        a, b = CFG.SILENCIO
        return a <= h < b if a < b else (h >= a or h < b)

    def callado(self, clave):
        ficha = self.estado.get("callados", {}).get(clave)
        if not ficha:
            return False
        try:
            fin = dt.datetime.strptime(ficha["hasta"], "%Y-%m-%d").date()
        except Exception:
            return False
        if ahora().date() > fin:
            del self.estado["callados"][clave]
            g = self.estado.get("grupos", {}).get(clave, {})
            N.enviar("\U0001F514 <b>%s</b> vuelve a avisarte.\nSe cumpli\u00f3 el plazo "
                     "que pusiste." % N.escapar(g.get("nombre", "Un ramo")))
            return False
        return True

    def perfil_de(self, clave):
        return (self.estado.get("perfiles", {}).get(clave)
                or self.cfg().get("perfil") or CFG.PERFIL_POR_DEFECTO)

    def nombre_de(self, clave):
        return self.estado.get("grupos", {}).get(clave, {}).get("nombre", "?")

    def emoji_de(self, clave):
        return self.estado.get("grupos", {}).get(clave, {}).get("emoji", "\U0001F4D8")

    def buscar(self, texto):
        """Encuentra un ramo por un pedazo del nombre."""
        t = pelado(texto)
        hits = [(k, v.get("nombre", "")) for k, v in self.estado.get("grupos", {}).items()
                if t in pelado(v.get("nombre", ""))]
        if not hits:
            return None, "No encuentro ning\u00fan ramo con eso."
        if len(hits) > 1:
            return None, ("Hay varios:\n" + "\n".join("\u2022 " + h[1] for h in hits[:6])
                          + "\nS\u00e9 m\u00e1s espec\u00edfico.")
        return hits[0][0], hits[0][1]

    # ---------------------------------------------------------- tarjetas
    def tarjeta(self, ficha, resumen=None):
        """El aviso de una novedad.  Todo lo de afuera de la cita es dato
        duro. La cita es lo unico que escribio la IA."""
        emoji = self.emoji_de(ficha["clave"])
        lineas = ["%s <b>%s</b>" % (emoji, N.escapar(self.nombre_de(ficha["clave"]).upper()))]

        for it in ficha["items"][:CFG.MAX_POR_MENSAJE]:
            lineas.append("%s %s" % (icono(it["tipo"]),
                                     N.enlace(it["titulo"], it["url"])))
        sobran = len(ficha["items"]) - CFG.MAX_POR_MENSAJE
        if sobran > 0:
            lineas.append("<i>y %d cosas m\u00e1s</i>" % sobran)

        if ficha.get("vence"):
            lineas.append("\u23F3 entrega %s" % fecha_linda(ficha["vence"]))

        texto = "\n".join(lineas)
        if resumen:
            texto += "\n" + N.cita(
                "\U0001F9E0 " + N.escapar(resumen["corto"])
                + (("\n\n" + N.escapar(resumen["largo"])) if resumen.get("largo") else ""),
                plegable=bool(resumen.get("largo")))
        texto += "\n<i>%s</i>" % ahora().strftime("%H:%M")
        return texto

    def botones_tarjeta(self, tarea_id, clave, hecha=False, es_tarea=True):
        """Lo que entregas se marca hecho.  Lo que solo hay que mirar se
        marca visto.  Mientras no lo marques, queda en Pendientes."""
        if hecha:
            primero = "\u21A9\uFE0F deshacer"
        else:
            primero = "\u2705 hecho" if es_tarea else "\U0001F440 lo vi"
        return N.teclado([
            [(primero, "hecho:" + tarea_id),
             ("\U0001F4DD nota", "nota:" + tarea_id)],
            [("\u23F0 1h", "dormir1:" + tarea_id),
             ("\u23F0 3h", "dormir:" + tarea_id),
             ("\U0001F515", "basta:" + clave)],
        ])

    def redibujar_tarjeta(self, tarea_id, mensaje_id=None):
        t = self.estado.get("tareas", {}).get(tarea_id)
        if not t:
            return
        mensaje_id = mensaje_id or t.get("mensaje_id")
        if not mensaje_id:
            return
        if t.get("hecho"):
            cuerpo = "\u2705 <s>%s</s>" % N.escapar(t["titulo"])
        else:
            cuerpo = t.get("tarjeta") or ("\U0001F4DD " + N.escapar(t["titulo"]))
        # La nota va SIEMPRE, esa es la confirmacion de que qued\u00f3 guardada.
        if t.get("nota"):
            cuerpo += "\n\U0001F4DD <i>%s</i>" % N.escapar(t["nota"])
        N.editar(mensaje_id, cuerpo,
                 self.botones_tarjeta(tarea_id, t.get("clave", ""), t.get("hecho"),
                                      t.get("es_tarea", True)))

    # ---------------------------------------------------------- animacion
    def animar(self, titulo):
        """Devuelve (avisar, cerrar).  Solo se usa cuando vos estas mirando.

        Se mueve sola, en su propio hilo, aunque la IA este trabada esperando
        una respuesta.  Abajo va la etapa real, que es informacion de verdad,
        con los puntos suspensivos creciendo hasta tres y volviendo a cero.
        Cada tanto se cuela una frase de compania.  Las etapas nunca mienten:
        si se queda en una, ahi esta el problema."""
        mid = N.enviar("\U0001F9E0 <b>%s</b>\n<i>%s</i>"
                       % (N.escapar(titulo), CFG.ETAPAS["buscando"]))
        vivo = threading.Event()
        vivo.set()
        cabeza = N.escapar(titulo)
        est = {"etapa": CFG.ETAPAS["buscando"], "tic": 0, "frase": 0,
               "ultimo": ""}

        def pintar():
            puntos = "." * (est["tic"] % (getattr(CFG, "ANIM_PUNTOS", 3) + 1))
            cada = getattr(CFG, "ANIM_CADA_FRASE", 5)
            frases = getattr(CFG, "FRASES", []) or [""]
            # Alterna: unos tics con la etapa real, unos con una frase suelta.
            vuelta = est["tic"] // max(cada, 1)
            if vuelta % 2 == 1 and frases:
                base = frases[(vuelta // 2 + est["frase"]) % len(frases)]
            else:
                base = est["etapa"]
            texto = "\U0001F9E0 <b>%s</b>\n<i>%s%s</i>" % (
                cabeza, N.escapar(base), puntos)
            if texto == est["ultimo"] or not mid:
                return
            est["ultimo"] = texto
            N.editar(mid, texto, limpiar_botones=False)

        def latir():
            while vivo.is_set():
                if vivo.wait(getattr(CFG, "ANIM_SEGUNDOS", 9.0)):
                    if not vivo.is_set():
                        return
                est["tic"] += 1
                try:
                    pintar()
                except Exception:
                    return

        hilo = None
        if mid:
            hilo = threading.Thread(target=latir, daemon=True)
            hilo.start()

        def avisar(etiqueta):
            """Cambia la etapa real. El movimiento lo pone el hilo."""
            if not mid or not etiqueta:
                return
            est["etapa"] = etiqueta
            est["tic"] = 0
            est["frase"] += 1
            try:
                pintar()
            except Exception:
                pass

        def cerrar(texto_final, botones=None):
            vivo.clear()
            if hilo:
                hilo.join(timeout=1.5)
            if mid:
                if not N.editar(mid, texto_final, botones):
                    N.enviar(texto_final, botones=botones)
            else:
                N.enviar(texto_final, botones=botones)

        return avisar, cerrar

    # ---------------------------------------------------------- panel
    def panel_tapado(self, mid):
        """.Quedo el panel enterrado bajo mensajes mas nuevos?

        Redibujarlo editando alla arriba, fuera de la vista, es igual a no
        contestar: el dueno escribe /compartir, se le borra lo que escribio
        y no aparece nada nuevo.  Ese era el silencio."""
        try:
            ultimo = int(getattr(N, "ULTIMO_MANDADO", 0) or 0)
            return bool(ultimo and int(mid) < ultimo)
        except Exception:
            return False

    def dibujar_panel(self, donde=None, mensaje_id=None):
        donde = donde or self.estado.get("panel_donde") or "p:raiz"
        if donde.startswith("c:") and not donde.startswith("c:si:"):
            texto, botones = P.confirmar_callar(self.estado, self.acc, donde[2:])
        else:
            texto, botones = P.pantalla(self.estado, donde, self.acc)
        self.estado["panel_donde"] = donde
        mid = mensaje_id or self.estado.get("panel_id")
        # Tapado se manda uno nuevo abajo, que es donde el dueno esta
        # mirando: cada orden tiene que tener respuesta visible.
        if mid and not mensaje_id and self.panel_tapado(mid):
            mid = None
        if mid and N.editar(mid, texto, botones):
            self.estado["panel_id"] = mid
            return
        self.abrir_panel(texto, botones)

    def abrir_panel(self, texto=None, botones=None, saludar=False):
        if texto is None:
            texto, botones = P.pantalla(self.estado, "p:raiz", self.acc)
            self.estado["panel_donde"] = "p:raiz"
        viejo = self.estado.get("panel_id")
        mid = N.enviar(texto, botones=botones)
        if mid:
            self.estado["panel_id"] = mid
            # No se ancla nada.  Cada anclada deja un cartelito en el chat y
            # ensucia mas de lo que ayuda.  Si algun dia lo queres, prende
            # ANCLAR_PANEL en fuentes.py.
            if getattr(CFG, "ANCLAR_PANEL", False):
                if self.estado.get("panel_anclado") != mid:
                    if self.estado.get("panel_anclado"):
                        N.desanclar(self.estado["panel_anclado"])
                    N.anclar(mid)
                    self.estado["panel_anclado"] = mid
            elif self.estado.get("panel_anclado"):
                N.desanclar(self.estado.pop("panel_anclado"))
            if viejo and viejo != mid:
                N.borrar(viejo)
        # Nada de "aca abajo te dejo los atajos": la botonera ya se ve sola.
        # Si molesta, se saca con /atajos.
        if saludar and self.cfg().get("teclado", getattr(CFG, "TECLADO_FIJO", True)):
            self.estado["_poner_teclado"] = True

    # ---------------------------------------------------------- charla
    def libreta(self):
        """Lo unico que ve la IA cuando charlas con ella.

        A proposito NO van: direcciones, usuarios, claves, ni el contenido de
        los archivos.  Solo la libreta: que ramos hay, que subieron, cuando
        vence y tus notas.  Con eso alcanza para casi todo lo que se pregunta,
        y si un dia la clave se filtra, lo que se filtro son titulos."""
        hoy = ahora()
        piezas = ["HOY: " + hoy.strftime("%A %d/%m/%Y %H:%M")]

        ramos = [v.get("nombre", "?") for v in self.estado.get("grupos", {}).values()]
        if ramos:
            piezas.append("RAMOS: " + ", ".join(sorted(ramos)))

        pend = [t for t in self.estado.get("tareas", {}).values() if not t.get("hecho")]
        pend.sort(key=lambda t: t.get("vence") or "9999")
        if pend:
            filas = []
            for t in pend[:20]:
                fila = "- %s (%s)" % (t.get("titulo", "?"), t.get("grupo") or "sin ramo")
                if t.get("vence"):
                    fila += " vence %s" % t["vence"]
                if t.get("nota"):
                    fila += " | mi nota: %s" % t["nota"]
                filas.append(fila)
            piezas.append("PENDIENTES\n" + "\n".join(filas))

        hechas = [t for t in self.estado.get("tareas", {}).values() if t.get("hecho")]
        if hechas:
            piezas.append("YA LISTAS: " + ", ".join(t.get("titulo", "?") for t in hechas[:15]))

        nov = self.estado.get("novedades", [])[:30]
        if nov:
            piezas.append("ULTIMO QUE SUBIERON\n" + "\n".join(
                "- %s | %s | %s | %s" % (n.get("f", ""), n.get("g", ""),
                                         n.get("tipo", ""), n.get("t", ""))
                for n in nov))
        return "\n\n".join(piezas)

    def preguntar(self, pregunta, cerrar=None):
        """Charla.  Un pedido, una respuesta.

        Dos reglas de esta version: no te repito tu propio mensaje, y si ya hay
        una animacion en el chat la respuesta la reemplaza, asi no llegan dos
        mensajes por lo mismo."""
        panel = N.teclado([[("\U0001F431 Panel", "p:raiz")]])
        if cerrar is None:
            avisar, cerrar = self.animar("Pensando")
            avisar(CFG.ETAPAS["pensando"])
        # Se mira si se puede INTENTAR, no si esta "disponible": el descanso
        # lo decide el bot solo, y no puede callarlo justo cuando le hablan.
        if not IA.se_puede_intentar(self.estado):
            cerrar("No te puedo contestar: " + N.escapar(self.por_que_no_hay_ia()),
                   panel)
            return
        respuesta = IA.preguntar(self.estado, pregunta, self.libreta())
        if not respuesta:
            cerrar("No pude contestarte ahora: %s"
                   % N.escapar(self.estado.get("ultimo_error_ia",
                                               "no me lleg\u00f3 respuesta"))[:200],
                   panel)
            return
        cerrar(N.cita("\U0001F9E0 " + N.escapar(respuesta)), panel)

    # ------------------------------------------------ ordenes habladas
    def _contexto_orden(self):
        """Lo minimo que la IA necesita para traducir un pedido."""
        hoy = ahora()
        ramos = [v.get("nombre", "?") for v in self.estado.get("grupos", {}).values()]
        pend = [t.get("titulo", "") for t in self.estado.get("tareas", {}).values()
                if not t.get("hecho")]
        return "AHORA: %s\nRAMOS: %s\nPENDIENTES: %s" % (
            hoy.strftime("%Y-%m-%d %H:%M (%A)"),
            ", ".join(sorted(ramos)) or "ninguno",
            " | ".join(pend[:20]) or "ninguno")

    def _en_cuanto(self, f):
        """Cuanto falta, calculado por el programa y no por la IA."""
        seg = (f - ahora()).total_seconds()
        if seg < 90:
            return "en un ratito"
        if seg < 5400:
            return "en %d minutos" % int(seg / 60)
        if seg < 172800:
            return "en %d horas" % int(seg / 3600)
        return "en %d d\u00edas" % int(seg / 86400)

    def validar_orden(self, orden):
        """El programa revisa lo que entendio la IA y arma la confirmacion.

        Devuelve (plan, texto).  Si el plan es None, el texto explica por que
        no se puede hacer.  Aca no se ejecuta nada todavia."""
        que = str((orden or {}).get("accion", "")).strip().lower()
        pie = "\n<i>Estos datos los resolv\u00ed yo, no la IA.</i>"

        if que == "recordar":
            f = leer_fecha(str(orden.get("cuando", "")))
            texto = str(orden.get("que", "")).strip()[:200]
            if not f:
                return None, "Entend\u00ed un recordatorio pero no la fecha. Decime la hora."
            if not texto:
                return None, "Y qu\u00e9 te recuerdo?"
            if (f - ahora()).total_seconds() < 30:
                return None, "Esa hora ya pas\u00f3. Decime una futura."
            if (f - ahora()).days > 365:
                return None, "Eso est\u00e1 demasiado lejos, no lo anoto."
            plan = {"accion": "recordar", "cuando": f.strftime("%Y-%m-%d %H:%M"),
                    "que": texto}
            return plan, ("\U0001F916 <b>Confirmame esto</b>\n"
                          "\u23F0 Recordatorio: %s\n"
                          "Cu\u00e1ndo: %s a las %s (%s)\n"
                          "Suena una sola vez.%s"
                          % (N.escapar(texto), f.strftime("%d/%m"),
                             f.strftime("%H:%M"), self._en_cuanto(f), pie))

        if que == "pausa":
            try:
                horas = float(orden.get("horas", 3))
            except Exception:
                horas = 3.0
            horas = max(0.25, min(horas, 72.0))
            hasta = ahora() + dt.timedelta(hours=horas)
            plan = {"accion": "pausa", "horas": horas}
            return plan, ("\U0001F916 <b>Confirmame esto</b>\n"
                          "\u23F8 Me callo %s, hasta las %s\n"
                          "Los plazos que venzan te llegan igual.%s"
                          % (self._en_cuanto(hasta).replace("en ", "por "),
                             hasta.strftime("%H:%M"), pie))

        if que == "seguir":
            return {"accion": "seguir"}, ("\U0001F916 <b>Confirmame esto</b>\n"
                                          "\u25B6 Vuelvo a avisarte ya mismo.%s" % pie)

        if que in ("callar", "resumen") and str(orden.get("ramo", "")).strip():
            clave, aviso = self.buscar(str(orden.get("ramo", "")))
            if not clave:
                return None, aviso
            if que == "callar":
                return ({"accion": "callar", "clave": clave},
                        "\U0001F916 <b>Confirmame esto</b>\n\U0001F515 Silencio %s "
                        "por %d d\u00edas\nLas entregas con fecha te llegan igual.%s"
                        % (N.escapar(aviso), CFG.DIAS_CALLADO, pie))
            return ({"accion": "resumen", "clave": clave},
                    "\U0001F916 <b>Confirmame esto</b>\n\U0001F9E0 Resumen de %s%s"
                    % (N.escapar(aviso), pie))

        if que == "perfil":
            perfil = pelado(str(orden.get("perfil", "")))
            if perfil not in CFG.PERFILES:
                return None, "Los perfiles son: suave, normal, apretado, diario."
            ramo = str(orden.get("ramo", "")).strip()
            if ramo:
                clave, aviso = self.buscar(ramo)
                if not clave:
                    return None, aviso
                plan = {"accion": "perfil", "perfil": perfil, "clave": clave}
                donde = N.escapar(aviso)
            else:
                plan = {"accion": "perfil", "perfil": perfil, "clave": ""}
                donde = "todos los ramos"
            return plan, ("\U0001F916 <b>Confirmame esto</b>\n"
                          "\u2699 Perfil <b>%s</b> para %s\n%s%s"
                          % (perfil, donde, N.escapar(comandos.explicar_perfil(perfil)), pie))

        if que == "revisar":
            return {"accion": "revisar"}, ("\U0001F916 <b>Confirmame esto</b>\n"
                                           "\U0001F50E Miro las dos plataformas ahora.%s" % pie)

        if que == "noche":
            ahora_noche = self.cfg().get("noche", True)
            return {"accion": "noche"}, ("\U0001F916 <b>Confirmame esto</b>\n"
                                         "\U0001F319 Madrugada: paso de <b>%s</b> a <b>%s</b>%s"
                                         % ("sin sonido" if ahora_noche else "con sonido",
                                            "con sonido" if ahora_noche else "sin sonido", pie))

        if que == "hecho":
            pedazo = pelado(str(orden.get("tarea", "")))
            if not pedazo:
                return None, "No entend\u00ed cu\u00e1l tarea."
            hits = [(i, t) for i, t in self.estado.get("tareas", {}).items()
                    if not t.get("hecho") and pedazo in pelado(t.get("titulo", ""))]
            if not hits:
                return None, "No tengo ninguna pendiente que se parezca a eso."
            if len(hits) > 1:
                return None, ("Hay varias:\n" + "\n".join(
                    "\u2022 " + N.escapar(t.get("titulo", "")) for _, t in hits[:6]))
            idt, t = hits[0]
            return ({"accion": "hecho", "idt": idt},
                    "\U0001F916 <b>Confirmame esto</b>\n\u2705 Marco como hecha:\n%s%s"
                    % (N.escapar(t.get("titulo", "")), pie))

        if que in ("buscar_archivos", "archivos", "material"):
            ramo = str(orden.get("ramo", "")).strip()
            if not ramo:
                return None, ("\u00bfDe qu\u00e9 ramo? Decime el nombre, por ejemplo "
                              "\u00abmandame los archivos de c\u00e1lculo\u00bb.")
            clave, aviso = self.buscar(ramo)
            if not clave:
                return None, aviso
            desde = str(orden.get("desde", "") or "")[:10]
            hasta = str(orden.get("hasta", "") or "")[:10]
            nombre = str(orden.get("nombre", "") or "")[:80]
            tipo = str(orden.get("tipo", "todo") or "todo").strip().lower()
            if tipo not in GRUPOS_DE_TIPO:
                tipo = "todo"
            # "el ultimo archivo" y "lo del ultimo dia": la IA solo avisa
            # que pediste eso; la fecha exacta la busca el programa.
            ultimo = pelado(str(orden.get("ultimo", "") or ""))
            if ultimo in ("1", "true", "si", "uno", "archivo", "ultimo"):
                ultimo = "uno"
            elif ultimo in ("dia", "jornada", "ultimo_dia", "clase"):
                ultimo = "dia"
            else:
                ultimo = ""
            alcance = "" if (desde or hasta) else getattr(
                CFG, "ALCANCE_POR_DEFECTO", "semana")
            if ultimo and not (desde or hasta):
                # Lo ultimo puede ser de hace un mes: mirar solo la ultima
                # semana seria decir "no hay nada" teniendo el archivo.
                alcance = "todo"
            # Buscar, contar y medir es trabajo del programa.  La IA solo dijo
            # ramo, fechas, nombre y tipo.
            elegidos, total, rango = self.filtrar_archivos(
                clave, alcance, desde, hasta, nombre, tipo)
            if ultimo and elegidos:
                elegidos, desde, hasta, nombre, rango = self._solo_lo_ultimo(
                    elegidos, ultimo, nombre)
                alcance = ""
            if not elegidos:
                # Antes este camino ni siquiera mostraba los parecidos: el
                # pedido hablado se moria en "no encontre nada".
                return None, self._sin_resultados(
                    clave, aviso, rango, nombre, tipo, total,
                    alcance, desde, hasta)
            plan = {"accion": "mandar_archivos", "clave": clave,
                    "alcance": alcance, "desde": desde, "hasta": hasta,
                    "nombre": nombre, "tipo": tipo}
            return plan, self.texto_confirmar_archivos(clave, elegidos, rango)

        return None, ""

    def ejecutar_plan(self, plan):
        """Hace lo que ya confirmaste. Devuelve el texto de cierre."""
        que = plan.get("accion")
        if que == "recordar":
            f = leer_fecha(plan["cuando"])
            tareas = self.estado.setdefault("tareas", {})
            # Este camino (el del pedido hablado) se habia quedado con las dos
            # fallas viejas de /recordar:
            #  1. el id sin correr los segundos, asi que dos apuntes de la
            #     misma hora se pisaban y uno desaparecia sin avisar;
            #  2. sin es_tarea=False, asi que tus apuntes caian en la seccion
            #     "PARA ENTREGAR", como si fueran entregas de un profe.
            idt = "mio_%d" % int(f.timestamp())
            while idt in tareas:
                f += dt.timedelta(seconds=1)
                idt = "mio_%d" % int(f.timestamp())
            tareas[idt] = {
                "grupo": "", "clave": "", "titulo": plan["que"], "url": "",
                "vence": f.strftime("%Y-%m-%d %H:%M"), "hecho": False,
                "nota": "", "mio": True, "es_tarea": False}
            return "\u2705 Anotado: <b>%s</b>\nTe aviso el %s a las %s, una sola vez." % (
                N.escapar(plan["que"]), f.strftime("%d/%m"), f.strftime("%H:%M"))
        if que == "pausa":
            hasta = ahora() + dt.timedelta(hours=plan["horas"])
            self.cfg()["pausa_hasta"] = hasta.strftime("%Y-%m-%d %H:%M")
            return "\u23F8 Me callo hasta las %s." % hasta.strftime("%H:%M")
        if que == "seguir":
            self.cfg()["pausa_hasta"] = None
            return "\u25B6 Volv\u00ed."
        if que == "callar":
            hasta = ahora() + dt.timedelta(days=CFG.DIAS_CALLADO)
            self.estado.setdefault("callados", {})[plan["clave"]] = {
                "hasta": hasta.strftime("%Y-%m-%d"), "cuenta": 0}
            return "\U0001F515 %s callado hasta el %s." % (
                N.escapar(self.nombre_de(plan["clave"])), hasta.strftime("%d/%m"))
        if que == "perfil":
            if plan.get("clave"):
                self.estado.setdefault("perfiles", {})[plan["clave"]] = plan["perfil"]
                return "\u2699 %s queda en <b>%s</b>." % (
                    N.escapar(self.nombre_de(plan["clave"])), plan["perfil"])
            self.cfg()["perfil"] = plan["perfil"]
            return "\u2699 Todos los ramos pasan a <b>%s</b>." % plan["perfil"]
        if que == "revisar":
            self.estado["_revisar_ya"] = True
            return "\U0001F50E Voy a mirar ahora."
        if que == "noche":
            self.cfg()["noche"] = not self.cfg().get("noche", True)
            return ("\U0001F319 De madrugada llego sin sonido."
                    if self.cfg()["noche"] else "\U0001F319 Ahora sueno a cualquier hora.")
        if que == "resumen":
            self.resumen_ramo(plan["clave"])
            return ""
        if que in ("mandar_sueltos", "mandar_paquete"):
            # Vale para este pedido nomas: no te cambia la preferencia fija.
            self.cfg()["material_una_vez"] = ("suelto" if que == "mandar_sueltos"
                                              else "paquete")
            self.pedir_archivos(plan["clave"], plan.get("alcance") or "",
                                plan.get("desde", ""), plan.get("hasta", ""),
                                plan.get("nombre", ""), plan.get("tipo", "todo"),
                                confirmado=True)
            return ""
        if que == "mandar_archivos":
            self.pedir_archivos(plan["clave"], plan.get("alcance") or "",
                                plan.get("desde", ""), plan.get("hasta", ""),
                                plan.get("nombre", ""), plan.get("tipo", "todo"),
                                confirmado=True)
            return ""
        if que == "hecho":
            t = self.estado.get("tareas", {}).get(plan["idt"])
            if not t:
                return "Esa ya no la tengo."
            t["hecho"] = True
            return "\u2705 Listo: <b>%s</b>." % N.escapar(t.get("titulo", ""))
        return "No supe qu\u00e9 hacer con eso."

    def orden_local(self, texto):
        """Lo que el programa entiende SOLO, sin IA.

        Sirve para dos cosas: que las ordenes anden con la IA apagada, y como
        red cuando la IA contesta cualquier cosa.  Todo lo que sale de aca es
        un pedido crudo, que despues pasa igual por validar_orden."""
        crudo = str(texto or "").strip()
        t = pelado(crudo)
        if not t:
            return None

        # Forma directa: "recordame el lunes a las 8 estudiar".
        for arranque in ("recordame", "recuerdame", "recordarme", "acordame",
                         "avisame", "avisarme", "recorda", "recuerda",
                         "despertame", "despiertame", "levantame",
                         "no me dejes olvidar", "acordate"):
            if t.startswith(arranque):
                resto = crudo[len(arranque):].strip()
                f, que = self._fecha_del_pedido(resto)
                if not f:
                    return None
                return {"accion": "recordar",
                        "que": self._limpiar_que(que) or "lo que me pediste",
                        "cuando": f.strftime("%Y-%m-%d %H:%M")}

        # Forma armada: "hazme un recordatorio de levantarme en 2 min".
        # Esto antes no lo entendia, y con la IA sin cupo el pedido se perdia
        # entero.  Ahora lo resuelve el programa solo, sin gastar nada.
        m = re.match(
            r"^\s*(?:hazme|haceme|hac[e\u00e9]me|hacer|ponme|poneme|pon[e\u00e9]me|"
            r"pon|crea|crear|cr[e\u00e9]ame|crearme|agrega|agregame|a\u00f1ade|"
            r"anade|anota|anotame|apunta|apuntame|programa|programame|"
            r"dejame|d[e\u00e9]jame|quiero|necesito|tengo que|hay que|"
            r"me gustaria|me gustar\u00eda)\s+"
            r"(?:un|una|el|la|mi|los|las)?\s*"
            r"(?:recordatorio|recordatorios|recordatoria|aviso|alarma|"
            r"apunte|nota|recuerdo|alerta|timer|cron[o\u00f3]metro)\b"
            r"\s*(?:de|del|para|que|:|,)?\s*(.*)$",
            crudo, re.I)
        if m:
            f, que = self._fecha_del_pedido(m.group(1).strip())
            if f:
                return {"accion": "recordar",
                        "que": self._limpiar_que(que) or "lo que me pediste",
                        "cuando": f.strftime("%Y-%m-%d %H:%M")}

        for arranque in ("mandame los archivos de", "mandame el material de",
                         "pasame los archivos de", "mandame los pdf de",
                         "buscame los archivos de"):
            if t.startswith(arranque):
                ramo = crudo[len(arranque):].strip()
                if not ramo:
                    return None
                pedido = {"accion": "buscar_archivos", "ramo": ramo,
                          "nombre": "", "tipo": "todo", "desde": "", "hasta": ""}
                if "pdf" in t:
                    pedido["tipo"] = "pdf"
                return pedido

        if t in ("seguir", "volve", "volvete", "segui"):
            return {"accion": "seguir"}
        if t in ("revisa", "revisar", "mira ahora", "revisa ahora"):
            return {"accion": "revisar"}
        m = re.match(r"^(pausa|callate|calla)\s*(\d+)?", t)
        if m:
            return {"accion": "pausa", "horas": float(m.group(2) or 3)}
        return None

    def _limpiar_que(self, que):
        """Saca el relleno que queda cuando le arranco la fecha al pedido.

        Sin esto, "hazme un recordatorio de levantarme en 2 min" dejaba el
        titulo "levantarme en", que se lee como algo a medio escribir.
        """
        t = str(que or "").strip()
        t = re.sub(r"^(?:que|de|del|para|a|al|:|,)\s+", "", t, flags=re.I)
        for _ in range(3):
            nuevo = re.sub(
                r"\s+(?:en|dentro|dentro de|a las|a la|para|el|la|los|las|"
                r"de|del|este|esta|hoy|manana|ma\u00f1ana|proximo|pr\u00f3ximo)\s*$",
                "", t, flags=re.I)
            if nuevo == t:
                break
            t = nuevo
        return t.strip(" ,:;.-")

    def _fecha_del_pedido(self, resto):
        """La fecha puede venir al principio o al final.  Prueba las dos."""
        f, que = comandos.cuando(resto, ahora())
        if f:
            return f, que
        piezas = resto.split()
        for i in range(len(piezas) - 1, -1, -1):
            f, sobra = comandos.cuando(" ".join(piezas[i:]), ahora())
            if f:
                queda = piezas[:i] + ([sobra] if sobra else [])
                return f, " ".join(queda)
        return None, resto

    def _pedir_confirmacion(self, plan, aviso, cerrar=None):
        """Guarda el plan y muestra los dos botones.  El texto ya viene armado
        por el programa: la IA nunca escribe una confirmacion."""
        # Cada propuesta lleva su propia marca. Sin esto, si te propongo dos
        # cosas seguidas, el boton Dale de la PRIMERA ejecutaba el plan de la
        # segunda: el boton hacia algo distinto de lo que decia arriba.
        marca = self.nueva_marca_de_propuesta(plan)
        self.guardar()
        botones = N.teclado([[("\u2705 Dale", "prop:si:" + marca),
                              ("\u274C No", "prop:no:" + marca)]])
        if cerrar:
            cerrar(aviso, botones)
        else:
            N.enviar(aviso, botones=botones)

    def proponer(self, texto):
        """Le hablas normal y hace cosas.  La IA solo traduce el pedido: el
        que valida, arma la confirmacion y ejecuta es este programa.

        Reglas que no se rompen mas:
        - el texto crudo de la IA no se imprime nunca en este camino
        - no te repito tu propio mensaje
        - toda rama termina en un mensaje para vos
        """
        panel = N.teclado([[("\U0001F431 Panel", "p:raiz")]])
        local = self.orden_local(texto)

        if not IA.se_puede_intentar(self.estado):
            if local:
                plan, aviso = self.validar_orden(local)
                if plan:
                    self._pedir_confirmacion(plan, aviso)
                else:
                    N.enviar(aviso or "No entend\u00ed el pedido.", botones=panel)
                return
            N.enviar("La IA est\u00e1 apagada, as\u00ed que no puedo interpretar lo que "
                     "me escribiste: " + N.escapar(self.por_que_no_hay_ia()),
                     botones=panel)
            return

        avisar, cerrar = self.animar("Entendiendo")
        avisar(CFG.ETAPAS["pensando"])
        orden = IA.interpretar(self.estado, texto, self._contexto_orden()) or {}
        accion = str(orden.get("accion", "")).strip().lower()

        if accion in ("", "ninguna"):
            if local:
                orden, accion = local, local["accion"]
            else:
                # No era una orden: es una pregunta.  Y la respuesta reemplaza
                # a la animacion, no llega un mensaje nuevo.
                self.preguntar(texto, cerrar=cerrar)
                return

        plan, aviso = self.validar_orden(orden)
        if not plan and local and local.get("accion") != accion:
            plan, aviso = self.validar_orden(local)
        if not plan:
            cerrar(aviso or ("No entend\u00ed qu\u00e9 quer\u00e9s que haga. Prob\u00e1 con "
                             "el Panel o escrib\u00edmelo de otra forma."), panel)
            return
        self._pedir_confirmacion(plan, aviso, cerrar=cerrar)

    def nueva_marca_de_propuesta(self, plan, junto_a=""):
        """Guarda la propuesta y devuelve su marca, para que el boton apunte
        exactamente a ESTA y no a la que venga despues."""
        # Un numero que sube de a uno, no la hora: dos pedidos seguidos en el
        # mismo instante llegaban a tener la MISMA marca, y ahi el boton viejo
        # volvia a ejecutar el pedido nuevo, que es justo lo que se quiere
        # evitar.
        n = int(self.estado.get("propuesta_n") or 0) + 1
        self.estado["propuesta_n"] = n % 100000000
        marca = "%d" % n
        # Una misma pregunta puede ofrecer varios botones (mandalos / de a
        # uno / en un paquete).  Si solo quedara guardado el ultimo, los
        # otros dos contestarian "ese boton era de un pedido anterior" y no
        # harian nada: el dueno toca y no pasa nada, que es la peor falla.
        anterior = self.estado.get("propuesta") or {}
        planes = dict(anterior.get("planes") or {}) if junto_a else {}
        planes[marca] = plan
        self.estado["propuesta"] = {"plan": plan, "cuando": time.time(),
                                    "id": marca, "planes": planes}
        return marca

    def confirmar_propuesta(self, si=True, marca=""):
        """El boton de la confirmacion. Devuelve el texto final."""
        p = self.estado.get("propuesta")
        if not p or time.time() - float(p.get("cuando", 0)) > 1800:
            self.estado.pop("propuesta", None)
            return "Esa propuesta ya venci\u00f3. Ped\u00edmelo de nuevo."
        guardada = str(p.get("id") or "")
        # Los botones hermanos de la MISMA pregunta valen todos; los de una
        # pregunta vieja siguen sin valer, que es lo que se queria evitar.
        elegido = (p.get("planes") or {}).get(str(marca)) if marca else None
        if marca and guardada and str(marca) != guardada and not elegido:
            return ("Ese bot\u00f3n era de un pedido anterior. Despu\u00e9s me "
                    "pediste otra cosa, as\u00ed que no toqu\u00e9 nada: "
                    "ped\u00edmelo de nuevo.")
        self.estado.pop("propuesta", None)
        if not si:
            self.guardar()
            return "\u274C Listo, no hice nada."
        try:
            salida = self.ejecutar_plan(elegido or p["plan"])
        except Exception as e:
            log("[!] no pude ejecutar el plan: %s" % e)
            return "No pude hacerlo. Prob\u00e1 con el comando."
        self.guardar()
        self.olvidar_cache()
        return salida

    # ---------------------------------------------------------- cache
    def _memo(self, nombre, fn, vida=8.0):
        """Guarda lo ya calculado por unos segundos.  Cuando navegas rapido
        por el panel, la segunda vez que pasas por una pantalla sale de aca
        y no se vuelve a armar."""
        guardado = self.cache.get(nombre)
        if guardado and time.time() - guardado[0] < vida:
            return guardado[1]
        valor = fn()
        self.cache[nombre] = (time.time(), valor)
        return valor

    def olvidar_cache(self):
        self.cache.clear()

    def precalentar(self):
        """Arma de antemano las tres pantallas que siempre terminas mirando.
        Cuestan milisegundos y se pagan solas al primer toque."""
        for nombre, fn in (("nov", self.texto_novedades),
                           ("pen", self.texto_pendientes),
                           ("sem", self.texto_semana)):
            try:
                self._memo(nombre, fn, vida=20.0)
            except Exception:
                pass

    # ---------------------------------------------------------- textos
    def tablero(self):
        hoy = ahora().date()
        novedades = self.estado.get("novedades", [])
        nuevas_hoy = len([n for n in novedades if n.get("f", "")[:10] == str(hoy)])
        pend = [t for t in self.estado.get("tareas", {}).values() if not t.get("hecho")]
        malas = len(self.estado.get("fallas", {}))
        return {
            "ramos": len(self.estado.get("grupos", {})),
            "pendientes": len(pend),
            "nuevas": min(len(novedades), 99),
            "nuevas_hoy": nuevas_hoy,
            "ultima": self.estado.get("ultima_corrida", "nunca")[-5:] or "nunca",
            "salud": "todo en orden" if not malas else "\u26A0\uFE0F %d problema(s)" % malas,
            "memoria": "gist privado" if self.modo == "gist" else "repositorio (reducida)",
            "ia": IA.en_palabras(self.estado),
            "silenciados": len(self.estado.get("callados", {})),
        }

    def lista_ramos(self):
        return sorted([(k, v.get("nombre", "?"), v.get("emoji", "\U0001F4D8"))
                       for k, v in self.estado.get("grupos", {}).items()],
                      key=lambda x: pelado(x[1]))

    def ficha_ramo(self, clave):
        g = self.estado.get("grupos", {}).get(clave)
        if not g:
            return None
        mios = [n for n in self.estado.get("novedades", []) if n.get("c") == clave]
        return {"nombre": g.get("nombre", "?"), "emoji": g.get("emoji", "\U0001F4D8"),
                "cantidad": len(mios),
                "ultima": mios[0]["f"][5:16].replace("-", "/") if mios else "todav\u00eda nada"}

    def material(self, clave):
        """La lista completa de lo que hay en el ramo, ordenada por tipo.
        Esto es el archivador.  El resumen con IA es otra cosa."""
        mios = [n for n in self.estado.get("novedades", []) if n.get("c") == clave]
        if not mios:
            return "Todav\u00eda no vi nada en este ramo."

        cajones = [("archivo", "\U0001F4C4 Archivos"), ("tarea", "\U0001F4DD Tareas"),
                   ("foro", "\U0001F4AC Foros"), ("material", "\U0001F4CE Otras cosas")]
        bloques = []
        for tipo, encabezado in cajones:
            cosas = [n for n in mios if n.get("tipo", "material") == tipo][:12]
            if not cosas:
                continue
            filas = ["<b>%s</b> (%d)" % (encabezado, len(
                [n for n in mios if n.get("tipo", "material") == tipo]))]
            filas += ["  %s  <i>%s</i>" % (N.enlace(n["t"], n["u"]),
                                           n["f"][5:16].replace("-", "/"))
                      for n in cosas]
            bloques.append("\n".join(filas))
        return "\n\n".join(bloques)

    # ---------------------------------------------- archivos de un ramo
    def leer_ramo_ahora(self, clave):
        """Vuelve a leer el ramo AHORA, entrando adentro de cada actividad y
        pasando por el menu que se arma con javascript.  El boton de archivos
        tiene que ver lo mismo que ve la deteccion automatica: antes uno
        miraba la memoria y el otro la pagina, y por eso se contradecian."""
        g = self.estado.get("grupos", {}).get(clave)
        if not g:
            return []
        s = self.sesiones.get(g.get("fuente"))
        base = self.bases.get(g.get("fuente"))
        if not s or not base:
            return []
        try:
            # Que no me devuelva lo cacheado: quiero lo de este momento.
            _ULTIMO_PROFUNDO.pop(g.get("id"), None)
            _ULTIMO_PROFUNDO.pop(str(g.get("id")), None)
        except Exception:
            pass
        try:
            items, _ = explorar_ramo(s, base, {"id": g.get("id"),
                                               "url": g.get("url"),
                                               "nombre": g.get("nombre", "")})
        except Exception as e:
            log("[!] leyendo el ramo de nuevo: %s" % type(e).__name__)
            return []
        return items or []

    def _fecha_heredada(self, url, fechas):
        """Un adjunto que vive adentro de una actividad hereda la fecha de esa
        actividad.  Sin esto, filtrar por fecha tiraba a la basura justo los
        archivos que no tienen fecha propia."""
        if url in fechas:
            return fechas[url]
        mejor, largo = "", 0
        for u, f in fechas.items():
            if u and url.startswith(u) and len(u) > largo:
                mejor, largo = f, len(u)
        return mejor

    def _dudoso(self, url, titulo=""):
        """Un enlace que no dice de que es: no parece archivo por su nombre,
        pero vive donde la plataforma guarda el material."""
        if not url or es_bajable(url, titulo):
            return False
        u = url.lower()
        return any(p in u for p in PISTAS_DE_ACTIVIDAD)

    def _que_hay_detras(self, s, url):
        """Devuelve "archivo", "pagina", o "" cuando no se pudo saber.

        Lo que no se pudo mirar NO se da por perdido: queda sin anotar para
        volver a intentarlo despues."""
        for metodo in ("head", "get"):
            try:
                if metodo == "head":
                    r = s.head(url, timeout=12, allow_redirects=True)
                else:
                    r = s.get(url, timeout=15, allow_redirects=True, stream=True)
                codigo = getattr(r, "status_code", 0)
                tipo = (r.headers.get("Content-Type") or "").lower()
                pegado = (r.headers.get("Content-Disposition") or "").lower()
                if metodo == "get":
                    try:
                        r.close()
                    except Exception:
                        pass
                if codigo >= 400:
                    continue
                if "attachment" in pegado or "filename" in pegado:
                    return "archivo"
                if tipo and "html" not in tipo and not tipo.startswith("text/"):
                    return "archivo"
                if tipo:
                    return "pagina"
            except Exception:
                continue
        return ""

    def comprobar_dudosos(self, clave, dudosos):
        """Le pregunta al servidor que hay detras de cada enlace raro.

        La plataforma no siempre avisa en el enlace si eso es un archivo o una
        pagina.  Antes esos enlaces se descartaban y el ramo aparecia vacio
        aunque tuviera material: era el caso de "no encontre archivos de todo
        el ramo" teniendo cuatro cosas anotadas.  La respuesta se guarda, asi
        no se pregunta lo mismo cada vez, y va con tope para no castigar a la
        plataforma ni demorar la respuesta."""
        if not getattr(CFG, "COMPROBAR_DUDOSOS", True) or not dudosos:
            return []
        g = self.estado.get("grupos", {}).get(clave, {})
        s = self.sesiones.get(g.get("fuente"))
        if not s:
            return []
        libreta = self.estado.setdefault("tipos_de_enlace", {})
        horas = max(1, getattr(CFG, "HORAS_QUE_VALE_LA_COMPROBACION", 72))
        tope = max(1, getattr(CFG, "DUDOSOS_POR_PEDIDO", 25))
        salida, preguntados = [], 0
        for it in dudosos:
            u = it.get("url") or ""
            if not u:
                continue
            ficha = libreta.get(u) or {}
            if (time.time() - ficha.get("t", 0)) < horas * 3600:
                if ficha.get("es") == "archivo":
                    salida.append(it)
                continue
            if preguntados >= tope:
                continue
            preguntados += 1
            es = self._que_hay_detras(s, u)
            if es:
                libreta[u] = {"es": es, "t": time.time()}
            if es == "archivo":
                salida.append(it)
        # La libreta no puede crecer para siempre: se van los mas viejos.
        if len(libreta) > 900:
            viejos = sorted(libreta.items(), key=lambda x: x[1].get("t", 0))
            for u, _f in viejos[:len(libreta) - 900]:
                libreta.pop(u, None)
        return salida

    def archivos_del_ramo(self, clave, frescos=True):
        """Todo lo que en este ramo se puede bajar de verdad.

        Junta las dos listas que antes no coincidian: lo anotado en la memoria
        y lo que hay ahora en la plataforma.  Un enlace sin extension, del
        tipo /archivo/8891, tambien entra: para eso esta es_bajable.  Y lo que
        queda en duda se le pregunta al servidor antes de descartarlo."""
        fechas = {}
        for n in self.estado.get("novedades", []):
            if n.get("c") == clave and n.get("u"):
                fechas.setdefault(n["u"], n.get("f", ""))
        salida, dudosos = {}, []
        for n in self.estado.get("novedades", []):
            if n.get("c") != clave or not n.get("u"):
                continue
            if n.get("tipo") == "archivo" or es_bajable(n["u"], n.get("t", "")):
                salida[n["u"]] = {"url": n["u"], "titulo": n.get("t") or "archivo",
                                  "cuando": n.get("f", "")}
            elif self._dudoso(n["u"], n.get("t", "")):
                dudosos.append({"url": n["u"], "titulo": n.get("t") or "archivo",
                                "cuando": n.get("f", "")})
        if frescos:
            for it in self.leer_ramo_ahora(clave):
                u = it.get("url") or ""
                if not u or u in salida:
                    continue
                if not es_bajable(u, it.get("titulo", "")):
                    if self._dudoso(u, it.get("titulo", "")):
                        dudosos.append(
                            {"url": u, "titulo": it.get("titulo") or "archivo",
                             "cuando": self._fecha_heredada(u, fechas)})
                    continue
                salida[u] = {"url": u, "titulo": it.get("titulo") or "archivo",
                             "cuando": self._fecha_heredada(u, fechas)}
            faltan = [d for d in dudosos if d["url"] not in salida]
            for it in self.comprobar_dudosos(clave, faltan):
                salida.setdefault(it["url"], it)
        else:
            # Sin tocar la red vale lo que ya se pregunto antes, asi el numero
            # que muestra el panel no puede contradecir a la lista de material.
            libreta = self.estado.get("tipos_de_enlace", {})
            for d in dudosos:
                if (libreta.get(d["url"]) or {}).get("es") == "archivo":
                    salida.setdefault(d["url"], d)
        return sorted(salida.values(), key=lambda x: x.get("cuando") or "",
                      reverse=True)

    def cuantos_archivos(self, clave):
        """El numero que muestra el panel.  Cuenta igual que el boton, asi que
        no puede decir una cosa arriba y otra abajo."""
        return len(self.archivos_del_ramo(clave, frescos=False))

    def filtrar_archivos(self, clave, alcance=None, desde="", hasta="",
                         nombre="", tipo="todo", frescos=True):
        """Busca, filtra y cuenta.  Esto lo hace el programa, nunca la IA.
        Devuelve (elegidos, cuantos_hay_en_total, como_se_dice_el_rango)."""
        d, h = rango_de_fechas(alcance, desde, hasta)
        todos = self.archivos_del_ramo(clave, frescos=frescos)
        elegidos = []
        for a in todos:
            # Se compara por palabras y sin el final del nombre: escribir
            # "Gu\u00eda 3.pdf" tiene que encontrar "Guia N\u00b03".
            if nombre and not calza_nombre(nombre, a):
                continue
            if not de_este_tipo(tipo, a.get("titulo", ""), a.get("url", "")):
                continue
            if d:
                cuando = (a.get("cuando") or "")[:10]
                if not cuando or cuando < str(d) or cuando > str(h):
                    continue
            elegidos.append(a)
        tope = getattr(CFG, "TOPE_ARCHIVOS_DE_UNA", 80)
        return elegidos[:tope], len(todos), rango_lindo(d, h)

    def _sin_resultados(self, clave, titulo, rango, nombre, tipo, total,
                        alcance="", desde="", hasta="", anotadas=0):
        """El "no encontre nada", contado como es.

        Antes, buscando en todo el ramo, contestaba "si tengo N en otras
        fechas".  No habia otras fechas: lo que sobraba era el nombre.  El
        dueno entendia que el archivo no existia, y existia.

        Esta explicacion vive en un solo lugar para que las dos formas de
        buscar, la escrita y la de botones, digan siempre lo mismo.
        """
        hubo_fechas = bool(desde or hasta or (alcance and alcance != "todo"))
        cuantos = lambda n: "%d archivo%s" % (n, "" if n == 1 else "s")
        texto = "En <b>%s</b> no encontr\u00e9 archivos %s." % (
            N.escapar(titulo), rango)
        if nombre:
            texto += "\nBusqu\u00e9 por nombre: <b>%s</b>." % N.escapar(nombre)
        if total and hubo_fechas:
            texto += "\nS\u00ed tengo %d en otras fechas." % total
        elif total and nombre:
            # Aca ya mire el ramo entero: el nombre es lo unico que sobro.
            texto += ("\nDel ramo tengo %s guardado%s, pero ninguno se llama "
                      "as\u00ed." % (cuantos(total), "" if total == 1 else "s"))
        elif total and tipo and tipo != "todo":
            texto += ("\nDel ramo tengo %s, pero ninguno de ese tipo."
                      % cuantos(total))
        elif total:
            texto += "\nDel ramo tengo %s guardado%s." % (
                cuantos(total), "" if total == 1 else "s")
        if nombre:
            parecidos = self.parecidos_a(clave, nombre)
            if parecidos:
                texto += ("\nLo m\u00e1s parecido que tengo:\n"
                          + "\n".join("\u2022 " + N.escapar(p) for p in parecidos)
                          + "\nProb\u00e1 con una sola palabra de esas, o pedime "
                            "todo el ramo y eleg\u00eds vos.")
            elif total:
                texto += ("\nSi ten\u00e9s el nombre a medias, pedime todo el ramo "
                          "y lo busc\u00e1s en la lista.")
        if not total:
            if anotadas:
                texto += ("\nTengo %d cosa%s anotada%s del ramo, pero ninguna es "
                          "un archivo que se pueda bajar."
                          % (anotadas, "" if anotadas == 1 else "s",
                             "" if anotadas == 1 else "s"))
            else:
                texto += "\nTodav\u00eda no vi nada en este ramo."
        return texto

    def parecidos_a(self, clave, nombre, cuantos=4):
        """Lo mas parecido a lo que escribiste.

        Decir "no encontre nada" cuando el archivo estaba ahi con otro
        nombre es la peor respuesta posible: el dueno no tiene forma de
        saber si fallo el bot o si de verdad no existe."""
        pedido = set(_solo_letras(_sin_final(nombre or "")).split())
        if not pedido:
            return []
        puntajes = []
        for a in self.archivos_del_ramo(clave, frescos=False):
            titulo = limpio(a.get("titulo") or "")
            if not titulo:
                continue
            palabras = set(_solo_letras(titulo).split())
            if not palabras:
                continue
            iguales = len(pedido & palabras)
            parecidas = sum(1 for p in pedido for q in palabras
                            if p != q and (p in q or q in p))
            punto = iguales * 3 + parecidas
            if punto:
                puntajes.append((punto, titulo))
        puntajes.sort(key=lambda x: (-x[0], x[1]))
        vistos, salida = set(), []
        for _, titulo in puntajes:
            if titulo in vistos:
                continue
            vistos.add(titulo)
            salida.append(titulo[:60])
            if len(salida) >= cuantos:
                break
        return salida

    def _bajar_uno(self, s, a):
        """Devuelve (crudo, motivo, respuesta).  Si crudo es None, el motivo
        se cuenta en una linea: nada falla en silencio."""
        try:
            r = s.get(a["url"], timeout=CFG.ESPERA_RED)
        except Exception as e:
            return None, "no me pude conectar (%s)" % type(e).__name__, None
        if r.status_code != 200:
            return None, "la plataforma contest\u00f3 %s" % r.status_code, r
        tipo = (r.headers.get("Content-Type") or "").lower()
        pegado = (r.headers.get("Content-Disposition") or "").lower()
        if "html" in tipo and "attachment" not in pegado:
            # Aca es donde llegaba la pagina de ingreso disfrazada de archivo.
            arranque = (r.text or "")[:4000].lower()
            if "password" in arranque or "contrase" in arranque or "login" in arranque:
                return None, "me devolvi\u00f3 la pantalla de ingreso, se cort\u00f3 la sesi\u00f3n", r
            return None, "eso es una p\u00e1gina, no un archivo", r
        if not r.content:
            return None, "lleg\u00f3 vac\u00edo", r
        return r.content, "", r

    def peso_aproximado(self, clave, elegidos):
        """Cuanto pesan, preguntando de a poco y sin bajar nada."""
        g = self.estado.get("grupos", {}).get(clave, {})
        s = self.sesiones.get(g.get("fuente"))
        if not s:
            return 0
        total, mirados = 0, 0
        for a in elegidos[:25]:
            try:
                r = s.head(a["url"], timeout=10, allow_redirects=True)
                largo = int(r.headers.get("Content-Length") or 0)
            except Exception:
                continue
            if largo > 0:
                total += largo
                mirados += 1
        if mirados and len(elegidos) > mirados:
            total = int(total * len(elegidos) / float(mirados))
        return total

    def texto_confirmar_archivos(self, clave, elegidos, rango):
        """La confirmacion la escribe el programa, con numeros de verdad."""
        peso = self.peso_aproximado(clave, elegidos)
        lineas = ["\U0001F4E6 <b>Encontr\u00e9 %d archivo%s</b>"
                  % (len(elegidos), "" if len(elegidos) == 1 else "s"),
                  "Ramo: %s" % N.escapar(self.nombre_de(clave)),
                  rango[0].upper() + rango[1:]]
        if peso:
            lineas.append("Pesan %s en total" % peso_lindo(peso))
        tanda = max(1, getattr(CFG, "ARCHIVOS_POR_TANDA", 5))
        if len(elegidos) > tanda:
            lineas.append("Van por tandas de %d y te cuento el avance" % tanda)
        lineas.append("<i>Estos n\u00fameros los cont\u00e9 yo, no la IA.</i>")
        return "\n".join(lineas)

    def pedir_archivos(self, clave, alcance=None, desde="", hasta="",
                       nombre="", tipo="todo", confirmado=False):
        """La puerta de entrada, venga de un boton o de un pedido hablado.
        Siempre termina en un mensaje: o los archivos, o el motivo."""
        if not self.estado.get("grupos", {}).get(clave):
            N.enviar("Ese ramo ya no est\u00e1.")
            return
        titulo = self.nombre_de(clave)
        elegidos, total, rango = self.filtrar_archivos(
            clave, alcance, desde, hasta, nombre, tipo)

        if not elegidos:
            anotadas = len([n for n in self.estado.get("novedades", [])
                            if n.get("c") == clave])
            texto = self._sin_resultados(clave, titulo, rango, nombre, tipo,
                                         total, alcance, desde, hasta, anotadas)
            N.enviar(texto, botones=N.teclado([
                [("\U0001F4C5 \u00daltimo mes", "a:baj:%s:mes" % clave),
                 ("\U0001F5C2 Todo el ramo", "a:baj:%s:todo" % clave)],
                [("\u2B05\uFE0F Volver", "p:r:" + clave)]]))
            return

        if not confirmado and len(elegidos) >= getattr(CFG, "PREGUNTAR_DESDE", 6):
            # Tres botones para mandar, no uno: asi elegis en el momento como
            # los queres recibir sin tener que entrar a los ajustes.
            base = {"clave": clave, "alcance": alcance or "", "desde": desde or "",
                    "hasta": hasta or "", "nombre": nombre or "",
                    "tipo": tipo or "todo"}
            suelto = self.nueva_marca_de_propuesta(
                dict(base, accion="mandar_sueltos"))
            paquete = self.nueva_marca_de_propuesta(
                dict(base, accion="mandar_paquete"), junto_a=suelto)
            # El de siempre se crea ultimo a proposito: asi es el que queda
            # como la propuesta en curso si algo se corta en el medio.
            marca = self.nueva_marca_de_propuesta(
                dict(base, accion="mandar_archivos"), junto_a=suelto)
            self.guardar()
            N.enviar(self.texto_confirmar_archivos(clave, elegidos, rango),
                     botones=N.teclado([
                         [("\U0001F4E5 Mandalos", "prop:si:" + marca)],
                         [("\U0001F4C4 De a uno", "prop:si:" + suelto),
                          ("\U0001F4E6 En un paquete", "prop:si:" + paquete)],
                         [("\u274C No", "prop:no:" + marca)]]))
            return

        self.mandar_archivos(clave, elegidos, rango)

    def como_mando_el_material(self):
        """Sueltos, en paquete, o que decida solo. Lo elige el dueno."""
        modo = self.cfg().get("material") or getattr(
            CFG, "MODO_ENVIO_MATERIAL", "auto")
        return modo if modo in ("auto", "suelto", "paquete") else "auto"

    def van_juntos(self, cuantos, como=""):
        """Pocos archivos se abren mejor de a uno; muchos tapan el chat.
        'como' es lo que elegiste para ESTE pedido: manda sobre la
        preferencia de siempre y despues se olvida."""
        if cuantos < 2:
            return False
        modo = (como if como in ("suelto", "paquete")
                else self.como_mando_el_material())
        if modo == "suelto":
            return False
        if modo == "paquete":
            return True
        return cuantos > max(1, getattr(CFG, "SUELTOS_HASTA", 4))

    def _es_paquete(self, como, crudo):
        """Esto que baje, .es un paquete ya armado por la plataforma?
        Los paquetes empiezan siempre con las mismas dos letras, asi que no
        hace falta creerle al nombre del archivo."""
        if str(como or "").lower().endswith(".zip"):
            return True
        return bool(crudo) and crudo[:2] == b"PK"

    def desarmar_paquetes(self, listos):
        """La plataforma tiene un boton propio de 'descargar todo' que entrega
        UN solo archivo comprimido.  Mandartelo tal cual era el peor de los
        mundos: pedias dos apuntes, te llegaba una cosa que hay que abrir en
        el computador, y encima parecia que el bot ignoraba tu preferencia de
        recibirlos de a uno.  Aca lo abro yo y te dejo lo de adentro."""
        if not getattr(CFG, "DESARMAR_PAQUETES", True):
            return listos
        import io
        import zipfile
        tope = max(1, getattr(CFG, "ARCHIVOS_DE_UN_PAQUETE", 25))
        salida, cambio = [], False
        for como, crudo, a in listos:
            if not self._es_paquete(como, crudo):
                salida.append((como, crudo, a))
                continue
            try:
                z = zipfile.ZipFile(io.BytesIO(crudo))
                adentro = [n for n in z.namelist()
                           if not n.endswith("/") and not n.startswith("__MACOSX")]
            except Exception as e:
                # Si no se deja abrir, no se pierde nada: va como vino.
                log("[!] no pude abrir el paquete: %s" % type(e).__name__)
                salida.append((como, crudo, a))
                continue
            # Vacio o gigante: mejor dejarlo cerrado que inundar el chat.
            if not adentro or len(adentro) > tope:
                salida.append((como, crudo, a))
                continue
            for nombre in adentro:
                try:
                    datos = z.read(nombre)
                except Exception:
                    continue
                if not datos:
                    continue
                corto = (nombre.replace("\\", "/").split("/")[-1] or "archivo")[:80]
                ficha = dict(a)
                ficha["titulo"] = corto
                ficha["de_un_paquete"] = True
                salida.append((corto, datos, ficha))
                cambio = True
        return salida if cambio else listos

    def armar_paquete(self, titulo, listos):
        """Un solo archivo con todo adentro, sin nombres repetidos."""
        import io
        import zipfile
        datos = io.BytesIO()
        usados = {}
        try:
            with zipfile.ZipFile(datos, "w", zipfile.ZIP_DEFLATED) as z:
                for como, crudo, _a in listos:
                    base = como or "archivo"
                    veces = usados.get(base, 0) + 1
                    usados[base] = veces
                    nombre = base
                    if veces > 1:
                        raiz, punto, ext = base.rpartition(".")
                        nombre = ("%s (%d).%s" % (raiz, veces, ext) if punto
                                  else "%s (%d)" % (base, veces))
                    z.writestr(nombre, crudo)
        except Exception as e:
            log("[!] armando el paquete: %s" % type(e).__name__)
            return None, ""
        etiqueta = re.sub(r"[^0-9a-z]+", "_", pelado(titulo))[:40].strip("_")
        como = "%s_%s_%s.zip" % (getattr(CFG, "NOMBRE_DEL_PAQUETE", "material"),
                                 etiqueta or "ramo", ahora().strftime("%d-%m"))
        return datos.getvalue(), como

    def mandar_archivos(self, clave, elegidos, rango=""):
        """Los baja y los manda por tandas.  Nunca manda el mismo dos veces y
        nunca deja una falla callada."""
        # Lo que elegiste en el boton vale solo para este pedido, por eso se
        # saca de la configuracion apenas se usa.
        una_vez = self.cfg().pop("material_una_vez", "")
        g = self.estado.get("grupos", {}).get(clave, {})
        titulo = g.get("nombre", "ese ramo")
        s = self.sesiones.get(g.get("fuente"))
        if not s:
            N.enviar("No pude entrar a la plataforma de <b>%s</b> ahora, as\u00ed que "
                     "no puedo bajar nada. Te dejo los enlaces:\n\n%s"
                     % (N.escapar(titulo),
                        "\n".join("\U0001F4C4 " + N.enlace(a["titulo"], a["url"])
                                  for a in elegidos[:10])),
                     botones=N.teclado([[("\u2B05\uFE0F Volver", "p:r:" + clave)]]))
            return 0

        total = len(elegidos)
        avisar, cerrar = self.animar("archivos de " + titulo)
        cada = max(1, getattr(CFG, "AVISAR_AVANCE_CADA", 10))
        tope = CFG.PESO_ADJUNTO_MB * 1024 * 1024
        mandados, repetidos, fallados, huellas = 0, 0, [], set()
        listos, en_paquete = [], False

        for i, a in enumerate(elegidos, 1):
            avisar("bajando %d de %d" % (i, total))
            crudo, motivo, r = self._bajar_uno(s, a)
            if crudo is None:
                fallados.append((a, motivo))
                continue
            marca = hashlib.sha256(crudo).hexdigest()
            if marca in huellas:
                repetidos += 1
                continue
            huellas.add(marca)
            if len(crudo) > tope:
                fallados.append((a, "pesa %s y la mensajer\u00eda aguanta %d MB"
                                 % (peso_lindo(len(crudo)), CFG.PESO_ADJUNTO_MB)))
                continue
            listos.append((nombre_de_archivo(r, a["url"],
                                             a.get("titulo", "archivo")), crudo, a))

        # Pocos archivos van tal cual, asi se abren de una desde el telefono.
        # Muchos van en un solo paquete, porque veinte mensajes seguidos tapan
        # el chat y despues no encontras nada.  Si el paquete no se pudo armar
        # o pesa demasiado, no se pierde nada: salen sueltos igual.
        antes = len(listos)
        listos = self.desarmar_paquetes(listos)
        abiertos = len(listos) - antes
        if abiertos > 0:
            # Ahora hay mas archivos que los que pediste: son los que venian
            # adentro.  El resumen final tiene que hablar de estos.
            total = len(listos)

        if self.van_juntos(len(listos), una_vez):
            avisar("armando el paquete con %d archivos" % len(listos))
            paquete, como = self.armar_paquete(titulo, listos)
            if paquete and len(paquete) <= tope and N.mandar_documento(
                    como, paquete,
                    leyenda="\U0001F4E6 %d archivos de %s"
                    % (len(listos), N.escapar(titulo)), silencioso=True):
                mandados, en_paquete = len(listos), True

        if not en_paquete:
            for como, crudo, a in listos:
                if N.mandar_documento(como, crudo, silencioso=True):
                    mandados += 1
                else:
                    fallados.append((a, "la mensajer\u00eda no lo acept\u00f3"))
                if mandados and mandados % cada == 0 and mandados < total:
                    avisar("van %d de %d" % (mandados, total))

        lineas = []
        if mandados and en_paquete:
            lineas.append("\U0001F4E6 Te mand\u00e9 los <b>%d</b> archivos de <b>%s</b> "
                          "en un solo paquete" % (mandados, N.escapar(titulo)))
            lineas.append("Toc\u00e1ndolo se abre y ves todo adentro. Si los prefer\u00eds "
                          "de a uno, cambialo en Ajustes \u2192 M\u00e1s.")
        elif mandados:
            lineas.append("\U0001F4E5 Te mand\u00e9 <b>%d</b> de %d archivo%s de <b>%s</b>"
                          % (mandados, total, "" if total == 1 else "s",
                             N.escapar(titulo)))
            if rango:
                lineas.append(rango[0].upper() + rango[1:])
        else:
            lineas.append("No pude bajar ninguno de los %d archivos de <b>%s</b>."
                          % (total, N.escapar(titulo)))
        if abiertos > 0 and not en_paquete:
            lineas.append("La plataforma me los dio todos juntos en un solo "
                          "paquete y te lo abr\u00ed: por eso los ves de a uno.")
        if repetidos:
            lineas.append("%d era%s el mismo archivo repetido, no te lo mand\u00e9 dos veces."
                          % (repetidos, "" if repetidos == 1 else "n"))
        if fallados:
            lineas.append("")
            lineas.append("<b>Estos no pude:</b>")
            for a, motivo in fallados[:8]:
                lineas.append("\u26A0\uFE0F %s \u00b7 %s"
                              % (N.enlace(a.get("titulo", "archivo"), a["url"]),
                                 N.escapar(motivo)))
            if len(fallados) > 8:
                lineas.append("<i>y %d m\u00e1s</i>" % (len(fallados) - 8))
        cerrar("\n".join(lineas),
               N.teclado([[("\U0001F4C4 Ver material", "p:mat:" + clave)],
                          [("\u2B05\uFE0F Volver", "p:r:" + clave)]]))
        return mandados

    def mandar_material(self, clave, alcance=None):
        """El boton de siempre. Por defecto la ultima semana."""
        self.pedir_archivos(clave, alcance or getattr(CFG, "ALCANCE_POR_DEFECTO",
                                                     "semana"))

    def texto_novedades(self):
        mios = self.estado.get("novedades", [])[:12]
        if not mios:
            return "Todav\u00eda no apareci\u00f3 nada." + self.texto_silenciados("\n\n")
        filas = ["%s <b>%s</b>\n%s %s  <i>%s</i>"
                 % (self.emoji_de(n.get("c", "")), N.escapar(n.get("g", "")),
                    icono(n.get("tipo")), N.enlace(n["t"], n["u"]),
                    n["f"][5:16].replace("-", "/"))
                 for n in mios]
        return "\n\n".join(filas) + self.texto_silenciados("\n\n")

    def texto_semana(self):
        limite = (ahora() - dt.timedelta(days=7)).strftime("%Y-%m-%d")
        mios = [n for n in self.estado.get("novedades", []) if n.get("f", "") >= limite]
        if not mios:
            return "Semana tranquila. Nada nuevo." + self.texto_silenciados("\n\n")
        por_ramo = {}
        for n in mios:
            por_ramo.setdefault(n.get("c", ""), []).append(n)
        bloques = []
        for clave, cosas in por_ramo.items():
            filas = ["%s <b>%s</b>" % (self.emoji_de(clave),
                                       N.escapar(self.nombre_de(clave)))]
            filas += ["%s %s" % (icono(c.get("tipo")), N.enlace(c["t"], c["u"]))
                      for c in cosas[:6]]
            bloques.append("\n".join(filas))
        return "\n\n".join(bloques) + self.texto_silenciados("\n\n")

    def texto_pendientes(self):
        hoy = ahora()
        todo = [(k, t) for k, t in self.estado.get("tareas", {}).items()
                if not t.get("hecho")]
        todo.sort(key=lambda x: x[1].get("vence") or "9999")
        if not todo:
            return "No te debo nada. Todo al d\u00eda." + self.texto_silenciados("\n\n")
        entregar = [x for x in todo if x[1].get("es_tarea", True)]
        mirar = [x for x in todo if not x[1].get("es_tarea", True)]
        partes = []
        if entregar:
            partes.append("<b>PARA ENTREGAR</b>\n\n" + self._filas_pendientes(entregar, hoy))
        if mirar:
            partes.append("<b>SIN REVISAR</b>\n\n" + self._filas_pendientes(mirar, hoy))
        return "\n\n".join(partes) + self.texto_silenciados("\n\n")

    def _filas_pendientes(self, pend, hoy):
        filas = []
        for _, t in pend[:15]:
            f = leer_fecha(t.get("vence"))
            if f:
                faltan = (f - hoy).total_seconds() / 3600.0
                cuando = ("\u26A0\uFE0F vencida" if faltan < 0 else
                          "en %d h" % faltan if faltan < 48 else
                          "en %d d\u00edas" % (faltan / 24))
                sello = "%s \u00b7 %s" % (fecha_linda(f), cuando)
            else:
                sello = "sin fecha"
            # El nombre del ramo tambien se escapa: un ramo con un < o un &
            # en el nombre rompia el formato del mensaje entero.
            linea = "\U0001F4CC <b>%s</b>\n<i>%s%s</i>" % (
                N.escapar(t["titulo"]),
                (N.escapar(t.get("grupo", "")) + " \u00b7 ")
                if t.get("grupo") else "", sello)
            if t.get("nota"):
                linea += "\n\U0001F4DD %s" % N.escapar(t["nota"])
            filas.append(linea)
        return "\n\n".join(filas)

    def texto_silenciados(self, prefijo=""):
        """El pie que aparece en TODO. Silenciar baja el volumen, no apaga."""
        callados = self.estado.get("callados", {})
        if not callados:
            return ""
        hoy = ahora().date()
        filas = []
        for clave, ficha in callados.items():
            try:
                quedan = (dt.datetime.strptime(ficha["hasta"], "%Y-%m-%d").date() - hoy).days
            except Exception:
                quedan = 0
            nuevas = ficha.get("cuenta", 0)
            filas.append("%s, quedan %d d\u00edas%s"
                         % (N.escapar(self.nombre_de(clave)), max(quedan, 0),
                            ", %d cosas nuevas" % nuevas if nuevas else ", sin novedad"))
        return prefijo + "\U0001F515 <b>SILENCIADOS</b>\n" + "\n".join(filas)

    def texto_diagnostico(self):
        d = self.tablero()
        lineas = [
            "\u2705 vivo" if not self.estado.get("fallas") else "\u26A0\uFE0F con problemas",
            "\u00faltima revisi\u00f3n: %s" % self.estado.get("ultima_corrida", "nunca"),
            "ramos: %d \u00b7 pendientes: %d" % (d["ramos"], d["pendientes"]),
            "memoria: %s" % d["memoria"],
            "versi\u00f3n: <b>v%s</b> (%s)" % (getattr(VER, "VERSION", "?"),
                                              getattr(VER, "FECHA", "?")),
            "IA: %s" % d["ia"],
            "claves de IA: %s" % IA.como_van_las_claves(self.estado),
            salud.linea_de_estado(self.estado),
            "compartiendo con: %d persona(s)" % len(self.estado.get("personas", {})),
            "claves ajenas: %s" % compartir.resumen_de_claves(self.estado),
            "clases por video detectadas: %d" % len(
                self.estado.get("clases_avisadas", {})),
            "pausa: %s" % ("s\u00ed" if self.en_pausa() else "no"),
            "madrugada: %s" % ("sin sonido" if self.cfg().get("noche", True) else "suena"),
        ]
        for clave, ficha_falla in self.estado.get("fallas", {}).items():
            # Antes esto pegaba el diccionario de la falla tal cual, o sea
            # {'veces': 3, 'desde': ...}, y se leia como un error del programa.
            if isinstance(ficha_falla, dict):
                lineas.append("\u26A0\uFE0F %s \u00b7 %s \u00b7 desde %s" % (
                    N.escapar(self.nombre_de(clave)),
                    N.escapar(ficha_falla.get("motivo", "no pude leerlo")),
                    N.escapar(ficha_falla.get("desde", "hace rato"))))
            else:
                lineas.append("\u26A0\uFE0F %s desde %s" % (
                    N.escapar(self.nombre_de(clave)), N.escapar(ficha_falla)))
        return "\n".join(lineas) + self.texto_silenciados("\n\n")

    def texto_version(self):
        """Que version esta corriendo y que trajo. Sale del codigo mismo,
        asi que no puede mentir: si lo ves, ese codigo es el que corre."""
        lineas = ["\U0001F195 <b>Versi\u00f3n v%s</b>" % getattr(VER, "VERSION", "?"),
                  "del %s" % getattr(VER, "FECHA", "?")]
        if getattr(VER, "TITULO", ""):
            lineas.append("<i>%s</i>" % N.escapar(VER.TITULO))
        cambios = getattr(VER, "CAMBIOS", [])
        if cambios:
            lineas += ["", "<b>Qu\u00e9 trajo</b>"]
            lineas += ["\u2022 " + N.escapar(c) for c in cambios[:12]]
        pruebas = getattr(VER, "A_PROBAR", [])
        if pruebas:
            lineas += ["", "<b>Para probar</b>"]
            lineas += ["%d. %s" % (i, N.escapar(p)) for i, p in enumerate(pruebas[:6], 1)]
        lineas += ["", "\u00faltima revisi\u00f3n: %s"
                   % self.estado.get("ultima_corrida", "nunca")]
        return "\n".join(lineas)

    def por_que_no_hay_ia(self):
        """En una linea, por que no hay resumen."""
        if not self.cfg().get("ia", True):
            return "los res\u00famenes est\u00e1n apagados, prend\u00e9los con /ia on"
        if not IA.claves():
            return ("no tengo ninguna clave de IA guardada, as\u00ed que no puedo "
                    "resumir")
        if not IA.disponible(self.estado):
            return IA.cuando_vuelve(self.estado)
        motivo = self.estado.get("ultimo_error_ia", "")
        if motivo:
            # Si el motivo ya dice cuando vuelve, no lo contradigo con un
            # "proba en un rato" que sonaria a que es cosa de minutos.
            corto = motivo[:130].rstrip(". ")
            if "ma\u00f1ana" in corto or "hora" in corto:
                return corto
            return "%s. Prob\u00e1 de nuevo en un rato" % corto
        return "no me lleg\u00f3 respuesta esta vez, prob\u00e1 de nuevo en un rato"

    # ---------------------------------------------------------- a pedido
    def resumen_ramo(self, clave):
        """Vos lo pediste, asi que este trabaja con la animacion puesta."""
        g = self.estado.get("grupos", {}).get(clave, {})
        nombre = g.get("nombre", "ese ramo")
        mios = [n for n in self.estado.get("novedades", []) if n.get("c") == clave]
        if not mios:
            N.enviar("Todav\u00eda no vi nada en <b>%s</b>." % N.escapar(nombre))
            return

        avisar, cerrar = self.animar(nombre)
        s = self.sesiones.get(g.get("fuente"))
        trabajo = {"grupo": nombre, "titulo": "Material de " + nombre,
                   "descripcion": "\n".join("- " + n["t"] for n in mios[:12]),
                   "vence": "",
                   "archivos": [{"titulo": n["t"], "url": n["u"]}
                                for n in mios if n.get("tipo") == "archivo"][:CFG.IA["archivos_maximos"]]}
        resumen = IA.resumir(self.estado, s, trabajo, avisar=avisar) if s else None

        cabeza = "%s <b>%s</b>\n%d cosas guardadas" % (
            g.get("emoji", "\U0001F4D8"), N.escapar(nombre), len(mios))
        if resumen:
            cuerpo = cabeza + "\n" + N.cita(
                "\U0001F9E0 " + N.escapar(resumen["corto"])
                + (("\n\n" + N.escapar(resumen["largo"])) if resumen.get("largo") else ""),
                plegable=bool(resumen.get("largo")))
        else:
            # Sin IA no repito la lista: para eso esta Ver material.
            cuerpo = (cabeza + "\n\n\U0001F9E0 No puedo resumirte esto ahora: "
                      + N.escapar(self.por_que_no_hay_ia())
                      + "\n\nMientras tanto ten\u00e9s la lista completa en "
                      "<b>Ver material</b>.")
        cerrar(cuerpo, N.teclado([[("\U0001F4C4 Ver material", "p:mat:" + clave)],
                                  [("\u2B05\uFE0F Panel", "p:r:" + clave)]]))

    def exportar(self):
        limpio_estado = dict(self.estado)
        limpio_estado.pop("_chat", None)
        return ("memoria_%s.json" % ahora().strftime("%Y%m%d"),
                json.dumps(limpio_estado, indent=1, ensure_ascii=False))

    def probar_ia_ahora(self):
        """Prueba la ayuda de IA de verdad y te cuenta que paso, en castellano.

        Sin esto, cuando la IA no anda no hay forma de saber si el problema es
        que no llegaron las claves, que se acabo el cupo o que el servicio no
        contesta.  Tambien deja claro que el bot funciona igual sin IA.
        """
        volver = N.teclado([[("\u2B05\uFE0F Volver", "p:mas")]])
        try:
            fichas = IA.claves()
        except Exception:
            fichas = []
        lineas = ["\U0001F9E0 <b>Prueba de la ayuda de IA</b>", ""]
        if not fichas:
            lineas.append("No me lleg\u00f3 <b>ninguna</b> clave, as\u00ed que no puedo "
                          "resumir ni entender lo que me escrib\u00eds.")
            lineas.append("")
            lineas.append("Las claves se cargan en las casillas secretas de tu "
                          "repositorio. La primera se llama IA_KEY y las de "
                          "repuesto IA_KEY_2, IA_KEY_3, IA_KEY_4 y IA_KEY_5. "
                          "El nombre tiene que estar escrito igual.")
            lineas.append("")
            lineas.append("Lo importante sigue andando igual: los avisos, el "
                          "material y los plazos no dependen de esto.")
            N.enviar("\n".join(lineas), botones=volver)
            return
        nombres = ", ".join(str(c.get("nombre", "?")) for c in fichas[:6])
        lineas.append("Claves que me llegaron: <b>%d</b>" % len(fichas))
        if nombres:
            lineas.append("<i>%s</i>" % N.escapar(nombres))
        if len(fichas) == 1:
            lineas.append("Si cargaste m\u00e1s de una y ac\u00e1 dice 1, es que el "
                          "nombre de la casilla no coincide: la segunda tiene "
                          "que llamarse IA_KEY_2, exacto.")
        lineas.append("")
        avisar, cerrar = self.animar("Probando la ayuda de IA")
        avisar("le hago una pregunta de prueba")
        respuesta, falla = "", ""
        try:
            respuesta = (IA._pedir(self.estado,
                                   "Contest\u00e1 solo con la palabra ok.") or "").strip()
        except Exception as e:
            # El texto de esta falla ya viene explicado para vos, sin jerga.
            falla = str(e) if isinstance(e, RuntimeError) else ""
        if respuesta:
            lineas.append("\u2705 Le pregunt\u00e9 de verdad y me contest\u00f3.")
            lineas.append("La ayuda de IA est\u00e1 <b>funcionando</b>.")
            # Esta pantalla decia "funcionando" mientras el chat contestaba
            # "no la tengo disponible".  Si el interruptor esta en no, se dice
            # aca mismo y se ofrece prenderla, en vez de dejar la duda.
            if not self.cfg().get("ia", True):
                lineas.append("")
                lineas.append("\u26A0\uFE0F Pero la ten\u00e9s <b>apagada</b> vos: por eso, "
                              "cuando me escrib\u00eds algo, te contesto que no "
                              "puedo. Prendela con el bot\u00f3n de abajo.")
                volver = N.teclado(
                    [[("\U0001F9E0 Prender la ayuda de IA", "t:ia")],
                     [("\u2B05\uFE0F Volver", "p:mas")]])
        else:
            lineas.append("\u26A0\uFE0F Le pregunt\u00e9 de verdad y <b>no</b> me contest\u00f3.")
            lineas.append(falla[:300] if falla
                          else "No pude conectarme con el servicio de IA.")
            try:
                cuando = IA.cuando_vuelve(self.estado) or ""
            except Exception:
                cuando = ""
            if cuando:
                lineas.append(cuando)
            lineas.append("")
            lineas.append("No perd\u00e9s nada importante: los avisos, el material "
                          "y los plazos no dependen de esto.")
        cerrar("\n".join(lineas), volver)

    def preguntar_si_reinicio(self):
        """Reiniciar no borra nada, pero igual se pregunta.

        Un boton que apaga el bot no puede dispararse de un dedazo, y menos
        cuando lo que se apaga es justo lo que avisa las cosas.
        """
        N.enviar(
            "\U0001F504 <b>\u00bfReinicio?</b>\n"
            "Me apago y arranco de nuevo. <b>No pierdo nada</b>: los avisos, "
            "el material y lo que ya te mand\u00e9 quedan igual.\n"
            "Tardo unos minutos en volver.",
            botones=N.teclado([
                [("\U0001F504 S\u00ed, reinici\u00e1", "a:reiniciar_si")],
                [("\u274C No, dejalo as\u00ed", "p:mas")]]))

    def reiniciarme(self):
        """Corta esta corrida para que empiece una limpia.

        No borra la memoria: la guarda primero y despues se apaga.  El reloj
        de GitHub vuelve a arrancar solo, asi que el bot vuelve sin que haya
        que tocar nada.  Se avisa ANTES de apagarse, porque un bot que se
        apaga en silencio es igual a un bot roto.
        """
        try:
            self.guardar()
        except Exception as e:
            log("[!] guardando antes de reiniciar:", type(e).__name__)
            N.enviar("\u26A0\uFE0F No pude guardar la memoria, as\u00ed que mejor no "
                     "me apago. Prob\u00e1 de nuevo en un rato.")
            return
        self.reiniciar_pedido = True
        N.enviar("\U0001F504 Listo, me apago y arranco de nuevo.\n"
                 "Guard\u00e9 todo: no perd\u00e9s ning\u00fan aviso. Vuelvo solo en unos "
                 "minutos y te aviso cuando est\u00e9 despierto.")

    def _solo_lo_ultimo(self, elegidos, modo, nombre=""):
        """Se queda con el ultimo archivo, o con todos los del ultimo dia que
        tuvo material.  Devuelve tambien las fechas exactas: asi, cuando
        confirmas, el bot vuelve a encontrar lo mismo y no algo parecido."""
        con_fecha = [a for a in elegidos if str(a.get("cuando") or "")[:10]]
        ordenados = sorted(con_fecha or list(elegidos),
                           key=lambda a: str(a.get("cuando") or ""), reverse=True)
        if not ordenados:
            return elegidos, "", "", nombre, ""
        primero = ordenados[0]
        dia = str(primero.get("cuando") or "")[:10]
        bonito = ("del %s/%s" % (dia[8:10], dia[5:7])) if len(dia) == 10 else ""
        if modo == "dia" and dia:
            del_dia = [a for a in ordenados
                       if str(a.get("cuando") or "")[:10] == dia]
            return del_dia, dia, dia, nombre, bonito or "del \u00faltimo d\u00eda"
        titulo_a = str(primero.get("titulo", "") or "")[:80]
        return ([primero], dia, dia, titulo_a or nombre,
                (bonito + ", el \u00faltimo") if bonito else "el \u00faltimo")

    def accion(self, cual):
        if cual == "revisar":
            self.estado["_revisar_ya"] = True
            N.enviar("Voy a mirar ahora.")
        elif cual == "exportar":
            nombre, contenido = self.exportar()
            N.mandar_archivo(nombre, contenido, "Todo lo que s\u00e9, en un archivo.")
        elif cual.startswith("resu:"):
            self.resumen_ramo(cual[5:])
        elif cual.startswith("bajar:"):
            self.mandar_material(cual[6:])
        elif cual == "tocar":
            self.despertar_reloj()
        elif cual == "reloj":
            texto = self.revisar_reloj(forzado=True)
            if not texto:
                N.enviar(salud.linea_de_estado(self.estado)
                         + "\nTodo en orden, no hay nada que hacer.")
        elif cual == "probar_ia":
            self.probar_ia_ahora()
        elif cual == "reiniciar":
            self.preguntar_si_reinicio()
        elif cual == "reiniciar_si":
            self.reiniciarme()
        elif cual == "cerrar_compartir":
            cuantos = compartir.cerrar_todo(self.estado)
            N.enviar("\U0001F512 Listo, cerr\u00e9 %d permiso(s). Nadie ve nada "
                     "tuyo hasta que lo vuelvas a abrir a mano." % cuantos)
            self.guardar()
        elif cual.startswith("baj:"):
            # baj:<clave>:<alcance>  ->  semana, mes o todo
            resto = cual[4:]
            clave, _, alcance = resto.rpartition(":")
            if not clave:
                clave, alcance = resto, ""
            self.pedir_archivos(clave, alcance or None)

    def _acciones(self):
        return {
            "tablero": self.tablero,
            "hoy": lambda: ahora().date(),
            "ahora": ahora,
            "en_pausa": self.en_pausa,
            "lista_ramos": self.lista_ramos,
            "ficha_ramo": self.ficha_ramo,
            "material": self.material,
            "cuantos_archivos": self.cuantos_archivos,
            "pedir_archivos": self.pedir_archivos,
            "buscar_por_nombre": lambda clave, texto: self.pedir_archivos(
                clave, "todo", nombre=texto),
            "texto_novedades": lambda: self._memo("nov", self.texto_novedades),
            "texto_pendientes": lambda: self._memo("pen", self.texto_pendientes),
            # v5.6: la lista de pendientes con botones, uno por pendiente.
            "pendientes_para_panel": self.pendientes_para_panel,
            "texto_avisos": self.texto_avisos,
            "ficha_tarea": lambda idt: (self.estado.get("tareas") or {}).get(idt),
            "texto_semana": lambda: self._memo("sem", self.texto_semana),
            "texto_silenciados": self.texto_silenciados,
            "texto_diagnostico": self.texto_diagnostico,
            "texto_ayuda": comandos.texto_ayuda,
            "texto_clases": self.texto_clases,
            "texto_compartir": self.texto_compartir,
            "texto_afuera": self.texto_afuera,
            "personas": lambda: compartir.lista(self.estado),
            "ramos_abiertos": lambda pid: compartir.ramos_abiertos(self.estado, pid),
            "alternar_ramo": lambda pid, clave: compartir.alternar_ramo(
                self.estado, pid, clave),
            "sacar_persona": lambda pid: compartir.sacar(self.estado, pid),
            "cerrar_todo": lambda pid=None: compartir.cerrar_todo(self.estado, pid),
            "resumen_de_claves": lambda: compartir.resumen_de_claves(self.estado),
            "buscar": self.buscar,
            "resumen_ramo": self.resumen_ramo,
            "preguntar": self.preguntar,
            "proponer": self.proponer,
            "confirmar_propuesta": self.confirmar_propuesta,
            "texto_version": self.texto_version,
            "dibujar_panel": self.dibujar_panel,
            "abrir_panel": lambda saludar=False: self.abrir_panel(saludar=saludar),
            "redibujar_tarjeta": self.redibujar_tarjeta,
            "accion": self.accion,
            "nombre": self.nombre_de,
        }

    # =================================================================
    #  escuchar el chat
    # =================================================================
    def escuchar(self, espera=0):
        """Mira el chat y contesta. Con espera 0 no cuesta casi nada, asi que
        se puede llamar en medio de una revision para que los botones no
        queden esperando a que termine de mirar las plataformas."""
        try:
            atendidas = comandos.atender(self.estado, self.acc, ahora(), espera=espera)
        except Exception as e:
            log("[!] atendiendo el chat:", type(e).__name__, e)
            return 0
        self.precalentar()
        if self.estado.pop("_poner_teclado", False):
            # No se borra: la botonera vive pegada a este mensaje.
            N.enviar("Atajos listos abajo. Se sacan con /atajos.",
                     silencioso=True, teclado_fijo=True)
        try:
            comandos.sacar_basura(self.estado)
        except Exception:
            pass
        if atendidas:
            self.guardar()
        return atendidas

    # =================================================================
    #  revisar las plataformas
    # =================================================================
    def _entrar(self, f):
        base = os.environ.get(f["env_url"], "").strip().rstrip("/")
        usuario = os.environ.get(f["env_user"], "").strip()
        clave = os.environ.get(f["env_pass"], "")
        if not (base and usuario and clave):
            return None, None
        self.bases[f["clave"]] = base
        if f["clave"] in self.sesiones:
            return self.sesiones[f["clave"]], base
        s = sesion()
        entrar, _ = ADAPTADORES[f["modo"]]
        try:
            if not entrar(s, base, usuario, clave):
                # Nunca reintentar en bucle: varias fallas seguidas pueden
                # dejarte la cuenta bloqueada.
                log("[!] no pude entrar en la fuente", f["clave"])
                self._aviso_de_clave(f)
                return None, base
        except Exception as e:
            log("[!] fuente %s: %s" % (f["clave"], type(e).__name__))
            return None, base
        self.sesiones[f["clave"]] = s
        return s, base

    def revisar_todo(self):
        vistos_ahora = set()
        for f in CFG.FUENTES:
            if not f.get("activo"):
                continue
            s, base = self._entrar(f)
            if not s:
                continue
            _, leer = ADAPTADORES[f["modo"]]
            try:
                grupos, viejos = leer(s, base)
            except Exception as e:
                log("[!] leyendo %s: %s" % (f["clave"], type(e).__name__))
                continue
            if grupos is None:
                self._aviso_de_plataforma(f, "no pude abrir sus paginas")
                continue
            if not grupos:
                self._aviso_de_plataforma(f, "entre pero no vi ni un ramo")
                continue
            self.estado.get("plataformas_mudas", {}).pop(f["clave"], None)
            for g in grupos:
                clave = huella("grupo", f["clave"], g["id"])
                vistos_ahora.add(clave)
                self._ver_grupo(clave, g, f)
                if f.get("modo") == "b64":
                    self.mirar_reuniones(clave, g, s, base)
                # Entre ramo y ramo miro el chat un segundo.  Asi los botones
                # siguen contestando aunque este en plena revision.
                self.escuchar(0)
            self._revisar_ausentes(f, grupos, viejos, vistos_ahora)
        self.estado["ultima_corrida"] = ahora().strftime("%d/%m %H:%M")
        self.olvidar_cache()

    def _ver_grupo(self, clave, g, f):
        grupos = self.estado.setdefault("grupos", {})
        nuevo_ramo = clave not in grupos
        ficha = grupos.setdefault(clave, {})
        ficha.update({"nombre": g["nombre"], "emoji": f["emoji"],
                      "fuente": f["clave"], "id": g["id"], "url": g["url"]})
        ficha["visto"] = ahora().strftime("%Y-%m-%d %H:%M")
        self.estado.get("fallas", {}).pop(clave, None)
        self.estado.get("ausentes", {}).pop(clave, None)

        if g.get("items") is None:
            self._anotar_falla(clave, "no pude leer la p\u00e1gina del ramo")
            return

        # Un ramo que tenia cosas y de golpe tiene cero no se lo traga nadie.
        if not g["items"] and ficha.get("cantidad", 0) >= 3:
            self._anotar_falla(clave, "el ramo qued\u00f3 vac\u00edo de golpe")
            return
        ficha["cantidad"] = len(g["items"])

        items = self.estado.setdefault("items", {})
        frescos = []
        for it in g["items"]:
            marca = huella("item", clave, it["url"], pelado(it["titulo"]))
            if marca in items:
                continue
            items[marca] = ahora().strftime("%Y-%m-%d")
            frescos.append(it)

        # La primera vez que entro ADENTRO de las actividades de un ramo
        # aparece de golpe todo lo viejo. Eso no es novedad: lo anoto callado.
        primera_honda = not ficha.get("honda")
        ficha["honda"] = True

        # Ultimo seguro: si la pagina cambio y no supe decir en que, aviso igual.
        firma = g.get("firma") or ""
        firma_vieja = ficha.get("firma") or ""
        cambio_ciego = bool(firma and firma_vieja and firma != firma_vieja)
        ficha["firma"] = firma

        if nuevo_ramo and not self.estado.get("arrancado"):
            return                      # la primera vez no grita nada
        if nuevo_ramo:
            N.enviar("%s <b>Ramo nuevo: %s</b>\nDesde ahora te aviso de todo lo "
                     "que suban ac\u00e1." % (f["emoji"], N.escapar(g["nombre"])),
                     silencioso=self.en_silencio())
            return                      # su material inicial no es novedad

        tope = getattr(CFG, "TOPE_PRIMERA_TANDA", 10)
        if frescos and primera_honda and len(frescos) > tope:
            log("[i] primera mirada honda en %s: %d cosas viejas anotadas"
                % (self.nombre_de(clave), len(frescos)))
            N.enviar("%s <b>%s</b>\nAhora tambi\u00e9n miro <i>adentro</i> de cada "
                     "actividad. Encontr\u00e9 %d cosas que ya estaban: no te las "
                     "mando, quedan anotadas. De ac\u00e1 en m\u00e1s te aviso solo "
                     "de lo nuevo." % (f["emoji"], N.escapar(g["nombre"]), len(frescos)),
                     silencioso=True)
            return

        # Los avisos escritos del profesor van primero y no esperan a nada:
        # aca vienen las suspensiones, las clases online y los cambios de
        # fecha, que es lo que no se puede perder.
        hubo_aviso = self.avisos_nuevos(clave, ficha, g.get("avisos"))

        if frescos:
            ficha["ciego_veces"] = 0
            self._avisar(clave, frescos)
        elif hubo_aviso:
            ficha["ciego_veces"] = 0
        elif cambio_ciego:
            self._cambio_sin_nombre(clave, ficha, firma_vieja, firma)

    def _cambio_sin_nombre(self, clave, ficha, firma_vieja="", firma_nueva=""):
        """La pagina del ramo cambio pero no pude decir en que.

        Este aviso existe porque es el ultimo seguro contra perderse algo.
        El problema es que avisaba de mas: la pagina cambia sola y te llegaban
        tres por dia sin que hubiera nada nuevo.  Ahora tiene tres frenos.
        """
        if not getattr(CFG, "AVISAR_CAMBIO_CIEGO", True):
            return False
        if self.callado(clave):
            return False

        # Freno 1, el importante: si esta firma ya la vi antes, la pagina esta
        # yendo y viniendo entre dos estados, o sea que se mueve sola.  Eso no
        # es un cambio, es ruido, y este ramo deja de dar avisos ciegos.
        historia = ficha.setdefault("firmas_vistas", [])
        if firma_nueva and firma_nueva in historia:
            if not ficha.get("pagina_inquieta"):
                ficha["pagina_inquieta"] = True
                log("[i] %s cambia sola, dejo de avisar a ciegas"
                    % self.nombre_de(clave))
            return False
        if firma_nueva:
            historia.append(firma_nueva)
            del historia[:-8]
        if ficha.get("pagina_inquieta"):
            return False

        # Freno 2: dos revisiones seguidas con la pagina distinta antes de
        # molestarte.  Un cambio de verdad sigue estando en la revision que
        # viene, el ruido no.
        faltan = getattr(CFG, "REVISIONES_PARA_AVISO_CIEGO", 2)
        ficha["ciego_veces"] = ficha.get("ciego_veces", 0) + 1
        if ficha["ciego_veces"] < faltan:
            return False
        ficha["ciego_veces"] = 0

        # Freno 3: como maximo uno por dia por ramo.
        horas = getattr(CFG, "HORAS_ENTRE_AVISOS_CIEGOS", 24)
        ultimo = leer_fecha(ficha.get("aviso_ciego", ""))
        hoy = ahora()
        if ultimo and (hoy - ultimo).total_seconds() < horas * 3600:
            return False
        ficha["aviso_ciego"] = hoy.strftime("%Y-%m-%d %H:%M")
        N.enviar("%s <b>%s</b>\nCambi\u00f3 algo en la p\u00e1gina del ramo y no "
                 "pude decirte qu\u00e9. Puede ser un texto editado o algo que la "
                 "plataforma no me deja ver.\n%s"
                 % (ficha.get("emoji", "\U0001F4D8"),
                    N.escapar(ficha.get("nombre", "un ramo")),
                    N.enlace("abrir el ramo", ficha.get("url", ""))),
                 silencioso=True)
        return True

    # =================================================================
    #  avisos escritos del profesor
    # =================================================================
    def avisos_nuevos(self, clave, ficha, fichas_de_avisos):
        """Lo que el profe escribe en el tablero de Avisos.

        Esto era el agujero mas grande que tenia el bot: solo miraba ENLACES,
        y un aviso no es un enlace, es texto.  Por ahi pasan las suspensiones,
        las clases online y los cambios de fecha de las pruebas.

        Un aviso NO respeta el silencio del ramo y, si es urgente, suena
        aunque sea de madrugada.  Perderse una suspension no se arregla
        despues.  Devuelve True si mando alguno.
        """
        if not getattr(CFG, "AVISAR_AVISOS", True):
            return False
        lista = fichas_de_avisos or []
        if not lista:
            return False

        guardadas = self.estado.setdefault("avisos_vistos", {})
        nuevos = avisos.nuevos(lista, guardadas)
        if not nuevos:
            return False

        hoy = ahora()
        sello = hoy.strftime("%Y-%m-%d")

        # La primera vez que leo los avisos de un ramo ya hay avisos viejos.
        # Esos se anotan callados: no son novedad, son historia.
        if not ficha.get("avisos_leidos"):
            ficha["avisos_leidos"] = True
            for a in nuevos:
                guardadas[a["huella"]] = sello
            log("[i] anote %d avisos viejos de %s"
                % (len(nuevos), self.nombre_de(clave)))
            return False

        nombre = self.nombre_de(clave)
        rompe = getattr(CFG, "AVISOS_ROMPEN_SILENCIO", True)
        if self.callado(clave) and not rompe:
            for a in nuevos:
                guardadas[a["huella"]] = sello
            return False

        mandados = 0
        for a in nuevos[:getattr(CFG, "AVISOS_POR_TANDA", 4)]:
            texto = avisos.lineas_del_aviso(
                a, ramo=nombre, url=ficha.get("url", ""),
                escapar=N.escapar, enlace=N.enlace)

            # Dos niveles, y la diferencia importa.  Nivel 1 (suspension,
            # clase online, cambio de fecha) te despierta.  Nivel 2 (prueba,
            # entrega, asistencia) NO: antes esas palabras contaban como
            # urgentes, o sea que casi todo iba a sonar a las 3 de la manana, y
            # una alarma que suena siempre se apaga.
            urgente = bool(a.get("urgente"))
            suena = urgente and getattr(CFG, "AVISOS_SUENAN_DE_NOCHE", True)
            # Vos pediste poder elegirlo: por defecto no suenan de madrugada,
            # pero se prende desde Ajustes sin tocar nada del programa.
            if a.get("importante") and self.cfg().get(
                    "noche_importantes",
                    getattr(CFG, "IMPORTANTES_SUENAN_DE_NOCHE", False)):
                suena = True
            callado = self.en_silencio() and not suena

            # Queda en Pendientes como algo para mirar, no para entregar, asi
            # no se te pierde entre los mensajes del chat.
            idt = "aviso_" + a["huella"]
            self.estado.setdefault("tareas", {})[idt] = {
                "grupo": nombre, "clave": clave, "titulo": a["titulo"],
                "url": ficha.get("url", ""), "vence": "", "hecho": False,
                "nota": "", "es_tarea": False, "aviso": True,
                "texto": a.get("texto", ""), "tarjeta": texto,
                # Sin fecha de nacimiento no se puede ordenar por fecha ni
                # archivar solo: un aviso no tiene fecha de entrega.
                "nacio": hoy.strftime("%Y-%m-%d %H:%M")}

            mid = N.enviar(texto, silencioso=callado,
                           botones=self.botones_tarjeta(idt, clave,
                                                        es_tarea=False))
            if not mid:
                # No salio: saco el pendiente que acababa de crear y NO lo
                # marco como visto, asi se reintenta en la revision que viene.
                # Un aviso de suspension perdido no se recupera despues.
                self.estado.get("tareas", {}).pop(idt, None)
                log("[!] no pude mandar un aviso del profe, lo reintento")
                continue
            self.estado["tareas"][idt]["mensaje_id"] = mid

            # Recien DESPUES de mandarlo lo anoto como visto. Al reves, si el
            # mensaje no sale, el aviso se pierde para siempre.
            guardadas[a["huella"]] = sello
            self.estado.setdefault("novedades", []).insert(0, {
                "f": hoy.strftime("%Y-%m-%d %H:%M"), "c": clave, "g": nombre,
                "t": a["titulo"], "u": ficha.get("url", ""), "tipo": "aviso"})
            mandados += 1

        del self.estado["novedades"][CFG.NOVEDADES_GUARDADAS:]

        # La lista de huellas no crece para siempre.
        tope = getattr(CFG, "AVISOS_GUARDADOS", 400)
        if len(guardadas) > tope:
            viejas = sorted(guardadas.items(), key=lambda x: x[1])
            for h, _ in viejas[:len(guardadas) - tope]:
                guardadas.pop(h, None)

        if mandados:
            self.guardar()
        return mandados > 0

    def texto_avisos(self, cuantos=8):
        """Los ultimos avisos escritos que junte, para /avisos."""
        fichas = []
        for idt, t in (self.estado.get("tareas") or {}).items():
            if t.get("aviso"):
                fichas.append((idt, t))
        if not fichas:
            return ("Todav\u00eda no junt\u00e9 ning\u00fan aviso escrito de los "
                    "profesores.\nLos leo del tabl\u00f3n de cada ramo en cada "
                    "revisi\u00f3n, as\u00ed que en cuanto haya uno te llega solo.")
        # Antes esto ordenaba por x[0], que es el id: "aviso_" + una huella.
        # O sea que el orden era el del hash, puro azar, y el aviso de arriba
        # no era el mas nuevo. Ahora va por fecha, el mas nuevo primero.
        fichas.sort(key=lambda x: str(x[1].get("nacio") or ""), reverse=True)
        lineas = ["\U0001F4E3 <b>Avisos de los profes</b>", ""]
        for _, t in fichas[:cuantos]:
            # La admiracion es solo para los urgentes de verdad. Antes la
            # llevaban TODOS, asi que no distinguia nada.
            if t.get("hecho"):
                marca = "\u2705"
            elif avisos.urgente(t.get("texto") or t.get("titulo", "")):
                marca = "\u2757"
            else:
                marca = "\U0001F4E3"
            lineas.append("%s <b>%s</b>" % (marca, N.escapar(t.get("grupo", ""))))
            cuerpo = t.get("texto") or t.get("titulo", "")
            lineas.append(N.escapar(cuerpo[:300]))
            lineas.append("")
        return "\n".join(lineas).strip()

    # =================================================================
    #  clases por videoconferencia anunciadas en la plataforma
    # =================================================================
    def mirar_reuniones(self, clave, g, s, base):
        """Avisa las clases por video apenas aparecen publicadas.

        Antes el bot solo se enteraba si el profesor ademas escribia un aviso.
        Si la dejaba anotada nada mas, la clase pasaba y el dueno no se
        enteraba nunca.
        """
        if not getattr(CFG, "AVISAR_CLASES", True):
            return 0
        try:
            filas = reuniones_b64(s, base, g.get("id"))
        except Exception as e:
            log("[!] mirando las videoconferencias:", type(e).__name__)
            return 0
        if filas is None:
            return 0
        guardadas = self.estado.setdefault("reuniones", {})
        hoy = ahora()
        nombre = g.get("nombre") or self.nombre_de(clave)
        cuantas = 0
        for r in filas:
            termina = r["cuando"] + dt.timedelta(minutes=r["minutos"])
            marca = huella("reunion", clave,
                           r["cuando"].strftime("%Y-%m-%d %H:%M"),
                           pelado(r["tema"]))
            if marca in guardadas:
                continue
            # Una clase que ya termino no se avisa: seria ruido puro y encima
            # tardio. Se anota igual para no descubrirla de nuevo manana.
            if termina < hoy:
                guardadas[marca] = {"c": clave, "tema": r["tema"],
                                    "cuando": r["cuando"].strftime("%Y-%m-%d %H:%M"),
                                    "avisada": "", "recordada": "vieja"}
                continue
            lineas = ["\U0001F3A5 <b>Clase por videoconferencia</b>",
                      "Ramo: <b>%s</b>" % N.escapar(nombre),
                      N.escapar(r["tema"]),
                      "\U0001F550 %s" % N.escapar(fecha_linda(r["cuando"]))]
            if r["minutos"]:
                lineas.append("\u23F3 Dura %d minutos" % r["minutos"])
            if r["anfitrion"]:
                lineas.append("\U0001F464 %s" % N.escapar(r["anfitrion"]))
            if r["llave"]:
                lineas.append("\U0001F511 Clave para entrar: <b>%s</b>"
                              % N.escapar(r["llave"]))
            lineas.append("\U0001F517 " + N.enlace("Abrir la sala",
                                                   r["enlace"] or r["pagina"]))
            lineas.append("<i>Te lo recuerdo %d minutos antes.</i>"
                          % getattr(CFG, "MINUTOS_ANTES_DE_LA_CLASE", 10))
            try:
                mid = N.enviar("\n".join(lineas))
            except Exception as e:
                log("[!] no pude avisar la videoconferencia:", type(e).__name__)
                continue
            if not mid:
                # Mandar primero, marcar despues: si el mensaje no salio, la
                # clase tiene que seguir figurando como no avisada.
                continue
            guardadas[marca] = {
                "c": clave, "tema": r["tema"], "llave": r["llave"],
                "enlace": r["enlace"] or r["pagina"], "ramo": nombre,
                "cuando": r["cuando"].strftime("%Y-%m-%d %H:%M"),
                "avisada": hoy.strftime("%Y-%m-%d %H:%M"), "recordada": ""}
            cuantas += 1
        return cuantas

    def recordar_reuniones(self):
        """El golpecito en el hombro justo antes de la clase.

        El aviso del dia anterior se pierde entre los mensajes; este llega
        cuando todavia se puede hacer algo. No pide nada por internet, asi
        que puede correr en cada vuelta del chat.
        """
        guardadas = self.estado.get("reuniones", {})
        if not guardadas:
            return 0
        antes = getattr(CFG, "MINUTOS_ANTES_DE_LA_CLASE", 10)
        hoy = ahora()
        cuantas = 0
        for marca, r in list(guardadas.items()):
            cuando = leer_fecha(r.get("cuando", ""))
            # Limpieza: lo de hace mas de dos dias no le sirve a nadie y la
            # memoria no puede crecer para siempre.
            if cuando and (hoy - cuando).total_seconds() > 2 * 86400:
                guardadas.pop(marca, None)
                continue
            if not cuando or r.get("recordada"):
                continue
            faltan = (cuando - hoy).total_seconds()
            if faltan > antes * 60 or faltan < -120:
                continue
            lineas = ["\u23F0 <b>Tu clase por video empieza en %d minutos</b>"
                      % max(1, int(round(faltan / 60.0))),
                      "Ramo: <b>%s</b>" % N.escapar(r.get("ramo", "")),
                      N.escapar(r.get("tema", ""))]
            if r.get("llave"):
                lineas.append("\U0001F511 Clave: <b>%s</b>" % N.escapar(r["llave"]))
            if r.get("enlace"):
                lineas.append("\U0001F517 " + N.enlace("Entrar ahora", r["enlace"]))
            try:
                mid = N.enviar("\n".join(lineas))
            except Exception as e:
                log("[!] no pude recordar la clase:", type(e).__name__)
                continue
            if not mid:
                continue
            r["recordada"] = hoy.strftime("%Y-%m-%d %H:%M")
            cuantas += 1
        if cuantas:
            self.guardar()
        return cuantas

    def _aviso_de_plataforma(self, f, motivo):
        """Una plataforma que no se puede leer tiene que doler.

        Quedarse callado deja al dueno creyendo que no hay novedades, cuando
        la verdad es que el bot no miro nada. Se avisa una vez cada seis horas:
        insistir en cada vuelta seria castigo.
        """
        mudas = self.estado.setdefault("plataformas_mudas", {})
        antes = mudas.get(f["clave"]) or {}
        ultimo = leer_fecha(antes.get("cuando", ""))
        if (ultimo and antes.get("motivo") == motivo
                and (ahora() - ultimo).total_seconds() < 6 * 3600):
            return
        mudas[f["clave"]] = {"cuando": ahora().strftime("%Y-%m-%d %H:%M"),
                             "motivo": motivo}
        N.enviar(
            "\u26a0\ufe0f <b>No estoy viendo la plataforma %s</b>\n"
            "%s.\n\nLo sigo intentando en la pr\u00f3xima vuelta. Si esto se "
            "repite, entr\u00e1 vos desde el navegador y fijate si te pide algo "
            "(cambiar la clave, aceptar un aviso o cerrar otra sesi\u00f3n)."
            % (N.escapar(f["clave"]), motivo.capitalize()))

    def _aviso_de_clave(self, f):
        """La plataforma rechazo el usuario o la clave.

        Casi siempre es porque cambiaste la clave y el bot sigue con la vieja.
        Se avisa UNA vez por dia: insistir no sirve y varios intentos seguidos
        pueden dejarte la cuenta bloqueada.
        """
        marcas = self.estado.setdefault("aviso_clave", {})
        hoy = ahora()
        ultimo = leer_fecha(marcas.get(f["clave"], ""))
        if ultimo and (hoy - ultimo).total_seconds() < 24 * 3600:
            return
        marcas[f["clave"]] = hoy.strftime("%Y-%m-%d %H:%M")
        N.enviar(
            "\U0001F510 <b>No pude entrar a la plataforma %s</b>\n"
            "El usuario y la clave est\u00e1n puestos, pero la plataforma no los "
            "acepta.\n\nCasi siempre es una de estas tres:\n"
            "1. Cambiaste la clave y ac\u00e1 sigue la vieja.\n"
            "2. La plataforma te pidi\u00f3 cambiarla al entrar.\n"
            "3. La cuenta est\u00e1 bloqueada por intentos fallidos.\n\n"
            "No voy a seguir probando para no bloquearte la cuenta. Cuando "
            "arregles la clave, avisame y reviso.\n"
            "<i>Mientras tanto sigo avisando de los otros ramos.</i>"
            % N.escapar(f.get("clave", "")))

    def pendientes_para_panel(self, cuantos=8):
        """La lista de pendientes lista para poner botones.

        Devuelve [(id, titulo, cuando, es_tarea, tiene_nota)].  El panel la usa
        para armar una fila por pendiente, que era justo lo que faltaba: la
        lista se ve\u00eda pero no se pod\u00eda tocar.
        """
        hoy = ahora()
        salida = []
        for idt, t in (self.estado.get("tareas") or {}).items():
            if t.get("hecho"):
                continue
            f = leer_fecha(t.get("vence"))
            if f:
                faltan = (f - hoy).total_seconds() / 3600.0
                cuando = ("vencida" if faltan < 0 else
                          "en %d h" % faltan if faltan < 48 else
                          "en %d d" % (faltan / 24))
                orden = f.strftime("%Y-%m-%d %H:%M")
            else:
                cuando, orden = "sin fecha", "9999"
            salida.append((orden, idt, t.get("titulo", ""), cuando,
                           t.get("es_tarea", True), bool(t.get("nota"))))
        salida.sort(key=lambda x: x[0])
        return [x[1:] for x in salida[:cuantos]]

    def _anotar_falla(self, clave, motivo):
        """Tres revisiones seguidas antes de alarmar. Las plataformas se
        reinician solas y no vale la pena despertarte por eso."""
        fallas = self.estado.setdefault("fallas", {})
        ficha = fallas.setdefault(clave, {"veces": 0, "desde": ahora().strftime("%d/%m %H:%M"),
                                          "motivo": motivo, "avisado": False})
        ficha["veces"] += 1
        if ficha["veces"] >= CFG.CONFIRMAR_FALLA and not ficha["avisado"]:
            ficha["avisado"] = True
            N.enviar("\u26A0\uFE0F <b>Algo raro en %s</b>\n%s\nLo vengo viendo desde "
                     "las %s. Puede ser la plataforma, no vos."
                     % (N.escapar(self.nombre_de(clave)), motivo, ficha["desde"]))

    def _revisar_ausentes(self, f, grupos, viejos, vistos):
        """Un ramo que desaparecio puede ser tres cosas muy distintas."""
        presentes = {g["id"] for g in grupos}
        ausentes = self.estado.setdefault("ausentes", {})

        for clave, ficha in list(self.estado.get("grupos", {}).items()):
            if ficha.get("fuente") != f["clave"] or clave in vistos:
                continue
            if ficha.get("id") in presentes:
                continue

            marca = ausentes.setdefault(clave, {"veces": 0})
            marca["veces"] += 1
            if marca["veces"] < CFG.CONFIRMAR_FALLA:
                continue

            if ficha.get("id") in set(viejos):
                # cambio de semestre: se archiva callado
                self.estado.setdefault("archivados", {})[clave] = ficha
                self.estado["grupos"].pop(clave, None)
                ausentes.pop(clave, None)
                log("[i] archivado por cambio de semestre:", ficha.get("nombre"))
                continue

            if len(presentes) == 0:
                continue        # no hay nada, es la plataforma

            # los demas ramos siguen ahi, asi que no es la plataforma
            N.enviar("\u26A0\uFE0F <b>Ya no est\u00e1s en %s</b>\n"
                     "Desapareci\u00f3 de tu lista.\nLos otros %d ramos siguen ah\u00ed, "
                     "as\u00ed que no parece un problema de la plataforma."
                     % (N.escapar(ficha.get("nombre", "un ramo")), len(presentes)))
            self.estado.setdefault("archivados", {})[clave] = ficha
            self.estado["grupos"].pop(clave, None)
            ausentes.pop(clave, None)

    # =================================================================
    #  avisar novedades
    # =================================================================
    def _avisar(self, clave, frescos):
        """Un trabajo con consigna, fecha y tres PDF es UN aviso, no cuatro."""
        nombre = self.nombre_de(clave)
        hoy = ahora()

        for n in frescos:
            self.estado.setdefault("novedades", []).insert(0, {
                "f": hoy.strftime("%Y-%m-%d %H:%M"), "c": clave, "g": nombre,
                "t": n["titulo"], "u": n["url"], "tipo": n["tipo"]})
        del self.estado["novedades"][CFG.NOVEDADES_GUARDADAS:]

        # Las clases por video van ANTES del silencio a proposito: perderse
        # una clase no se arregla despues, y un ramo callado sigue teniendo
        # clases.  Esta es la unica cosa que rompe el silencio.
        self.clases_nuevas(clave, nombre, frescos, hoy)

        if self.callado(clave):
            ficha = self.estado["callados"][clave]
            ficha["cuenta"] = ficha.get("cuenta", 0) + len(frescos)
            log("[i] %d cosas nuevas en %s (silenciado)" % (len(frescos), nombre))
            return

        principal = None
        for n in frescos:
            if n["tipo"] == "tarea":
                principal = n
                break
        principal = principal or frescos[0]
        adjuntos = [n for n in frescos if n is not principal]

        descripcion = principal.get("descripcion", "")
        vence = fecha_en_texto(descripcion, hoy)

        ficha = {"clave": clave, "items": frescos, "vence": vence}
        tarea_id = huella("tarea", clave, principal["url"])

        # trabaja callado: a esta hora no hay nadie mirando
        s = self.sesiones.get(self.estado["grupos"][clave].get("fuente"))
        resumen = None
        if s and not self.en_pausa():
            resumen = IA.resumir(self.estado, s, {
                "grupo": nombre, "titulo": principal["titulo"],
                "descripcion": descripcion,
                "vence": fecha_linda(vence) if vence else "",
                "archivos": [{"titulo": a["titulo"], "url": a["url"]}
                             for a in ([principal] + adjuntos)
                             if a["tipo"] in ("archivo", "tarea")]})

        texto = self.tarjeta(ficha, resumen)
        self.estado.setdefault("tareas", {})[tarea_id] = {
            "grupo": nombre, "clave": clave, "titulo": principal["titulo"],
            "url": principal["url"],
            "vence": vence.strftime("%Y-%m-%d %H:%M") if vence else "",
            "hecho": False, "nota": "", "tarjeta": texto,
            "nacio": hoy.strftime("%Y-%m-%d %H:%M"),
            "es_tarea": principal["tipo"] == "tarea"}

        if self.en_pausa():
            log("[i] en pausa, guardo sin avisar")
            return
        mid = N.enviar(texto, silencioso=self.en_silencio(),
                       botones=self.botones_tarjeta(
                           tarea_id, clave, False, principal["tipo"] == "tarea"))
        if not mid:
            # El aviso no salio. Si dejara todo marcado como visto, esta
            # novedad no se reintentaria NUNCA: el usuario no se enteraria y
            # el silencio quedaria igual que "no hay noticias". Saco las
            # marcas y se vuelve a intentar en la revision siguiente.
            self._desmarcar(clave, frescos)
            log("[!] no pude avisar %d cosas de %s, lo reintento"
                % (len(frescos), nombre))
            return
        # Guardo el id: asi puedo redibujar la tarjeta despues, por ejemplo
        # cuando me mandas una nota desde el teclado.
        self.estado["tareas"][tarea_id]["mensaje_id"] = mid
        self.mandar_adjuntos(s, [principal] + adjuntos, mid)

    def _desmarcar(self, clave, frescos):
        """Deshace las marcas de "esto ya lo vi" cuando el aviso no salio.

        Es la contracara de "mando primero, marco despues": sin esto, un rato
        de mensajeria caida se come novedades para siempre.
        """
        items = self.estado.setdefault("items", {})
        novedades = self.estado.setdefault("novedades", [])
        for it in frescos:
            items.pop(huella("item", clave, it["url"], pelado(it["titulo"])), None)
            for i, n in enumerate(novedades):
                if n.get("c") == clave and n.get("u") == it["url"]:
                    del novedades[i]
                    break

    # ------------------------------------------------------- adjuntos
    def mandar_adjuntos(self, sesion, items, responde_a=None):
        """Te baja el archivo y te lo deja en el chat, asi no entras a la
        pagina solo para bajarlo.  Si falla, el enlace de la tarjeta sigue
        estando: no se pierde nada."""
        if not sesion or not getattr(CFG, "ADJUNTAR", False):
            return
        tope = CFG.PESO_ADJUNTO_MB * 1024 * 1024
        mandados = 0
        for it in items:
            if mandados >= CFG.ADJUNTOS_POR_AVISO:
                return mandados
            if not es_bajable(it.get("url", ""), it.get("titulo", "")):
                continue
            try:
                r = sesion.get(it["url"], timeout=CFG.ESPERA_RED, stream=True)
                if r.status_code != 200:
                    continue
                tipo = (r.headers.get("Content-Type") or "").lower()
                pegado = (r.headers.get("Content-Disposition") or "").lower()
                # Si dice html y ademas no viene como descarga, es una pagina.
                if "html" in tipo and "attachment" not in pegado:
                    continue
                crudo = r.content
            except Exception:
                continue
            if not crudo or len(crudo) > tope:
                continue
            nombre = nombre_de_archivo(r, it["url"], it.get("titulo", "archivo"))
            if N.mandar_documento(nombre, crudo, silencioso=True, responde_a=responde_a):
                mandados += 1
        return mandados

    # =================================================================
    #  plazos
    # =================================================================
    def procesar_agenda(self):
        hoy = ahora()
        for ev in leer_agenda():
            uid = huella("plazo", ev.get("uid") or ev["titulo"])
            t = self.estado.setdefault("tareas", {}).setdefault(uid, {
                "grupo": "", "clave": "", "titulo": ev["titulo"], "url": ev.get("url", ""),
                "hecho": False, "nota": "", "de_agenda": True})
            t["vence"] = ev["vence"].strftime("%Y-%m-%d %H:%M")
            if ev.get("descripcion") and not t.get("descripcion"):
                t["descripcion"] = ev["descripcion"]

    def avisos_de_plazo(self):
        hoy = ahora()
        # OJO: esta variable NO puede llamarse "avisos": arriba del archivo hay
        # un `import avisos`, y un nombre local le tapa el modulo entero dentro
        # de la funcion. Cualquier avisos.algo() de aca reventaria.
        ya_avisados = self.estado.setdefault("avisos", {})
        for idt, t in list(self.estado.get("tareas", {}).items()):
            if t.get("hecho") or not t.get("vence"):
                continue
            f = leer_fecha(t["vence"])
            if not f:
                continue
            dormida = leer_fecha(t.get("dormida_hasta"))
            if dormida and hoy < dormida:
                continue
            faltan = (f - hoy).total_seconds() / 3600.0
            if faltan < -2:
                continue

            if t.get("mio"):
                # Un apunte tuyo suena UNA vez, a la hora que pediste.  Los
                # perfiles de insistencia son para las entregas de los
                # profesores, no para tus recordatorios.
                perfil = list(getattr(CFG, "AVISOS_DE_MIS_RECORDATORIOS", [0]))
            else:
                perfil = CFG.PERFILES.get(self.perfil_de(t.get("clave", "")),
                                          CFG.PERFILES[CFG.PERFIL_POR_DEFECTO])
            if perfil == "diario":
                hitos = [h for h in range(int(faltan) + 24, 0, -24)]
            else:
                hitos = perfil

            for h in hitos:
                # La lista de hitos ya avisados es ya_avisados. Aca decia
                # avisos.setdefault(), que es el MODULO de avisos del profe:
                # la vuelta entera se cortaba en este punto en cada revision,
                # asi que nunca llegaba un recordatorio de entrega y ademas se
                # dejaban de hacer el resumen, el latido y el reloj. Todo
                # callado, porque mas arriba hay un except que se lo tragaba.
                if faltan <= h and str(h) not in ya_avisados.setdefault(idt, []):
                    # Mando primero y marco despues: si el mensaje no sale, el
                    # hito se vuelve a intentar en la revision siguiente.
                    if self._avisar_plazo(idt, t, f, faltan):
                        ya_avisados[idt].append(str(h))
                    break

    def _avisar_plazo(self, idt, t, f, faltan):
        if faltan <= 0:
            cuenta = "\u26A0\uFE0F vence <b>ahora</b>"
        elif faltan < 1:
            cuenta = "\u23F0 faltan <b>%d minutos</b>" % int(faltan * 60)
        elif faltan < 48:
            cuenta = "\u23F0 faltan <b>%d horas</b>" % int(faltan)
        else:
            cuenta = "\u23F3 faltan <b>%d d\u00edas</b>" % int(faltan / 24)

        emoji = self.emoji_de(t.get("clave", ""))
        lineas = ["%s <b>%s</b>" % (emoji, N.escapar(t.get("grupo") or "Recordatorio")),
                  cuenta,
                  N.enlace(t["titulo"], t["url"]) if t.get("url") else N.escapar(t["titulo"]),
                  "vence %s" % fecha_linda(f)]
        if t.get("nota"):
            lineas.append("\U0001F4DD %s" % N.escapar(t["nota"]))
        texto = "\n".join(lineas)
        t["tarjeta"] = texto
        # Un plazo suena aunque sea de madrugada y aunque el ramo este callado.
        # Devuelve si el mensaje SALIO, porque de eso depende que el hito se
        # marque o se reintente.
        return bool(N.enviar(
            texto, botones=self.botones_tarjeta(idt, t.get("clave", ""))))

    # =================================================================
    #  resumen periodico y latido
    # =================================================================
    def recordar_sin_ver(self):
        """Te lo recuerda hasta que lo marques visto, no una sola vez.

        Vos elegiste insistir antes que perderte algo.  Igual hay tope de
        veces y hay que dejar pasar las mismas horas entre empujon y empujon,
        porque un recordatorio que aparece a cada rato se vuelve invisible."""
        horas = getattr(CFG, "HORAS_PARA_RECORDAR_VISTO", 0)
        if not horas or self.en_pausa() or self.en_silencio():
            return
        insistir = getattr(CFG, "INSISTIR_HASTA_VISTO", False)
        tope = max(1, getattr(CFG, "VECES_PARA_RECORDAR_VISTO", 1))
        hoy = ahora()
        pendientes = []
        for idt, t in self.estado.get("tareas", {}).items():
            if t.get("hecho") or t.get("mio") or t.get("de_agenda"):
                continue
            if t.get("es_tarea", True):
                continue          # esas ya avisan por su fecha de entrega
            if self.callado(t.get("clave", "")):
                continue
            # Una memoria vieja trae solo "recordado": eso vale como un empujon.
            veces = int(t.get("empujones") or 0)
            if not veces and t.get("recordado"):
                veces = 1
            if veces and not insistir:
                continue
            if veces >= tope:
                continue
            nacio = leer_fecha(t.get("nacio"))
            if not nacio or (hoy - nacio).total_seconds() < horas * 3600:
                continue
            ultimo = leer_fecha(t.get("ultimo_empujon")) or nacio
            if veces and (hoy - ultimo).total_seconds() < horas * 3600:
                continue
            pendientes.append(t)
        if not pendientes:
            return
        filas = ["\U0001F440 <b>SIN REVISAR</b>", ""]
        for t in pendientes[:8]:
            filas.append("%s\n<i>%s</i>" % (
                N.enlace(t["titulo"], t["url"]), N.escapar(t.get("grupo", ""))))
        if len(pendientes) > 8:
            filas.append("<i>y %d cosas m\u00e1s</i>" % (len(pendientes) - 8))
        filas.append("")
        filas.append("<i>Est\u00e1n en Pendientes hasta que las marques.</i>")
        if not N.enviar("\n".join(filas), botones=N.teclado([[
                ("\U0001F4CC Pendientes", "p:pen"),
                ("\U0001F431 Panel", "p:raiz")]])):
            return          # no salio: no marco nada y se reintenta
        # Marco DESPUES de mandar, asi el empujoncito no se pierde callado.
        for t in pendientes:
            previos = int(t.get("empujones") or (1 if t.get("recordado") else 0))
            t["empujones"] = previos + 1
            t["recordado"] = True
            t["ultimo_empujon"] = hoy.strftime("%Y-%m-%d %H:%M")

    def _toca_ahora(self, dia, hora, ultimo_guardado):
        hoy = ahora()
        if hoy.strftime("%Y-%m-%d") == ultimo_guardado:
            return False
        try:
            h, mi = [int(x) for x in hora.split(":")]
        except Exception:
            return False
        if dia and pelado(dia) != pelado(DIAS_LARGOS[hoy.weekday()]):
            return False
        objetivo = hoy.replace(hour=h, minute=mi, second=0, microsecond=0)
        return objetivo <= hoy < objetivo + dt.timedelta(hours=2)

    def resumen_periodico(self):
        r = self.cfg().setdefault("resumen", dict(CFG.RESUMEN))
        if not r.get("activo", True):
            return
        dia = None if r.get("cada") == "dia" else r.get("dia")
        if not self._toca_ahora(dia, r.get("hora", "20:00"),
                                self.estado.get("ultimo_resumen", "")):
            return
        self.estado["ultimo_resumen"] = ahora().strftime("%Y-%m-%d")
        cabeza = "\U0001F4C5 <b>Resumen %s</b>" % (
            "del d\u00eda" if r.get("cada") == "dia" else "de la semana")
        N.enviar(cabeza + "\n\n" + self.texto_semana()
                 + "\n\n" + self.texto_pendientes(),
                 silencioso=self.en_silencio())

    # =================================================================
    #  clases por videoconferencia
    # =================================================================
    def clases_nuevas(self, clave, nombre, frescos, hoy=None):
        """Mira lo que acaba de aparecer y busca clases por video.

        Una clase con enlace se avisa SIEMPRE: aunque el ramo este callado y
        aunque sea de madrugada.  Es la unica cosa del bot que rompe el
        silencio, y lo hace a proposito.

        Cada clase se avisa una sola vez.  Devuelve cuantas aviso.
        """
        if not getattr(CFG, "AVISAR_CLASES", True):
            return 0
        hoy = hoy or ahora()
        avisadas = self.estado.setdefault("clases_avisadas", {})
        cuantas = 0

        for n in frescos or []:
            titulo = n.get("titulo", "")
            url = n.get("url", "")
            descripcion = n.get("descripcion", "")
            try:
                ficha = clases.detectar(titulo, url, descripcion)
            except Exception as e:
                log("[!] mirando si era clase:", type(e).__name__)
                continue
            if not ficha:
                continue
            if not ficha.get("seguro") and not getattr(CFG, "CLASES_SIN_ENLACE", True):
                continue

            marca = huella("clase", clave, ficha.get("enlace") or url, pelado(titulo))
            if marca in avisadas:
                continue

            cuando = fecha_en_texto(" ".join([titulo, descripcion]), hoy)
            lineas = clases.lineas_del_aviso(
                ficha, ramo=nombre, titulo=titulo,
                cuando=fecha_linda(cuando) if cuando else "",
                escapar=N.escapar, enlace=N.enlace)
            if not ficha.get("enlaces") and url:
                lineas.append("\U0001F517 " + N.enlace("Abrir en la plataforma", url))

            # Solo rompe el silencio de la madrugada una clase SEGURA, o sea
            # con enlace de sala de verdad. Cuando la detecte por palabras
            # puede ser el profe hablando de la clase que ya paso, y eso no
            # justifica despertarte: una alarma que suena de gusto se apaga, y
            # el dia que hay una clase online de verdad no te enteras.
            segura = clases.prioritaria(ficha)
            silencioso = self.en_silencio() and not (
                segura and getattr(CFG, "CLASES_SUENAN_DE_NOCHE", True))
            try:
                mid = N.enviar("\n".join(lineas), silencioso=silencioso)
            except Exception as e:
                log("[!] no pude avisar la clase:", type(e).__name__)
                continue
            if not mid:
                log("[!] la clase no se pudo avisar, lo reintento")
                continue
            # Recien ahora queda marcada. Al reves, un mensaje que no sale
            # dejaba la clase como avisada y no llegaba nunca.
            avisadas[marca] = hoy.strftime("%Y-%m-%d %H:%M")
            cuantas += 1
            log("[i] clase por video en %s (%s)" % (nombre, ficha.get("sala")))

        # que la lista no crezca para siempre
        if len(avisadas) > 400:
            for k in list(avisadas)[:-400]:
                avisadas.pop(k, None)
        return cuantas

    def texto_clases(self, cuantas=12):
        """Las ultimas clases por video que detecte, para poder volver a
        entrar al enlace sin buscarlo en el chat."""
        vistas = self.estado.get("clases_avisadas", {})
        if not vistas:
            return ("Todav\u00eda no detect\u00e9 ninguna clase por videoconferencia.\n\n"
                    "<i>Cuando alg\u00fan profe suba el enlace de un Meet, un Zoom o "
                    "una sala virtual, te aviso al toque, aunque el ramo est\u00e9 "
                    "silenciado y aunque sea de madrugada.</i>")
        lineas = []
        for n in self.estado.get("novedades", []):
            ficha = None
            try:
                ficha = clases.detectar(n.get("t", ""), n.get("u", ""))
            except Exception:
                ficha = None
            if not ficha or not ficha.get("seguro"):
                continue
            lineas.append("%s %s  <i>%s \u00b7 %s</i>" % (
                clases.EMOJI, N.enlace(n.get("t", "la sala"), n.get("u", "")),
                N.escapar(n.get("g", "")), n.get("f", "")[5:16].replace("-", "/")))
            if len(lineas) >= cuantas:
                break
        if not lineas:
            return ("Detect\u00e9 %d avisos de clase, pero ninguno con enlace "
                    "todav\u00eda guardado." % len(vistas))
        return "\n".join(lineas)

    # =================================================================
    #  el reloj de GitHub
    # =================================================================
    def revisar_reloj(self, forzado=False):
        """GitHub apaga el horario programado a los 60 dias sin movimiento.
        A los 50 avisa, y si puede lo arregla solo.  Una vez por dia."""
        if not getattr(CFG, "REVISAR_RELOJ", True) and not forzado:
            return ""
        hoy = ahora()
        if not forzado:
            if self.estado.get("ultimo_reloj", "") == hoy.strftime("%Y-%m-%d"):
                return ""
            if hoy.strftime("%H:%M") < str(getattr(CFG, "HORA_REVISAR_RELOJ", "10:00")):
                return ""
            self.estado["ultimo_reloj"] = hoy.strftime("%Y-%m-%d")
        try:
            texto, botones = salud.revisar(
                self.estado, hoy,
                aviso=getattr(CFG, "DIAS_PARA_AVISAR_QUIETO", 50),
                apaga=getattr(CFG, "DIAS_QUE_APAGA_GITHUB", 60),
                arreglar_solo=getattr(CFG, "DESPERTAR_RELOJ_SOLO", True))
        except Exception as e:
            log("[!] no pude revisar el reloj:", type(e).__name__, e)
            return ""
        if texto:
            N.enviar(texto, botones=N.teclado(botones) if botones else None)
        return texto

    def despertar_reloj(self):
        """El boton: mueve el repositorio a mano y contesta que paso."""
        bien, motivo = salud.tocar()
        if bien:
            self.estado["repo_movido"] = ahora().strftime("%Y-%m-%dT%H:%M:%SZ")
            self.estado["repo_dias"] = 0
            self.estado["repo_aviso"] = ""
            self.estado["repo_toques"] = int(self.estado.get("repo_toques", 0)) + 1
            N.enviar("\u2705 Listo, mov\u00ed el repositorio. La cuenta de los "
                     "60 d\u00edas volvi\u00f3 a cero y sigo despertando normal.")
        else:
            N.enviar("\u26A0\uFE0F No pude moverlo: %s.\nCon que hagas cualquier "
                     "cambio en el repositorio alcanza." % motivo)
        self.guardar()
        return bien

    # =================================================================
    #  material de otras secciones
    # =================================================================
    def nombre_de_ramo(self, clave):
        return self.nombre_de(clave)

    def avisar_de_afuera(self, pid, items):
        """Llego material de otra seccion.  Una linea y se termina ahi.

        Sin perfil, sin recordatorio de "no lo viste" y sin boton para
        callarlo.  Lo que ya te mando tu propio profe no se avisa.
        """
        if not getattr(CFG, "COMPARTIR", True):
            return 0
        hoy = ahora()
        try:
            nuevos, repetidos = compartir.recibir(self.estado, pid, items, hoy)
        except Exception as e:
            log("[!] recibiendo de afuera:", type(e).__name__, e)
            return 0
        if repetidos:
            log("[i] %d cosas de afuera ya las ten\u00eda" % repetidos)
        if not nuevos:
            return 0

        resumen = ""
        if getattr(CFG, "RESUMIR_LO_DE_AFUERA", True) and IA.disponible(self.estado):
            resumen = self.resumir_de_afuera(nuevos)

        tandas = [nuevos] if getattr(CFG, "AGRUPAR_LO_DE_AFUERA", True) \
            else [[x] for x in nuevos]
        for tanda in tandas:
            texto = compartir.aviso_corto(tanda, escapar=N.escapar,
                                          enlace=N.enlace, resumen=resumen)
            if not texto:
                continue
            # Silencioso siempre: no es prioridad y no tiene que despertarte.
            N.enviar(texto, silencioso=getattr(
                CFG, "AVISOS_DE_AFUERA_SILENCIOSOS", True))
        return len(nuevos)

    def resumir_de_afuera(self, fichas):
        """Una linea, no un informe.  Si la IA no contesta, no pasa nada:
        el aviso va igual con el titulo, que es lo que importa."""
        largo = int(getattr(CFG, "LARGO_RESUMEN_DE_AFUERA", 180))
        titulos = "; ".join(str(x.get("t", ""))[:70] for x in fichas[:5])
        pedido = ("En UNA sola frase de menos de %d caracteres, en castellano "
                  "rioplatense, decime que subieron. No saludes, no expliques, "
                  "no uses comillas. Esto es lo que subieron: %s"
                  % (largo, titulos))
        try:
            salida = IA._pedir(self.estado, pedido)
        except Exception:
            return ""
        salida = limpio(salida or "")
        if not salida or len(salida) > largo * 2:
            return ""
        return salida[:largo]

    def compartir_lo_mio(self, pid):
        """Lo que esta persona puede ver de lo mio, ya filtrado y revisado.

        Antes de devolver nada pasa por el control de salida: si aparece un
        campo que no esta en la lista blanca, no sale NADA.  Prefiero no
        compartir a compartir de mas.
        """
        try:
            paquete = compartir.paquete_para(self.estado, pid)
        except Exception as e:
            log("[!] armando el paquete:", type(e).__name__, e)
            return []
        fugas = compartir.revisar_fuga(paquete)
        if fugas:
            log("[!] freno el envio, se colaron campos: %s" % ", ".join(fugas))
            return []
        ficha = compartir.persona(self.estado, pid)
        if ficha:
            ficha["mandados"] = int(ficha.get("mandados", 0)) + len(paquete)
        return paquete

    def texto_compartir(self):
        return compartir.texto_personas(self.estado, nombre_de=self.nombre_de,
                                        escapar=N.escapar)

    def texto_afuera(self):
        return compartir.texto_de_afuera(self.estado, escapar=N.escapar,
                                         enlace=N.enlace)

    def latido(self):
        """Una linea por semana. Si un lunes no llega, algo pasa.
        Asi el silencio deja de ser ambiguo."""
        if not self._toca_ahora(CFG.LATIDO_DIA, CFG.LATIDO_HORA,
                                self.estado.get("ultimo_latido", "")):
            return
        self.estado["ultimo_latido"] = ahora().strftime("%Y-%m-%d")
        d = self.tablero()
        N.enviar("\u2764\uFE0F Sigo ac\u00e1. %d ramos vigilados, %d pendientes."
                 % (d["ramos"], d["pendientes"]), silencioso=True)

    # =================================================================
    #  la corrida
    # =================================================================
    def avisar_version(self):
        """Si el codigo que esta corriendo no es el mismo de la ultima vez,
        te aviso que el parche entro y que trae.  Este mensaje NO se borra:
        queda como comprobante y como lista de que probar."""
        try:
            actual = str(VER.VERSION)
        except Exception:
            return
        if self.estado.get("version_avisada") == actual:
            return
        hoy = ahora()
        lineas = ["\U0001F195 <b>Actualizaci\u00f3n aplicada: v%s</b>" % actual,
                  "\U0001F553 entr\u00f3 el %s a las %s"
                  % (hoy.strftime("%d/%m"), hoy.strftime("%H:%M"))]
        if getattr(VER, "TITULO", ""):
            lineas.append("<i>%s</i>" % N.escapar(VER.TITULO))
        lineas.append("")
        lineas.append("<b>Qu\u00e9 cambi\u00f3</b>")
        for c in getattr(VER, "CAMBIOS", [])[:12]:
            lineas.append("\u2022 " + N.escapar(c))
        pruebas = getattr(VER, "A_PROBAR", [])
        if pruebas:
            lineas.append("")
            lineas.append("<b>Para probar</b>")
            for i, p in enumerate(pruebas[:6], 1):
                lineas.append("%d. %s" % (i, N.escapar(p)))
        lineas.append("")
        lineas.append("Si algo de esto no funciona, avisame y lo corrijo.")
        # Primero MANDO, despues anoto.  Al reves, si el mensaje no salia, la
        # memoria ya decia "avisada" y el aviso se perdia para siempre: era
        # exactamente el caso de "actualice y el bot no me dijo nada".
        if N.enviar("\n".join(lineas)) is None:
            log("[!] no pude mandar el aviso de la v%s, lo reintento" % actual)
            return
        self.estado["version_avisada"] = actual
        self.estado["version_desde"] = hoy.strftime("%Y-%m-%d %H:%M")
        self.guardar()
        log("[i] avise la version %s" % actual)

    def avisar_primera_vez(self):
        """La primera vez no inunda ni se queda callado.

        Avisar cada cosa vieja era doscientos mensajes de golpe; no avisar nada
        dejaba la duda de si mir\u00f3 algo.  Un resumen corto de lo ultimo que
        encontro resuelve las dos cosas."""
        if not getattr(CFG, "RESUMEN_DE_PRIMERA_VEZ", True):
            return
        cuantas = max(1, getattr(CFG, "COSAS_EN_EL_RESUMEN_INICIAL", 8))
        todas = self.estado.get("novedades", []) or []
        mios = todas[:cuantas]
        if not mios:
            return
        por_ramo = {}
        for n in mios:
            por_ramo.setdefault(n.get("g") or "Sin ramo", []).append(n)
        filas = ["\U0001F4CB <b>Lo \u00faltimo que encontr\u00e9</b>",
                 "<i>Esto ya estaba, no te lo voy a avisar de nuevo.</i>", ""]
        for ramo, cosas in list(por_ramo.items())[:6]:
            filas.append("<b>%s</b>" % N.escapar(ramo))
            for c in cosas[:3]:
                titulo = c.get("t") or "algo"
                filas.append("\u2022 " + (N.enlace(titulo, c["u"]) if c.get("u")
                                          else N.escapar(titulo)))
            filas.append("")
        if len(todas) > len(mios):
            filas.append("<i>Y %d cosas m\u00e1s guardadas, las ten\u00e9s en "
                         "Novedades.</i>" % (len(todas) - len(mios)))
        N.enviar("\n".join(filas).strip(), silencioso=True,
                 botones=N.teclado([[("\U0001F4E5 Novedades", "p:nov"),
                                     ("\U0001F431 Panel", "p:raiz")]]))

    def arranque(self):
        # Bandera del boton de reinicio.  Vive solo mientras dura la corrida:
        # si se guardara en la memoria, el bot arrancaria apagandose.
        self.reiniciar_pedido = False
        N.publicar_menu(comandos.MENU)
        self.avisar_version()
        if not self.estado.get("arrancado"):
            self.revisar_todo()
            self.procesar_agenda()
            self.estado["arrancado"] = True
            d = self.tablero()
            N.enviar("\u2705 <b>Vigilante encendido</b>\n"
                     "Anot\u00e9 %d ramos y lo que ya hab\u00eda dentro, sin avisarte de "
                     "cada cosa vieja.\nDesde ahora te aviso solo lo nuevo."
                     % d["ramos"], teclado_fijo=True)
            self.avisar_primera_vez()
            self.abrir_panel()
            if self.gist_nuevo:
                N.enviar("Guard\u00e9 la memoria en un gist privado nuevo. "
                         "Si quer\u00e9s fijarlo, su id es <code>%s</code>."
                         % almacen.id_actual())
            self.guardar()

    def olvidar_recordatorios_viejos(self):
        """Un recordatorio tuyo que ya paso hace rato se archiva solo.  Si no,
        te queda en Pendientes para siempre y ensucia la lista."""
        horas = getattr(CFG, "HORAS_PARA_OLVIDAR_MIO", 12)
        dias_aviso = getattr(CFG, "DIAS_PARA_ARCHIVAR_AVISOS", 21)
        hoy = ahora()
        for idt, t in list(self.estado.get("tareas", {}).items()):
            # Un aviso del profe NO tiene fecha de entrega, asi que nunca
            # entraba aca y se quedaba en Pendientes para siempre. En un
            # semestre la lista quedaba inservible. Se archiva solo, callado.
            if t.get("aviso") and not t.get("hecho") and dias_aviso:
                nacio = leer_fecha(t.get("nacio"))
                if not nacio:
                    # De una version vieja: le pongo fecha ahora y lo dejo
                    # vivir el plazo completo desde hoy.
                    t["nacio"] = hoy.strftime("%Y-%m-%d %H:%M")
                elif (hoy - nacio).days >= dias_aviso:
                    t["hecho"] = True
                continue
            if not t.get("mio") or t.get("hecho") or not t.get("vence"):
                continue
            f = leer_fecha(t["vence"])
            if not f:
                continue
            if (hoy - f).total_seconds() / 3600.0 >= horas:
                t["hecho"] = True
                self.redibujar_tarjeta(idt)

    def podar_memoria(self):
        """La memoria no puede crecer para siempre.

        Dos listas no tenian ningun tope: las huellas de todo lo visto y los
        pendientes ya cerrados. En un semestre la memoria se hace enorme, y
        cuando el gist no la puede guardar el bot se queda sin memoria.

        Las huellas se podan solo cuando son MUY viejas (mas de un ano), asi
        no se puede dar el caso de borrar la huella de algo que todavia esta
        publicado y volver a avisarlo como nuevo.
        """
        dias = int(getattr(CFG, "DIAS_PARA_PODAR_HUELLAS", 400) or 0)
        hoy = ahora()
        if dias:
            items = self.estado.get("items", {})
            corte = (hoy - dt.timedelta(days=dias)).strftime("%Y-%m-%d")
            for marca in [k for k, f in items.items()
                          if isinstance(f, str) and f and f[:10] < corte]:
                items.pop(marca, None)

        tope = int(getattr(CFG, "PENDIENTES_CERRADOS_GUARDADOS", 300) or 0)
        if tope:
            tareas = self.estado.get("tareas", {})
            hechas = [(str(t.get("nacio") or t.get("vence") or ""), k)
                      for k, t in tareas.items() if t.get("hecho")]
            if len(hechas) > tope:
                hechas.sort()
                for _f, k in hechas[:len(hechas) - tope]:
                    tareas.pop(k, None)

    def una_vuelta(self):
        self.revisar_todo()
        self.procesar_agenda()
        self.avisos_de_plazo()
        self.podar_memoria()
        self.olvidar_recordatorios_viejos()
        self.recordar_sin_ver()
        self.resumen_periodico()
        self.latido()
        self.revisar_reloj()
        if self.estado.get("panel_id") and self.estado.get("panel_donde") == "p:raiz":
            self.dibujar_panel("p:raiz")
        self.guardar()

    def correr(self):
        despierto = en_ventana(ahora())
        fin = time.time() + cuanto_vivir(ahora())
        log("[i] turno %s, hasta las %s (se relanza solo)"
            % ("despierto" if despierto else "dormido",
               (ahora() + dt.timedelta(seconds=fin - time.time())).strftime("%H:%M")))
        self.arranque()
        proxima_revision = 0
        while time.time() < fin:
            # OJO: el pop va PRIMERO y siempre. Adentro de un "or" no corria
            # cuando la otra condicion ya era verdadera, y /revisar quedaba mudo.
            forzado = bool(self.estado.pop("_revisar_ya", False))
            if forzado or time.time() >= proxima_revision:
                proxima_revision = time.time() + CFG.SEGUNDOS_ENTRE_REVISIONES
                antes = len(self.estado.get("novedades", []))
                try:
                    self.una_vuelta()
                except Exception as e:
                    log("[!] la vuelta fall\u00f3:", type(e).__name__, e)
                    if forzado:
                        N.enviar("\u26A0\uFE0F No pude mirar (%s). Lo reintento solo."
                                 % type(e).__name__)
                else:
                    if forzado:
                        nuevas = len(self.estado.get("novedades", [])) - antes
                        N.enviar("\U0001F440 Mir\u00e9 las dos plataformas: %s"
                                 % ("%d cosas nuevas" % nuevas if nuevas > 0
                                    else "nada nuevo por ahora."), silencioso=True)
            # El recordatorio no puede esperar a la proxima revision: si la
            # clase empieza en diez minutos, diez minutos es todo lo que hay.
            try:
                self.recordar_reuniones()
            except Exception as e:
                log("[!] recordando la clase:", type(e).__name__)
            # se queda escuchando el chat: por eso los botones contestan al toque
            self.escuchar(CFG.ESPERA_CHAT)
            if getattr(self, "reiniciar_pedido", False):
                # Cortar aca es todo el reinicio: la memoria ya quedo guardada
                # y el reloj de GitHub levanta una corrida nueva y limpia.
                log("[i] reinicio pedido desde el chat")
                break
        self.guardar()


def main():
    if not N.listo():
        print("[!] faltan TG_TOKEN o TG_CHAT")
        return 1
    v = Vigilante()
    v.correr()
    log("[i] corrida terminada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
