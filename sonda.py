# -*- coding: utf-8 -*-
"""SONDA: mira las plataformas de arriba abajo y escribe un informe.

Se corre UNA vez, en tu computadora, parado en la carpeta del bot:

    python sonda.py

Que hace:
  - entra a las dos plataformas con los datos de mis_datos.txt
  - recorre cada ramo entero, tambien lo que vive adentro de las actividades
  - por cada enlace que no dice de que es, le pregunta al servidor que hay
    detras (solo pregunta, no baja nada)
  - escribe todo en sonda.txt

Que NO hace: no te manda mensajes, no entrega archivos, no borra nada, no
toca la memoria del bot y no escribe ni una letra en las plataformas.

sonda.txt sale anonimo: las direcciones quedan como PLATAFORMA_A y
PLATAFORMA_B, y tu usuario y tu clave nunca aparecen.  Igual conviene abrirlo
y mirarlo antes de mandarlo.
"""
import os
import re
import sys
import time

import secretos

SALIDA = "sonda.txt"
LINEAS = []

# Cada cosa que no puede aparecer en el informe, con el nombre que va en su
# lugar.  Se tapan por largo, primero las mas largas, para que tapar la
# direccion completa no deje suelto el pedazo del host.
TAPAR = []

# Topes, para que el informe sea largo pero no infinito.
ITEMS_POR_RAMO = 60
DUDOSOS_POR_RAMO = 40
AVISOS_POR_RAMO = 6


def guardar_secreto(valor, etiqueta):
    valor = (valor or "").strip()
    if len(valor) < 4:
        return
    TAPAR.append((valor, etiqueta))
    sin_barra = valor.rstrip("/")
    TAPAR.append((sin_barra, etiqueta))
    # el host solo, sin http, por si aparece pelado en algun enlace
    host = re.sub(r"^https?://", "", sin_barra)
    if host and host != sin_barra:
        TAPAR.append((host, etiqueta))
    TAPAR.sort(key=lambda x: len(x[0]), reverse=True)


def tapar(texto):
    """Saca del informe todo lo que te identifica."""
    t = str(texto or "")
    for valor, etiqueta in TAPAR:
        if valor:
            t = t.replace(valor, etiqueta)
    # llaves de sesion que van pegadas a los enlaces
    t = re.sub(r"(?i)([?&](?:sesskey|logintoken|token|key|auth|jwt)=)[^&\s]+",
               r"\1OCULTO", t)
    # cualquier correo que se haya colado en un titulo
    t = re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "CORREO_OCULTO", t)
    return t


def escribir(texto=""):
    linea = tapar(texto)
    LINEAS.append(linea)
    try:
        print(linea)
    except Exception:
        # una consola vieja puede no poder mostrar un emoji: el informe sigue
        print(linea.encode("ascii", "replace").decode("ascii"))


def titulo(t):
    escribir("")
    escribir("=" * 64)
    escribir(t)
    escribir("=" * 64)


def volcar():
    """Deja el informe en disco.  Se llama pase lo que pase."""
    try:
        with open(SALIDA, "w", encoding="utf-8") as f:
            f.write("\n".join(LINEAS) + "\n")
        print("")
        print("Listo. El informe quedo en %s" % SALIDA)
        print("Abrilo, mirá que no tenga nada tuyo, y mandámelo.")
    except Exception as e:
        print("No pude escribir %s (%s)" % (SALIDA, type(e).__name__))


def mirar_enlace(s, url, W):
    """Le pregunta al servidor que hay detras de un enlace, sin bajarlo."""
    ficha = {"estado": "", "tipo": "", "pegado": "no", "largo": "",
             "como": "", "veredicto": ""}
    for metodo in ("head", "get"):
        try:
            if metodo == "head":
                r = s.head(url, timeout=12, allow_redirects=True)
            else:
                r = s.get(url, timeout=15, allow_redirects=True, stream=True)
            ficha["como"] = metodo
            ficha["estado"] = str(getattr(r, "status_code", ""))
            ficha["tipo"] = (r.headers.get("Content-Type") or "")[:60]
            pegado = (r.headers.get("Content-Disposition") or "")
            ficha["pegado"] = "si" if pegado else "no"
            ficha["largo"] = r.headers.get("Content-Length") or ""
            if metodo == "get":
                try:
                    r.close()
                except Exception:
                    pass
            if ficha["estado"] and int(ficha["estado"]) < 400:
                break
        except Exception as e:
            ficha["estado"] = "sin respuesta (%s)" % type(e).__name__
    # El veredicto se saca con la misma regla que usa el bot: si viene pegado
    # como adjunto, o si el tipo no es una pagina, es un archivo.
    tipo = ficha["tipo"].lower()
    if ficha["pegado"] == "si":
        ficha["veredicto"] = "ARCHIVO"
    elif tipo and "html" not in tipo and not tipo.startswith("text/"):
        ficha["veredicto"] = "ARCHIVO"
    elif tipo:
        ficha["veredicto"] = "pagina"
    else:
        ficha["veredicto"] = "no se pudo saber"
    return ficha


def informe_de_ramo(W, CFG, s, base, ficha, etiqueta):
    """Todo lo que se vio en un ramo, y como lo clasificaria el bot."""
    g = ficha["g"]
    items = ficha["items"]
    escribir("")
    escribir("-" * 64)
    escribir("RAMO: %s" % (g.get("nombre") or "sin nombre"))
    escribir("  plataforma      : %s   id interno: %s" % (etiqueta, g.get("id")))
    escribir("  demoro          : %.1f segundos" % ficha["seg"])
    if items is None:
        escribir("  NO SE PUDO LEER esta pagina (no es lo mismo que estar vacia)")
        return
    escribir("  cosas que vio   : %d" % len(items))

    bajables, dudosos, paginas = [], [], []
    for it in items:
        url, tit = it.get("url") or "", it.get("titulo") or ""
        if W.es_bajable(url, tit):
            bajables.append(it)
        elif any(p in url.lower() for p in W.PISTAS_DE_ACTIVIDAD):
            dudosos.append(it)
        else:
            paginas.append(it)
    escribir("  se pueden bajar : %d" % len(bajables))
    escribir("  en duda         : %d  (a estos les pregunto al servidor)"
             % len(dudosos))
    escribir("  paginas sueltas : %d" % len(paginas))
    avisos_del_ramo = g.get("avisos") or []
    escribir("  avisos del profe: %d" % len(avisos_del_ramo))

    if bajables:
        escribir("")
        escribir("  --- lo que YA reconoce como archivo")
        for it in bajables[:ITEMS_POR_RAMO]:
            escribir("    * %s" % (it.get("titulo") or "")[:90])
            escribir("      %s" % it.get("url"))
        if len(bajables) > ITEMS_POR_RAMO:
            escribir("    ... y %d mas" % (len(bajables) - ITEMS_POR_RAMO))

    if dudosos:
        escribir("")
        escribir("  --- enlaces en duda, con lo que contesto el servidor")
        ganados = 0
        for it in dudosos[:DUDOSOS_POR_RAMO]:
            d = mirar_enlace(s, it.get("url") or "", W)
            if d["veredicto"] == "ARCHIVO":
                ganados += 1
            escribir("    * %s" % (it.get("titulo") or "")[:90])
            escribir("      %s" % it.get("url"))
            escribir("      respuesta %s por %s | tipo: %s | pegado: %s | "
                     "peso: %s -> %s"
                     % (d["estado"] or "?", d["como"] or "?",
                        d["tipo"] or "(no dijo)", d["pegado"],
                        d["largo"] or "(no dijo)", d["veredicto"]))
        if len(dudosos) > DUDOSOS_POR_RAMO:
            escribir("    ... y %d mas sin preguntar"
                     % (len(dudosos) - DUDOSOS_POR_RAMO))
        escribir("    resultado: %d de %d enlaces en duda eran archivos de verdad"
                 % (ganados, min(len(dudosos), DUDOSOS_POR_RAMO)))

    if paginas:
        escribir("")
        escribir("  --- paginas que no parecen material (por si alguna deberia)")
        for it in paginas[:12]:
            escribir("    * %s | %s" % ((it.get("titulo") or "")[:60],
                                        it.get("url")))
        if len(paginas) > 12:
            escribir("    ... y %d mas" % (len(paginas) - 12))

    if avisos_del_ramo:
        escribir("")
        escribir("  --- avisos escritos que leyo")
        for a in avisos_del_ramo[:AVISOS_POR_RAMO]:
            escribir("    * %s%s" % ((a.get("titulo") or "")[:80],
                                     "  [urgente]" if a.get("urgente")
                                     else ("  [importante]" if a.get("importante")
                                           else "")))
        if len(avisos_del_ramo) > AVISOS_POR_RAMO:
            escribir("    ... y %d mas" % (len(avisos_del_ramo) - AVISOS_POR_RAMO))


def main():
    secretos.cargar(silencioso=True)

    import fuentes as CFG
    import watcher as W

    titulo("SONDA DEL VIGILANTE")
    try:
        import version as VER
        escribir("version del bot : v%s" % VER.VERSION)
    except Exception:
        pass
    escribir("fecha de la sonda: %s" % W.ahora().strftime("%d-%m-%Y %H:%M"))
    escribir("zona horaria     : %s" % getattr(CFG, "ZONA_HORARIA", "?"))
    escribir("")
    escribir("La sonda mira MAS que el bot en su vuelta normal: entra a todas")
    escribir("las actividades, sin esperar ni saltarse nada.")

    # Para la sonda no hay atajos: sin cache de exploracion, un nivel mas
    # adentro y mas paginas por ramo.  Esto NO cambia como corre el bot.
    CFG.MINUTOS_EXPLORACION_PROFUNDA = 0
    CFG.PROFUNDIDAD = max(2, getattr(CFG, "PROFUNDIDAD", 1))
    CFG.PAGINAS_POR_RAMO = max(30, getattr(CFG, "PAGINAS_POR_RAMO", 14))
    W._ULTIMO_PROFUNDO.clear()

    hubo = False
    for f in CFG.FUENTES:
        etiqueta = "PLATAFORMA_" + str(f.get("clave"))
        titulo(etiqueta + "   (modo de entrada: %s)" % f.get("modo"))
        if not f.get("activo"):
            escribir("esta apagada en la configuracion, la salteo")
            continue
        base = os.environ.get(f["env_url"], "").strip().rstrip("/")
        usuario = os.environ.get(f["env_user"], "").strip()
        clave = os.environ.get(f["env_pass"], "")
        guardar_secreto(base, etiqueta)
        guardar_secreto(usuario, "USUARIO_OCULTO")
        guardar_secreto(clave, "CLAVE_OCULTA")
        if not (base and usuario and clave):
            escribir("faltan datos de esta plataforma en mis_datos.txt, la salteo")
            continue

        s = W.sesion()
        entrar, leer = W.ADAPTADORES[f["modo"]]
        t0 = time.time()
        try:
            entro = entrar(s, base, usuario, clave)
        except Exception as e:
            escribir("no pude entrar: %s" % type(e).__name__)
            continue
        escribir("entrada          : %s  (%.1f s)"
                 % ("ok" if entro else "NO PUDE ENTRAR", time.time() - t0))
        if not entro:
            escribir("Si el usuario y la clave estan bien, puede que la")
            escribir("plataforma haya cambiado la pagina de entrada.")
            continue
        hubo = True

        # Se espia explorar_ramo para medir cada ramo por separado, pero lo que
        # corre adentro es EL MISMO codigo del bot, no una copia.
        registro = []
        original = W.explorar_ramo

        def espia(s2, base2, g2, _o=original, _r=registro):
            t = time.time()
            items, firma = _o(s2, base2, g2)
            _r.append({"g": dict(g2), "items": items, "firma": firma,
                       "seg": time.time() - t})
            return items, firma

        W.explorar_ramo = espia
        t0 = time.time()
        try:
            grupos, viejos = leer(s, base)
        except Exception as e:
            escribir("se cayo leyendo la plataforma: %s" % type(e).__name__)
            grupos, viejos = None, []
        finally:
            W.explorar_ramo = original

        if grupos is None:
            escribir("no pude leer la lista de ramos")
            continue
        escribir("ramos activos    : %d" % len(grupos))
        escribir("ramos viejos     : %d (esos se ignoran a proposito)"
                 % len(viejos or []))
        escribir("recorrido entero : %.1f segundos" % (time.time() - t0))

        for ficha in registro:
            informe_de_ramo(W, CFG, s, base, ficha, etiqueta)

    titulo("AGENDA DE PLAZOS")
    try:
        import watcher as W2
        enlaces = W2.enlaces_de_agenda()
        escribir("calendarios configurados: %d" % len(enlaces))
        for nombre, url in enlaces:
            guardar_secreto(url, "CALENDARIO_OCULTO")
        eventos = W2.leer_agenda() if enlaces else []
        escribir("eventos leidos          : %d" % len(eventos))
        for e in eventos[:10]:
            escribir("  * %s | vence %s" % ((e.get("titulo") or "")[:70],
                                            e.get("vence")))
        if len(eventos) > 10:
            escribir("  ... y %d mas" % (len(eventos) - 10))
    except Exception as e:
        escribir("no pude revisar la agenda: %s" % type(e).__name__)

    titulo("FIN")
    if not hubo:
        escribir("No entre a ninguna plataforma, asi que este informe no dice")
        escribir("mucho. Revisa mis_datos.txt y volve a correrlo.")
    else:
        escribir("Mandame este archivo completo. Con esto se puede ver, ramo por")
        escribir("ramo, que material existe y que estaba quedando afuera.")
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    except KeyboardInterrupt:
        escribir("")
        escribir("Lo cortaste a mano. Guardo lo que alcance a mirar.")
        codigo = 1
    except Exception as e:
        escribir("")
        escribir("La sonda se cayo: %s" % type(e).__name__)
        codigo = 1
    volcar()
    sys.exit(codigo)
