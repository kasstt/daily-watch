# -*- coding: utf-8 -*-
"""El panel: un solo mensaje anclado que se edita a si mismo.

Regla de estilo de todo el panel: el estado se escribe DENTRO del boton.
No dice "Noche", dice "Noche: si".  Asi sabes donde estas parado sin abrir
nada, y un toque cambia el valor sin cambiar de pantalla.

Los avisos de material nuevo NO pasan por aca.  Llegan sueltos y suenan,
porque una novedad no puede depender de que vos abras un menu.
"""
import datetime as dt

import fuentes as CFG
import notificar as N


def _cfg(estado):
    return estado.setdefault("config", {})


def _si_no(v):
    return "s\u00ed" if v else "no"


def _resumen_cfg(estado):
    return _cfg(estado).setdefault("resumen", dict(CFG.RESUMEN))


def _perfil_de(estado, clave):
    return (estado.get("perfiles", {}).get(clave)
            or _cfg(estado).get("perfil") or CFG.PERFIL_POR_DEFECTO)


def _callado(estado, clave):
    return estado.get("callados", {}).get(clave)


def _dias_de_callado(ficha, hoy):
    try:
        fin = dt.datetime.strptime(ficha["hasta"], "%Y-%m-%d").date()
        return max(0, (fin - hoy).days)
    except Exception:
        return 0


# ------------------------------------------------------------- pantallas
def _raiz(estado, acc):
    d = acc["tablero"]()
    cfg = _cfg(estado)
    pausa = acc["en_pausa"]()

    cabeza = "\U0001F431 <b>Vigilante</b>   %s\n%d ramos \u00b7 %d pendientes \u00b7 %d nuevas hoy" % (
        d["salud"], d["ramos"], d["pendientes"], d["nuevas_hoy"])
    pie = "\n\nactualizado %s" % d["ultima"]

    botones = N.teclado([
        [("\U0001F4E5 Novedades%s" % (" (%d)" % d["nuevas"] if d["nuevas"] else ""), "p:nov")],
        [("\U0001F4CC Pendientes%s" % (" (%d)" % d["pendientes"] if d["pendientes"] else ""), "p:pen"),
         ("\U0001F4C5 Semana", "p:sem")],
        [("\U0001F4DA Ramos", "p:ramos"), ("\U0001F514 Avisos", "p:avisos")],
        [("\u23F8 Pausa: %s" % ("s\u00ed" if pausa else "no"), "t:pausa"),
         ("\U0001F319 Noche: %s" % _si_no(cfg.get("noche", True)), "t:noche")],
        [("\U0001F9E0 IA: %s" % _si_no(cfg.get("ia", True)), "t:ia"),
         ("\u2699\uFE0F Ajustes", "p:ajustes")],
    ])
    return cabeza + pie, botones


def _ramos(estado, acc):
    hoy = acc["hoy"]()
    filas = []
    for clave, nombre, emoji in acc["lista_ramos"]():
        marca = " \U0001F515" if _callado(estado, clave) else ""
        filas.append([("%s %s%s" % (emoji, nombre[:26], marca), "p:r:" + clave)])
    if not filas:
        filas = [[("todav\u00eda no veo ning\u00fan ramo", "p:raiz")]]
    filas.append([("\u2B05\uFE0F Volver", "p:raiz")])
    return "\U0001F4DA <b>Tus ramos</b>\n%d en curso" % len(acc["lista_ramos"]()), N.teclado(filas)


def _ramo(estado, acc, clave):
    f = acc["ficha_ramo"](clave)
    if not f:
        return "Ese ramo ya no est\u00e1.", N.teclado([[("\u2B05\uFE0F Volver", "p:ramos")]])

    ficha_callado = _callado(estado, clave)
    texto = "%s <b>%s</b>\n%d cosas \u00b7 \u00faltima novedad %s" % (
        f["emoji"], N.escapar(f["nombre"]), f["cantidad"], f["ultima"])
    if ficha_callado:
        texto += "\n\n\U0001F515 silenciado, quedan %d d\u00edas" % _dias_de_callado(
            ficha_callado, acc["hoy"]())

    botones = N.teclado([
        [("\U0001F4C4 Ver material", "p:mat:" + clave)],
        [("\U0001F9E0 Resumen del ramo", "a:resu:" + clave)],
        [("\U0001F514 Perfil: %s" % _perfil_de(estado, clave), "t:perfil:" + clave)],
        [("\U0001F514 Volver a avisar" if ficha_callado else "\U0001F515 Silenciar",
          "t:callar:" + clave)],
        [("\u2B05\uFE0F Volver", "p:ramos")],
    ])
    return texto, botones


def _avisos(estado, acc):
    r = _resumen_cfg(estado)
    cada = "todos los d\u00edas" if r.get("cada") == "dia" else "los %s" % r.get("dia")
    texto = ("\U0001F514 <b>Cu\u00e1ndo te hablo</b>\n"
             "Resumen %s a las %s.\n"
             "Perfil general: %s." % (cada, r.get("hora"),
                                      _cfg(estado).get("perfil", CFG.PERFIL_POR_DEFECTO)))
    botones = N.teclado([
        [("\U0001F4C5 Resumen: %s" % ("encendido" if r.get("activo") else "apagado"),
          "t:resumen")],
        [("Cambiar d\u00eda", "p:dia"), ("Cambiar hora", "p:hora")],
        [("\U0001F501 Cada: %s" % ("d\u00eda" if r.get("cada") == "dia" else "semana"),
          "t:cada")],
        [("\U0001F319 Madrugada: %s" % ("sin sonido" if _cfg(estado).get("noche", True)
                                        else "suena"), "t:noche")],
        [("\U0001F514 Perfil general: %s" % _cfg(estado).get("perfil", CFG.PERFIL_POR_DEFECTO),
          "t:perfilg")],
        [("\u2B05\uFE0F Volver", "p:raiz")],
    ])
    return texto, botones


def _dia(estado, acc):
    dias = ["lunes", "martes", "mi\u00e9rcoles", "jueves", "viernes", "s\u00e1bado", "domingo"]
    filas = [[(d.capitalize(), "d:" + d)] for d in dias]
    filas.append([("\u2B05\uFE0F Volver", "p:avisos")])
    return "\U0001F4C5 <b>Qu\u00e9 d\u00eda te mando el resumen</b>", N.teclado(filas)


def _hora(estado, acc):
    horas = [7, 8, 9, 12, 14, 16, 18, 19, 20, 21, 22, 23]
    filas, fila = [], []
    for h in horas:
        fila.append(("%02d:00" % h, "h:%02d" % h))
        if len(fila) == 3:
            filas.append(fila)
            fila = []
    if fila:
        filas.append(fila)
    filas.append([("\u2B05\uFE0F Volver", "p:avisos")])
    return "\U0001F551 <b>A qu\u00e9 hora</b>", N.teclado(filas)


def _ajustes(estado, acc):
    d = acc["tablero"]()
    texto = ("\u2699\uFE0F <b>Ajustes</b>\n"
             "Memoria: %s\n"
             "IA: %s\n"
             "Silenciados: %d" % (d["memoria"], d["ia"], d["silenciados"]))
    botones = N.teclado([
        [("\U0001F50D Revisar ahora", "a:revisar")],
        [("\U0001F4E4 Exportar todo", "a:exportar")],
        [("\U0001FA7A Diagn\u00f3stico", "p:diag")],
        [("\u2753 Ayuda", "p:ayuda")],
        [("\u2B05\uFE0F Volver", "p:raiz")],
    ])
    return texto, botones


def _simple(titulo, cuerpo, volver="p:raiz"):
    return titulo + "\n\n" + cuerpo, N.teclado([[("\u2B05\uFE0F Volver", volver)]])


def pantalla(estado, donde, acc):
    """Devuelve (texto, botones) de la pantalla pedida."""
    try:
        if donde in ("", "p:raiz", "raiz"):
            return _raiz(estado, acc)
        if donde == "p:ramos":
            return _ramos(estado, acc)
        if donde.startswith("p:r:"):
            return _ramo(estado, acc, donde[4:])
        if donde.startswith("p:mat:"):
            clave = donde[6:]
            return _simple("\U0001F4C4 <b>Material</b>", acc["material"](clave),
                           "p:r:" + clave)
        if donde == "p:avisos":
            return _avisos(estado, acc)
        if donde == "p:dia":
            return _dia(estado, acc)
        if donde == "p:hora":
            return _hora(estado, acc)
        if donde == "p:ajustes":
            return _ajustes(estado, acc)
        if donde == "p:nov":
            return _simple("\U0001F4E5 <b>Novedades</b>", acc["texto_novedades"]())
        if donde == "p:pen":
            return _simple("\U0001F4CC <b>Pendientes</b>", acc["texto_pendientes"]())
        if donde == "p:sem":
            return _simple("\U0001F4C5 <b>Los \u00faltimos 7 d\u00edas</b>", acc["texto_semana"]())
        if donde == "p:diag":
            return _simple("\U0001FA7A <b>Diagn\u00f3stico</b>", acc["texto_diagnostico"](),
                           "p:ajustes")
        if donde == "p:ayuda":
            return _simple("\u2753 <b>Ayuda</b>", acc["texto_ayuda"](), "p:ajustes")
    except Exception as e:
        return ("Algo se rompi\u00f3 dibujando esto (%s)." % type(e).__name__,
                N.teclado([[("\u2B05\uFE0F Volver", "p:raiz")]]))
    return _raiz(estado, acc)


# ------------------------------------------------------------- toques
def _rotar_perfil(actual):
    orden = CFG.ORDEN_PERFILES
    try:
        return orden[(orden.index(actual) + 1) % len(orden)]
    except ValueError:
        return CFG.PERFIL_POR_DEFECTO


def toque(estado, dato, acc, ahora):
    """Procesa un boton del panel.
    Devuelve (aviso_cortito, pantalla_a_dibujar)."""
    cfg = _cfg(estado)

    if dato.startswith("p:"):
        return "", dato

    # ---- interruptores
    if dato == "t:noche":
        cfg["noche"] = not cfg.get("noche", True)
        return ("De madrugada sin sonido" if cfg["noche"] else "Suena a cualquier hora"), None

    if dato == "t:ia":
        cfg["ia"] = not cfg.get("ia", True)
        if cfg["ia"]:
            estado["fallas_ia"] = 0
        return ("Res\u00famenes encendidos" if cfg["ia"] else "Res\u00famenes apagados"), None

    if dato == "t:pausa":
        if acc["en_pausa"]():
            cfg["pausa_hasta"] = None
            return "Volv\u00ed", None
        hasta = ahora + dt.timedelta(hours=3)
        cfg["pausa_hasta"] = hasta.strftime("%Y-%m-%d %H:%M")
        return "Callado hasta las %s" % hasta.strftime("%H:%M"), None

    if dato == "t:resumen":
        r = _resumen_cfg(estado)
        r["activo"] = not r.get("activo", True)
        return ("Resumen encendido" if r["activo"] else "Resumen apagado"), None

    if dato == "t:cada":
        r = _resumen_cfg(estado)
        r["cada"] = "dia" if r.get("cada") == "semana" else "semana"
        return ("Todos los d\u00edas" if r["cada"] == "dia" else "Una vez por semana"), None

    if dato == "t:perfilg":
        cfg["perfil"] = _rotar_perfil(cfg.get("perfil", CFG.PERFIL_POR_DEFECTO))
        return "Perfil general: %s" % cfg["perfil"], None

    if dato.startswith("t:perfil:"):
        clave = dato[9:]
        nuevo = _rotar_perfil(_perfil_de(estado, clave))
        estado.setdefault("perfiles", {})[clave] = nuevo
        return "Perfil: %s" % nuevo, None

    if dato.startswith("t:callar:"):
        clave = dato[9:]
        callados = estado.setdefault("callados", {})
        if clave in callados:
            del callados[clave]
            return "Vuelve a avisarte", None
        return "", "c:" + clave        # pide confirmacion

    if dato.startswith("c:si:"):
        clave = dato[5:]
        hasta = ahora + dt.timedelta(days=CFG.DIAS_CALLADO)
        estado.setdefault("callados", {})[clave] = {
            "hasta": hasta.strftime("%Y-%m-%d"), "cuenta": 0}
        return "Silenciado %d d\u00edas" % CFG.DIAS_CALLADO, "p:r:" + clave

    # ---- dia y hora del resumen
    if dato.startswith("d:"):
        _resumen_cfg(estado)["dia"] = dato[2:]
        return "Los %s" % dato[2:], "p:avisos"

    if dato.startswith("h:"):
        _resumen_cfg(estado)["hora"] = "%s:00" % dato[2:]
        return "A las %s:00" % dato[2:], "p:avisos"

    return "", None


def confirmar_callar(estado, acc, clave):
    """La unica pregunta del panel. Se pregunta donde duele, no en todo."""
    f = acc["ficha_ramo"](clave) or {"nombre": "ese ramo", "emoji": "\U0001F4D8"}
    texto = ("\U0001F515 <b>Silenciar %s?</b>\n\n"
             "Durante %d d\u00edas no te aviso de material nuevo.\n\n"
             "Igual te van a llegar:\n"
             "\u2022 las entregas con fecha, siempre\n"
             "\u2022 el resumen, con este ramo al pie\n\n"
             "Se prende solo cuando se cumpla el plazo."
             % (N.escapar(f["nombre"]), CFG.DIAS_CALLADO))
    botones = N.teclado([
        [("S\u00ed, silenciar", "c:si:" + clave)],
        [("No, dejalo", "p:r:" + clave)],
    ])
    return texto, botones
