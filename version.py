# -*- coding: utf-8 -*-
"""La version del bot.

Esto es lo unico que hay que tocar en cada parche.  El bot lee este archivo
al arrancar: si el numero cambio, te manda el aviso de actualizacion y ese
mensaje NO se borra.  Ademas lo podes ver cuando quieras en
Ajustes -> Version y novedades, o escribiendo /version.
"""

VERSION = "5.5"
FECHA = "03-08-2026"
TITULO = "clases por videoconferencia, el reloj de GitHub y compartir material"

CAMBIOS = [
    "NUEVO: si el profe arma una clase por videoconferencia, te llega el "
    "aviso con el enlace listo para entrar, aunque tengas el ramo callado",
    "Reconoce las salas de las dos plataformas y las de afuera: Meet, Zoom, "
    "Teams, Webex, Jitsi y las salas virtuales de la plataforma B",
    "Si el profe avisa que se suspende o se cambia una clase, tambien te lo "
    "dice, y te marca cuando todavia no publico el enlace",
    "NUEVO: el bot se vigila a si mismo. GitHub apaga los trabajos "
    "automaticos a los 60 dias sin movimiento, asi que a los 50 te avisa",
    "Y no solo avisa: mueve el repositorio solo y te dice que ya lo "
    "resolvio. Si no puede, te deja el boton Despertar el reloj",
    "NUEVO: podes compartir material con companeros, ramo por ramo. De "
    "fabrica no comparte nada, cada ramo lo abris vos y lo cerras cuando quieras",
    "Vos recibis todos los ramos de ellos, pero ellos ven solo lo que les abriste",
    "Nunca sale nada personal: ni notas, ni pendientes, ni tu usuario, ni "
    "nada tuyo. Solo el titulo, el enlace y el tipo de material",
    "Si te llega algo que tus profes ya subieron, te lo marca como repetido "
    "y te dice de que ramo tuyo lo tenes",
    "Lo de otras secciones llega sin sonido, en una sola linea y sin botones. "
    "No es prioridad y no te va a insistir nunca",
    "Cada uno carga su propia clave de IA por privado con /miclave. Se guarda "
    "cifrada, no la ves y tu mensaje se borra al instante",
    "Boton de panico: Cerrar todo deja de compartir con todos de una",
    "Comandos nuevos: /clases, /compartir, /afuera, /reloj y /miclave",
    "Panel nuevo: Ajustes -> Mas, con Clases por video, Compartir, Otras "
    "secciones y el Reloj de GitHub",
    "Arreglado lo peor: el boton de archivos ahora mira la pagina igual que "
    "el contador, asi que no te dice cero cuando arriba dice cuatro",
    "Los enlaces sin extension, del tipo /archivo/8891, tambien se bajan",
    "Si lo que baja es la pantalla de ingreso disfrazada de archivo, te lo "
    "digo en vez de mandarte basura",
    "Tres alcances en cada ramo: Semana, Mes y Todo, mas Buscar por nombre",
    "Si son muchos archivos te digo cuantos son y cuanto pesan, y recien "
    "mando cuando tocas Mandalos",
    "Van por tandas y te aviso el avance, sin repetir el mismo archivo",
    "Ningun archivo falla en silencio: va el enlace y el motivo en una linea",
    "Cuando no hay nada te lo digo con el rango, no te dejo sin respuesta",
    "Le podes pedir archivos hablando: mandame los archivos de calculo de la "
    "semana pasada, o buscame el programa del ramo",
    "Las confirmaciones las escribe el programa, la IA no cuenta ni mide nada",
    "Ya no te repito tu propio mensaje ni te contesto en ingles",
    "Si la IA esta apagada te lo digo con esas palabras y las ordenes simples "
    "andan igual",
    "Varias claves de IA con relevo automatico y vuelta a la primera",
    "En /estado ves cual clave uso y por que las otras descansan, sin mostrar "
    "ninguna clave",
    "La animacion va todavia mas lenta, y todo el programa usa el mismo numero",
    "Pantallas mas cortas: dos botones por fila y Volver al final",
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
    "Pedile /clases y fijate que aparezcan las videoconferencias que "
    "encontro, con el enlace",
    "Silencia un ramo y despues fijate que igual te avise si hay clase",
    "Toca /reloj y mira que te diga hace cuantos dias no se mueve el bot",
    "Entra a Ajustes -> Mas -> Compartir, agrega a alguien y abrile un solo "
    "ramo. Fijate que los otros ramos sigan cerrados",
    "Toca Cerrar todo y verifica que no quede nadie viendo nada",
    "Manda /miclave y pega una clave. El mensaje se tiene que borrar solo y "
    "la clave no tiene que aparecer en ningun lado",
    "Panel -> Ramos -> un ramo de la plataforma de la facultad -> Semana",
    "En el mismo ramo tocar Todo: primero tiene que llegar el conteo con el "
    "peso y los botones Mandalos y No",
    "En el mismo ramo tocar Por nombre y escribir un pedazo del nombre",
    "Escribir sin comando: mandame los archivos de calculo de la semana pasada",
    "Escribir: recordame en 2 min que six seven viene a la casa, tiene que "
    "llegar UNA sola respuesta, en castellano y con la hora exacta",
    "Mirar /estado y ver la linea de claves de IA",
    "Panel -> Recordar -> 15 min, escribi el texto y mira la lista",
    "Probar /recordar lunes 18:45 osi un lunes: tiene que caer hoy",
    "Escribi sin comando: recordame en 5 minutos probar el bot, y toca Dale",
    "Abri /ayuda y toca un comando de la lista",
    "Anda a Ajustes y mira Perfiles de aviso y Version y novedades",
]


def etiqueta():
    return "v%s (%s)" % (VERSION, FECHA)
