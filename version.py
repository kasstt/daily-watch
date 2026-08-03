# -*- coding: utf-8 -*-
"""La version del bot.

Esto es lo unico que hay que tocar en cada parche.  El bot lee este archivo
al arrancar: si el numero cambio, te manda el aviso de actualizacion y ese
mensaje NO se borra.  Ademas lo podes ver cuando quieras en
Ajustes -> Version y novedades, o escribiendo /version.
"""

VERSION = "5.3"
FECHA = "03-08-2026"
TITULO = "recordatorios de dos toques, rapidos y sin escribir fechas"

CAMBIOS = [
    "Apartado de recordatorios nuevo: elegis la hora de un toque y despues "
    "escribis que te recuerdo, nada de fechas a mano",
    "Atajos de 15 min, 1 hora, 3 horas, Hoy 21:00 y Manana 9:00",
    "Cada recordatorio tiene su fila con Hecho, +1h y borrar",
    "Boton Recordar en la primera fila del panel",
    "Arreglado: si decias el dia de hoy (lunes 18:45 un lunes) se iba a la "
    "semana que viene, ahora cae hoy si la hora todavia no paso",
    "Ahora entiende minutos escritos de cualquier forma: 5m, 5 min, en 5 minutos",
    "Los comandos de /ayuda se pueden apretar, ya no son texto muerto",
    "La ayuda explica los cuatro perfiles y cada cuanto avisa cada uno",
    "Ajustes tiene Perfiles de aviso y Version y novedades",
    "La animacion de espera va mas lenta",
    "Le podes pedir cosas hablando normal: recordatorios, pausa, callar un "
    "ramo, perfil, revisar, marcar hecha",
    "Lo que entiende la IA lo revisa el programa y te muestra una "
    "confirmacion con Dale o No antes de tocar nada",
    "Tus recordatorios suenan UNA sola vez, a la hora que pediste",
    "La IA conoce el manual del bot y contesta dudas de uso",
    "El aviso de actualizacion ya no se saltea",
]

A_PROBAR = [
    "Panel -> Recordar -> 15 min, escribi el texto y mira la lista",
    "Probar /recordar lunes 18:45 osi un lunes: tiene que caer hoy",
    "Escribi sin comando: recordame en 5 minutos probar el bot, y toca Dale",
    "Abri /ayuda y toca un comando de la lista",
    "Anda a Ajustes y mira Perfiles de aviso y Version y novedades",
]


def etiqueta():
    return "v%s (%s)" % (VERSION, FECHA)
