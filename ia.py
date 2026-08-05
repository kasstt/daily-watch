# -*- coding: utf-8 -*-
"""Los resumenes.  Todo lo que tenga que ver con inteligencia artificial
vive aca adentro y en ningun otro lado.

Dos reglas que no se rompen nunca:

1. La IA NO escribe el aviso.  Rellena una sola parte, la de la cita.  Las
   fechas, los nombres y los enlaces los pone el codigo, siempre.  Una IA
   que inventa un plazo te cuesta una nota.
2. Si la IA falla, devuelve None y el aviso sale igual, sin la cita.
   Ninguna funcion de este archivo lanza errores hacia afuera.

Cambiar de proveedor son tres lineas en fuentes.py.  Casi todos los
servicios de hoy hablan el formato de OpenAI, asi que "compatible" cubre
Groq, DeepSeek, OpenRouter, Together y hasta el propio Gemini.
"""
import base64
import hashlib
import json
import os
import re
import time

import requests

import fuentes as CFG

CORTE = "###"

ORDEN = (
    "Sos un asistente que le resume material de clase a un estudiante de "
    "ingenieria. Te paso el titulo, la descripcion que escribio el profesor y "
    "el texto de los archivos adjuntos, si hay.\n\n"
    "Escribi en castellano rioplatense neutro, directo, sin saludos, sin "
    "introduccion y sin repetir el titulo.\n\n"
    "Respondeme en dos partes separadas por una linea con " + CORTE + ":\n"
    "PARTE 1: una o dos frases con lo esencial. Que es y que hay que hacer. "
    "Maximo %d caracteres. Esta parte es obligatoria.\n"
    "PARTE 2: solo si de verdad hace falta, el detalle util. Temas que cubre, "
    "cuantos ejercicios, que se entrega, condiciones importantes. Usa vinetas "
    "con guion. Maximo %d caracteres. Si con la parte 1 alcanza, deja la "
    "parte 2 vacia. No rellenes por rellenar.\n\n"
    "No inventes fechas ni notas ni porcentajes que no esten en el texto. "
    "Si el material esta vacio o ilegible, responde exactamente SIN TEXTO."
)


# Para conversar.  Aca la IA NO ve archivos ni claves: solo la libreta de
# lo que el bot ya anoto (ramos, titulos, fechas, tus notas).
ORDEN_CHARLA = (
    "Sos el ayudante personal de un estudiante de ingenieria. Te paso su "
    "libreta: los ramos que cursa, lo que subieron los profesores, las fechas "
    "de entrega y sus notas personales.\n\n"
    "Contesta con esa libreta y con el MANUAL del bot que te paso abajo. Si "
    "pregunta como se usa algo del bot, contesta con el manual y nombra el "
    "comando o el boton exacto. Si el dato no esta en ningun lado, deci que "
    "no lo tenes anotado y en una linea deci donde podria mirarlo. Nunca "
    "inventes fechas, notas, porcentajes, archivos ni comandos.\n\n"
    "Castellano rioplatense neutro, directo, sin saludos ni preambulo.\n\n"
    "El largo lo decide la pregunta, no vos. Si es una pregunta simple, dos "
    "lineas y listo. Si de verdad hay varias cosas que contar, explayate, "
    "hasta %d caracteres. Nunca rellenes para llegar al limite y nunca "
    "cierres a mitad de una idea. Sin markdown raro, solo texto y guiones "
    "para las vinetas."
)


# El manual del bot, en criollo.  Va pegado a cada charla para que la IA
# pueda contestar dudas de uso sin inventar botones que no existen.
MANUAL = (
    "COMO FUNCIONA ESTE BOT (usalo para contestar dudas de uso):\n"
    "- Miro dos plataformas de la universidad cada 10 minutos y aviso apenas "
    "aparece algo nuevo: archivos, tareas, foros, cambios de fecha.\n"
    "- Trabajo de 07:00 a 02:00. De madrugada, si esta puesto el modo noche, "
    "llego sin sonido.\n"
    "- Botones de cada aviso: hecho o lo vi, nota, posponer 1 hora, posponer "
    "3 horas, y la campana tachada para callar ese ramo.\n"
    "- Panel: Pendientes, Novedades, Semana, Ramos, Avisos, Pausa, Noche, IA "
    "y Ajustes. Dentro de un ramo hay Ver material, Mandame los archivos y "
    "Resumen con IA.\n"
    "- Comandos: /pendientes lo que falta, /ultimo lo ultimo que subieron, "
    "/semana los ultimos 7 dias, /resumen ramo NOMBRE resumen de un ramo, "
    "/pausa 3 callarme 3 horas, /noche avisos de madrugada, /estado si todo "
    "funciona, /perfil cuanto insistir, /callar silenciar un ramo, /revisar "
    "mirar ahora, /recordar guardar un apunte, /ia prender o apagar los "
    "resumenes, /exportar mandar todo en un archivo, /ayuda la lista.\n"
    "- Perfiles de insistencia, o sea cada cuanto recuerdo una entrega:\n"
    "  suave: 3 dias antes y 12 horas antes.\n"
    "  normal: 3 dias, 1 dia y 3 horas antes. Es el que viene puesto.\n"
    "  apretado: 7 dias, 3 dias, 1 dia, 6 horas, 2 horas y 30 minutos antes.\n"
    "  diario: una vez por dia hasta la entrega.\n"
    "  Se cambia con /perfil apretado NOMBREDELRAMO, o desde el ramo en el "
    "panel. Vale uno distinto por ramo.\n"
    "- Los recordatorios que pide el estudiante suenan una sola vez, a la "
    "hora pedida.\n"
    "- Tambien podes pedirme acciones hablando normal, sin comando. Yo "
    "entiendo el pedido y despues el programa te muestra una confirmacion "
    "antes de hacer nada.\n"
)


# Ordenes habladas.  La IA SOLO traduce lo que pediste a un JSON. No ejecuta
# nada: el programa valida, arma la confirmacion y recien ahi se hace.
ORDEN_ACCION = (
    "Sos el traductor de pedidos de un bot de avisos de universidad. Te paso "
    "lo que escribio el estudiante y tenes que devolver UNICAMENTE un objeto "
    "JSON, sin explicaciones, sin markdown y sin texto alrededor.\n\n"
    "Formas validas:\n"
    '{"accion":"recordar","cuando":"AAAA-MM-DD HH:MM","que":"texto corto"}\n'
    '{"accion":"pausa","horas":3}\n'
    '{"accion":"seguir"}\n'
    '{"accion":"callar","ramo":"nombre"}\n'
    '{"accion":"perfil","perfil":"suave|normal|apretado|diario","ramo":"nombre o vacio"}\n'
    '{"accion":"revisar"}\n'
    '{"accion":"resumen","ramo":"nombre"}\n'
    '{"accion":"buscar_archivos","ramo":"nombre o vacio",'
    '"desde":"AAAA-MM-DD","hasta":"AAAA-MM-DD",'
    '"nombre":"parte del nombre o vacio","tipo":"pdf|doc|ppt|xls|todo"}\n'
    '{"accion":"hecho","tarea":"titulo o parte del titulo"}\n'
    '{"accion":"noche"}\n'
    '{"accion":"ninguna"}\n\n'
    "Reglas:\n"
    "- Si el estudiante pregunta algo en vez de pedir una accion, devolve "
    'accion "ninguna".\n'
    "- Las fechas se calculan contra el AHORA que te paso, nunca contra otra "
    "cosa, y siempre en el formato AAAA-MM-DD HH:MM.\n"
    "- Los nombres de ramo salen de la lista RAMOS que te paso, tal cual.\n"
    "- Si pide archivos, material, documentos, pdf o apuntes de un ramo, la "
    'accion es "buscar_archivos". Vos NO contas archivos ni decis cuantos '
    "hay: solo traducis el pedido. Si no dijo fechas, deja desde y hasta "
    "vacios. Si dijo la semana pasada o el ultimo mes, calcula las fechas "
    "contra el AHORA.\n"
    "- Contesta siempre en castellano, nunca en ingles.\n"
    '- Ante la menor duda, accion "ninguna".'
)


def _json_de(salida):
    """Saca el primer objeto JSON de lo que haya contestado la IA."""
    if not salida:
        return None
    texto = str(salida).strip()
    texto = re.sub(r"^```[a-zA-Z]*|```$", "", texto).strip()
    i = texto.find("{")
    j = texto.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        dato = json.loads(texto[i:j + 1])
    except Exception:
        return None
    return dato if isinstance(dato, dict) else None


def interpretar(estado, texto, contexto):
    """Traduce un pedido hablado a un plan. Devuelve dict o None.

    Nunca ejecuta nada y nunca lanza errores hacia afuera."""
    if not disponible(estado) or not (texto or "").strip():
        return None
    pedido = "%s\n\nCONTEXTO\n%s\n\nPEDIDO\n%s" % (
        ORDEN_ACCION, contexto[:2000], texto[:400])
    try:
        salida = _pedir(estado, pedido, [])
    except Exception as e:
        estado["fallas_ia"] = estado.get("fallas_ia", 0) + 1
        estado["ultimo_error_ia"] = str(e)[:200]
        return None
    estado["fallas_ia"] = 0
    return _json_de(salida)


def preguntar(estado, pregunta, libreta):
    """Charla sobre lo que el bot ya sabe. Devuelve texto o None."""
    if not disponible(estado) or not (pregunta or "").strip():
        return None
    pedido = "%s\n\n%s\nLIBRETA\n%s\n\nPREGUNTA\n%s" % (
        ORDEN_CHARLA % CFG.IA.get("largo_charla", 900),
        MANUAL, libreta[:12000], pregunta[:600])
    try:
        salida = _pedir(estado, pedido, [])
    except Exception as e:
        estado["fallas_ia"] = estado.get("fallas_ia", 0) + 1
        estado["ultimo_error_ia"] = str(e)[:200]
        return None
    estado["fallas_ia"] = 0
    salida = (salida or "").strip()
    # Dos filtros para que al chat no salga cualquier cosa.
    if _parece_json(salida):
        estado["ultimo_error_ia"] = "me contesto en formato de maquina"
        return None
    if _parece_ingles(salida):
        estado["ultimo_error_ia"] = "me contesto en ingles y lo tir\u00e9"
        return None
    return _recortar(salida, CFG.IA.get("techo_charla", 1800)) or None


# Al chat NUNCA sale texto en ingles ni un JSON crudo.
PALABRAS_INGLESAS = (" the ", " with ", " your ", " you ", " and ", " will ",
                     " minutes", " hours", " remind", " is going", " at the ",
                     " i will", " here is", " tomorrow", " please")


def _parece_ingles(texto):
    t = " " + (texto or "").lower().replace("\n", " ") + " "
    return sum(1 for p in PALABRAS_INGLESAS if p in t) >= 2


def _parece_json(texto):
    t = (texto or "").strip()
    return t.startswith("{") or t.startswith("[") or t.startswith('"accion"')


def _recortar(texto, limite):
    """Recorta sin cortar a mitad de una frase.

    Antes tajeaba en el caracter justo y la ultima oracion quedaba colgada.
    Ahora vuelve hasta el ultimo punto, y si no hay, hasta el ultimo espacio.
    El limite es un techo, no una meta."""
    texto = (texto or "").strip()
    if len(texto) <= limite:
        return texto
    recorte = texto[:limite]
    corte = max(recorte.rfind(". "), recorte.rfind(".\n"),
                recorte.rfind("\n- "), recorte.rfind("! "), recorte.rfind("? "))
    if corte > limite * 0.55:
        return recorte[:corte + 1].strip()
    # Los tres puntos tambien ocupan lugar: el limite es limite de verdad.
    return recorte[:max(limite - 3, 1)].rsplit(" ", 1)[0].strip() + "..."


# ---------------------------------------------------------- las claves
# Varias claves con orden de preferencia y relevo automatico.
# Regla de oro: una clave NUNCA se escribe en un registro ni en el chat.
# Se las nombra "clave 2 de 3".


class SinCupo(RuntimeError):
    """Se acabo el regalo del dia o me pase de pedidos por minuto."""


class ClaveMala(RuntimeError):
    """La clave no sirve o no tiene permiso. No se reintenta sola."""


class SeCayo(RuntimeError):
    """Problema de red o del servicio. Se reintenta en un rato."""


_MODELO_QUE_ANDA = {}


def _marca(clave):
    """Huella corta de la clave. Si la cambias, la penitencia se borra sola."""
    return hashlib.sha1((clave or "").encode("utf-8")).hexdigest()[:10]


def _una_clave(nombre, valor, sufijo=""):
    return {
        "nombre": nombre,
        "clave": valor,
        "proveedor": (os.environ.get(sufijo + "_PROVEEDOR", "").strip()
                      or CFG.IA["proveedor"]),
        "modelo": (os.environ.get(sufijo + "_MODELO", "").strip()
                   or CFG.IA["modelo"]),
        "url": os.environ.get(sufijo + "_URL", "").strip() or CFG.IA.get("url", ""),
    }


def claves():
    """Las claves en orden de preferencia, sin repetidas.

    Podes cargarlas de dos maneras, la que menos te cueste:
    una por Secret (IA_KEY, IA_KEY_2, IA_KEY_3...) o todas juntas separadas
    por coma en IA_KEYS. Cada una puede ser de otro proveedor si le agregas
    IA_KEY_2_PROVEEDOR y IA_KEY_2_MODELO."""
    salida, vistas = [], set()
    for env in CFG.IA.get("claves_env", ["IA_KEY"]):
        valor = os.environ.get(env, "").strip()
        if valor and valor not in vistas:
            vistas.add(valor)
            salida.append(_una_clave(env, valor, env))
    juntas = os.environ.get(CFG.IA.get("env_lista", "IA_KEYS"), "")
    for pedazo in re.split(r"[,;\n]+", juntas):
        pedazo = pedazo.strip()
        if pedazo and pedazo not in vistas:
            vistas.add(pedazo)
            salida.append(_una_clave("IA_KEYS_%d" % len(salida), pedazo))
    return salida


def _fichas(estado):
    if estado is None:
        return {}
    return estado.setdefault("ia_claves", {})


def _descansando(estado, c):
    """Devuelve por que esta en penitencia, o vacio si esta lista."""
    ficha = _fichas(estado).get(c["nombre"])
    if not ficha or ficha.get("marca") != _marca(c["clave"]):
        return ""
    motivo = ficha.get("motivo", "")
    if motivo == "mala":
        return "marcada como mala, cambiala vos"
    falta = ficha.get("hasta", 0) - time.time()
    if falta <= 0:
        return ""
    minutos = int(falta / 60) + 1
    if motivo == "cupo":
        return "sin cupo, %s" % _en_cuanto(falta)
    if motivo == "cansada":
        return "fallo muchas veces, vuelve en %d min" % minutos
    return "se cayo, vuelve en %d min" % minutos


def _en_cuanto(segundos):
    """Cuanto falta, dicho como lo diria una persona."""
    minutos = int(segundos / 60) + 1
    if minutos < 90:
        return "vuelve en %d min" % minutos
    if segundos < 20 * 3600:
        return "vuelve en %d horas" % int(round(segundos / 3600.0))
    return "vuelve ma\u00f1ana"


def _segundos_hasta_manana():
    """Lo que falta para que se renueve el cupo del dia, en la hora de casa."""
    try:
        import datetime as _dt
        from zoneinfo import ZoneInfo
        aca = _dt.datetime.now(ZoneInfo(getattr(CFG, "ZONA_HORARIA", "UTC")))
        manana = (aca + _dt.timedelta(days=1)).replace(
            hour=0, minute=10, second=0, microsecond=0)
        return max(60, int((manana - aca).total_seconds()))
    except Exception:
        return 6 * 3600


def _es_cupo_del_dia(detalle):
    """Un rechazo por cupo puede ser "me pegaste muy seguido" o "se te acabo
    lo del dia".  No es lo mismo: por el primero conviene esperar un rato, por
    el segundo no vale la pena insistir hasta que cambie el dia."""
    d = str(detalle or "").lower()
    return any(p in d for p in ("per day", "perday", "por dia", "daily",
                                "por hoy", "quota", "cuota", "requests per"))


def _penitencia(estado, c, motivo, detalle=""):
    ficha = _fichas(estado).setdefault(c["nombre"], {})
    if ficha.get("marca") != _marca(c["clave"]):
        ficha.clear()
    fallas = ficha.get("fallas", 0) + 1
    if motivo == "cupo":
        espera = CFG.IA.get("descanso_cupo_minutos", 60) * 60
        if CFG.IA.get("cupo_hasta_manana", True) and _es_cupo_del_dia(detalle):
            espera = max(espera, _segundos_hasta_manana())
    elif motivo == "mala":
        espera = 0
    else:
        espera = CFG.IA.get("descanso_red_minutos", 5) * 60
    # El apagado por fallas se cuenta POR CLAVE, no para toda la IA.
    if motivo != "mala" and fallas >= CFG.IA.get("fallas_para_apagar", 5):
        motivo, espera = "cansada", max(espera, 6 * 3600)
    ficha.update({"marca": _marca(c["clave"]), "motivo": motivo,
                  "fallas": fallas, "hasta": time.time() + espera})


def _anduvo(estado, c):
    _fichas(estado).pop(c["nombre"], None)


def como_van_las_claves(estado=None):
    """Para /estado. Sin nombres de variables ni pedazos de clave."""
    lista = claves()
    if not lista:
        return "ninguna cargada"
    partes = []
    for i, c in enumerate(lista, 1):
        partes.append("clave %d de %d: %s"
                      % (i, len(lista), _descansando(estado, c) or "lista"))
    en_uso = (estado or {}).get("ia_clave_en_uso")
    if en_uso:
        partes.append("ahora uso la %s" % en_uso)
    return " \u00b7 ".join(partes)


def cuando_vuelve(estado=None):
    """Por que no hay resumen ahora, dicho para el dueno del bot.

    /estado muestra el detalle clave por clave.  Esto es la version corta que
    va en un mensaje cualquiera: sin numeros de clave, sin nombres de
    variables y diciendo cuando conviene volver a probar."""
    lista = claves()
    if not lista:
        return "no tengo ninguna clave de IA guardada"
    peor, cupo, mala = 0, False, False
    for c in lista:
        ficha = _fichas(estado).get(c["nombre"]) or {}
        if ficha.get("marca") != _marca(c["clave"]):
            return "puedo intentarlo de nuevo"
        if ficha.get("motivo") == "mala":
            mala = True
            continue
        falta = ficha.get("hasta", 0) - time.time()
        if falta <= 0:
            return "puedo intentarlo de nuevo"
        peor = max(peor, falta)
        if ficha.get("motivo") == "cupo":
            cupo = True
    if cupo and peor > 3 * 3600:
        return "hoy ya se me acab\u00f3 el cupo de res\u00famenes, vuelve ma\u00f1ana"
    if peor:
        return "estoy descansando un rato, %s" % _en_cuanto(peor)
    if mala:
        return "la clave de IA que tengo no sirve, hay que cambiarla"
    return "no puedo resumir en este momento"


def _pedir(estado, texto, pdfs=()):
    """Prueba las claves en orden y devuelve la primera respuesta buena.

    El relevo es callado: no te aviso cada vez que cambio de clave, solo
    cuando no queda ninguna. Siempre se arranca desde la primera, asi que
    cuando la preferida se recupera vuelve sola."""
    lista = claves()
    if not lista:
        raise RuntimeError("no hay ninguna clave de IA cargada")
    motivos = []
    for i, c in enumerate(lista, 1):
        quieta = _descansando(estado, c)
        if quieta:
            # Al dueno no le sirve saber CUAL de las claves fue, solo por que.
            motivos.append(quieta.split(",")[0])
            continue
        motor = PROVEEDORES.get(c.get("proveedor") or CFG.IA["proveedor"])
        if not motor:
            motivos.append("mal configurada")
            continue
        try:
            salida = motor(texto, list(pdfs or []), c)
        except SinCupo as e:
            _penitencia(estado, c, "cupo", str(e))
            motivos.append("sin cupo")
            continue
        except ClaveMala as e:
            _penitencia(estado, c, "mala")
            motivos.append("no sirve")
            continue
        except Exception as e:
            _penitencia(estado, c, "red")
            motivos.append("se cay\u00f3")
            continue
        _anduvo(estado, c)
        if estado is not None:
            estado["ia_clave_en_uso"] = "clave %d de %d" % (i, len(lista))
            estado.pop("ia_sin_claves", None)
        return salida
    if estado is not None:
        estado["ia_sin_claves"] = True
    # Este texto lo lee el dueno, asi que va sin jerga y diciendo que hacer.
    # Ordenados y sin repetir: "sin cupo, sin cupo, sin cupo" no dice mas.
    resumen = ", ".join(sorted(set(m for m in motivos if m)))[:120] or "no pudo"
    if len(lista) == 1:
        raise RuntimeError("mi \u00fanica clave de IA no puede ahora: %s. Con una "
                           "segunda clave de repuesto esto casi no te pasar\u00eda"
                           % resumen)
    raise RuntimeError("mis %d claves de IA no pueden ahora: %s"
                       % (len(lista), resumen))


def disponible(estado=None):
    if CFG.IA["proveedor"] == "ninguno":
        return False
    lista = claves()
    if not lista:
        return False
    if estado is not None:
        if not estado.get("config", {}).get("ia", True):
            return False
        if all(_descansando(estado, c) for c in lista):
            return False
    return True


def ramo_excluido(nombre):
    n = (nombre or "").lower()
    return any(x.lower() in n for x in CFG.IA.get("ramos_sin_ia", []))


# ------------------------------------------------------------ proveedores
def _gemini(texto, pdfs, c=None):
    """Hay dos formatos de clave dando vueltas.

    Las viejas empiezan con AIza y viajan como parametro en la direccion.
    Las nuevas empiezan con AQ. y SOLO funcionan en la cabecera
    x-goog-api-key.  Mandamos la cabecera siempre, que sirve para las dos.

    Si el modelo configurado no existe para tu clave, prueba los de
    repuesto antes de darse por vencido.
    """
    partes = [{"text": texto[:24000]}]
    for crudo in pdfs:
        partes.append({"inline_data": {
            "mime_type": "application/pdf",
            "data": base64.b64encode(crudo).decode()}})
    c = c or {"clave": "", "modelo": CFG.IA["modelo"], "nombre": "IA_KEY"}
    cuerpo = {"contents": [{"parts": partes}],
              "generationConfig": {
                  "maxOutputTokens": CFG.IA.get("tokens_maximos", 1200),
                  "temperature": 0.2}}
    cabeceras = {"x-goog-api-key": c["clave"],
                 "Content-Type": "application/json"}

    preferido = _MODELO_QUE_ANDA.get(c["nombre"]) or c.get("modelo") or CFG.IA["modelo"]
    modelos = [preferido] + [m for m in CFG.IA.get("modelos_de_repuesto", [])
                             if m != preferido]
    ultimo = ""
    for modelo in modelos:
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "%s:generateContent" % modelo)
        try:
            r = requests.post(url, headers=cabeceras, json=cuerpo, timeout=90)
        except Exception as e:
            ultimo = "no pude conectarme (%s)" % type(e).__name__
            continue
        if r.status_code == 200:
            # El modelo que anda se recuerda por clave, no para todos.
            _MODELO_QUE_ANDA[c["nombre"]] = modelo
            d = r.json()
            try:
                return d["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                raise RuntimeError("contesto vacio, puede ser el filtro de contenido")
        ultimo = _motivo(r, modelo)
        if r.status_code == 429:
            raise SinCupo(ultimo)              # esta clave descansa un rato
        if r.status_code in (400, 401, 403):
            if r.status_code in (401, 403) or "clave" in ultimo:
                raise ClaveMala(ultimo)        # esta no se reintenta sola
            break                              # es la clave, cambiar de modelo no ayuda
    raise SeCayo(ultimo or "no contesto")


def _motivo(r, modelo=""):
    """El error de verdad, en castellano, para no adivinar."""
    try:
        detalle = str((r.json().get("error") or {}).get("message", ""))[:200]
    except Exception:
        detalle = ""
    if r.status_code in (401, 403):
        return "la clave no sirve o no tiene permiso. %s" % detalle
    if r.status_code == 400 and "api key" in detalle.lower():
        return "la clave esta mal escrita. %s" % detalle
    if r.status_code == 404:
        return "el modelo %s no existe para tu clave. %s" % (modelo, detalle)
    if r.status_code == 429:
        return "te pasaste del limite gratis por hoy. %s" % detalle
    return "error %s. %s" % (r.status_code, detalle)


def _compatible(texto, pdfs, c=None):
    """Cualquier servicio con el formato de OpenAI.
    Estos no leen archivos, asi que el PDF ya viene convertido a texto."""
    c = c or {"clave": "", "modelo": CFG.IA["modelo"], "url": CFG.IA["url"]}
    url = (c.get("url") or CFG.IA["url"]).rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    r = requests.post(url,
                      headers={"Authorization": "Bearer %s" % c["clave"]},
                      json={"model": c.get("modelo") or CFG.IA["modelo"],
                            "messages": [{"role": "user", "content": texto[:24000]}],
                            "max_tokens": CFG.IA.get("tokens_maximos", 1200),
                            "temperature": 0.2},
                      timeout=60)
    if r.status_code == 429:
        raise SinCupo("sin cupo")
    if r.status_code in (401, 403):
        raise ClaveMala("la clave no sirve o no tiene permiso")
    if r.status_code != 200:
        raise SeCayo("ia %s" % r.status_code)
    return r.json()["choices"][0]["message"]["content"]


PROVEEDORES = {"gemini": _gemini, "compatible": _compatible}


def lee_archivos():
    """True si el proveedor de hoy puede tragarse un PDF entero."""
    return CFG.IA["proveedor"] == "gemini"


# ------------------------------------------------------------ bajar cosas
def _texto_de_html(html):
    from bs4 import BeautifulSoup
    sopa = BeautifulSoup(html, "html.parser")
    for b in sopa.find_all(["script", "style", "nav", "header", "footer"]):
        b.decompose()
    return " ".join(sopa.get_text(" ").split())


def _texto_de_pdf(crudo):
    try:
        import io
        from pypdf import PdfReader
        lector = PdfReader(io.BytesIO(crudo))
        hojas = [(p.extract_text() or "") for p in lector.pages[:CFG.IA["paginas_maximas"]]]
        return " ".join(" ".join(hojas).split()), len(lector.pages)
    except Exception:
        return "", 0


def _texto_de_office(crudo, ext):
    """Saca el texto de un .docx o un .pptx sin instalar nada.

    Por dentro son un zip con XML.  Los .doc y .ppt viejos no entran aca:
    esos no tienen texto legible y se quedan sin resumen, a proposito.
    """
    import io
    import re as _re
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(crudo)) as z:
            if ext == ".docx":
                partes = ["word/document.xml"]
            else:
                partes = sorted(n for n in z.namelist()
                                if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
            trozos = []
            for p in partes[:60]:
                try:
                    xml = z.read(p).decode("utf-8", "replace")
                except Exception:
                    continue
                xml = _re.sub(r"</w:p>|</a:p>", "\n", xml)
                trozos.append(_re.sub(r"<[^>]+>", " ", xml))
        return " ".join(" ".join(trozos).split())
    except Exception:
        return ""


def bajar(sesion, url):
    """Devuelve (texto, pdf_crudo).  Los dos pueden venir vacios."""
    try:
        r = sesion.get(url, timeout=CFG.ESPERA_RED)
        if r.status_code != 200:
            return "", None
        tope = CFG.IA["peso_maximo_mb"] * 1024 * 1024
        if len(r.content) > tope:
            return "", None
        tipo = (r.headers.get("Content-Type") or "").lower()
        crudo = r.content
    except Exception:
        return "", None

    if "pdf" in tipo or url.lower().endswith(".pdf"):
        return "", crudo
    bajo = url.lower().split("?")[0]
    for ext in (".docx", ".pptx"):
        if bajo.endswith(ext):
            return _texto_de_office(crudo, ext), None
    if "html" in tipo or "text" in tipo:
        try:
            return _texto_de_html(crudo.decode("utf-8", "replace")), None
        except Exception:
            return "", None
    return "", None       # video, imagen, planilla: no se resumen


# ------------------------------------------------------------ armar y pedir
def _partir(salida, corto_max=None, largo_max=None):
    """Separa lo esencial de lo ampliado."""
    corto_max = corto_max or CFG.IA["largo_corto"]
    largo_max = largo_max or CFG.IA["largo_ampliado"]
    salida = (salida or "").strip()
    if CORTE in salida:
        corto, largo = salida.split(CORTE, 1)
    else:
        corto, largo = salida, ""
    corto = " ".join(corto.split())
    corto = re.sub(r"^(parte\s*1|resumen|claro|por supuesto)[:.\-]?\s*", "",
                   corto, flags=re.I)
    largo = re.sub(r"^(parte\s*2)[:.\-]?\s*", "", largo.strip(), flags=re.I)
    largo = "\n".join(l.strip() for l in largo.split("\n") if l.strip())

    return _recortar(corto, corto_max), _recortar(largo, largo_max)


def resumir(estado, sesion, trabajo, avisar=None):
    """Resume UNA cosa, sea un archivo suelto o un trabajo entero.

    trabajo = {"grupo", "titulo", "descripcion", "vence", "archivos":[{titulo,url}]}
    avisar  = funcion opcional para contar en que anda, para la animacion.

    Devuelve {"corto":..., "largo":...} o None.  Nunca revienta.
    """
    def paso(etiqueta):
        if avisar:
            try:
                avisar(etiqueta)
            except Exception:
                pass

    if not disponible(estado) or ramo_excluido(trabajo.get("grupo")):
        return None

    try:
        piezas = ["TITULO: " + (trabajo.get("titulo") or "sin titulo")]
        if trabajo.get("vence"):
            piezas.append("ENTREGA: " + trabajo["vence"])
        if trabajo.get("descripcion"):
            piezas.append("DESCRIPCION DEL PROFESOR: " + trabajo["descripcion"][:6000])

        archivos = (trabajo.get("archivos") or [])[:CFG.IA["archivos_maximos"]]
        pdfs, leidos, paginas = [], 0, 0

        if archivos:
            paso("bajando %d archivo%s" % (len(archivos), "" if len(archivos) == 1 else "s"))

        for a in archivos:
            texto, crudo = bajar(sesion, a.get("url", ""))
            if crudo and lee_archivos():
                pdfs.append(crudo)
                leidos += 1
            elif crudo:
                t, n = _texto_de_pdf(crudo)
                paginas += n
                if t:
                    piezas.append("ARCHIVO %s: %s" % (a.get("titulo", ""), t[:9000]))
                    leidos += 1
            elif texto:
                piezas.append("ARCHIVO %s: %s" % (a.get("titulo", ""), texto[:9000]))
                leidos += 1

        if archivos and leidos:
            paso("leyendo %d p\u00e1ginas" % paginas if paginas else "leyendo el material")

        cuerpo = "\n\n".join(piezas)
        util = len(cuerpo) - len(piezas[0])
        if not pdfs and util < 120:
            return None            # no hay nada que resumir

        paso("resumiendo")
        motor = PROVEEDORES.get(CFG.IA["proveedor"])
        if not motor:
            return None
        # Cuanto mas material trajo el profesor, mas lugar tiene el resumen.
        # Un aviso suelto sigue siendo de dos lineas.
        cuantos = max(len(archivos), 1)
        techo = min(CFG.IA["largo_ampliado"]
                    + CFG.IA.get("extra_por_archivo", 300) * (cuantos - 1),
                    CFG.IA.get("techo_ampliado", 1900))
        largo_orden = ORDEN % (CFG.IA["largo_corto"], techo)
        salida = motor(largo_orden + "\n\n" + cuerpo, pdfs)
    except Exception as e:
        estado["fallas_ia"] = estado.get("fallas_ia", 0) + 1
        print("[i] la IA no contesto (%s), van %d"
              % (type(e).__name__, estado["fallas_ia"]))
        return None

    estado["fallas_ia"] = 0
    corto, ampliado = _partir(salida, CFG.IA["largo_corto"], techo)
    if not corto or "SIN TEXTO" in corto.upper():
        return None
    return {"corto": corto, "largo": ampliado}
