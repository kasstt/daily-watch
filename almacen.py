# -*- coding: utf-8 -*-
"""Donde vive la memoria del bot.

Primera opcion: un gist privado de GitHub.  Ahi la memoria puede guardar
texto legible (tus tareas, tus notas) porque nadie mas lo ve.

Si el gist falla, el bot no se cae: guarda en el propio repositorio, pero
solo huellas, sin una sola palabra legible.  Perdes las notas de ese rato,
no perdes un aviso.
"""
import json
import os

import requests

VERSION = 2
ARCHIVO_LOCAL = os.path.join("estado", "visto.json")
NOMBRE_EN_GIST = "memoria.json"
API = "https://api.github.com"


def _cabeceras():
    return {
        "Authorization": "Bearer %s" % os.environ.get("GH_TOKEN", "").strip(),
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def vacio():
    return {
        "version": VERSION,
        "arrancado": False,
        "items": {},          # huella -> fecha
        "grupos": {},         # clave de ramo -> {nombre, fuente, visto}
        "archivados": {},     # ramos que ya cursaste
        "ausentes": {},       # clave de ramo -> revisiones seguidas sin verlo
        "avisos": {},         # recordatorios ya mandados
        "tareas": {},         # id -> {grupo, titulo, url, vence, hecho, nota}
        "perfiles": {},       # clave de ramo -> nombre de perfil
        "callados": {},       # clave de ramo -> {hasta, cuenta}
        "novedades": [],      # ultimas cosas vistas, para /ultimo y /semana
        "pendientes_ia": {},  # cosas que faltan resumir
        "config": {},
        "fallas": {},
        "tg_offset": 0,
        "esperando_nota": None,
        "ultimo_resumen": "",
        "ultimo_latido": "",
        "fallas_ia": 0,
    }


def migrar(e):
    """Deja cualquier memoria vieja con la forma de hoy."""
    base = vacio()
    for k, v in base.items():
        e.setdefault(k, v)
    e["version"] = VERSION
    return e


def reducir(e):
    """Version sin nada legible, para cuando hay que guardar en el repo."""
    return {
        "version": VERSION,
        "arrancado": e.get("arrancado", False),
        "items": e.get("items", {}),
        "avisos": e.get("avisos", {}),
        "grupos": {k: {"visto": v.get("visto", "")} for k, v in e.get("grupos", {}).items()},
        "archivados": e.get("archivados", {}),
        "tg_offset": e.get("tg_offset", 0),
        "nota": "memoria reducida: el resto vive en el gist privado",
    }


# ------------------------------------------------------------------ gist
def _gist_id():
    return os.environ.get("GIST_ID", "").strip()


def hay_gist():
    return bool(os.environ.get("GH_TOKEN", "").strip())


_ULTIMO_ID = {"valor": ""}


def id_actual():
    """El id del gist que se esta usando ahora, para poder mostrarlo."""
    return _ULTIMO_ID["valor"] or _gist_id()


def crear_gist():
    """Crea el gist privado la primera vez. Devuelve el id o None."""
    if not hay_gist():
        return None
    cuerpo = {
        "description": "memoria",
        "public": False,
        "files": {NOMBRE_EN_GIST: {"content": json.dumps(vacio(), indent=1)}},
    }
    try:
        r = requests.post(API + "/gists", headers=_cabeceras(),
                          json=cuerpo, timeout=25)
        if r.status_code in (200, 201):
            return r.json().get("id")
        print("[!] no pude crear el gist (%s)" % r.status_code)
    except Exception as e:
        print("[!] no pude crear el gist (%s)" % type(e).__name__)
    return None


def _leer_gist(gid):
    r = requests.get(API + "/gists/" + gid, headers=_cabeceras(), timeout=25)
    if r.status_code != 200:
        raise RuntimeError("gist %s" % r.status_code)
    archivos = r.json().get("files", {})
    ficha = archivos.get(NOMBRE_EN_GIST) or (list(archivos.values()) or [{}])[0]
    texto = ficha.get("content") or ""
    if ficha.get("truncated") and ficha.get("raw_url"):
        texto = requests.get(ficha["raw_url"], timeout=25).text
    return json.loads(texto) if texto.strip() else vacio()


def _escribir_gist(gid, estado):
    cuerpo = {"files": {NOMBRE_EN_GIST: {
        "content": json.dumps(estado, indent=1, ensure_ascii=False, sort_keys=True)}}}
    r = requests.patch(API + "/gists/" + gid, headers=_cabeceras(),
                       json=cuerpo, timeout=25)
    if r.status_code != 200:
        raise RuntimeError("gist %s" % r.status_code)


# ------------------------------------------------------------------ local
def _leer_local():
    try:
        with open(ARCHIVO_LOCAL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return vacio()


def _escribir_local(estado):
    carpeta = os.path.dirname(ARCHIVO_LOCAL)
    if carpeta and not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    with open(ARCHIVO_LOCAL, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=1, ensure_ascii=False, sort_keys=True)


# ------------------------------------------------------------------ puerta
def cargar():
    """Devuelve (estado, modo, gist_nuevo).

    modo es "gist" o "repo".  gist_nuevo trae el id si se acaba de crear,
    para poder avisartelo por el chat.
    """
    gid = _gist_id()
    nuevo = None

    if hay_gist() and not gid:
        nuevo = crear_gist()
        gid = nuevo or ""
    _ULTIMO_ID["valor"] = gid

    if gid:
        try:
            return migrar(_leer_gist(gid)), "gist", nuevo
        except Exception as e:
            print("[!] no pude leer el gist (%s), uso el repositorio" % e)

    return migrar(_leer_local()), "repo", nuevo


def guardar(estado, modo):
    """Guarda y devuelve el modo con el que realmente se guardo."""
    gid = _gist_id() or _ULTIMO_ID["valor"]
    if modo == "gist" and gid:
        try:
            _escribir_gist(gid, estado)
            return "gist"
        except Exception as e:
            print("[!] no pude escribir el gist (%s), guardo reducido" % e)
    _escribir_local(reducir(estado) if modo == "gist" else estado)
    return "repo"
