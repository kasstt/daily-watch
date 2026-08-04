# -*- coding: utf-8 -*-
"""Compartir material entre companeros, sin regalar nada personal.

Las tres reglas, en orden de importancia:

1. Solo viaja MATERIAL: titulo, fecha, enlace y tipo.  Nunca notas, nunca
   tus tareas, nunca tus apuntes, nunca tus claves, nunca tu nombre de
   usuario.  Lo que no esta en la lista blanca no sale.

2. El permiso es desigual y es tuyo.  De fabrica vos recibis lo que los
   demas comparten, y nadie ve nada tuyo hasta que vos lo aprobes, ramo por
   ramo.  Podes compartir contabilidad y no compartir calculo.  Se saca
   cuando quieras y deja de viajar en el acto.

3. Lo de otras secciones es de segunda.  Llega un aviso de una linea y se
   termina ahi.  No hay perfil de insistencia, no hay recordatorio de "no
   lo viste" y no hay boton para callarlo, porque no hace falta callar algo
   que no insiste.

Y una cosa mas: si el archivo ya te lo mando tu propio profesor, no te lo
avisa de nuevo.  Te lo marca como repetido y listo.

Sobre las claves de IA de cada persona: cada uno carga la suya por privado
en su propio chat y se guarda cifrada.  No aparece en el panel, no aparece
en el diagnostico, no aparece en los registros y no se puede listar.  Ver
la nota honesta que esta mas abajo, en "hasta donde llega el cifrado".

Este archivo no toca internet.  Todo lo que hace es sobre la memoria, asi
se puede probar entero sin plataforma y sin claves.
"""
import base64
import datetime as dt
import hashlib
import hmac
import os
import re

# ------------------------------------------------------------ lo que sale
# Lista blanca: SOLO estos campos salen de tu memoria hacia otra persona.
# Si manana alguien agrega un campo nuevo con datos tuyos, no sale, porque
# hay que anotarlo aca a mano y a proposito.
CAMPOS_QUE_SALEN = ("t", "u", "f", "tipo")

# Y estos NUNCA salen, ni aunque alguien los agregue a la lista de arriba
# por error.  Doble candado.
CAMPOS_PROHIBIDOS = ("nota", "notas", "nombre", "usuario", "user", "mail",
                     "correo", "clave", "pass", "token", "chat", "telefono",
                     "rut", "matricula", "legajo", "calificacion", "nota_final",
                     "promedio", "hecho", "vence", "tarjeta", "mio")

MAXIMO_DE_AFUERA = 60        # cuantos avisos ajenos se guardan
MAXIMO_PERSONAS = 12         # circulo chico y cerrado, a proposito


# =====================================================================
#  el cifrado de las claves ajenas
# =====================================================================
# Hasta donde llega el cifrado, dicho sin vueltas:
#
# La clave de cada persona se guarda cifrada y nunca se muestra en ningun
# lado.  No la ves vos, no la ve el panel, no la ve el diagnostico y no
# queda escrita en los registros.  Eso es real y esta probado.
#
# Lo que NO es cierto es que sea imposible de recuperar: el bot tiene que
# poder usar esa clave para hablar con la IA, asi que en algun momento la
# tiene que descifrar.  Quien controle el repositorio puede correr el
# codigo y obtenerla.  La unica manera de que sea imposible de verdad es
# que cada persona corra su propio bot, que es el otro camino.
#
# Preferi decirte esto antes que venderte humo.

SAL = b"watcher-compartir-v1"
VUELTAS = 120000


def _derivar(llave):
    return hashlib.pbkdf2_hmac("sha256", str(llave or "").encode("utf-8"),
                               SAL, VUELTAS)


def _flujo(llave, nonce, largo):
    """Un chorro de bytes largo como haga falta, sacado de la llave."""
    salida = bytearray()
    bloque = 0
    while len(salida) < largo:
        salida += hashlib.sha256(
            llave + nonce + bloque.to_bytes(4, "big")).digest()
        bloque += 1
    return bytes(salida[:largo])


def llave_del_bot():
    """La llave con la que se cifra.  Sale de un Secret aparte si existe, y
    si no, de las llaves que el bot ya tiene.  Nunca se escribe en ningun
    lado ni se muestra."""
    propia = os.environ.get("CLAVE_COMPARTIR", "").strip()
    if propia:
        return propia
    mezcla = (os.environ.get("GH_TOKEN", "").strip()
              + "|" + os.environ.get("TG_TOKEN", "").strip())
    return mezcla.strip("|") or "sin-llave"


def cifrar(texto, llave=None):
    """Devuelve un paquete de texto plano que no se puede leer sin la llave.
    Trae su propio sello: si alguien lo toca, al abrirlo revienta."""
    llave_b = _derivar(llave if llave is not None else llave_del_bot())
    nonce = os.urandom(12)
    datos = str(texto or "").encode("utf-8")
    cripto = bytes(a ^ b for a, b in zip(datos, _flujo(llave_b, nonce, len(datos))))
    sello = hmac.new(llave_b, nonce + cripto, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(nonce + sello + cripto).decode("ascii")


def descifrar(paquete, llave=None):
    """Abre el paquete.  Devuelve el texto, o vacio si no se puede abrir.
    Nunca revienta hacia afuera: un error aca no puede tirar el bot."""
    try:
        llave_b = _derivar(llave if llave is not None else llave_del_bot())
        crudo = base64.urlsafe_b64decode(str(paquete or "").encode("ascii"))
        if len(crudo) < 28:
            return ""
        nonce, sello, cripto = crudo[:12], crudo[12:28], crudo[28:]
        esperado = hmac.new(llave_b, nonce + cripto, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(sello, esperado):
            return ""
        return bytes(a ^ b for a, b in zip(
            cripto, _flujo(llave_b, nonce, len(cripto)))).decode("utf-8")
    except Exception:
        return ""


def tapada(clave):
    """Como se muestra una clave en pantalla: nunca entera."""
    c = str(clave or "").strip()
    if not c:
        return "ninguna"
    if len(c) <= 8:
        return "*" * len(c)
    return c[:3] + "\u2026" + c[-2:]


# =====================================================================
#  las personas
# =====================================================================
def _bolsa(estado):
    return estado.setdefault("personas", {})


def limpiar_alias(texto):
    """Un apodo corto y sin datos.  Nada de mails ni de numeros largos."""
    t = " ".join(str(texto or "").split())
    t = re.sub(r"[^\w \-\.]", "", t, flags=re.UNICODE)
    t = re.sub(r"\S+@\S+", "", t)
    t = re.sub(r"\d{5,}", "", t)
    return t.strip()[:24] or "companero"


def agregar(estado, pid, alias="", hoy=None):
    """Anota a una persona.  Entra SIN permiso: no ve nada tuyo hasta que
    vos le abras un ramo a mano."""
    pid = str(pid or "").strip()
    if not pid:
        return None, "me falta el identificador de esa persona"
    bolsa = _bolsa(estado)
    if pid in bolsa:
        return bolsa[pid], "esa persona ya estaba anotada"
    if len(bolsa) >= MAXIMO_PERSONAS:
        return None, ("ya hay %d personas y el c\u00edrculo es chico a prop\u00f3sito. "
                      "Sac\u00e1 a alguien primero" % MAXIMO_PERSONAS)
    ficha = {
        "alias": limpiar_alias(alias or "companero"),
        "chat": pid,
        "desde": (hoy or dt.datetime.now()).strftime("%Y-%m-%d"),
        "ramos": [],          # los ramos MIOS que esta persona puede ver
        "bloqueada": False,
        "recibidos": 0,       # cuantas cosas me mando
        "mandados": 0,        # cuantas cosas le mande
    }
    bolsa[pid] = ficha
    return ficha, ""


def sacar(estado, pid):
    """La saca y le corta todo el acceso en el acto."""
    return _bolsa(estado).pop(str(pid or ""), None) is not None


def persona(estado, pid):
    return _bolsa(estado).get(str(pid or ""))


def lista(estado):
    return sorted(_bolsa(estado).items(),
                  key=lambda x: str(x[1].get("alias", "")).lower())


def bloquear(estado, pid, si=True):
    f = persona(estado, pid)
    if not f:
        return False
    f["bloqueada"] = bool(si)
    return True


# ------------------------------------------------------- permisos por ramo
def ramos_abiertos(estado, pid):
    f = persona(estado, pid)
    return list(f.get("ramos", [])) if f else []


def puede_ver(estado, pid, clave_ramo):
    """El unico lugar donde se decide si algo tuyo sale.  Si esto dice que
    no, no sale por ningun camino."""
    f = persona(estado, pid)
    if not f or f.get("bloqueada"):
        return False
    return str(clave_ramo or "") in (f.get("ramos") or [])


def alternar_ramo(estado, pid, clave_ramo):
    """Abre o cierra UN ramo para UNA persona.  Devuelve (quedo_abierto, ok)."""
    f = persona(estado, pid)
    clave_ramo = str(clave_ramo or "")
    if not f or not clave_ramo:
        return False, False
    ramos = f.setdefault("ramos", [])
    if clave_ramo in ramos:
        ramos.remove(clave_ramo)
        return False, True
    ramos.append(clave_ramo)
    return True, True


def cerrar_todo(estado, pid=None):
    """El boton de panico: deja de compartir todo, con todos o con uno."""
    cuantos = 0
    for clave, f in _bolsa(estado).items():
        if pid and clave != str(pid):
            continue
        cuantos += len(f.get("ramos") or [])
        f["ramos"] = []
    return cuantos


# =====================================================================
#  lo que sale de tu memoria hacia otra persona
# =====================================================================
def limpiar_item(novedad):
    """Deja SOLO los campos de la lista blanca.  Todo lo demas se tira."""
    salida = {}
    for campo in CAMPOS_QUE_SALEN:
        if campo in CAMPOS_PROHIBIDOS:
            continue
        valor = (novedad or {}).get(campo)
        if valor in (None, ""):
            continue
        salida[campo] = valor
    return salida


def paquete_para(estado, pid, novedades=None, tope=40):
    """Lo que esta persona puede ver de lo tuyo, ya limpio.

    No incluye el nombre real del ramo si no hace falta: va el nombre del
    ramo porque es el dato util, pero nada mas.
    """
    f = persona(estado, pid)
    if not f or f.get("bloqueada"):
        return []
    abiertos = set(f.get("ramos") or [])
    if not abiertos:
        return []
    salida = []
    for n in (novedades if novedades is not None else estado.get("novedades", [])):
        if str(n.get("c", "")) not in abiertos:
            continue
        limpio = limpiar_item(n)
        if not limpio.get("t"):
            continue
        limpio["ramo"] = str(n.get("g", ""))[:60]
        salida.append(limpio)
        if len(salida) >= tope:
            break
    return salida


def revisar_fuga(paquete):
    """El control de salida.  Devuelve la lista de campos prohibidos que se
    colaron.  Tiene que devolver siempre vacio: si no, hay un error."""
    problemas = []
    for item in paquete or []:
        for campo in item:
            if campo in ("ramo",) or campo in CAMPOS_QUE_SALEN:
                continue
            problemas.append(campo)
    return sorted(set(problemas))


# =====================================================================
#  lo que llega de otras secciones
# =====================================================================
def _sin_tildes(t):
    reemplazos = (("\u00e1", "a"), ("\u00e9", "e"), ("\u00ed", "i"),
                  ("\u00f3", "o"), ("\u00fa", "u"), ("\u00fc", "u"),
                  ("\u00f1", "n"))
    t = str(t or "").lower()
    for de, a in reemplazos:
        t = t.replace(de, a)
    return t


RE_RUIDO = re.compile(r"[^a-z0-9]+")
RE_VERSION = re.compile(r"\b(v|version|ver|copia|final|corregid[oa]|rev)\s*\d*\b")


def huella_de_material(titulo, url=""):
    """Como se reconoce que dos archivos de dos secciones son el mismo.

    No se puede comparar la direccion, porque cada seccion tiene la suya.
    Se compara el nombre, sin tildes, sin extension, sin numeros de version
    y sin relleno.  "Guia 3.pdf" y "guia_3_v2.PDF" son el mismo archivo.
    """
    t = _sin_tildes(titulo)
    t = re.sub(r"\.(pdf|docx?|pptx?|xlsx?|zip|rar|txt|csv|odt|odp|ods)$", " ", t)
    t = RE_VERSION.sub(" ", t)
    t = RE_RUIDO.sub(" ", t)
    palabras = [p for p in t.split() if len(p) > 1 or p.isdigit()]
    if not palabras:
        # Nombre inservible: se cae para atras y se usa la direccion.
        base = RE_RUIDO.sub("", _sin_tildes(url).split("?")[0])[-40:]
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    return hashlib.sha256(" ".join(palabras).encode("utf-8")).hexdigest()[:16]


def mis_huellas(estado, novedades=None):
    """Todo lo que ya te mando TU profesor, listo para comparar."""
    salida = {}
    for n in (novedades if novedades is not None else estado.get("novedades", [])):
        h = huella_de_material(n.get("t", ""), n.get("u", ""))
        if h not in salida:
            salida[h] = {"titulo": n.get("t", ""), "ramo": n.get("g", ""),
                         "f": n.get("f", "")}
    return salida


def clasificar(item, huellas):
    """Decide que hacer con una cosa que llego de otra seccion.

    Devuelve ("repetido", ficha_mia) si ya lo tenes de tu propio profesor,
    o ("nuevo", None) si es algo que tu seccion no tiene.
    """
    h = huella_de_material((item or {}).get("t", ""), (item or {}).get("u", ""))
    mio = (huellas or {}).get(h)
    return ("repetido", mio) if mio else ("nuevo", None)


def recibir(estado, pid, items, hoy=None, huellas=None):
    """Guarda lo que mando otra persona y devuelve solo lo que vale avisar.

    Lo repetido se guarda igual, marcado, para que lo puedas mirar si
    queres, pero NO se avisa.  Que tu profesor y el de la otra seccion
    suban la misma guia no es una novedad.
    """
    f = persona(estado, pid)
    if not f or f.get("bloqueada"):
        return [], 0
    hoy = hoy or dt.datetime.now()
    huellas = mis_huellas(estado) if huellas is None else huellas
    bolsa = estado.setdefault("de_afuera", [])
    ya = set(x.get("h", "") for x in bolsa)

    nuevos, repetidos = [], 0
    for item in items or []:
        limpio = limpiar_item(item)
        if not limpio.get("t"):
            continue
        h = huella_de_material(limpio.get("t", ""), limpio.get("u", ""))
        if h in ya:
            continue
        ya.add(h)
        estado_item, mio = clasificar(limpio, huellas)
        ficha = {
            "h": h,
            "de": f.get("alias", "companero"),
            "pid": str(pid),
            "ramo": str(item.get("ramo", ""))[:60],
            "t": limpio.get("t", ""),
            "u": limpio.get("u", ""),
            "tipo": limpio.get("tipo", "material"),
            "f": hoy.strftime("%Y-%m-%d %H:%M"),
            "repetido": estado_item == "repetido",
            "igual_a": (mio or {}).get("titulo", "") if mio else "",
            "igual_en": (mio or {}).get("ramo", "") if mio else "",
        }
        bolsa.insert(0, ficha)
        if ficha["repetido"]:
            repetidos += 1
        else:
            nuevos.append(ficha)

    del bolsa[MAXIMO_DE_AFUERA:]
    f["recibidos"] = int(f.get("recibidos", 0)) + len(items or [])
    return nuevos, repetidos


# ------------------------------------------------------------- el aviso
ICONO = "\U0001F91D"           # dos manos, para distinguirlo de lo tuyo


def aviso_corto(fichas, escapar=None, enlace=None, resumen=""):
    """El aviso de otra seccion: una linea y se termina.

    Sin botones, sin perfil, sin recordatorio y sin boton de silenciar.  No
    hace falta callar algo que no vuelve a hablar.
    """
    esc = escapar or (lambda t: str(t or ""))
    lin = enlace or (lambda t, u: "%s (%s)" % (t, u))
    if not fichas:
        return ""

    primera = fichas[0]
    de = esc(primera.get("de", "otra secci\u00f3n"))
    ramo = esc(primera.get("ramo", ""))

    if len(fichas) == 1:
        cuerpo = lin(primera.get("t", "algo"), primera.get("u", "")) \
            if primera.get("u") else esc(primera.get("t", "algo"))
        linea = "%s <i>%s, compartido:</i> %s" % (ICONO, de, cuerpo)
    else:
        titulos = ", ".join(esc(x.get("t", ""))[:40] for x in fichas[:3])
        if len(fichas) > 3:
            titulos += " y %d m\u00e1s" % (len(fichas) - 3)
        linea = "%s <i>%s, compartido:</i> subieron %d cosas: %s" % (
            ICONO, de, len(fichas), titulos)

    if ramo:
        linea += "  <i>(%s)</i>" % ramo
    if resumen:
        linea += "\n<i>%s</i>" % esc(resumen[:300])
    return linea


def texto_de_afuera(estado, cuantos=15, escapar=None, enlace=None):
    """La pantalla con todo lo que llego de otras secciones, con los
    repetidos marcados para que no los abras al pedo."""
    esc = escapar or (lambda t: str(t or ""))
    lin = enlace or (lambda t, u: "%s (%s)" % (t, u))
    bolsa = estado.get("de_afuera", [])[:cuantos]
    if not bolsa:
        return ("Todav\u00eda no me lleg\u00f3 nada de otras secciones.\n\n"
                "<i>Esto no es prioridad: cuando llegue algo te lo digo en "
                "una l\u00ednea y no te lo vuelvo a recordar.</i>")
    lineas = []
    for x in bolsa:
        cabeza = lin(x.get("t", ""), x.get("u", "")) if x.get("u") \
            else esc(x.get("t", ""))
        marca = ""
        if x.get("repetido"):
            donde = esc(x.get("igual_en", "")) or "tu secci\u00f3n"
            marca = "  \u267B\uFE0F <i>ya lo ten\u00e9s de %s</i>" % donde
        lineas.append("%s  <i>%s \u00b7 %s</i>%s" % (
            cabeza, esc(x.get("de", "")), x.get("f", "")[5:16].replace("-", "/"),
            marca))
    repes = len([x for x in estado.get("de_afuera", []) if x.get("repetido")])
    pie = "\n\n<i>%d de estos ya los ten\u00e9s de tus profes.</i>" % repes if repes else ""
    return "\n".join(lineas) + pie


def texto_personas(estado, nombre_de=None, escapar=None):
    """El resumen de con quien compartis y que."""
    esc = escapar or (lambda t: str(t or ""))
    nombre = nombre_de or (lambda c: c)
    gente = lista(estado)
    if not gente:
        return ("Todav\u00eda no compartis con nadie.\n\n"
                "<i>De f\u00e1brica vos ves lo que los dem\u00e1s comparten y ellos no "
                "ven nada tuyo. Para abrirle un ramo a alguien, agregalo y "
                "eleg\u00ed el ramo a mano.</i>")
    lineas = []
    for pid, f in gente:
        ramos = f.get("ramos") or []
        if f.get("bloqueada"):
            que = "\U0001F6AB bloqueada"
        elif not ramos:
            que = "no ve nada tuyo"
        else:
            que = "ve %d ramo%s: %s" % (
                len(ramos), "" if len(ramos) == 1 else "s",
                ", ".join(esc(nombre(c))[:18] for c in ramos[:4]))
        lineas.append("\u2022 <b>%s</b> \u00b7 %s" % (esc(f.get("alias", "?")), que))
    return "\n".join(lineas)


# =====================================================================
#  las claves de IA de cada persona
# =====================================================================
def guardar_clave(estado, pid, clave_en_claro):
    """Guarda la clave de una persona, cifrada.  Devuelve (ok, motivo).

    Nunca se guarda en claro, nunca se devuelve y nunca se muestra.
    """
    pid = str(pid or "").strip()
    clave = str(clave_en_claro or "").strip()
    if not pid:
        return False, "me falta saber de qui\u00e9n es"
    if len(clave) < 12:
        return False, "eso no parece una clave de IA, es muy corta"
    if " " in clave:
        return False, "una clave no lleva espacios, revis\u00e1 que no se haya cortado"
    paquete = cifrar(clave)
    if not paquete or descifrar(paquete) != clave:
        return False, "no pude guardarla cifrada, mejor no la guardo"
    estado.setdefault("claves_ajenas", {})[pid] = {
        "paquete": paquete,
        "largo": len(clave),
        "desde": dt.datetime.now().strftime("%Y-%m-%d"),
    }
    return True, ""


def hay_clave(estado, pid):
    return str(pid or "") in (estado.get("claves_ajenas") or {})


def borrar_clave(estado, pid):
    return (estado.get("claves_ajenas") or {}).pop(str(pid or ""), None) is not None


def usar_clave(estado, pid):
    """La devuelve descifrada, SOLO para usarla contra el servicio de IA.
    No la imprimas, no la mandes al chat y no la guardes en otro lado."""
    ficha = (estado.get("claves_ajenas") or {}).get(str(pid or ""))
    if not ficha:
        return ""
    return descifrar(ficha.get("paquete", ""))


def resumen_de_claves(estado):
    """Lo unico que se puede ver de las claves ajenas: cuantas hay.  Ni el
    largo real, ni un pedazo, ni de quien es cual."""
    cuantas = len(estado.get("claves_ajenas") or {})
    if not cuantas:
        return "Nadie carg\u00f3 su clave de IA todav\u00eda."
    return ("%d persona%s carg\u00f3 su clave. Est\u00e1n cifradas y no se pueden "
            "ver desde ac\u00e1." % (cuantas, "" if cuantas == 1 else "s"))


def texto_privacidad():
    """Lo que se le muestra a alguien antes de que cargue su clave."""
    return ("\U0001F510 <b>Tu clave de IA</b>\n\n"
            "Peg\u00e1mela ac\u00e1 y la guardo cifrada. No aparece en el panel, no "
            "aparece en el diagn\u00f3stico y no queda escrita en ning\u00fan "
            "registro.\n\n"
            "Para ser honesto: el bot tiene que poder usarla, as\u00ed que no es "
            "matem\u00e1ticamente imposible de recuperar para quien controla el "
            "repositorio. Si eso te incomoda, corr\u00e9 tu propia copia del bot "
            "y list\u00f3.\n\n"
            "Borro tu mensaje apenas la lea.")
