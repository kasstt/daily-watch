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
        [("\U0001F4CC Pendientes%s" % (" (%d)" % d["pendientes"] if d["pendientes"] else ""), "p:pen"),
         ("\u23F0 Recordar", "p:rec")],
        [("\U0001F4E5 Novedades%s" % (" (%d)" % d["nuevas"] if d["nuevas"] else ""), "p:nov"),
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
    # Dos por fila: la pantalla entra sin scroll.
    filas, fila = [], []
    for clave, nombre, emoji in acc["lista_ramos"]():
        marca = " \U0001F515" if _callado(estado, clave) else ""
        fila.append(("%s %s%s" % (emoji, nombre[:16], marca), "p:r:" + clave))
        if len(fila) == 2:
            filas.append(fila)
            fila = []
    if fila:
        filas.append(fila)
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

    cuantos = acc["cuantos_archivos"](clave) if "cuantos_archivos" in acc else 0
    if cuantos:
        texto += "\n\U0001F4C4 %d documento%s guardado%s" % (
            cuantos, "" if cuantos == 1 else "s", "" if cuantos == 1 else "s")

    # El buscador de archivos, con los tres alcances a mano.
    botones = N.teclado([
        [("\U0001F4E5 Semana", "a:baj:%s:semana" % clave),
         ("\U0001F4C5 Mes", "a:baj:%s:mes" % clave)],
        [("\U0001F5C2 Todo", "a:baj:%s:todo" % clave),
         ("\U0001F50E Por nombre", "p:busc:" + clave)],
        [("\U0001F4C4 Material", "p:mat:" + clave),
         ("\U0001F9E0 Resumen", "a:resu:" + clave)],
        [("\U0001F514 %s" % _perfil_de(estado, clave), "t:perfil:" + clave),
         ("\U0001F514 Volver a avisar" if ficha_callado else "\U0001F515 Silenciar",
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
        [("\U0001F4C5 Resumen: %s" % ("s\u00ed" if r.get("activo") else "no"), "t:resumen"),
         ("\U0001F501 Cada: %s" % ("d\u00eda" if r.get("cada") == "dia" else "semana"),
          "t:cada")],
        [("D\u00eda", "p:dia"), ("Hora", "p:hora")],
        [("\U0001F319 Madrugada: %s" % ("sin sonido" if _cfg(estado).get("noche", True)
                                        else "suena"), "t:noche"),
         ("\U0001F514 %s" % _cfg(estado).get("perfil", CFG.PERFIL_POR_DEFECTO),
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
    teclado = _cfg(estado).get("teclado", getattr(CFG, "TECLADO_FIJO", True))
    try:
        import version as VER
        texto += "\nVersi\u00f3n: <b>v%s</b>" % VER.VERSION
    except Exception:
        pass
    # Cinco filas como mucho, de lo mas usado a lo menos usado.
    botones = N.teclado([
        [("\U0001F50D Revisar", "a:revisar"), ("\u2753 Ayuda", "p:ayuda")],
        [("\U0001F195 Versi\u00f3n", "p:version"), ("\u2699\uFE0F Perfiles", "p:perfiles")],
        [("\U0001FA7A Diagn\u00f3stico", "p:diag"), ("\U0001F4E4 Exportar", "a:exportar")],
        [("\u2328\uFE0F Atajos: %s" % _si_no(teclado), "t:teclado"),
         ("\u2795 M\u00e1s", "p:mas")],
        [("\u2B05\uFE0F Volver", "p:raiz")],
    ])
    return texto, botones


# ------------------------------------------- compartir y clases por video
def _mas(estado, acc):
    """Lo que se usa poco pero tiene que estar a mano."""
    personas = len(estado.get("personas", {}) or {})
    afuera = len(estado.get("de_afuera", []) or [])
    texto = ("\u2795 <b>M\u00e1s cosas</b>\n"
             "Compartiendo con %d persona%s\n"
             "De otras secciones: %d cosa%s guardada%s"
             % (personas, "" if personas == 1 else "s",
                afuera, "" if afuera == 1 else "s",
                "" if afuera == 1 else "s"))
    return texto, N.teclado([
        [("\U0001F3A5 Clases por video", "p:clases"),
         ("\U0001F91D Compartir", "p:comp")],
        [("\U0001F4E8 Otras secciones", "p:afuera"),
         ("\u23F3 Reloj de GitHub", "a:reloj")],
        [("\u2B05\uFE0F Volver", "p:ajustes")],
    ])


def _compartir(estado, acc):
    """Con quien compartis y que ve cada uno."""
    texto = "\U0001F91D <b>Compartir material</b>\n\n" + acc["texto_compartir"]()
    filas = []
    for pid, f in (acc["personas"]() or [])[:6]:
        cuantos = len(f.get("ramos") or [])
        marca = "\U0001F6AB" if f.get("bloqueada") else (
            "\u2705" if cuantos else "\u26AA")
        filas.append([("%s %s (%d)" % (marca, f.get("alias", "?")[:14], cuantos),
                       "p:per:" + str(pid))])
    if estado.get("personas"):
        filas.append([("\U0001F512 Cerrar todo", "a:cerrar_compartir")])
    filas.append([("\u2B05\uFE0F Volver", "p:mas")])
    return texto, N.teclado(filas)


def _persona(estado, acc, pid):
    """Que ramos MIOS ve esta persona.  Se abre y se cierra uno por uno."""
    ficha = (estado.get("personas") or {}).get(str(pid))
    if not ficha:
        return ("Esa persona ya no est\u00e1.",
                N.teclado([[("\u2B05\uFE0F Volver", "p:comp")]]))
    abiertos = set(ficha.get("ramos") or [])
    texto = ("\U0001F464 <b>%s</b>\n"
             "Ve %d ramo%s tuyo%s. Lo dem\u00e1s no lo ve.\n\n"
             "<i>Toc\u00e1 un ramo para abrirlo o cerrarlo. Sale material nada "
             "m\u00e1s: t\u00edtulo, fecha y enlace. Nunca tus notas ni tus "
             "pendientes.</i>"
             % (N.escapar(ficha.get("alias", "?")), len(abiertos),
                "" if len(abiertos) == 1 else "s",
                "" if len(abiertos) == 1 else "s"))
    filas = []
    for clave, nombre, _emoji in (acc["lista_ramos"]() or [])[:8]:
        marca = "\u2705" if clave in abiertos else "\u2B1C"
        filas.append([("%s %s" % (marca, str(nombre)[:22]),
                       "tc:%s:%s" % (pid, clave))])
    filas.append([("\U0001F6AB Sacar", "tq:" + str(pid)),
                  ("\u2B05\uFE0F Volver", "p:comp")])
    return texto, N.teclado(filas)


# ------------------------------------------------------ recordatorios
ATAJOS_RECORDAR = [
    ("r:15m", "\u23F0 15 min", 15),
    ("r:1h", "\u23F0 1 hora", 60),
    ("r:3h", "\u23F0 3 horas", 180),
]


def _mis_recordatorios(estado):
    """Los apuntes tuyos que todavia no vencieron ni marcaste."""
    salida = []
    for idt, t in (estado.get("tareas") or {}).items():
        if not t.get("mio") or t.get("hecho"):
            continue
        try:
            f = dt.datetime.strptime(t.get("vence", ""), "%Y-%m-%d %H:%M")
        except Exception:
            continue
        salida.append((f, idt, t))
    salida.sort(key=lambda x: x[0])
    return salida


def _cuando_corto(f, hoy):
    if f.date() == hoy.date():
        return "hoy %s" % f.strftime("%H:%M")
    if (f.date() - hoy.date()).days == 1:
        return "ma\u00f1ana %s" % f.strftime("%H:%M")
    return f.strftime("%d/%m %H:%M")


def _recordatorios(estado, acc):
    """Pantalla de recordatorios: dos toques y listo."""
    hoy = acc["ahora"]()
    esperando = estado.get("esperando_rec")

    lineas = ["\u23F0 <b>Recordatorios</b>"]
    if esperando:
        try:
            f = dt.datetime.strptime(esperando, "%Y-%m-%d %H:%M")
            lineas.append("\u270D\uFE0F Escribime <b>qu\u00e9</b> te recuerdo para "
                          "<b>%s</b>. Mandalo como mensaje." % _cuando_corto(f, hoy))
        except Exception:
            estado.pop("esperando_rec", None)
            esperando = None

    mios = _mis_recordatorios(estado)
    if mios:
        lineas.append("")
        for f, _, t in mios[:8]:
            lineas.append("\u2022 <b>%s</b> \u00b7 %s"
                          % (_cuando_corto(f, hoy), N.escapar(t.get("titulo", ""))))
    elif not esperando:
        lineas.append("No tengo ninguno. Eleg\u00ed cu\u00e1ndo y escrib\u00ed qu\u00e9.")

    lineas += ["", "<i>Tambi\u00e9n vale escribirme: recordame el lunes 18:45 osi</i>"]

    filas = [[(txt, cod) for cod, txt, _ in ATAJOS_RECORDAR]]
    filas.append([("\U0001F319 Hoy 21:00", "r:hoy21"), ("\u2600\uFE0F Ma\u00f1ana 9:00", "r:man9")])
    for f, idt, t in mios[:5]:
        titulo = t.get("titulo", "")[:18]
        filas.append([("\u2705 %s" % titulo, "rl:" + idt),
                      ("+1h", "rm:" + idt),
                      ("\U0001F5D1", "rx:" + idt)])
    if esperando:
        filas.append([("\u274C Cancelar", "r:no")])
    filas.append([("\u2B05\uFE0F Volver", "p:raiz")])
    return "\n".join(lineas), N.teclado(filas)


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
        if donde.startswith("p:busc:"):
            clave = donde[7:]
            estado["esperando_busqueda"] = clave
            return ("\U0001F50E <b>Buscar por nombre</b>\n"
                    "Escrib\u00edme un pedazo del nombre del archivo, por ejemplo "
                    "<b>gu\u00eda 3</b> o <b>programa</b>.\n"
                    "Busco en todo el ramo y te digo cu\u00e1ntos encontr\u00e9 antes "
                    "de mandarte nada.",
                    N.teclado([[("\u2B05\uFE0F Volver", "p:r:" + clave)]]))
        if donde.startswith("p:mat:"):
            clave = donde[6:]
            filas = []
            if acc["cuantos_archivos"](clave):
                filas.append([("\U0001F4E5 Semana", "a:baj:%s:semana" % clave),
                              ("\U0001F5C2 Todo", "a:baj:%s:todo" % clave)])
            filas.append([("\u2B05\uFE0F Volver", "p:r:" + clave)])
            return ("\U0001F4C4 <b>Todo el material</b>\n\n" + acc["material"](clave),
                    N.teclado(filas))
        if donde == "p:rec":
            return _recordatorios(estado, acc)
        if donde == "p:avisos":
            return _avisos(estado, acc)
        if donde == "p:dia":
            return _dia(estado, acc)
        if donde == "p:hora":
            return _hora(estado, acc)
        if donde == "p:ajustes":
            return _ajustes(estado, acc)
        if donde == "p:mas":
            return _mas(estado, acc)
        if donde == "p:comp":
            return _compartir(estado, acc)
        if donde.startswith("p:per:"):
            return _persona(estado, acc, donde[6:])
        if donde == "p:clases":
            return _simple("\U0001F3A5 <b>Clases por videoconferencia</b>",
                           acc["texto_clases"](), "p:mas")
        if donde == "p:afuera":
            return _simple("\U0001F4E8 <b>De otras secciones</b>",
                           acc["texto_afuera"](), "p:mas")
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
        if donde == "p:perfiles":
            import comandos as C
            return C.texto_perfiles(), N.teclado([
                [("\u2B05\uFE0F Volver", "p:ajustes")]])
        if donde == "p:version":
            return acc["texto_version"](), N.teclado([
                [("\u2B05\uFE0F Volver", "p:ajustes")]])
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

    # ---- recordatorios rapidos
    if dato.startswith("r:"):
        cual = dato[2:]
        if cual == "no":
            estado.pop("esperando_rec", None)
            return "Cancelado", "p:rec"
        if cual == "hoy21":
            f = ahora.replace(hour=21, minute=0, second=0, microsecond=0)
            if f <= ahora:
                f += dt.timedelta(days=1)
        elif cual == "man9":
            f = (ahora + dt.timedelta(days=1)).replace(hour=9, minute=0, second=0,
                                                       microsecond=0)
        else:
            minutos = dict((c[2:], m) for c, _, m in ATAJOS_RECORDAR).get(cual, 60)
            f = ahora + dt.timedelta(minutes=minutos)
        estado["esperando_rec"] = f.strftime("%Y-%m-%d %H:%M")
        return "Escribime qu\u00e9 te recuerdo", "p:rec"

    if dato.startswith(("rl:", "rm:", "rx:")):
        idt = dato[3:]
        t = (estado.get("tareas") or {}).get(idt)
        if not t:
            return "Ese ya no est\u00e1", "p:rec"
        if dato.startswith("rl:"):
            t["hecho"] = True
            return "Listo", "p:rec"
        if dato.startswith("rx:"):
            estado["tareas"].pop(idt, None)
            return "Borrado", "p:rec"
        try:
            f = dt.datetime.strptime(t["vence"], "%Y-%m-%d %H:%M") + dt.timedelta(hours=1)
        except Exception:
            f = ahora + dt.timedelta(hours=1)
        nuevo = "mio_%d" % int(f.timestamp())
        t["vence"] = f.strftime("%Y-%m-%d %H:%M")
        estado.setdefault("avisos", {}).pop(idt, None)
        estado["tareas"].pop(idt, None)
        estado["tareas"][nuevo] = t
        return "Movido a las %s" % f.strftime("%H:%M"), "p:rec"

    # ---- compartir: abrir o cerrar UN ramo para UNA persona
    if dato.startswith("tc:"):
        pid, _, clave = dato[3:].partition(":")
        if not clave:
            return "No entend\u00ed ese ramo", "p:comp"
        abierto, bien = acc["alternar_ramo"](pid, clave)
        if not bien:
            return "Esa persona ya no est\u00e1", "p:comp"
        nombre = acc["nombre"](clave)
        return ("Ahora ve %s" % nombre) if abierto else (
            "Ya no ve %s" % nombre), "p:per:" + pid

    if dato.startswith("tq:"):
        pid = dato[3:]
        acc["sacar_persona"](pid)
        return "Listo, no comparte m\u00e1s con vos", "p:comp"

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

    if dato == "t:teclado":
        cfg["teclado"] = not cfg.get("teclado", getattr(CFG, "TECLADO_FIJO", True))
        if cfg["teclado"]:
            # Este mensaje NO se borra: la botonera de abajo vive pegada al
            # mensaje que la trajo.
            N.enviar("Atajos puestos abajo.", teclado_fijo=True)
            return "Atajos puestos", None
        N.quitar_teclado()
        return "Atajos sacados", None

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
