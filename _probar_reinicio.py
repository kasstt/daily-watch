# -*- coding: utf-8 -*-
# Prueba suelta: el boton de reiniciar. Que reinicie, que no borre nada,
# que no lo pueda apretar nadie mas, y que no tape la pantalla de todos los dias.
import os
os.environ.setdefault("TG_TOKEN", "x")
os.environ.setdefault("TG_CHAT", "555")

import watcher as W
import notificar as N
import panel as P
import comandos

malas = []
mandados = []
avisos_de_boton = []
acciones = []


def revisar(titulo, condicion, detalle=""):
    if not condicion:
        malas.append(titulo)
    print("%-4s %s%s" % ("OK" if condicion else "MAL", titulo,
                         "" if condicion else "  <- " + str(detalle)))


def enviar_falso(texto, silencioso=False, botones=None, teclado_fijo=False):
    mandados.append((texto, botones))
    return 100 + len(mandados)


N.enviar = enviar_falso
N.avisar_boton = lambda ident, texto="": avisos_de_boton.append(texto)


def filas_de(teclado):
    return (teclado or {}).get("inline_keyboard", [])


def vigilante(guardar_revienta=False):
    v = object.__new__(W.Vigilante)
    v.estado = {"novedades": [{"t": "algo importante"}], "grupos": {"r1": {}}}
    v.guardado = []

    def guardar():
        if guardar_revienta:
            raise IOError("el gist no contesta")
        v.guardado.append(dict(v.estado))
    v.guardar = guardar
    return v


# ------------------------------------------------- 1. primero pregunta
v = vigilante()
del mandados[:]
v.preguntar_si_reinicio()
revisar("antes de apagarse, pregunta", len(mandados) == 1, mandados)
texto, botones = mandados[0] if mandados else ("", None)
revisar("y avisa que no se pierde nada", "No pierdo nada" in texto, texto[:80])
revisar("y todav\u00eda no se apaga",
        getattr(v, "reiniciar_pedido", False) is False)
crudo = str(botones)
revisar("con un s\u00ed y un no",
        "a:reiniciar_si" in crudo and "p:mas" in crudo, crudo[:120])

# --------------------------------------- 2. al confirmar, guarda y se apaga
del mandados[:]
v.reiniciarme()
revisar("guarda la memoria ANTES de apagarse", len(v.guardado) == 1, v.guardado)
revisar("y reci\u00e9n ah\u00ed pide el corte", v.reiniciar_pedido is True)
revisar("y avisa que se va y que vuelve",
        mandados and "arranco de nuevo" in mandados[0][0], mandados[:1])
revisar("la memoria queda entera",
        v.estado.get("novedades") and v.estado.get("grupos"), v.estado.keys())

# --------------------------- 3. si no puede guardar, NO se apaga y lo dice
v2 = vigilante(guardar_revienta=True)
del mandados[:]
v2.reiniciarme()
revisar("si no puede guardar, no se apaga",
        getattr(v2, "reiniciar_pedido", False) is False)
revisar("y lo dice en vez de callarse",
        mandados and "No pude guardar" in mandados[0][0], mandados[:1])

# ------------------------- 4. donde vive el bot\u00f3n: en Diagn\u00f3stico, solo
acc = {"texto_diagnostico": lambda: "todo en orden por ac\u00e1"}
texto_diag, teclado_diag = P.pantalla({}, "p:diag", acc)
filas = filas_de(teclado_diag)
fila_reinicio = [f for f in filas
                 if any(b.get("callback_data") == "a:reiniciar" for b in f)]
revisar("el bot\u00f3n de reiniciar est\u00e1 en Diagn\u00f3stico", len(fila_reinicio) == 1, filas)
revisar("y va solo en su fila, sin nada al lado",
        fila_reinicio and len(fila_reinicio[0]) == 1, fila_reinicio)
revisar("y desde ah\u00ed se puede volver", "p:ajustes" in str(filas), filas)
revisar("la pantalla de diagn\u00f3stico sigue diciendo lo suyo",
        "todo en orden" in texto_diag, texto_diag[:60])

# ------------- 5. y NO invade la pantalla de todos los d\u00edas ni la agranda
texto_mas, teclado_mas = P._mas({}, {})
revisar("no qued\u00f3 en M\u00e1s cosas, donde se apretar\u00eda sin querer",
        "a:reiniciar" not in str(teclado_mas))
revisar("y M\u00e1s cosas sigue entrando en el tel\u00e9fono (6 filas o menos)",
        len(filas_de(teclado_mas)) <= 6, len(filas_de(teclado_mas)))

# ------------------------------------ 6. el dueno aprieta: se ejecuta
N.novedades = lambda offset, espera=0: [
    {"update_id": 1,
     "callback_query": {"id": "c1", "data": "a:reiniciar",
                        "from": {"id": 555, "first_name": "due\u00f1o"},
                        "message": {"message_id": 9}}}]
estado = {"_chat": "555"}
del acciones[:]
comandos.atender(estado, {"accion": lambda c: acciones.append(c)},
                 W.ahora(), espera=0)
revisar("si lo aprieta el due\u00f1o, se hace", acciones == ["reiniciar"], acciones)

# ------------------------------ 7. otra persona aprieta: NO pasa nada
N.novedades = lambda offset, espera=0: [
    {"update_id": 2,
     "callback_query": {"id": "c2", "data": "a:reiniciar_si",
                        "from": {"id": 999, "first_name": "intruso"},
                        "message": {"message_id": 9}}}]
estado = {"_chat": "555"}
del acciones[:]
comandos.atender(estado, {"accion": lambda c: acciones.append(c)},
                 W.ahora(), espera=0)
revisar("si lo aprieta otra persona, no pasa nada", acciones == [], acciones)
revisar("y queda anotado que alguien lo intent\u00f3",
        bool(estado.get("desconocidos")), estado.get("desconocidos"))

print("\nresultado: %s" % ("TODO BIEN" if not malas else "%d MALAS" % len(malas)))
raise SystemExit(1 if malas else 0)
