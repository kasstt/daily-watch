# -*- coding: utf-8 -*-
"""Todo lo que sale hacia el chat.

Ninguna funcion de aca lanza errores: si la mensajeria esta caida, el bot
sigue trabajando y lo reintenta despues.

Dos formatos importantes:
- La cita con barra al costado es SOLO para el texto de la IA.  Esa barra
  significa "esto lo escribio una maquina".  Todo lo de afuera es dato duro.
- La cita plegable deja el resumen largo escondido detras de un toque.
"""
import os
import re
import time

import requests

ESPERA = 25

# La mensajeria acepta 4096 letras. Dejo aire para las etiquetas que cierro.
LARGO_MAXIMO = 4000

# Etiquetas que van de a pares y hay que cerrar si el corte las dejo abiertas.
_PARES = ("b", "i", "u", "s", "code", "pre", "a", "blockquote")

# Una sola conexion viva para todo el chat.  Sin esto, cada mensaje abre y
# cierra una conexion cifrada nueva, y ese saludo cuesta entre 200 y 400 ms.
# Con esto, el segundo mensaje y los que siguen salen casi al instante.
_SESION = requests.Session()
_SESION.headers.update({"Connection": "keep-alive"})
_SESION.mount("https://", requests.adapters.HTTPAdapter(
    pool_connections=4, pool_maxsize=8, max_retries=0))

# Lo ultimo que contesto la mensajeria cuando algo salio mal.  Sirve para
# distinguir un error de verdad de un "ya estaba asi", que no es un error.
_ULTIMO_ERROR = {"texto": ""}


def _token():
    return os.environ.get("TG_TOKEN", "").strip()


def _chat():
    return os.environ.get("TG_CHAT", "").strip()


def listo():
    return bool(_token() and _chat())


def _api(metodo, datos=None, intentos=3):
    if not _token():
        return None
    url = "https://api.telegram.org/bot%s/%s" % (_token(), metodo)
    for i in range(intentos):
        try:
            r = _SESION.post(url, json=datos or {}, timeout=ESPERA + 10)
            if r.status_code == 429:
                espera = 3
                try:
                    espera = int(r.json()["parameters"]["retry_after"]) + 1
                except Exception:
                    pass
                time.sleep(min(espera, 30))
                continue
            if r.status_code != 200:
                try:
                    _ULTIMO_ERROR["texto"] = str(r.json().get("description", "")).lower()
                except Exception:
                    _ULTIMO_ERROR["texto"] = ""
                return None
            _ULTIMO_ERROR["texto"] = ""
            return r.json().get("result")
        except Exception:
            time.sleep(2 * (i + 1))
    return None


# ------------------------------------------------------------- formato
def escapar(t):
    return (str(t or "").replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def cita(texto, plegable=False):
    """La barra de color al costado. Reservada para lo que escribe la IA."""
    if not texto:
        return ""
    etiqueta = "<blockquote expandable>" if plegable else "<blockquote>"
    return etiqueta + texto + "</blockquote>"


def enlace(texto, url):
    return '<a href="%s">%s</a>' % (escapar(url), escapar(texto))


def sin_etiquetas(t):
    """Saca todas las etiquetas. Es el plan B cuando el formato falla."""
    return re.sub(r"<[^>]*>", "", t or "")


def cortar(texto, largo=LARGO_MAXIMO):
    """Corta un texto largo SIN partir una etiqueta ni un &simbolo;.

    Antes esto era texto[:4000] a lo bruto, y era una perdida de informacion
    callada: si el corte caia dentro de un <b> o de un &amp;, la mensajeria
    rechazaba el mensaje COMPLETO y el usuario no se enteraba de nada.  Le
    pasaba justo al resumen semanal, que es el mensaje mas largo del bot.
    """
    texto = texto or ""
    if len(texto) <= largo:
        return texto
    corte = texto[:largo]
    # 1. no dejar una etiqueta abierta por la mitad: <b o <a href="...
    if corte.rfind("<") > corte.rfind(">"):
        corte = corte[:corte.rfind("<")]
    # 2. no dejar un simbolo por la mitad: &amp o &#39
    ultimo_amp = corte.rfind("&")
    if ultimo_amp > corte.rfind(";") and len(corte) - ultimo_amp <= 10:
        corte = corte[:ultimo_amp]
    # 3. cerrar lo que quedo abierto, al reves de como se abrio
    abiertas = []
    for m in re.finditer(r"<(/?)([a-zA-Z]+)[^>]*>", corte):
        cierra, nombre = m.group(1), m.group(2).lower()
        if nombre not in _PARES:
            continue
        if cierra:
            if abiertas and nombre in abiertas:
                # saco la ultima igual, no la primera
                for i in range(len(abiertas) - 1, -1, -1):
                    if abiertas[i] == nombre:
                        del abiertas[i]
                        break
        else:
            abiertas.append(nombre)
    for nombre in reversed(abiertas):
        corte += "</%s>" % nombre
    return corte


def teclado(filas):
    """filas = [[(texto, dato), ...], ...]

    La mensajeria solo deja 64 BYTES por boton.  Antes esto hacia d[:64], que
    es peor que no poner el boton: un dato recortado apunta a OTRA cosa, asi
    que el boton hacia algo distinto de lo que decia.  Ahora, si el dato no
    entra, el boton NO se pone y queda avisado en el registro.
    """
    if not filas:
        return None
    armadas = []
    for fila in filas:
        if not fila:
            continue
        botones = []
        for t, d in fila:
            if not t:
                continue
            dato = str(d or "")
            if len(dato.encode("utf-8")) > 64:
                print("[!] boton con dato muy largo, no lo pongo: %s" % dato[:30])
                continue
            botones.append({"text": str(t)[:64], "callback_data": dato})
        if botones:
            armadas.append(botones)
    if not armadas:
        return None
    return {"inline_keyboard": armadas}


def botonera_fija():
    """Los tres atajos que quedan pegados abajo del teclado, para siempre."""
    return {"keyboard": [[{"text": "\U0001F4E5 Novedades"},
                          {"text": "\U0001F4CC Pendientes"},
                          {"text": "\U0001F431 Panel"}]],
            "resize_keyboard": True, "is_persistent": True}


def quitar_teclado():
    """Saca la botonera de abajo.  Se vuelve a poner con /atajos."""
    mid = enviar("Listo, saqu\u00e9 los atajos de abajo.",
                 botones={"remove_keyboard": True})
    return mid


# ------------------------------------------------------------- mandar
def enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    """Manda un mensaje. Devuelve el id del mensaje, o None."""
    if not listo() or not texto:
        return None
    datos = {
        "chat_id": _chat(),
        "text": cortar(texto),
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
        "disable_notification": bool(silencioso),
    }
    if botones:
        datos["reply_markup"] = botones
    elif teclado_fijo:
        datos["reply_markup"] = botonera_fija()
    r = _api("sendMessage", datos)
    if r is None and "parse" in _ULTIMO_ERROR["texto"].lower():
        # El formato salio mal. Antes de perder el mensaje, lo mando pelado:
        # es mejor leerlo sin negritas que no leerlo nunca.
        print("[!] el formato fallo, mando el mensaje sin etiquetas")
        datos.pop("parse_mode", None)
        datos["text"] = cortar(sin_etiquetas(texto))
        r = _api("sendMessage", datos)
    return (r or {}).get("message_id")


def editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    """Cambia un mensaje que ya esta en el chat, sin mandar uno nuevo.
    Es lo que hace que el panel se sienta una pantalla y no una catarata."""
    if not listo() or not mensaje_id:
        return False
    datos = {"chat_id": _chat(), "message_id": mensaje_id,
             "text": cortar(texto), "parse_mode": "HTML",
             "link_preview_options": {"is_disabled": True}}
    if botones:
        datos["reply_markup"] = botones
    elif limpiar_botones:
        datos["reply_markup"] = {"inline_keyboard": []}
    if _api("editMessageText", datos, intentos=2) is not None:
        return True
    if "parse" in _ULTIMO_ERROR["texto"].lower():
        datos.pop("parse_mode", None)
        datos["text"] = cortar(sin_etiquetas(texto))
        if _api("editMessageText", datos, intentos=2) is not None:
            return True
    # "el mensaje ya dice exactamente eso" no es una falla.  Si lo tomara por
    # falla, el panel se volveria a mandar y se volveria a anclar de gusto.
    return "not modified" in _ULTIMO_ERROR["texto"]


def anclar(mensaje_id):
    if mensaje_id:
        _api("pinChatMessage", {"chat_id": _chat(), "message_id": mensaje_id,
                                "disable_notification": True}, intentos=1)


def desanclar(mensaje_id):
    if mensaje_id:
        _api("unpinChatMessage", {"chat_id": _chat(), "message_id": mensaje_id},
             intentos=1)


def borrar(mensaje_id):
    if mensaje_id:
        _api("deleteMessage", {"chat_id": _chat(), "message_id": mensaje_id},
             intentos=1)


def avisar_boton(consulta_id, texto=""):
    """El cartelito que aparece arriba cuando apretas un boton."""
    _api("answerCallbackQuery", {"callback_query_id": consulta_id,
                                 "text": texto[:180]}, intentos=1)


def novedades(offset, espera=0):
    """Lee lo que le escribiste al bot desde la ultima vez.
    Con espera > 0 se queda escuchando hasta que llegue algo, que es lo que
    hace que los botones respondan al toque mientras el bot esta despierto."""
    if not listo():
        return []
    datos = {"timeout": espera, "limit": 40,
             "allowed_updates": ["message", "callback_query"]}
    if offset:
        datos["offset"] = offset
    return _api("getUpdates", datos, intentos=1) or []


def publicar_menu(lista):
    """lista = [(comando, descripcion), ...] en el orden que se muestran."""
    _api("setMyCommands", {"commands": [
        {"command": c, "description": d} for c, d in lista]}, intentos=1)


def mandar_archivo(nombre, contenido, leyenda=""):
    """Manda un archivo de texto armado por el bot."""
    datos = contenido.encode("utf-8") if isinstance(contenido, str) else contenido
    return mandar_documento(nombre, datos, leyenda)


def mandar_documento(nombre, datos, leyenda="", silencioso=True, responde_a=None):
    """Manda un archivo ya bajado, tal cual, sin tocarlo.

    En el chat no ocupa lugar en tu telefono hasta que lo tocas: vive en la
    nube de la mensajeria.
    """
    if not listo() or not datos:
        return None
    campos = {"chat_id": _chat(),
              "caption": (leyenda or "")[:900],
              "parse_mode": "HTML",
              "disable_notification": "true" if silencioso else "false"}
    if responde_a:
        campos["reply_to_message_id"] = str(responde_a)
    try:
        r = requests.post(
            "https://api.telegram.org/bot%s/sendDocument" % _token(),
            data=campos, files={"document": (nombre, datos)}, timeout=180)
        if r.status_code != 200:
            try:
                _ULTIMO_ERROR["texto"] = str(r.json().get("description", "")).lower()
            except Exception:
                _ULTIMO_ERROR["texto"] = ""
            return None
        return (r.json().get("result") or {}).get("message_id")
    except Exception:
        return None
