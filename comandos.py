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
    ("preguntar", "pregunt\u00e1 por tus ramos"),
    ("panel", "todo a botones"),
    ("ultimo", "lo \u00faltimo que subieron"),
    ("pendientes", "lo que te falta"),
    ("semana", "los \u00faltimos 7 d\u00edas"),
    ("resumen", "resumen de un ramo"),
    ("pausa", "callate unas horas"),
    ("noche", "avisos de madrugada"),
    ("estado", "\u00bffunciona todo?"),
    ("perfil", "cu\u00e1nto insistir por ramo"),
    ("callar", "silenciar un ramo"),
    ("revisar", "mir\u00e1 ahora"),
    ("recordar", "guardame un apunte"),
    ("ia", "prender o apagar res\u00famenes"),
    ("exportar", "mandame todo en un archivo"),
    ("ayuda", "c\u00f3mo se usa cada uno"),
]

# Lo que va DESPUES del comando, cuando lleva algo.  Se ve solo en /ayuda,
# pegado al comando, para que no parezca un comando repetido.
COLA = {
    "preguntar": "que entrego esta semana",
    "resumen": "ramo calculo",
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


def texto_ayuda():
    lineas = ["<b>Comandos</b>", ""]
    for c, d in MENU:
        cola = COLA.get(c)
        firma = "/%s %s" % (c, cola) if cola else "/" + c
        # Sin <code>: asi Telegram los deja apretables.
        lineas.append("%s \u00b7 %s" % (firma, d))
    lineas += [
        "",
        "<b>/resumen</b>",
        "/resumen ramo calculo \u00b7 ese ramo, con IA",
        "/resumen \u00b7 prende o apaga el semanal",
        "/resumen viernes 20:00 \u00b7 cambia cu\u00e1ndo llega",
        "/resumen diario 21:00 \u00b7 todos los d\u00edas",
        "",
        "<b>Recordatorios</b>",
        "/recordar 20m sacar la ropa \u00b7 en minutos",
        "/recordar 3h mandar el informe \u00b7 en horas",
        "/recordar viernes 18:00 estudiar \u00b7 dia y hora",
        "",
        "<b>Perfiles</b> \u00b7 suave, normal, apretado, diario",
        "/perfil apretado termo \u00b7 uno por ramo",
    ]
    return "\n".join(lineas)


# ---------------------------------------------------------------- fechas
def cuando(texto, ahora):
    """Entiende 'viernes 18:00', 'manana 20:00', '2m', '3h', '2d' y 'HH:MM'.
    Devuelve (fecha, resto) o (None, texto)."""
    p = texto.split()
    if not p:
        return None, texto
    uno = pelado(p[0])

    # '2m' minutos, '3h' horas, '2d' dias.  Tambien 'min', 'hs', 'dias'.
    m = re.fullmatch(r"(\d+)\s*(m|min|mins|minutos?|h|hs|horas?|d|dias?)", uno)
    if m:
        n = int(m.group(1))
        letra = m.group(2)[0]
        if letra == "m":
            salto = dt.timedelta(minutes=n)
        elif letra == "h":
            salto = dt.timedelta(hours=n)
        else:
            salto = dt.timedelta(days=n)
        return ahora + salto, " ".join(p[1:])

    resto = p[1:]
    if uno == "hoy":
        base = ahora
    elif uno in ("manana", "mnana"):
        base = ahora + dt.timedelta(days=1)
    elif uno in DIAS:
        falta = (DIAS.index(uno) - ahora.weekday()) % 7 or 7
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
    fecha, texto = cuando(resto, ahora)
    if not fecha:
        return ("Decime cu\u00e1ndo. Por ejemplo:\n/recordar 20m sacar la ropa\n"
                "/recordar 3h mandar el informe\n/recordar viernes 18:00 estudiar")
    if not texto.strip():
        return "Y qu\u00e9 te recuerdo?"
    idt = "mio_%d" % int(fecha.timestamp())
    estado.setdefault("tareas", {})[idt] = {
        "grupo": "", "clave": "", "titulo": texto.strip(), "url": "",
        "vence": fecha.strftime("%Y-%m-%d %H:%M"), "hecho": False,
        "nota": "", "mio": True}
    return "Anotado: <b>%s</b>\nTe aviso el %s a las %s." % (
        N.escapar(texto.strip()), fecha.strftime("%d/%m"), fecha.strftime("%H:%M"))


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
    """Lo tuyo: comandos y toques de la botonera. No aportan nada al historial."""
    if _limpiar() and mensaje_id:
        N.borrar(mensaje_id)


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
        t["hecho"] = not t.get("hecho")
        return ("Marcada como hecha" if t["hecho"] else "Vuelve a pendientes"), cual

    if accion == "dormir":
        if not t:
            return "Ya no la tengo", None
        t["dormida_hasta"] = (ahora + dt.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
        return "Te la recuerdo en 3 horas", cual

    if accion == "nota":
        if not t:
            return "Ya no la tengo", None
        estado["esperando_nota"] = cual
        estado["pidiendo_nota"] = efimero(
            estado, "\U0001F4DD Escribime la nota para <b>%s</b>."
                    % N.escapar(t["titulo"]))
        return "Mandame la nota", None

    if accion == "basta":
        hasta = ahora + dt.timedelta(days=CFG.DIAS_CALLADO)
        estado.setdefault("callados", {})[cual] = {
            "hasta": hasta.strftime("%Y-%m-%d"), "cuenta": 0}
        return "Silenciado %d d\u00edas" % CFG.DIAS_CALLADO, None

    return "", None


# ---------------------------------------------------------------- puerta
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
            if mio and str((cb.get("from") or {}).get("id")) != mio:
                continue
            atendidas += 1
            dato = cb.get("data", "")
            mensaje_id = (cb.get("message") or {}).get("message_id")

            if dato.startswith(("hecho:", "dormir:", "nota:", "basta:")):
                aviso, tarea_id = _boton_de_tarjeta(estado, dato, acc, ahora)
                N.avisar_boton(cb.get("id"), aviso)
                if tarea_id:
                    acc["redibujar_tarjeta"](tarea_id, mensaje_id)
                continue

            if dato.startswith("a:"):
                N.avisar_boton(cb.get("id"), "Voy")
                acc["accion"](dato[2:])
                continue

            aviso, donde = P.toque(estado, dato, acc, ahora)
            N.avisar_boton(cb.get("id"), aviso)
            acc["dibujar_panel"](donde, mensaje_id)
            continue

        # ------------------------------------------------ mensajes
        m = u.get("message") or {}
        texto = (m.get("text") or "").strip()
        quien = str((m.get("chat") or {}).get("id") or "")
        if not texto or (mio and quien != mio):
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

        # la botonera fija
        plano = pelado(texto)
        if "novedades" in plano and not texto.startswith("/"):
            borrar_ya(estado, mi_mensaje)
            informativo(estado, acc["texto_novedades"]())
            continue
        if "pendientes" in plano and not texto.startswith("/"):
            borrar_ya(estado, mi_mensaje)
            informativo(estado, acc["texto_pendientes"]())
            continue
        if "panel" in plano and not texto.startswith("/"):
            borrar_ya(estado, mi_mensaje)
            acc["abrir_panel"]()
            continue

        # Cualquier cosa que escribas y no sea un comando es una pregunta
        # para la IA sobre tus propias cosas.
        if not texto.startswith("/"):
            if acc.get("preguntar"):
                acc["preguntar"](texto)
            else:
                efimero(estado, "Toc\u00e1 \U0001F431 Panel, o prob\u00e1 /ayuda")
            continue

        borrar_ya(estado, mi_mensaje)

        partes = texto[1:].split(" ", 1)
        cmd = pelado(partes[0].split("@")[0])
        resto = partes[1].strip() if len(partes) > 1 else ""
        r = None

        info = cmd in ("ayuda", "help", "ultimo", "pendientes", "semana", "estado")

        if cmd in ("start", "panel", "menu"):
            acc["abrir_panel"](saludar=(cmd == "start"))
        elif cmd == "atajos":
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
            if not resto:
                r = "Escribime la pregunta y ya. No hace falta el comando."
            elif acc.get("preguntar"):
                acc["preguntar"](resto)
            else:
                r = "No tengo IA disponible ahora."
        elif cmd in ("ayuda", "help"):
            r = texto_ayuda()
        elif cmd == "resumen":
            r = _resumen(estado, resto, acc, ahora)
        elif cmd == "ultimo":
            r = acc["texto_novedades"]()
        elif cmd == "pendientes":
            r = acc["texto_pendientes"]()
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
        elif cmd == "perfil":
            r = _perfil(estado, resto, acc)
        elif cmd in ("callar", "silenciar"):
            r = _callar(estado, resto, acc, ahora)
        elif cmd == "revisar":
            estado["_revisar_ya"] = True
            r = "Voy a mirar ahora."
        elif cmd == "recordar":
            r = _recordar(estado, resto, ahora)
        elif cmd == "ia":
            r = _ia(estado, resto)
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
    estado["basura"] = quedan[-60:]
