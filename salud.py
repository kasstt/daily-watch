# -*- coding: utf-8 -*-
"""El seguro contra el apagon silencioso.

GitHub apaga solo los horarios programados de un repositorio que lleva 60
dias sin ningun movimiento.  No avisa con carteles: un dia el bot deja de
despertar y vos te enteras cuando ya perdiste una entrega.

En vacaciones de verano eso pasa seguro: no hay clases, nadie toca el
repositorio, y a los dos meses se apaga.

Por eso este archivo hace dos cosas:
  1. Cuenta cuantos dias hace que el repositorio no se mueve.
  2. A los 50 dias te avisa, con 10 dias de sobra para reaccionar.

Y ademas puede mover el repositorio solo, con un archivito de latido, asi
el reloj de los 60 dias vuelve a cero sin que hagas nada.

Las funciones de cuenta no tocan internet: se les pasa la fecha y listo.
Asi se pueden probar sin conexion y sin claves.
"""
import base64
import datetime as dt
import json
import os

import requests

try:                                  # el reloj de GitHub anda en otro huso
    from zoneinfo import ZoneInfo
    import fuentes as _CFG
    _ZONA = ZoneInfo(_CFG.ZONA_HORARIA)
except Exception:                     # sin husos instalados, mejor algo que nada
    _ZONA = None


def _ahora():
    """La hora de tu ciudad.  La maquina de GitHub vive varias horas adelante,
    asi que contar dias con SU reloj adelantaba o atrasaba el aviso un dia."""
    return dt.datetime.now(_ZONA) if _ZONA else dt.datetime.now()

API = "https://api.github.com"
ARCHIVO_LATIDO = "estado/latido.txt"


def _cabeceras():
    return {
        "Authorization": "Bearer %s" % os.environ.get("GH_TOKEN", "").strip(),
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def repo():
    """usuario/repositorio, o vacio si no esta configurado."""
    crudo = os.environ.get("GH_REPO", "").strip()
    if not crudo:
        # En GitHub Actions esto viene solo.
        crudo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    crudo = crudo.replace("https://github.com/", "").strip("/ ")
    if crudo.endswith(".git"):
        crudo = crudo[:-4]
    return crudo if crudo.count("/") == 1 else ""


# --------------------------------------------------------------- la cuenta
def leer_fecha_github(texto):
    """De "2026-06-01T13:45:02Z" saca un datetime sin zona.  None si no se puede."""
    t = str(texto or "").strip()
    if not t:
        return None
    t = t.replace("Z", "").replace("z", "")
    if "+" in t[10:]:
        t = t[:10] + t[10:].split("+")[0]
    for formato in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(t[:len("2026-06-01T13:45:02")], formato)
        except ValueError:
            continue
    return None


def dias_quieto(movido, hoy):
    """Cuantos dias hace que el repositorio no se mueve.

    movido puede ser el texto que devuelve GitHub o un datetime.
    hoy es un datetime (con o sin zona, no importa: se compara por dia).
    Devuelve None si no se sabe, para no inventar una alarma.
    """
    f = movido if isinstance(movido, dt.datetime) else leer_fecha_github(movido)
    if not f or not hoy:
        return None
    try:
        dias = (hoy.date() - f.date()).days
    except Exception:
        return None
    return max(0, dias)


def hay_que_avisar(dias, avisado_en="", hoy=None, aviso=50, repetir=7):
    """True si toca mandar el aviso.

    dias        cuantos lleva quieto (None = no se sabe, no se avisa)
    avisado_en  el dia en que se aviso la ultima vez, "AAAA-MM-DD"
    aviso       el umbral, 50 por defecto
    repetir     si sigue quieto, se recuerda cada tantos dias, no todos
    """
    if dias is None or dias < aviso:
        return False
    if not avisado_en:
        return True
    ultimo = None
    try:
        ultimo = dt.datetime.strptime(str(avisado_en)[:10], "%Y-%m-%d").date()
    except Exception:
        return True
    hoy_dia = (hoy or _ahora()).date()
    return (hoy_dia - ultimo).days >= repetir


def texto_del_aviso(dias, apaga=60, se_arreglo_solo=False):
    """El aviso, escrito por el programa. La IA no cuenta ni mide nada."""
    faltan = max(0, int(apaga) - int(dias))
    if se_arreglo_solo:
        return ("\u2705 <b>Ya lo resolv\u00ed</b>\n"
                "El repositorio llevaba %d d\u00edas quieto y GitHub apaga el reloj "
                "a los %d.\nLe di un toque solo, as\u00ed que la cuenta volvi\u00f3 a "
                "cero y sigo despertando normal.\nNo tenés que hacer nada."
                % (int(dias), int(apaga)))
    lineas = [
        "\u23F3 <b>Ojo con el reloj de GitHub</b>",
        "El repositorio lleva <b>%d d\u00edas</b> sin moverse." % int(dias),
        "A los %d d\u00edas GitHub apaga solo el horario programado y yo dejo "
        "de despertar, sin avisar nada." % int(apaga),
        "",
        "Te quedan <b>%d d\u00edas</b> para moverlo." % faltan,
        "",
        "Tocá <b>Despertar el reloj</b> ac\u00e1 abajo y lo arreglo yo en cinco "
        "segundos. Si preferís hacerlo a mano, alcanza con cualquier cambio "
        "en el repositorio.",
    ]
    return "\n".join(lineas)


# ------------------------------------------------------------- preguntarle
def consultar(nombre_repo=None, espera=20):
    """Le pregunta a GitHub cuando se movio el repositorio por ultima vez.

    Devuelve (texto_de_fecha, motivo_del_error).  Uno de los dos siempre
    viene vacio.  Nunca revienta: si no se puede saber, se dice.
    """
    r_nombre = nombre_repo or repo()
    if not r_nombre:
        return "", "no s\u00e9 c\u00f3mo se llama el repositorio"
    if not os.environ.get("GH_TOKEN", "").strip():
        return "", "no tengo la llave de GitHub"
    try:
        r = requests.get("%s/repos/%s" % (API, r_nombre),
                         headers=_cabeceras(), timeout=espera)
    except Exception as e:
        return "", "no me pude conectar (%s)" % type(e).__name__
    if r.status_code == 404:
        return "", ("GitHub contesta 404: la llave no alcanza para ver el "
                    "repositorio, o el nombre est\u00e1 mal")
    if r.status_code != 200:
        return "", "GitHub contest\u00f3 %s" % r.status_code
    try:
        ficha = r.json()
    except Exception:
        return "", "GitHub contest\u00f3 algo que no entend\u00ed"
    return str(ficha.get("pushed_at") or ficha.get("updated_at") or ""), ""


def tocar(nombre_repo=None, rama=None, espera=25):
    """Escribe un archivito de latido para que el reloj vuelva a cero.

    Devuelve (True, "") o (False, motivo).
    """
    r_nombre = nombre_repo or repo()
    if not r_nombre:
        return False, "no s\u00e9 c\u00f3mo se llama el repositorio"
    if not os.environ.get("GH_TOKEN", "").strip():
        return False, "no tengo la llave de GitHub"
    rama = rama or os.environ.get("GH_RAMA", "").strip() or "main"
    url = "%s/repos/%s/contents/%s" % (API, r_nombre, ARCHIVO_LATIDO)

    sha = ""
    try:
        vieja = requests.get(url, headers=_cabeceras(),
                             params={"ref": rama}, timeout=espera)
        if vieja.status_code == 200:
            sha = vieja.json().get("sha", "")
        elif vieja.status_code == 404:
            sha = ""
        else:
            return False, "GitHub contest\u00f3 %s al buscar el archivo" % vieja.status_code
    except Exception as e:
        return False, "no me pude conectar (%s)" % type(e).__name__

    cuerpo = {
        "message": "latido",
        "content": base64.b64encode(
            ("sigo vivo %s\n" % _ahora().strftime("%Y-%m-%d %H:%M")
             ).encode("utf-8")).decode("ascii"),
        "branch": rama,
    }
    if sha:
        cuerpo["sha"] = sha
    try:
        r = requests.put(url, headers=_cabeceras(), data=json.dumps(cuerpo),
                         timeout=espera)
    except Exception as e:
        return False, "no me pude conectar (%s)" % type(e).__name__
    if r.status_code in (200, 201):
        return True, ""
    if r.status_code == 404:
        return False, ("GitHub contesta 404: la llave tiene que ser una "
                       "clasica con permiso de repositorio")
    if r.status_code == 409:
        return False, "el repositorio estaba ocupado, lo reintento despu\u00e9s"
    return False, "GitHub contest\u00f3 %s" % r.status_code


# ------------------------------------------------------- pedir un turno nuevo
ARCHIVO_DEL_RELOJ = "watch.yml"


def relanzar(nombre_repo=None, rama=None, archivo=None, espera=25):
    """Le pide a GitHub que arranque un turno nuevo AHORA.

    Antes, apagarse dependia de que el reloj sonara solo: entre que sonaba y
    que arrancaba podian pasar veinte minutos o mas, y en el chat eso se ve
    igual que un bot muerto.  Pedir el turno a mano es la unica forma de
    prometer una vuelta y cumplirla.

    Devuelve (True, "") o (False, motivo escrito para una persona).
    """
    r_nombre = nombre_repo or repo()
    if not r_nombre:
        return False, "no s\u00e9 c\u00f3mo se llama el repositorio"
    if not os.environ.get("GH_TOKEN", "").strip():
        return False, "no tengo la llave de GitHub"
    rama = rama or os.environ.get("GH_RAMA", "").strip() or "main"
    archivo = archivo or os.environ.get("GH_RELOJ", "").strip() or ARCHIVO_DEL_RELOJ
    url = "%s/repos/%s/actions/workflows/%s/dispatches" % (API, r_nombre, archivo)
    try:
        r = requests.post(url, headers=_cabeceras(),
                          data=json.dumps({"ref": rama}), timeout=espera)
    except Exception as e:
        return False, "no me pude conectar (%s)" % type(e).__name__
    if r.status_code in (200, 201, 204):
        return True, ""
    if r.status_code in (401, 403):
        return False, ("la llave de GitHub no alcanza para pedir un turno "
                       "nuevo")
    if r.status_code == 404:
        return False, ("no encuentro el reloj del repositorio (%s)"
                       % archivo)
    if r.status_code == 422:
        return False, ("el reloj del repositorio no acepta arranques a mano")
    return False, "GitHub contest\u00f3 %s" % r.status_code


# ------------------------------------------------------------- la revision
def revisar(estado, hoy, aviso=50, apaga=60, arreglar_solo=True,
            consultar_fn=None, tocar_fn=None):
    """La revision completa, la que llama el bot una vez por dia.

    Devuelve (texto_para_mandar, botones_sugeridos).  Si no hay nada que
    decir, devuelve ("", []).  Nunca revienta.

    consultar_fn y tocar_fn se pueden reemplazar para probar sin internet.
    """
    pedir = consultar_fn or consultar
    empujar = tocar_fn or tocar

    fecha, motivo = pedir()
    if motivo:
        # No se pudo preguntar.  Se anota, pero no se molesta al usuario mas
        # de una vez por semana: no saber no es una emergencia.
        estado["repo_motivo"] = motivo
        ultimo = estado.get("repo_aviso_ciego", "")
        if hay_que_avisar(999, ultimo, hoy, aviso=0, repetir=7):
            estado["repo_aviso_ciego"] = hoy.strftime("%Y-%m-%d")
            return ("\u2139\uFE0F No pude revisar el reloj de GitHub: %s.\n"
                    "No es urgente, pero si esto sigue as\u00ed no voy a poder "
                    "avisarte si el horario se apaga solo." % motivo), []
        return "", []

    estado["repo_motivo"] = ""
    estado["repo_movido"] = fecha
    dias = dias_quieto(fecha, hoy)
    estado["repo_dias"] = dias if dias is not None else -1

    if not hay_que_avisar(dias, estado.get("repo_aviso", ""), hoy, aviso=aviso):
        return "", []

    estado["repo_aviso"] = hoy.strftime("%Y-%m-%d")

    if arreglar_solo:
        bien, falla = empujar()
        if bien:
            estado["repo_movido"] = hoy.strftime("%Y-%m-%dT%H:%M:%SZ")
            estado["repo_dias"] = 0
            estado["repo_toques"] = int(estado.get("repo_toques", 0)) + 1
            return texto_del_aviso(dias, apaga, se_arreglo_solo=True), []
        return (texto_del_aviso(dias, apaga)
                + "\n\n<i>Intent\u00e9 arreglarlo solo y no pude: %s.</i>" % falla,
                [[("\u23F0 Despertar el reloj", "a:tocar")]])

    return texto_del_aviso(dias, apaga), [[("\u23F0 Despertar el reloj", "a:tocar")]]


def linea_de_estado(estado):
    """Una linea para el diagnostico."""
    if estado.get("repo_motivo"):
        return "Reloj de GitHub: no lo pude revisar (%s)" % estado["repo_motivo"]
    dias = estado.get("repo_dias", -1)
    try:
        dias = int(dias)
    except Exception:
        dias = -1
    if dias < 0:
        return "Reloj de GitHub: todav\u00eda no lo revis\u00e9"
    return "Reloj de GitHub: el repositorio se movi\u00f3 hace %d d\u00eda%s (se apaga a los 60)" % (
        dias, "" if dias == 1 else "s")
