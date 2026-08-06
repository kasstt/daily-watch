# -*- coding: utf-8 -*-
# Prueba suelta: cuando no encuentra, que diga la verdad.
# Reproduce la captura del dueno: busca "semana1.pdf" en todo el ramo, no lo
# encuentra, y el bot contestaba "si tengo 1 en otras fechas" cuando no habia
# ninguna otra fecha: lo que sobraba era el nombre.
import os
os.environ.setdefault("TG_TOKEN", "x")
os.environ.setdefault("TG_CHAT", "1")

import watcher as W
import notificar as N

malas = []
mandados = []


def revisar(titulo, condicion, detalle=""):
    if not condicion:
        malas.append(titulo)
    print("%-4s %s%s" % ("OK" if condicion else "MAL", titulo,
                         "" if condicion else "  <- " + str(detalle)))


def enviar_falso(texto, silencioso=False, botones=None, teclado_fijo=False):
    mandados.append(texto)
    return 100 + len(mandados)


N.enviar = enviar_falso


def vigilante(archivos=()):
    """Un ramo con los archivos que le pasemos, sin red ni memoria en disco."""
    v = object.__new__(W.Vigilante)
    v.estado = {"grupos": {"r1": {"nombre": "C\u00c1LCULO INTEGRAL"}},
                "novedades": [{"c": "r1", "u": a[0], "t": a[1], "f": a[2],
                               "tipo": "archivo"} for a in archivos]}
    v.leer_ramo_ahora = lambda clave: []   # sin internet
    v._dudoso = lambda u, t: False
    v.nombre_de = lambda clave: "C\u00c1LCULO INTEGRAL"
    v.guardar = lambda: None
    return v


SEMANA = ("https://x/pluginfile/Semana1.pdf", "Semana1.pdf", "2026-07-01")
GUIA = ("https://x/pluginfile/Guia3.pdf", "Gu\u00eda N\u00b03 de ejercicios", "2026-07-20")

# ============================================ 1. el texto, caso por caso
v = vigilante([SEMANA, GUIA])

sin_fechas = v._sin_resultados("r1", "C\u00c1LCULO INTEGRAL", "de todo el ramo",
                               "tarea9", "todo", 2, alcance="todo")
revisar("buscando en todo el ramo NO habla de otras fechas",
        "en otras fechas" not in sin_fechas, sin_fechas)
revisar("y explica que el que sobraba era el nombre",
        "ninguno se llama as\u00ed" in sin_fechas, sin_fechas)
revisar("y dice cu\u00e1ntos tiene de verdad",
        "2 archivos" in sin_fechas, sin_fechas)

con_fechas = v._sin_resultados("r1", "C\u00c1LCULO INTEGRAL", "de esta semana",
                               "tarea9", "todo", 2, alcance="semana")
revisar("buscando una semana, ah\u00ed s\u00ed avisa que hay en otras fechas",
        "en otras fechas" in con_fechas, con_fechas)

vacio = vigilante()
nada = vacio._sin_resultados("r1", "RAMO", "de todo el ramo", "", "todo", 0)
revisar("sin nada guardado, lo dice claro",
        "Todav\u00eda no vi nada" in nada, nada)

anotado = vacio._sin_resultados("r1", "RAMO", "de todo el ramo", "", "todo", 0,
                                anotadas=5)
revisar("con avisos pero sin archivos, tambi\u00e9n lo explica",
        "ninguna es un archivo" in anotado, anotado)

# ================================= 2. el camino real, como lo vive el dueno
del mandados[:]
v = vigilante([SEMANA, GUIA])
v.pedir_archivos("r1", "todo", nombre="tarea9")
revisar("buscar por nombre siempre contesta algo", len(mandados) == 1, mandados)
salida = mandados[0] if mandados else ""
revisar("y esa respuesta no inventa otras fechas",
        "en otras fechas" not in salida, salida)
revisar("si no hay nada parecido, igual le dice qu\u00e9 hacer",
        "nombre a medias" in salida, salida)
revisar("y le ofrece pedir el ramo entero",
        "todo el ramo" in salida, salida)

# ------- y la otra rama: cuando S\u00cd hay algo parecido, lo tiene que mostrar
v_par = vigilante([SEMANA, GUIA])
v_par.parecidos_a = lambda clave, nombre, cuantos=4: ["Semana1.pdf"]
con_parecidos = v_par._sin_resultados("r1", "C\u00c1LCULO INTEGRAL",
                                      "de todo el ramo", "semana uno", "todo",
                                      2, alcance="todo")
revisar("cuando hay algo parecido, lo muestra",
        "Lo m\u00e1s parecido" in con_parecidos and "Semana1.pdf" in con_parecidos,
        con_parecidos)
revisar("y ah\u00ed tampoco habla de otras fechas",
        "en otras fechas" not in con_parecidos, con_parecidos)

# ------- y el caso de la captura: el nombre exacto SÍ tiene que encontrarlo
del mandados[:]
v2 = vigilante([SEMANA, GUIA])
v2.mandar_material = lambda *a, **k: mandados.append("MANDADO")
elegidos, total, rango = v2.filtrar_archivos("r1", "todo", nombre="semana1.pdf")
revisar("el nombre exacto encuentra el archivo",
        len(elegidos) == 1 and elegidos[0]["titulo"] == "Semana1.pdf",
        (len(elegidos), rango))
revisar("y no se lleva puesto el resto del ramo", total == 2, total)

print("\nresultado: %s" % ("TODO BIEN" if not malas else "%d MALAS" % len(malas)))
raise SystemExit(1 if malas else 0)
