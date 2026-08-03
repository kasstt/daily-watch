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
import comandos
import fuentes as CFG
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
                   "/documento/", "/fichero")

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
RE_VOLATIL = re.compile(
    r"\d{1,2}:\d{2}(:\d{2})?|\d{6,}|sesskey|csrf|token|jsessionid", re.I)


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


def _toca_profundo(id_ramo, firma_raiz):
    """Entrar adentro de cada actividad en cada vuelta seria maltratar la
    plataforma.  Entro cuando la portada cambio, y cada tanto igual."""
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
    return bool(rid) and rid in u


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
    items = {}
    for it in cosas_de_la_pagina(html, base, propia=raiz):
        items.setdefault(it["url"], it)
    # el material que vive en el JavaScript de la pagina
    escondido = arbol_escondido(html, base, g.get("id"))
    for it in escondido:
        items.setdefault(it["url"], it)
    if escondido:
        firmas.append(huella("arbol", *sorted(x["url"] + x["titulo"] for x in escondido)))

    if hondo <= 0 or not _toca_profundo(str(g.get("id")), firmas[0]):
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


def entrar_aula(s, base, usuario, clave):
    r0 = s.get(base + "/login/index.php", timeout=CFG.ESPERA_RED)
    ficha = BeautifulSoup(r0.text, "html.parser").find("input", {"name": "logintoken"})
    datos = {"anchor": "", "username": usuario, "password": clave}
    if ficha:
        datos["logintoken"] = ficha.get("value", "")
    r = s.post(base + "/login/index.php", data=datos,
               headers={"Referer": base + "/login/index.php"},
               timeout=CFG.ESPERA_RED)
    return "login/index.php" not in r.url


def leer_aula(s, base):
    try:
        html = s.get(base + "/my/", timeout=CFG.ESPERA_RED).text
    except Exception:
        return None, []
    grupos, vistos = [], set()
    for a in BeautifulSoup(html, "html.parser").select('a[href*="/course/view.php?id="]'):
        m = re.search(r"id=(\d+)", a["href"])
        nombre = limpio(a.get_text(" "))
        if not m or not nombre or m.group(1) in vistos:
            continue
        vistos.add(m.group(1))
        grupos.append({"id": m.group(1), "nombre": nombre[:120],
                       "url": urljoin(base, a["href"])})
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
#  el vigilante
# =====================================================================
class Vigilante(object):

    def __init__(self):
        self.estado, self.modo, gist_nuevo = almacen.cargar()
        self.estado["_chat"] = os.environ.get("TG_CHAT", "").strip()
        self.gist_nuevo = gist_nuevo
        self.sesiones = {}
        self.cache = {}          # pantallas ya calculadas, ver _memo
        self.acc = self._acciones()

    # ---------------------------------------------------------- guardar
    def guardar(self):
        self.modo = almacen.guardar(self.estado, self.modo)

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
            cada = getattr(CFG, "ANIM_CADA_FRASE", 4)
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
                if vivo.wait(getattr(CFG, "ANIM_SEGUNDOS", 2.4)):
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
    def dibujar_panel(self, donde=None, mensaje_id=None):
        donde = donde or self.estado.get("panel_donde") or "p:raiz"
        if donde.startswith("c:") and not donde.startswith("c:si:"):
            texto, botones = P.confirmar_callar(self.estado, self.acc, donde[2:])
        else:
            texto, botones = P.pantalla(self.estado, donde, self.acc)
        self.estado["panel_donde"] = donde
        mid = mensaje_id or self.estado.get("panel_id")
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

    def preguntar(self, pregunta):
        """Charla. Si la IA esta apagada te lo dice y no te deja colgado."""
        if not IA.disponible(self.estado):
            N.enviar("La IA est\u00e1 apagada. Prendela con /ia on."
                     if self.cfg().get("ia", True) is False
                     else "No tengo IA disponible ahora. Prob\u00e1 /estado.")
            return
        avisar, cerrar = self.animar("Pensando")
        avisar(CFG.ETAPAS["pensando"])
        respuesta = IA.preguntar(self.estado, pregunta, self.libreta())
        if not respuesta:
            cerrar("No pude contestarte. %s"
                   % N.escapar(self.estado.get("ultimo_error_ia", ""))[:200])
            return
        cerrar("\U0001F9E0 <b>%s</b>\n%s"
               % (N.escapar(pregunta[:80]), N.cita(N.escapar(respuesta))),
               N.teclado([[("\U0001F431 Panel", "p:raiz")]]))

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

        return None, ""

    def ejecutar_plan(self, plan):
        """Hace lo que ya confirmaste. Devuelve el texto de cierre."""
        que = plan.get("accion")
        if que == "recordar":
            f = leer_fecha(plan["cuando"])
            idt = "mio_%d" % int(f.timestamp())
            self.estado.setdefault("tareas", {})[idt] = {
                "grupo": "", "clave": "", "titulo": plan["que"], "url": "",
                "vence": f.strftime("%Y-%m-%d %H:%M"), "hecho": False,
                "nota": "", "mio": True}
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
        if que == "hecho":
            t = self.estado.get("tareas", {}).get(plan["idt"])
            if not t:
                return "Esa ya no la tengo."
            t["hecho"] = True
            return "\u2705 Listo: <b>%s</b>." % N.escapar(t.get("titulo", ""))
        return "No supe qu\u00e9 hacer con eso."

    def proponer(self, texto):
        """Le hablas normal y hace cosas.  La IA solo traduce el pedido: el
        que valida, arma la confirmacion y ejecuta es este programa."""
        if not IA.disponible(self.estado):
            self.preguntar(texto)          # ahi se explica por que no hay IA
            return
        avisar, cerrar = self.animar("Entendiendo")
        avisar(CFG.ETAPAS["pensando"])
        orden = IA.interpretar(self.estado, texto, self._contexto_orden())
        accion = str((orden or {}).get("accion", "")).strip().lower()
        if not orden or accion in ("", "ninguna"):
            cerrar("\U0001F9E0 <i>%s</i>" % N.escapar(texto[:80]))
            self.preguntar(texto)          # no era una orden: es una pregunta
            return
        plan, aviso = self.validar_orden(orden)
        if not plan:
            cerrar(aviso or "No entend\u00ed qu\u00e9 quer\u00e9s que haga.")
            return
        self.estado["propuesta"] = {"plan": plan, "cuando": time.time()}
        self.guardar()
        cerrar(aviso, N.teclado([[("\u2705 Dale", "prop:si"), ("\u274C No", "prop:no")]]))

    def confirmar_propuesta(self, si=True):
        """El boton de la confirmacion. Devuelve el texto final."""
        p = self.estado.pop("propuesta", None)
        if not p or time.time() - float(p.get("cuando", 0)) > 1800:
            return "Esa propuesta ya venci\u00f3. Ped\u00edmelo de nuevo."
        if not si:
            self.guardar()
            return "\u274C Listo, no hice nada."
        try:
            salida = self.ejecutar_plan(p["plan"])
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
            "ia": "encendida" if IA.disponible(self.estado) else "apagada",
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

    def cuantos_archivos(self, clave):
        return len([n for n in self.estado.get("novedades", [])
                    if n.get("c") == clave and n.get("tipo") == "archivo"])

    def mandar_material(self, clave):
        """Te deja los documentos del ramo en el chat, sin entrar a la pagina."""
        g = self.estado.get("grupos", {}).get(clave, {})
        nombre = g.get("nombre", "ese ramo")
        archivos = [n for n in self.estado.get("novedades", [])
                    if n.get("c") == clave and n.get("tipo") == "archivo"]
        if not archivos:
            N.enviar("En <b>%s</b> todav\u00eda no hay ning\u00fan documento para bajar."
                     % N.escapar(nombre))
            return
        avisar, cerrar = self.animar("bajando los documentos de " + nombre)
        s = self.sesiones.get(g.get("fuente"))
        cuantos = 0
        if s:
            cuantos = self.mandar_adjuntos(
                s, [{"url": n["u"], "titulo": n["t"]} for n in archivos[:8]]) or 0
        if cuantos:
            cerrar("\U0001F4E5 Te mand\u00e9 %d documento%s de <b>%s</b>."
                   % (cuantos, "" if cuantos == 1 else "s", N.escapar(nombre)),
                   N.teclado([[("\u2B05\uFE0F Volver", "p:r:" + clave)]]))
        else:
            cerrar("No pude bajarlos. Te dejo los enlaces:\n\n"
                   + "\n".join("\U0001F4C4 " + N.enlace(n["t"], n["u"])
                               for n in archivos[:10]),
                   N.teclado([[("\u2B05\uFE0F Volver", "p:r:" + clave)]]))

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
            linea = "\U0001F4CC <b>%s</b>\n<i>%s%s</i>" % (
                N.escapar(t["titulo"]),
                (t.get("grupo", "") + " \u00b7 ") if t.get("grupo") else "", sello)
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
            "pausa: %s" % ("s\u00ed" if self.en_pausa() else "no"),
            "madrugada: %s" % ("sin sonido" if self.cfg().get("noche", True) else "suena"),
        ]
        for clave, cuando_fallo in self.estado.get("fallas", {}).items():
            lineas.append("\u26A0\uFE0F %s desde %s" % (clave, cuando_fallo))
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
        if self.estado.get("fallas_ia", 0) >= CFG.IA.get("fallas_para_apagar", 5):
            motivo = self.estado.get("ultimo_error_ia", "")
            return ("se apag\u00f3 sola por fallas (%s). Prend\u00e9la con /ia on"
                    % motivo[:80]) if motivo else \
                   "se apag\u00f3 sola por fallas. Prend\u00e9la con /ia on"
        if not IA.disponible():
            return "falta la clave de la IA"
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
            "texto_novedades": lambda: self._memo("nov", self.texto_novedades),
            "texto_pendientes": lambda: self._memo("pen", self.texto_pendientes),
            "texto_semana": lambda: self._memo("sem", self.texto_semana),
            "texto_silenciados": self.texto_silenciados,
            "texto_diagnostico": self.texto_diagnostico,
            "texto_ayuda": comandos.texto_ayuda,
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
        if f["clave"] in self.sesiones:
            return self.sesiones[f["clave"]], base
        s = sesion()
        entrar, _ = ADAPTADORES[f["modo"]]
        try:
            if not entrar(s, base, usuario, clave):
                # Nunca reintentar en bucle: varias fallas seguidas pueden
                # dejarte la cuenta bloqueada.
                log("[!] no pude entrar en la fuente", f["clave"])
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
                continue
            for g in grupos:
                clave = huella("grupo", f["clave"], g["id"])
                vistos_ahora.add(clave)
                self._ver_grupo(clave, g, f)
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
        cambio_ciego = bool(firma and ficha.get("firma") and firma != ficha["firma"])
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

        if frescos:
            self._avisar(clave, frescos)
        elif cambio_ciego:
            self._cambio_sin_nombre(clave, ficha)

    def _cambio_sin_nombre(self, clave, ficha):
        """La pagina del ramo cambio pero no pude decir en que. Antes esto
        pasaba callado y era justo el caso que se me escapaba. Ahora avisa,
        con freno para no repetir."""
        if not getattr(CFG, "AVISAR_CAMBIO_CIEGO", True):
            return
        if self.callado(clave):
            return
        horas = getattr(CFG, "HORAS_ENTRE_AVISOS_CIEGOS", 6)
        ultimo = leer_fecha(ficha.get("aviso_ciego", ""))
        hoy = ahora()
        if ultimo and (hoy - ultimo).total_seconds() < horas * 3600:
            return
        ficha["aviso_ciego"] = hoy.strftime("%Y-%m-%d %H:%M")
        N.enviar("%s <b>%s</b>\nCambi\u00f3 algo en la p\u00e1gina del ramo y no "
                 "pude decirte qu\u00e9. Puede ser un texto editado o algo que la "
                 "plataforma no me deja ver.\n%s"
                 % (ficha.get("emoji", "\U0001F4D8"),
                    N.escapar(ficha.get("nombre", "un ramo")),
                    N.enlace("abrir el ramo", ficha.get("url", ""))),
                 silencioso=True)

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
        # Guardo el id: asi puedo redibujar la tarjeta despues, por ejemplo
        # cuando me mandas una nota desde el teclado.
        self.estado["tareas"][tarea_id]["mensaje_id"] = mid
        self.mandar_adjuntos(s, [principal] + adjuntos, mid)

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
        avisos = self.estado.setdefault("avisos", {})
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
                if faltan <= h and str(h) not in avisos.setdefault(idt, []):
                    avisos[idt].append(str(h))
                    self._avisar_plazo(idt, t, f, faltan)
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
        N.enviar(texto, botones=self.botones_tarjeta(idt, t.get("clave", "")))

    # =================================================================
    #  resumen periodico y latido
    # =================================================================
    def recordar_sin_ver(self):
        """Un solo empujon por cosa: si a las tantas horas no la marcaste
        vista, te lo recuerda una vez y no jode mas."""
        horas = getattr(CFG, "HORAS_PARA_RECORDAR_VISTO", 0)
        if not horas or self.en_pausa() or self.en_silencio():
            return
        hoy = ahora()
        pendientes = []
        for idt, t in self.estado.get("tareas", {}).items():
            if t.get("hecho") or t.get("recordado") or t.get("mio") or t.get("de_agenda"):
                continue
            if t.get("es_tarea", True):
                continue          # esas ya avisan por su fecha de entrega
            if self.callado(t.get("clave", "")):
                continue
            nacio = leer_fecha(t.get("nacio"))
            if not nacio or (hoy - nacio).total_seconds() < horas * 3600:
                continue
            t["recordado"] = True
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
        N.enviar("\n".join(filas), botones=N.teclado([[
            ("\U0001F4CC Pendientes", "p:pen"), ("\U0001F431 Panel", "p:raiz")]]))

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
        self.estado["version_avisada"] = actual
        self.guardar()
        lineas = ["\U0001F195 <b>Actualizaci\u00f3n aplicada: v%s</b>" % actual]
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
        N.enviar("\n".join(lineas))
        log("[i] avise la version %s" % actual)

    def arranque(self):
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
        hoy = ahora()
        for idt, t in list(self.estado.get("tareas", {}).items()):
            if not t.get("mio") or t.get("hecho") or not t.get("vence"):
                continue
            f = leer_fecha(t["vence"])
            if not f:
                continue
            if (hoy - f).total_seconds() / 3600.0 >= horas:
                t["hecho"] = True
                self.redibujar_tarjeta(idt)

    def una_vuelta(self):
        self.revisar_todo()
        self.procesar_agenda()
        self.avisos_de_plazo()
        self.olvidar_recordatorios_viejos()
        self.recordar_sin_ver()
        self.resumen_periodico()
        self.latido()
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
            # se queda escuchando el chat: por eso los botones contestan al toque
            self.escuchar(CFG.ESPERA_CHAT)
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
