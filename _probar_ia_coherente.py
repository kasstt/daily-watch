# -*- coding: utf-8 -*-
# Prueba suelta: que la IA diga lo mismo la mires donde la mires.
import os
os.environ["IA_KEY"] = "AIzaDePrueba1"
os.environ["IA_KEY_2"] = "AIzaDePrueba2"
os.environ.setdefault("TG_TOKEN", "x")
os.environ.setdefault("TG_CHAT", "1")

import ia as IA

malas = []
llamadas = []


def revisar(titulo, condicion, detalle=""):
    if not condicion:
        malas.append(titulo)
    print("%-4s %s%s" % ("OK" if condicion else "MAL", titulo,
                         "" if condicion else "  <- " + str(detalle)))


def motor_falso(texto, pdfs, c=None):
    llamadas.append((c or {}).get("nombre", "?"))
    return "Listo, ya lo mir\u00e9 y no hay nada raro."


# El proveedor de verdad sale de la configuracion; lo reemplazamos entero
# para que la prueba corra sin internet y sin claves reales.
for _nombre in list(IA.PROVEEDORES):
    IA.PROVEEDORES[_nombre] = motor_falso

LISTA = IA.claves()
revisar("la prueba tiene claves de mentira cargadas", len(LISTA) >= 1, len(LISTA))


def estado_limpio():
    return {"config": {"ia": True}}


def dormir_todas(estado, motivo="cupo", detalle="quota"):
    for c in IA.claves():
        IA._penitencia(estado, c, motivo, detalle)
    return estado


# ------------------------------------------------ 1. la frase de siempre
e = estado_limpio()
revisar("con todo bien dice que est\u00e1 encendida",
        IA.en_palabras(e) == "encendida", IA.en_palabras(e))

apagada = {"config": {"ia": False}}
revisar("si vos la apagaste, lo dice as\u00ed",
        IA.en_palabras(apagada) == "apagada por vos", IA.en_palabras(apagada))
revisar("y con la apagada no intenta nada",
        IA.se_puede_intentar(apagada) is False)

# ---------------------------- 2. el descanso: dos verdades que no se peleen
e = dormir_todas(estado_limpio())
revisar("descansando, el trabajo de fondo se aguanta",
        IA.disponible(e) is False)
revisar("pero si vos pregunt\u00e1s, s\u00ed se intenta",
        IA.se_puede_intentar(e) is True)
frase = IA.en_palabras(e)
revisar("y la frase dice que est\u00e1 descansando, no 'apagada'",
        frase.startswith("descansando"), frase)
revisar("y esa frase nunca dice 'encendida' cuando no lo est\u00e1",
        "encendida" not in frase, frase)

# ------------------ 3. LA FALLA DEL DUENO: preguntar mientras descansa
del llamadas[:]
e = dormir_todas(estado_limpio())
respuesta = IA.preguntar(e, "\u00bfqu\u00e9 tengo pendiente?", "libreta corta")
revisar("pregunt\u00e1ndole en el chat, contesta igual", bool(respuesta), respuesta)
revisar("y para contestar us\u00f3 una clave de verdad", len(llamadas) == 1, llamadas)

# --------------------------- 4. el trabajo de fondo sigue respetando el descanso
e = dormir_todas(estado_limpio())
del llamadas[:]
tranquilo = False
try:
    IA._pedir(e, "resum\u00ed esto")
except RuntimeError:
    tranquilo = True
revisar("solo, el bot no gasta cupo mientras descansa", tranquilo)
revisar("y no llam\u00f3 a nadie", not llamadas, llamadas)

# ------------------------------- 5. una clave mala no se insiste ni forzando
e = estado_limpio()
for c in IA.claves():
    IA._penitencia(e, c, "mala")
del llamadas[:]
freno = False
try:
    IA._pedir(e, "hola", forzar=True)
except RuntimeError:
    freno = True
revisar("una clave marcada como mala no se reintenta nunca", freno)
revisar("y tampoco se la llama", not llamadas, llamadas)

# ---------------------------- 6. cuando anda, la penitencia se borra sola
e = dormir_todas(estado_limpio())
IA.preguntar(e, "hola", "libreta")
revisar("despu\u00e9s de una respuesta buena vuelve a decir 'encendida'",
        IA.en_palabras(e) == "encendida", IA.en_palabras(e))
revisar("y el trabajo de fondo tambi\u00e9n queda habilitado",
        IA.disponible(e) is True)

print("\nresultado: %s" % ("TODO BIEN" if not malas else "%d MALAS" % len(malas)))
raise SystemExit(1 if malas else 0)
