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
import os
import re

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
    "Contesta SOLO con esa libreta. Si el dato no esta ahi, deci que no lo "
    "tenes anotado y en una linea deci donde podria mirarlo. Nunca inventes "
    "fechas, notas, porcentajes ni archivos.\n\n"
    "Castellano rioplatense neutro, directo, sin saludos ni preambulo.\n\n"
    "El largo lo decide la pregunta, no vos. Si es una pregunta simple, dos "
    "lineas y listo. Si de verdad hay varias cosas que contar, explayate, "
    "hasta %d caracteres. Nunca rellenes para llegar al limite y nunca "
    "cierres a mitad de una idea. Sin markdown raro, solo texto y guiones "
    "para las vinetas."
)


def preguntar(estado, pregunta, libreta):
    """Charla sobre lo que el bot ya sabe. Devuelve texto o None."""
    if not disponible(estado) or not (pregunta or "").strip():
        return None
    pedido = "%s\n\nLIBRETA\n%s\n\nPREGUNTA\n%s" % (
        ORDEN_CHARLA % CFG.IA.get("largo_charla", 900),
        libreta[:12000], pregunta[:600])
    try:
        salida = PROVEEDORES[CFG.IA["proveedor"]](pedido, [])
    except Exception as e:
        estado["fallas_ia"] = estado.get("fallas_ia", 0) + 1
        estado["ultimo_error_ia"] = str(e)[:200]
        return None
    estado["fallas_ia"] = 0
    return _recortar(salida, CFG.IA.get("techo_charla", 1800)) or None


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


def _clave():
    """La clave, limpia.

    Al pegarla en un secreto es facil que se cuelen comillas, espacios o un
    salto de linea invisible.  Eso hace que la web conteste 400 y parezca
    que la clave esta mal cuando en realidad esta bien."""
    crudo = os.environ.get("IA_KEY", "")
    crudo = crudo.replace("\r", " ").replace("\n", " ").strip()
    crudo = crudo.strip("'\"").strip()
    if crudo.lower().startswith("ia_key="):
        crudo = crudo[7:].strip()
    return crudo


def disponible(estado=None):
    if CFG.IA["proveedor"] == "ninguno" or not _clave():
        return False
    if estado is not None:
        if not estado.get("config", {}).get("ia", True):
            return False
        if estado.get("fallas_ia", 0) >= CFG.IA["fallas_para_apagar"]:
            return False
    return True


def ramo_excluido(nombre):
    n = (nombre or "").lower()
    return any(x.lower() in n for x in CFG.IA.get("ramos_sin_ia", []))


# ------------------------------------------------------------ proveedores
def _gemini(texto, pdfs):
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
    cuerpo = {"contents": [{"parts": partes}],
              "generationConfig": {"maxOutputTokens": 700, "temperature": 0.2}}
    cabeceras = {"x-goog-api-key": _clave(),
                 "Content-Type": "application/json"}

    modelos = [CFG.IA["modelo"]] + [m for m in CFG.IA.get("modelos_de_repuesto", [])
                                    if m != CFG.IA["modelo"]]
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
            if modelo != CFG.IA["modelo"]:
                CFG.IA["modelo"] = modelo      # el que anda, para esta corrida
            d = r.json()
            try:
                return d["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                raise RuntimeError("contesto vacio, puede ser el filtro de contenido")
        ultimo = _motivo(r, modelo)
        if r.status_code in (400, 401, 403):
            break                              # es la clave, cambiar de modelo no ayuda
    raise RuntimeError(ultimo or "no contesto")


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


def _compatible(texto, pdfs):
    """Cualquier servicio con el formato de OpenAI.
    Estos no leen archivos, asi que el PDF ya viene convertido a texto."""
    url = CFG.IA["url"].rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    r = requests.post(url,
                      headers={"Authorization": "Bearer %s" % _clave()},
                      json={"model": CFG.IA["modelo"],
                            "messages": [{"role": "user", "content": texto[:24000]}],
                            "max_tokens": 700, "temperature": 0.2},
                      timeout=60)
    if r.status_code != 200:
        raise RuntimeError("ia %s" % r.status_code)
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
