# -*- coding: utf-8 -*-
"""Lo que llega desde el chat: botones, botonera fija y comandos.

Los botones son para explorar, los comandos para ir directo.  Los dos
caminos llevan al mismo lugar.

Ojo con una cosa: el bot no vive en un servidor.  Mientras esta despierto
contesta en uno o dos segundos.  Si GitHub se demora en despertarlo, tu
toque queda en la cola y se ejecuta cuando abre los ojos.  Por eso el panel
siempre muestra a que hora se actualizo.

A cualquiera que no seas vos se lo ignora en silencio.
"""
import datetime as dt
import re
import unicodedata

import fuentes as CFG
import notificar as N
import panel as P

# El orden importa: asi se muestran en el menu del chat, de mas usado a menos.
MENU = [
    ("pendientes", "lo que te falta"),
    ("ultimo", "lo \u00faltimo que subieron"),
    ("panel", "todo a botones"),
    ("semana", "los \u00faltimos 7 d\u00edas"),
    ("resumen", "resumen de un ramo"),
    ("pausa", "callate unas horas"),
    ("noche", "avisos de madrugada"),
    ("estado", "\u00bffunciona todo?"),
    ("perfil", "cu\u00e1nto insistir por ramo"),
    ("callar", "silenciar un ramo"),
    ("revisar", "mir\u00e1 ahora"),
    ("recordar", "guardame un apunte"),
    ("avisos", "lo que escribieron los profes"),
    ("deshacer", "volver atr\u00e1s lo \u00faltimo"),
    ("clases", "clases por videoconferencia"),
    ("compartir", "con qui\u00e9n comparto y qu\u00e9"),
    ("afuera", "material de otras secciones"),
    ("ia", "prender o apagar res\u00famenes"),
    ("reloj", "revisar el reloj de GitHub"),
    ("miclave", "cargar tu clave de IA cifrada"),
    ("exportar", "mandame todo en un archivo"),
    ("ayuda", "c\u00f3mo se usa cada uno"),
]

# Lo que va DESPUES del comando, cuando lleva algo.  Se ve solo en /ayuda,
# pegado al comando, para que no parezca un comando repetido.
COLA = {
    "resumen": "ramo calculo",
    "compartir": "con juan calculo",
    "pausa": "3",
    "perfil": "apretado termo",
    "callar": "calculo",
    "recordar": "viernes 18:00 estudiar",
}

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def pelado(t):
    """Sin tildes y en minusculas, para comparar sin sufrir."""
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def _hora_valida(t):
    return bool(re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", t or ""))


def _horas_lindas(h):
    """0.5 -> '30 minutos', 24 -> '1 dia', 168 -> '7 dias'."""
    h = float(h)
    if h < 1:
        return "%d minutos" % int(round(h * 60))
    if h < 24:
        return "%d hora%s" % (int(h), "" if int(h) == 1 else "s")
    dias = int(round(h / 24.0))
    return "%d d\u00eda%s" % (dias, "" if dias == 1 else "s")


def explicar_perfil(nombre):
    """En una linea, cada cuanto avisa ese perfil.  Se arma leyendo la
    configuracion de verdad, asi que nunca puede mentir."""
    perfil = CFG.PERFILES.get(pelado(nombre))
    if perfil is None:
        return ""
    if perfil == "diario":
        return "avisa una vez por d\u00eda hasta la entrega"
    partes = [_horas_lindas(h) for h in perfil]
    return "avisa " + ", ".join(partes) + " antes de la entrega"


def texto_perfiles():
    """La pantalla que explica los perfiles."""
    porde = getattr(CFG, "PERFIL_POR_DEFECTO", "normal")
    lineas = ["\u2699 <b>Perfiles de insistencia</b>",
              "Es cada cu\u00e1nto te recuerdo una entrega que todav\u00eda no "
              "marcaste como hecha. No cambia los avisos de material nuevo: "
              "eso llega siempre, apenas aparece.", ""]
    for nombre in ("suave", "normal", "apretado", "diario"):
        if nombre not in CFG.PERFILES:
            continue
        marca = " \u00b7 el que viene puesto" if nombre == porde else ""
        lineas.append("<b>%s</b>%s" % (nombre, marca))
        lineas.append(explicar_perfil(nombre))
        lineas.append("")
    lineas += [
        "Cada ramo puede tener el suyo.",
        "/perfil apretado calculo \u00b7 solo ese ramo",
        "/perfil suave \u00b7 todos los ramos",
        "",
        "Tus recordatorios propios no usan perfil: suenan una sola vez, a la "
        "hora que pediste.",
    ]
    return "\n".join(lineas)


def texto_ayuda():
    # OJO: los comandos van en texto pelado, sin <code>.  Telegram convierte
    # en boton cualquier /palabra suelta, pero adentro de <code> queda como
    # texto muerto que solo se puede copiar.
    lineas = ["<b>Comandos</b>", "Toc\u00e1 cualquiera para usarlo.", ""]
    for c, d in MENU:
        cola = COLA.get(c)
        if cola:
            lineas.append("/%s <i>%s</i> \u00b7 %s" % (c, N.escapar(cola), d))
        else:
            lineas.append("/%s \u00b7 %s" % (c, d))
    lineas += [
        "",
        "<b>Res\u00famenes</b>",
        "/resumen <i>ramo calculo</i> \u00b7 ese ramo, con IA",
        "/resumen \u00b7 prende o apaga el semanal",
        "/resumen <i>viernes 20:00</i> \u00b7 cambia cu\u00e1ndo llega",
        "/resumen <i>diario 21:00</i> \u00b7 todos los d\u00edas",
        "",
        "<b>Perfiles</b>",
    ]
    for nombre in ("suave", "normal", "apretado", "diario"):
        if nombre in CFG.PERFILES:
            lineas.append("<b>%s</b> \u00b7 %s" % (nombre, explicar_perfil(nombre)))
    lineas += [
        "/perfil <i>apretado termo</i> \u00b7 uno por ramo",
        "",
        "<b>Sin comandos</b>",
        "Escribime normal y hago lo que pidas: \u00abrecordame el jueves a las "
        "18 estudiar termo\u00bb. Antes de tocar nada te muestro una "
        "confirmaci\u00f3n armada por el programa, no por la IA.",
    ]
    return "\n".join(lineas)


# ---------------------------------------------------------------- fechas
RELLENO = ("en", "el", "la", "este", "esta", "al", "a", "proximo", "dentro", "de")


def cuando(texto, ahora):
    """Entiende 'viernes 18:00', 'manana 20:00', '3h', '20m', '2d' y 'HH:MM'.
    Devuelve (fecha, resto) o (None, texto)."""
    p = texto.split()
    # "en 5 minutos", "el viernes", "este lunes": las muletillas no molestan
    while p and pelado(p[0]) in RELLENO:
        p = p[1:]
    if not p:
        return None, texto
    uno = pelado(p[0])

    # 20m, 3h, 2d, y tambien "5 minutos" o "2 horas" separados
    m = re.fullmatch(r"(\d+)(m|min|mins|minutos?|h|hs|horas?|d|dias?)", uno)
    if not m and uno.isdigit() and len(p) > 1:
        unido = uno + pelado(p[1])
        m = re.fullmatch(r"(\d+)(m|min|mins|minutos?|h|hs|horas?|d|dias?)", unido)
        if m:
            p = [unido] + p[2:]
    if m:
        n = int(m.group(1))
        letra = m.group(2)[0]
        salto = (dt.timedelta(minutes=n) if letra == "m"
                 else dt.timedelta(hours=n) if letra == "h"
                 else dt.timedelta(days=n))
        return ahora + salto, " ".join(p[1:])

    resto = p[1:]
    if uno == "hoy":
        base = ahora
    elif uno in ("manana", "mnana"):
        base = ahora + dt.timedelta(days=1)
    elif uno in DIAS:
        falta = (DIAS.index(uno) - ahora.weekday()) % 7
        # Si nombras el dia de hoy y la hora todavia no paso, es HOY.  Antes
        # se iba siempre a la semana que viene.
        if falta == 0:
            hoy_sirve = False
            if resto and _hora_valida(resto[0]):
                h, mi = [int(x) for x in resto[0].split(":")]
                hoy_sirve = ahora.replace(hour=h, minute=mi, second=0,
                                          microsecond=0) > ahora
            if not hoy_sirve:
                falta = 7
        base = ahora + dt.timedelta(days=falta)
    elif _hora_valida(uno):
        h, mi = [int(x) for x in uno.split(":")]
        base = ahora.replace(hour=h, minute=mi, second=0, microsecond=0)
        if base <= ahora:
            base += dt.timedelta(days=1)
        return base, " ".join(p[1:])
    else:
        return None, texto

    if resto and _hora_valida(resto[0]):
        h, mi = [int(x) for x in resto[0].split(":")]
        base = base.replace(hour=h, minute=mi, second=0, microsecond=0)
        resto = resto[1:]
    else:
        base = base.replace(hour=9, minute=0, second=0, microsecond=0)
    return base, " ".join(resto)


# ---------------------------------------------------------------- comandos
def _resumen(estado, resto, acc, ahora):
    r = estado.setdefault("config", {}).setdefault("resumen", dict(CFG.RESUMEN))
    p = resto.split()

    if not p:
        r["activo"] = not r.get("activo", True)
        return "Resumen peri\u00f3dico <b>%s</b>." % ("encendido" if r["activo"] else "apagado")

    if pelado(p[0]) == "ramo":
        nombre = " ".join(p[1:]).strip()
        if not nombre:
            return "Decime cu\u00e1l. Por ejemplo: /resumen ramo calculo"
        clave, aviso = acc["buscar"](nombre)
        if not clave:
            return aviso
        acc["resumen_ramo"](clave)
        return None

    uno = pelado(p[0])
    if uno in ("on", "off"):
        r["activo"] = uno == "on"
        return "Resumen peri\u00f3dico %s." % ("encendido" if r["activo"] else "apagado")
    if uno == "diario":
        r.update({"cada": "dia", "activo": True})
        if len(p) > 1 and _hora_valida(p[1]):
            r["hora"] = p[1]
        return "Listo. Resumen todos los d\u00edas a las %s." % r["hora"]
    if uno in DIAS:
        r.update({"cada": "semana", "dia": uno, "activo": True})
        if len(p) > 1 and _hora_valida(p[1]):
            r["hora"] = p[1]
        return "Listo. Resumen los %s a las %s." % (uno, r["hora"])
    if _hora_valida(p[0]):
        r["hora"] = p[0]
        return "Listo. Ahora a las %s." % r["hora"]

    return ("No entend\u00ed. Prob\u00e1:\n/resumen ramo calculo\n"
            "/resumen viernes 20:00\n/resumen diario 21:00")


def _pausa(estado, resto, ahora):
    try:
        horas = float(resto.split()[0]) if resto.split() else 3
    except ValueError:
        horas = 3
    horas = max(0.25, min(horas, 72))
    hasta = ahora + dt.timedelta(hours=horas)
    estado.setdefault("config", {})["pausa_hasta"] = hasta.strftime("%Y-%m-%d %H:%M")
    return ("Me callo hasta las %s.\nLos plazos que venzan te llegan igual."
            % hasta.strftime("%H:%M"))


def _perfil(estado, resto, acc):
    p = resto.split()
    if not p:
        return "Perfiles: suave, normal, apretado, diario.\nProb\u00e1: /perfil apretado calculo"
    nombre_perfil = pelado(p[0])
    if nombre_perfil not in CFG.PERFILES:
        return "Los perfiles son: suave, normal, apretado, diario."
    if len(p) == 1:
        estado.setdefault("config", {})["perfil"] = nombre_perfil
        return "Todos los ramos pasan a <b>%s</b>." % nombre_perfil
    clave, aviso = acc["buscar"](" ".join(p[1:]))
    if not clave:
        return aviso
    estado.setdefault("perfiles", {})[clave] = nombre_perfil
    return "%s queda en <b>%s</b>." % (N.escapar(aviso), nombre_perfil)


def _callar(estado, resto, acc, ahora):
    if not resto.strip():
        return acc["texto_silenciados"]() or "No hay ning\u00fan ramo silenciado."
    clave, aviso = acc["buscar"](resto)
    if not clave:
        return aviso
    callados = estado.setdefault("callados", {})
    if clave in callados:
        del callados[clave]
        return "%s vuelve a avisarte." % N.escapar(aviso)
    hasta = ahora + dt.timedelta(days=CFG.DIAS_CALLADO)
    callados[clave] = {"hasta": hasta.strftime("%Y-%m-%d"), "cuenta": 0}
    return ("\U0001F515 %s silenciado por %d d\u00edas.\n\n"
            "Se prende solo el %s. Las entregas con fecha te llegan igual, "
            "y lo vas a seguir viendo al pie de cada resumen."
            % (N.escapar(aviso), CFG.DIAS_CALLADO, hasta.strftime("%d/%m")))


def _recordar(estado, resto, ahora):
    """/recordar <cuando> <que>

    Tres cosas estaban mal aca y por eso parecia que el comando no andaba:
    1. El id era "mio_<minuto>", asi que dos recordatorios del mismo minuto
       se pisaban y uno desaparecia sin decir nada.
    2. No se marcaba "es_tarea": False, asi que tus apuntes aparecian en
       Pendientes bajo "PARA ENTREGAR", como si fueran entregas del ramo.
    3. Nadie guardaba la memoria, asi que si el proceso se cortaba antes de
       la proxima guardada, el recordatorio se perdia.
    """
    if not (resto or "").strip():
        return ("\u23F0 <b>C\u00f3mo se usa</b>\n"
                "/recordar viernes 18:00 estudiar\n"
                "/recordar 3h mandar el informe\n"
                "/recordar manana 9:00 comprar el cuaderno\n\n"
                "Tambi\u00e9n vale sin comando: <i>recordame el lunes 8:00 "
                "la prueba</i>\n"
                "O sin escribir nada: abr\u00ed el panel y toc\u00e1 "
                "<b>Nuevo recordatorio</b>.")
    fecha, texto = cuando(resto, ahora)
    if not fecha:
        return ("No le encontr\u00e9 la fecha a eso.\nProb\u00e1 as\u00ed:\n"
                "/recordar viernes 18:00 estudiar\n"
                "/recordar 3h mandar el informe\n"
                "/recordar 20 min sacar la ropa")
    if not texto.strip():
        return ("Tengo la fecha (%s) pero no qu\u00e9 recordarte.\n"
                "Escribilo despu\u00e9s de la hora, por ejemplo:\n"
                "/recordar %s estudiar c\u00e1lculo"
                % (fecha.strftime("%d/%m %H:%M"), fecha.strftime("%H:%M")))

    tareas = estado.setdefault("tareas", {})
    # El id lleva los segundos y, si igual choca, se corre uno por uno.
    marca = fecha
    idt = "mio_%d" % int(marca.timestamp())
    while idt in tareas:
        marca = marca + dt.timedelta(seconds=1)
        idt = "mio_%d" % int(marca.timestamp())

    tareas[idt] = {
        "grupo": "", "clave": "", "titulo": texto.strip(), "url": "",
        "vence": fecha.strftime("%Y-%m-%d %H:%M"), "hecho": False,
        "nota": "", "mio": True,
        # Esto es TUYO, no una entrega del ramo. Sin esta linea caia en
        # "PARA ENTREGAR" y se mezclaba con las tareas de la facultad.
        "es_tarea": False}
    return ("\u23F0 Anotado: <b>%s</b>\nTe aviso el %s a las %s.\n"
            "<i>Lo pod\u00e9s abrir, anotarle algo o borrarlo desde "
            "Pendientes.</i>"
            % (N.escapar(texto.strip()), fecha.strftime("%d/%m"),
               fecha.strftime("%H:%M")))


def _compartir(estado, resto, acc):
    """/compartir con <alias> <ramo>   abre o cierra UN ramo para UNA persona.

    Sin argumentos se abre el panel, que es mas comodo.  Esto es para ir
    directo cuando ya sabes que queres.
    """
    import compartir as CO

    palabras = [p for p in resto.split() if pelado(p) != "con"]
    if not palabras:
        return CO.texto_personas(estado, nombre_de=acc["nombre"],
                                 escapar=N.escapar)

    alias = pelado(palabras[0])
    pid = ""
    for clave, ficha in CO.lista(estado):
        if pelado(ficha.get("alias", "")).startswith(alias):
            pid = clave
            break
    if not pid:
        return ("No tengo a nadie que se llame <b>%s</b>.\n"
                "Los que tengo: %s"
                % (N.escapar(palabras[0]),
                   ", ".join(f.get("alias", "?") for _c, f in CO.lista(estado))
                   or "ninguno todav\u00eda"))

    if len(palabras) < 2:
        abiertos = CO.ramos_abiertos(estado, pid)
        if not abiertos:
            return ("<b>%s</b> no ve ning\u00fan ramo tuyo."
                    % N.escapar(palabras[0]))
        return ("<b>%s</b> ve: %s"
                % (N.escapar(palabras[0]),
                   ", ".join(N.escapar(acc["nombre"](c)) for c in abiertos)))

    buscado = pelado(" ".join(palabras[1:]))
    for clave, nombre, _emoji in (acc["lista_ramos"]() or []):
        if buscado in pelado(nombre):
            abierto, bien = CO.alternar_ramo(estado, pid, clave)
            if not bien:
                return "No pude tocar ese permiso."
            return ("Listo. <b>%s</b> ahora ve <b>%s</b>." if abierto else
                    "Listo. <b>%s</b> ya no ve <b>%s</b>.") % (
                N.escapar(palabras[0]), N.escapar(nombre))
    return "No encontr\u00e9 el ramo <b>%s</b>." % N.escapar(" ".join(palabras[1:]))


def _ia(estado, resto):
    cfg = estado.setdefault("config", {})
    p = pelado(resto)
    if p in ("on", "off"):
        cfg["ia"] = p == "on"
    elif p:
        return "Prob\u00e1 /ia on o /ia off."
    else:
        cfg["ia"] = not cfg.get("ia", True)
    if cfg["ia"]:
        estado["fallas_ia"] = 0
    return ("Res\u00famenes con IA <b>%s</b>.\nLos avisos siguen igual en los dos casos."
            % ("encendidos" if cfg["ia"] else "apagados"))


# ------------------------------------------------------------- limpieza
def _limpiar():
    return bool(getattr(CFG, "LIMPIAR_CHAT", False))


def basura(estado, mensaje_id, segundos=None):
    """Anota un mensaje para borrarlo dentro de un rato."""
    if not (_limpiar() and mensaje_id):
        return
    import time as _t
    cuando_ = _t.time() + (segundos or CFG.SEGUNDOS_BASURA)
    estado.setdefault("basura", []).append([mensaje_id, cuando_])


def borrar_ya(estado, mensaje_id):
    """Lo tuyo: comandos y toques de la botonera. No aportan nada al historial.
    No se borra al instante: se le dan unos segundos para que alcances a ver
    que lo mandaste."""
    basura(estado, mensaje_id, getattr(CFG, "SEGUNDOS_MIS_MENSAJES", 5))


def efimero(estado, texto, botones=None):
    """Una confirmacion: se ve, se lee, se va sola."""
    mid = N.enviar(texto, botones=botones)
    basura(estado, mid)
    return mid


def informativo(estado, texto, botones=None):
    """Listas que se piden seguido. Queda una sola en el chat: la nueva
    reemplaza a la anterior en lugar de apilarse."""
    viejo = estado.get("ultimo_info")
    mid = N.enviar(texto, botones=botones)
    if _limpiar() and viejo and viejo != mid:
        N.borrar(viejo)
    estado["ultimo_info"] = mid
    return mid


# ---------------------------------------------------------------- botones
def _boton_de_tarjeta(estado, dato, acc, ahora):
    """Los botones que van debajo de un aviso de novedad."""
    accion, _, cual = dato.partition(":")
    tareas = estado.setdefault("tareas", {})
    t = tareas.get(cual)

    if accion == "hecho":
        if not t:
            return "Ya no la tengo", None
        # Guardo como estaba ANTES de tocarla, asi se puede deshacer.
        import panel as P
        P._guardar_deshacer(estado, "listo", cual, dict(t),
                            "marqu\u00e9 %s" % str(t.get("titulo", ""))[:20],
                            "p:pen")
        t["hecho"] = not t.get("hecho")
        return ("Marcada como hecha" if t["hecho"] else "Vuelve a pendientes"), cual

    if accion in ("dormir", "dormir1"):
        if not t:
            return "Ya no la tengo", None
        horas = 1 if accion == "dormir1" else 3
        nueva = ahora + dt.timedelta(hours=horas)
        if t.get("mio"):
            # Un recordatorio tuyo se MUEVE de fecha. Callarlo dejando la fecha
            # vieja no sirve de nada: seguia figurando como vencido.
            t["vence"] = nueva.strftime("%Y-%m-%d %H:%M")
            t.pop("dormida_hasta", None)
            estado.setdefault("avisos", {}).pop(cual, None)
        else:
            t["dormida_hasta"] = nueva.strftime("%Y-%m-%d %H:%M")
        return "Te la recuerdo en %d hora%s" % (horas, "" if horas == 1 else "s"), cual

    if accion == "basta":
        # Este es el boton mas facil de apretar sin querer de todo el bot:
        # esta al lado de "hecho" y callaba el ramo DOS SEMANAS de un toque,
        # sin preguntar, sin decir hasta cuando y sin forma de volver atras.
        import panel as P
        callados = estado.setdefault("callados", {})
        antes = dict(callados.get(cual) or {})
        hasta = ahora + dt.timedelta(days=CFG.DIAS_CALLADO)
        callados[cual] = {"hasta": hasta.strftime("%Y-%m-%d"), "cuenta": 0}
        P._guardar_deshacer(estado, "callar", cual, antes,
                            "silenci\u00e9 el ramo", "p:raiz")
        efimero(estado,
                "\U0001F515 Silenci\u00e9 ese ramo hasta el <b>%s</b>.\n"
                "Los plazos y los avisos del profe te siguen llegando igual.\n"
                "Si fue sin querer, escrib\u00ed /deshacer."
                % hasta.strftime("%d/%m"))
        return "Silenciado %d d\u00edas" % CFG.DIAS_CALLADO, None

    if accion == "nota":
        if not t:
            return "Ya no la tengo", None
        estado["esperando_nota"] = cual
        estado["pidiendo_nota"] = efimero(
            estado, "\U0001F4DD Escribime la nota para <b>%s</b>."
                    % N.escapar(t["titulo"]))
        return "Mandame la nota", None

    return "", None


# ---------------------------------------------------------------- puerta
def anotar_desconocido(estado, quien, nombre="", cuando=None):
    """Alguien que no sos vos le escribio al bot.

    A esa persona NO se le contesta nunca, ni siquiera un "no tenes permiso":
    esa respuesta ya le confirmaria que el bot existe y que es tuyo.  Pero vos
    te enteras, una sola vez por persona, con un boton para no volver a saber
    de ella.  Asi nadie te puede llenar el chat escribiendole al bot.
    """
    if not quien:
        return
    try:
        tope = int(getattr(CFG, "AVISOS_POR_DESCONOCIDO", 1))
    except Exception:
        tope = 1
    gente = estado.setdefault("desconocidos", {})
    ficha = gente.setdefault(str(quien), {"veces": 0, "avisos": 0,
                                          "nombre": "", "bloqueado": False})
    ficha["veces"] = ficha.get("veces", 0) + 1
    if nombre and not ficha.get("nombre"):
        ficha["nombre"] = str(nombre)[:30]
    if cuando is not None:
        try:
            ficha["ultima"] = cuando.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    # Que la lista no crezca para siempre si alguien insiste con cuentas nuevas.
    if len(gente) > 40:
        for viejo in list(gente)[:-40]:
            gente.pop(viejo, None)
    if ficha.get("bloqueado") or ficha.get("avisos", 0) >= max(0, tope):
        return
    ficha["avisos"] = ficha.get("avisos", 0) + 1
    como = ("<b>%s</b>" % N.escapar(ficha["nombre"])) if ficha.get("nombre") \
        else "Alguien"
    N.enviar("\U0001F6A6 %s que no sos vos le escribi\u00f3 al bot.\n"
             "No le contest\u00e9 nada y no puede ver nada tuyo: el bot le hace "
             "caso a un solo tel\u00e9fono, el tuyo.\n\n"
             "<i>Si no sab\u00e9s qui\u00e9n es, no ten\u00e9s que hacer nada.</i>" % como,
             botones=N.teclado([
                 [("\U0001F6AB No avisarme m\u00e1s de esta persona",
                   "g:no:" + str(quien))],
                 [("\U0001F465 Qui\u00e9n puede usar el bot", "p:gente")]]))


def atender(estado, acc, ahora, espera=0):
    """Lee lo que llego del chat y contesta. Devuelve cuantas cosas atendio."""
    mio = str(estado.get("_chat") or "")
    pendientes = N.novedades(estado.get("tg_offset", 0), espera=espera)
    atendidas = 0

    for u in pendientes:
        estado["tg_offset"] = u.get("update_id", 0) + 1

        # ------------------------------------------------ botones
        cb = u.get("callback_query")
        if cb:
            dato = cb.get("data", "")
            de_quien = str((cb.get("from") or {}).get("id") or "")
            if mio and de_quien != mio:
                anotar_desconocido(estado, de_quien,
                                   (cb.get("from") or {}).get("first_name", ""),
                                   ahora)
                continue
            atendidas += 1
            mensaje_id = (cb.get("message") or {}).get("message_id")

            # "dormir1" faltaba en esta lista: el boton de posponer una hora
            # caia al panel y le tapaba la tarjeta sin hacer nada.
            if dato.startswith(("hecho:", "dormir:", "dormir1:", "nota:",
                                "basta:")):
                aviso, tarea_id = _boton_de_tarjeta(estado, dato, acc, ahora)
                N.avisar_boton(cb.get("id"), aviso)
                if tarea_id:
                    acc["redibujar_tarjeta"](tarea_id, mensaje_id)
                continue

            if dato.startswith("a:"):
                N.avisar_boton(cb.get("id"), "Voy")
                acc["accion"](dato[2:])
                continue

            # La confirmacion de una orden hablada.  La marca dice de QUE
            # pedido era este boton: si quedaron dos preguntas sin contestar y
            # el usuario aprieta la vieja, antes se ejecutaba la nueva.
            if dato.startswith(("prop:si", "prop:no")):
                si = dato.startswith("prop:si")
                partes = dato.split(":")
                marca = partes[2] if len(partes) > 2 else ""
                N.avisar_boton(cb.get("id"), "Dale" if si else "Listo")
                salida = acc["confirmar_propuesta"](si, marca)
                if mensaje_id:
                    N.editar(mensaje_id, salida or "Listo.")
                elif salida:
                    N.enviar(salida)
                continue

            # Un boton de una version anterior del bot no lo entiende nadie:
            # antes se contestaba en blanco y se redibujaba el panel encima
            # del mensaje viejo, asi que parecia que el bot se habia colgado.
            if not P.reconoce(dato):
                N.avisar_boton(cb.get("id"),
                               "Ese bot\u00f3n es de un mensaje viejo")
                continue

            aviso, donde = P.toque(estado, dato, acc, ahora)
            N.avisar_boton(cb.get("id"), aviso)
            acc["dibujar_panel"](donde, mensaje_id)
            continue

        # ------------------------------------------------ mensajes
        m = u.get("message") or {}
        texto = (m.get("text") or "").strip()
        quien = str((m.get("chat") or {}).get("id") or "")
        if not texto:
            continue
        if mio and quien != mio:
            anotar_desconocido(estado, quien,
                               (m.get("from") or {}).get("first_name", ""), ahora)
            continue
        atendidas += 1

        mi_mensaje = m.get("message_id")

        # una nota que estabamos esperando
        if not texto.startswith("/") and estado.get("esperando_nota"):
            idt = estado["esperando_nota"]
            t = estado.get("tareas", {}).get(idt)
            estado["esperando_nota"] = None
            pedido = estado.pop("pidiendo_nota", None)
            if pedido:
                N.borrar(pedido)
            borrar_ya(estado, mi_mensaje)
            if not t:
                efimero(estado, "Esa ya no la tengo, no guard\u00e9 la nota.")
                continue
            t["nota"] = texto[:400]
            # La confirmacion de verdad es verla en la tarjeta.
            acc["redibujar_tarjeta"](idt, None)
            efimero(estado, "\U0001F4DD Anotado en <b>%s</b>:\n<i>%s</i>"
                    % (N.escapar(t["titulo"]), N.escapar(t["nota"])))
            continue

        # La botonera fija.
        #
        # OJO: esto tiene que ser el texto EXACTO del boton, no "la palabra
        # aparece en alguna parte".  Antes era `if "pendientes" in plano`, asi
        # que cualquier frase que contuviera la palabra --por ejemplo
        # "que pendientes tengo?"-- se trataba como si hubieras apretado el
        # boton: te tiraba la lista pelada y nunca llegaba a proponer() ni a
        # la IA.  O sea que no se le podia hablar normal al bot.
        plano = pelado(texto)
        if plano in ("novedades", "nuevo") and not texto.startswith("/"):
            borrar_ya(estado, mi_mensaje)
            informativo(estado, acc["texto_novedades"]())
            continue
        if plano in ("pendientes", "pendiente") and not texto.startswith("/"):
            borrar_ya(estado, mi_mensaje)
            informativo(estado, acc["texto_pendientes"]())
            continue
        if plano in ("panel", "menu") and not texto.startswith("/"):
            borrar_ya(estado, mi_mensaje)
            acc["abrir_panel"]()
            continue

        # Estabas cargando tu clave de IA.  Se guarda cifrada y tu mensaje
        # se borra en el acto, para que no quede colgado en el chat.
        if not texto.startswith("/") and estado.get("esperando_clave"):
            pid = estado.pop("esperando_clave", None)
            borrar_ya(estado, mi_mensaje)
            import compartir as CO
            bien, motivo = CO.guardar_clave(estado, pid, texto)
            if bien:
                efimero(estado, "\U0001F510 Guardada y cifrada. No la muestro "
                                "en ning\u00fan lado y borr\u00e9 tu mensaje.")
            else:
                efimero(estado, "No la guard\u00e9: %s." % motivo)
            continue

        # Cualquier cosa que escribas y no sea un comando es una pregunta
        # para la IA sobre tus propias cosas.
        # Elegiste la hora con un boton y ahora mandas el texto: se anota al
        # toque, sin IA y sin parseo.
        if not texto.startswith("/") and estado.get("esperando_rec"):
            fecha = estado.pop("esperando_rec", None)
            try:
                f = dt.datetime.strptime(fecha, "%Y-%m-%d %H:%M")
            except Exception:
                f = None
            if f:
                tareas = estado.setdefault("tareas", {})
                # Mismo cuidado que en /recordar: dos apuntes del mismo minuto
                # se pisaban y uno desaparecia sin avisar.
                marca = f
                idt = "mio_%d" % int(marca.timestamp())
                while idt in tareas:
                    marca = marca + dt.timedelta(seconds=1)
                    idt = "mio_%d" % int(marca.timestamp())
                tareas[idt] = {
                    "grupo": "", "clave": "", "titulo": texto.strip()[:200], "url": "",
                    "vence": f.strftime("%Y-%m-%d %H:%M"), "hecho": False,
                    "nota": "", "mio": True, "es_tarea": False}
                borrar_ya(estado, m.get("message_id"))
                acc["dibujar_panel"]("p:rec", None)
                continue

        # Tocaste "Buscar por nombre" en un ramo: lo que escribas es el nombre
        # del archivo, no una pregunta para la IA.
        if not texto.startswith("/") and estado.get("esperando_busqueda"):
            clave = estado.pop("esperando_busqueda", None)
            if clave and acc.get("buscar_por_nombre"):
                borrar_ya(estado, m.get("message_id"))
                acc["buscar_por_nombre"](clave, texto.strip()[:80])
                continue

        if not texto.startswith("/"):
            if acc.get("proponer"):
                # Puede ser una orden ("recordame a las 8") o una pregunta.
                # Si es orden, el programa te pide confirmacion antes de nada.
                acc["proponer"](texto)
            elif acc.get("preguntar"):
                acc["preguntar"](texto)
            else:
                efimero(estado, "Toc\u00e1 \U0001F431 Panel, o prob\u00e1 /ayuda")
            continue

        borrar_ya(estado, mi_mensaje)

        partes = texto[1:].split(" ", 1)
        cmd = pelado(partes[0].split("@")[0])
        resto = partes[1].strip() if len(partes) > 1 else ""
        r = None

        info = cmd in ("clases", "clase", "video", "videoconferencia",
                       "afuera", "otras", "secciones",
                       "avisos", "aviso", "tablon", "anuncios",
                       "ayuda", "help", "ultimo", "semana", "estado",
                       "perfil", "perfiles", "version", "actualizacion")

        if cmd in ("start", "panel", "menu"):
            acc["abrir_panel"](saludar=(cmd == "start"))
        elif cmd in ("atajos", "teclado", "botones"):
            c = estado.setdefault("config", {})
            c["teclado"] = not c.get("teclado", getattr(CFG, "TECLADO_FIJO", True))
            if c["teclado"]:
                # OJO: este mensaje NO se borra.  La botonera de abajo vive
                # pegada al mensaje que la trajo; si borro el mensaje, Telegram
                # se lleva la botonera con el.  Por eso queda.
                N.enviar("Atajos puestos abajo.", teclado_fijo=True)
            else:
                N.quitar_teclado()
        elif cmd == "limpiar":
            c = estado.setdefault("config", {})
            c["limpiar"] = not c.get("limpiar", True)
            r = ("Borro solo lo que no aporta: tus comandos y mis confirmaciones."
                 if c["limpiar"] else "Ya no borro nada del chat.")
        elif cmd in ("preguntar", "preg"):
            # Atajo viejo, ya no esta en el menu: se le escribe y listo.
            if not resto:
                r = ("No hace falta el comando: escribime la pregunta directo "
                     "en el chat y te contesto.")
            elif acc.get("preguntar"):
                acc["preguntar"](resto)
            else:
                r = ("Ahora mismo no te puedo contestar eso. En el panel, "
                     "en Probar la ayuda de IA, te digo por qu\u00e9.")
        elif cmd in ("ayuda", "help"):
            r = texto_ayuda()
        elif cmd == "resumen":
            r = _resumen(estado, resto, acc, ahora)
        elif cmd == "ultimo":
            r = acc["texto_novedades"]()
        elif cmd == "pendientes":
            # Ahora abre la pantalla con botones, no un texto muerto.
            acc["abrir_panel"]()
            acc["dibujar_panel"]("p:pen", None)
        elif cmd in ("avisos", "aviso", "tablon", "anuncios"):
            r = acc["texto_avisos"]() if acc.get("texto_avisos") else None
        elif cmd in ("deshacer", "undo", "atras"):
            # Antes esto tiraba la pantalla que devuelve _deshacer, asi que el
            # panel seguia mostrando lo de antes y parecia que el deshacer no
            # habia hecho nada.
            r, donde = P._deshacer(estado)
            if donde and acc.get("dibujar_panel"):
                acc["dibujar_panel"](donde, None)
        elif cmd == "semana":
            r = acc["texto_semana"]()
        elif cmd == "pausa":
            r = _pausa(estado, resto, ahora)
        elif cmd in ("seguir", "volver"):
            estado.setdefault("config", {})["pausa_hasta"] = None
            r = "Volv\u00ed."
        elif cmd == "noche":
            c = estado.setdefault("config", {})
            c["noche"] = not c.get("noche", True)
            r = ("De madrugada llego sin sonido." if c["noche"]
                 else "Ahora sueno a cualquier hora.")
        elif cmd == "estado":
            r = acc["texto_diagnostico"]()
        elif cmd in ("perfiles", "perfilar"):
            r = texto_perfiles()
        elif cmd == "perfil":
            r = texto_perfiles() if not resto.strip() else _perfil(estado, resto, acc)
        elif cmd in ("callar", "silenciar"):
            r = _callar(estado, resto, acc, ahora)
        elif cmd == "revisar":
            estado["_revisar_ya"] = True
            r = "Voy a mirar ahora."
        elif cmd in ("recordar", "recordatorios", "recordatorio"):
            if not resto.strip():
                acc["dibujar_panel"]("p:rec", None)
            else:
                r = _recordar(estado, resto, ahora)
        elif cmd == "ia":
            r = _ia(estado, resto)
        elif cmd in ("clases", "clase", "video", "videoconferencia"):
            r = acc["texto_clases"]()
        elif cmd in ("compartir", "comparto"):
            if not resto.strip():
                acc["dibujar_panel"]("p:comp", None)
            else:
                r = _compartir(estado, resto, acc)
        elif cmd in ("afuera", "otras", "secciones"):
            r = acc["texto_afuera"]()
        elif cmd in ("reloj", "latido", "github"):
            acc["accion"]("reloj")
        elif cmd in ("miclave", "micalve", "clave"):
            import compartir as CO
            estado["esperando_clave"] = str(estado.get("_chat") or "yo")
            r = CO.texto_privacidad()
        elif cmd in ("version", "actualizacion"):
            r = acc["texto_version"]()
        elif cmd == "exportar":
            acc["accion"]("exportar")
        elif cmd == "ramos":
            acc["dibujar_panel"]("p:ramos", None)
        else:
            r = "No conozco /%s. Toc\u00e1 \U0001F431 Panel o prob\u00e1 /ayuda" % N.escapar(cmd)

        if r:
            if info:
                informativo(estado, r)
            else:
                efimero(estado, r)

    return atendidas


def sacar_basura(estado):
    """Borra las confirmaciones que ya cumplieron su rato. Se llama en cada
    vuelta del bucle: no cuesta nada y el historial queda limpio."""
    import time as _t
    cola = estado.get("basura") or []
    if not cola:
        return
    ahora_ = _t.time()
    quedan = []
    for par in cola:
        try:
            mid, cuando_ = par[0], float(par[1])
        except Exception:
            continue
        if cuando_ <= ahora_:
            N.borrar(mid)
        else:
            quedan.append([mid, cuando_])
    # Si la cola crecio de mas, los que sobran se BORRAN del chat antes de
    # sacarlos de la lista. Antes se tiraban de la lista sin borrarlos, asi
    # que esos mensajes se quedaban en el chat para siempre y nadie los
    # limpiaba nunca.
    if len(quedan) > 60:
        for mid, _c in quedan[:-60]:
            N.borrar(mid)
        quedan = quedan[-60:]
    estado["basura"] = quedan
