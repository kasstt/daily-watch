# -*- coding: utf-8 -*-
"""La version del bot.

Esto es lo unico que hay que tocar en cada parche.  El bot lee este archivo
al arrancar: si el numero cambio, te manda el aviso de actualizacion y ese
mensaje NO se borra.  Ademas lo podes ver cuando quieras en
Ajustes -> Version y novedades, o escribiendo /version.
"""

VERSION = "6.0"
FECHA = "05-08-2026 09:40"
TITULO = "cuarta revision: quien entra al bot, la IA que por fin contesta y el material como vos lo pediste"

CAMBIOS = [
    "LO MAS IMPORTANTE: le dabas a 'descargar todo' en un ramo con dos "
    "archivos y te llegaba una sola cosa comprimida, que en el telefono no "
    "se abre. No era el bot juntandolos: era la plataforma, que entrega su "
    "propio paquete ya armado y el bot te lo pasaba tal cual. Ahora lo abre "
    "el, te manda los archivos de a uno con su nombre y su formato, y te "
    "explica por que los ves separados.",
    "Cuando son varios archivos, antes de mandarlos te pregunta cómo los "
    "queres: de a uno o todo junto en un solo envio. Eso vale para ese "
    "pedido nomas, no te queda pegado para siempre.",
    "Boton nuevo para probar la ayuda de IA, en Mas. Le hace una pregunta de "
    "verdad y te cuenta en castellano que paso: cuantas claves le llegaron, "
    "si se acabo el cupo del dia o si el servicio no contesta. Nunca muestra "
    "tus claves, y te recuerda que los avisos y el material no dependen de "
    "la IA.",
    "Ya le podes pedir archivos escribiendo, no solo con botones: 'mandame "
    "el ultimo archivo de calculo', 'lo del ultimo dia de calculo' o 'busca "
    "los archivos que digan certamen'. Siempre te muestra que encontro y "
    "espera que confirmes antes de mandarte nada.",
    "Pantalla nueva 'Quien puede usar el bot', en Mas: de un vistazo ves a "
    "quien le hace caso, quien recibe material tuyo y quien intento "
    "escribirle sin permiso. Desde ahi cortas todo lo compartido de una, "
    "aunque parezca que no hay nadie.",
    "Si un desconocido le escribe al bot, el bot no le contesta nada y te "
    "avisa a vos una sola vez, con un boton para no volver a saber de esa "
    "persona. Antes no te enterabas.",
    "LO MAS IMPORTANTE: un ramo podia tener material subido hace DIAS y el "
    "bot te decia que no habia ni un archivo. Pasaban dos cosas: muchos "
    "enlaces de material no terminan en .pdf y el bot los descartaba por el "
    "nombre; y cuando un ramo se veia vacio, se conformaba con la portada y "
    "solo entraba a mirar por dentro cada tanto. Ahora los reconoce igual, y "
    "un ramo que parece vacio se revisa por dentro en cada vuelta, hasta "
    "encontrar lo que hay.",
    "Cuando un enlace no dice de que es, ahora el bot le pregunta a la "
    "plataforma si es algo para bajar o una pagina para leer, y se acuerda de "
    "la respuesta por unos dias para no preguntar dos veces lo mismo. Antes "
    "adivinaba por el nombre y se le escapaban guias enteras.",
    "El numero que muestra el panel y la lista de material ya no se pueden "
    "contradecir. Antes te decia '4 cosas guardadas' arriba y 'no encontre "
    "archivos' abajo, en la misma pantalla.",
    "Las claves de repuesto de la IA no le llegaban al bot cuando corre solo. "
    "Cargabas la segunda y el bot seguia usando una sola: en cuanto se "
    "acababa el cupo del dia te quedabas sin resumenes igual. Ahora si las "
    "recibe, y la de repuesto puede ser incluso de otro servicio de IA.",
    "Los mensajes de la IA ahora se entienden. En vez de 'clave 1 sin cupo' "
    "te dice 'hoy ya se me acabo el cupo de resumenes, vuelve manana'. Y si "
    "el limite es por dia, espera hasta el otro dia en vez de reintentar cada "
    "hora sin sentido.",
    "Como te llega el material: hasta 4 archivos te llegan de a uno y en su "
    "formato de siempre, asi los abris de un toque. De 5 en adelante, en un "
    "solo paquete para no taparte el chat. Lo podes elegir vos en Ajustes y "
    "despues Mas: de a uno, en paquete, o que decida el bot. Si el paquete no "
    "se puede mandar, te llegan igual de a uno: no se pierde ningun archivo.",
    "Lo que no marcaste visto te lo vuelve a recordar, una vez por dia y "
    "hasta cuatro veces. Antes lo nombraba una sola vez y si te distraias, "
    "quedaba enterrado.",
    "El primer arranque con la memoria vacia ya no es una loteria: te manda "
    "un resumen corto y sin sonido de lo que encontro, con un boton para ver "
    "el resto. Antes o te llenaba el chat con cosas viejas o no decia nada.",
    "Ahora vos decidis si los avisos de prueba, entrega o asistencia te "
    "suenan de madrugada. Esta en la pantalla de Avisos.",
    "Herramienta nueva de revision, para correr a mano en tu computadora "
    "cuando algo no aparece: recorre las dos plataformas de punta a punta y "
    "deja un informe SIN tus datos (sin usuario, sin clave, sin direcciones y "
    "sin correos) para poder seguir afinando la busqueda de material. No "
    "escribe nada en las plataformas ni toca la memoria del bot.",

    "LO MAS IMPORTANTE: los recordatorios de las entregas NO te estaban "
    "llegando. Ni uno. Cada vez que el bot revisaba tus ramos se tropezaba "
    "justo en esa parte y se quedaba callado, y de paso se saltaba el resumen, "
    "el aviso de 'no lo viste' y la vigilancia de su propio reloj. Te podias "
    "perder una entrega y el bot nunca te iba a avisar. Ya funciona.",
    "Si el mensaje no sale, el bot ya no lo da por mandado. Antes, cuando la "
    "mensajeria fallaba un segundo, el aviso se anotaba como enviado igual y "
    "nunca te llegaba: ni ese ni ninguna repeticion. Ahora lo reintenta en la "
    "revision siguiente. Pasaba con los avisos del profe, las clases por "
    "videoconferencia, los recordatorios y los 'no lo viste'.",
    "El boton '+1 hora' de las tarjetas no hacia nada: te tapaba el aviso con "
    "el panel y el recordatorio seguia igual. Ya posterga de verdad.",
    "Los botones de un mensaje viejo ahora te contestan que son viejos, en vez "
    "de dibujarte el panel encima del mensaje que estabas mirando.",
    "Si le pediste dos cosas seguidas y le quedaron dos preguntas sin "
    "contestar, apretar 'Dale' en la vieja hacia lo NUEVO. Ahora cada boton "
    "sabe de que pedido era y te lo dice si ya no corresponde.",
    "Un nombre de ramo o un titulo con signos raros (menor que, comillas, "
    "un ampersand) rompia el mensaje entero: no llegaba nada. Ahora se "
    "muestra tal cual lo escribio el profe.",
    "Un aviso que hablaba de 'tomate una foto' o de 'tomar asistencia' te "
    "sonaba como urgencia de madrugada, porque buscaba las palabras adentro "
    "de otras palabras. Ahora solo te despierta lo que te cambia el dia.",
    "Una clase que el bot adivinaba por las palabras del profe (sin enlace) "
    "te despertaba de madrugada igual que una clase de verdad. Ahora esa "
    "llega sin sonido; la que tiene enlace sigue sonando siempre.",
    "Cuando la mensajeria le pide al bot que espere, ahora espera y reintenta "
    "en vez de perder el aviso. Si detecta muchas cosas de golpe, no se le "
    "cae ninguna.",
    "Si algo no entra en un solo mensaje, ahora te avisa que le cortaste el "
    "final, en vez de mandarlo cortado como si estuviera completo.",
    "La memoria del bot ya no crece para siempre: se olvida sola de lo de "
    "hace mas de un ano y de los pendientes cerrados mas viejos. Sin eso, un "
    "dia dejaba de poder guardar y volvia a avisarte cosas viejas.",
    "La memoria se guarda de un solo golpe: si la corrida se corta en el "
    "peor momento, ya no queda partida al medio ni arranca en blanco.",
    "Y si aun asi se queda sin memoria, te lo dice en palabras simples. Un "
    "bot callado se parece demasiado a un bot sin noticias.",
    "El reloj automatico ya no corta la revision que esta trabajando. Antes "
    "podia matarla justo despues de avisarte y antes de anotarlo, y el mismo "
    "aviso te llegaba dos veces.",
    "Las fechas de lo compartido y del control del reloj ahora usan la hora "
    "de tu ciudad. Antes usaban la de la maquina, varias horas adelantada: "
    "lo de las 9 de la noche quedaba fechado al dia siguiente.",

    "Revise el bot COMPLETO, linea por linea, no solo lo nuevo de la 5.6.",
    "Los mensajes largos ya no se perdian en silencio. Si un mensaje se "
    "pasaba de largo, se cortaba a lo bruto y podia quedar partido al medio "
    "de una negrita: la plataforma lo rechazaba ENTERO y vos no te "
    "enterabas de nada. Le pasaba justo al resumen semanal, que es el "
    "mensaje mas largo que te manda el bot.",
    "Apretar +1 hora en una entrega del profe ya no te la duplica. Antes le "
    "cambiaba el nombre interno, el bot la perdia de vista y en la revision "
    "siguiente la anotaba como nueva: te quedaba la misma entrega dos veces "
    "y con la fecha cambiada. Ahora solo se posterga el recordatorio y la "
    "fecha del profe no se toca.",
    "Los avisos ahora tienen dos niveles. Solo te despierta de madrugada lo "
    "que te cambia el dia: suspension, clase online, cambio de fecha o de "
    "sala. Que hable de una prueba o una entrega te lo marco igual, pero de "
    "dia. Antes 'prueba', 'entrega' y 'asistencia' contaban como urgentes, y "
    "esas palabras estan en casi todos los avisos: te iba a sonar todo a las "
    "3 de la manana.",
    "Volvio a aparecer el boton 'Cuando te hablo' en Ajustes. Se habia "
    "quedado sin puerta de entrada, asi que no habia forma de cambiar el dia "
    "ni la hora del resumen desde el panel.",
    "El boton Deshacer ahora se vence a los 30 minutos. Antes sobrevivia "
    "horas y podias deshacer a ciegas algo que ya no te acordabas.",
    "La campanita que silencia un ramo ahora te dice hasta que dia lo "
    "callo y se puede deshacer. Es el boton mas facil de apretar sin querer: "
    "esta al lado de 'ya esta' y callaba el ramo dos semanas de un toque.",
    "Marcar algo como hecho tambien se puede deshacer.",
    "Ya se te puede hablar normal. Antes cualquier frase que tuviera la "
    "palabra 'pendientes' adentro -por ejemplo 'que pendientes tengo?'- se "
    "tomaba como si hubieras apretado el boton, y nunca llegaba a "
    "entenderte de verdad.",
    "Los recordatorios pedidos hablando ya no se pisan entre ellos ni "
    "caen en 'PARA ENTREGAR'. Van a 'SIN REVISAR', que es donde van tus "
    "cosas.",
    "/avisos sale en orden de fecha, el mas nuevo arriba. Antes salia en el "
    "orden interno del programa, que es azar puro.",
    "La admiracion roja en /avisos es solo para los urgentes de verdad. "
    "Antes la llevaban todos y no distinguia nada.",
    "Los avisos del profe se archivan solos a las 3 semanas. No tienen "
    "fecha de entrega, asi que se quedaban en Pendientes para siempre y en "
    "un semestre la lista quedaba inservible.",
    "El diagnostico ya no muestra codigo crudo: ahora dice el nombre del "
    "ramo, que fallo y desde cuando.",
    "Un boton nunca puede hacer algo distinto de lo que dice. Si un boton no "
    "cabe en el limite de la plataforma, ahora no se pone; antes se "
    "recortaba y apuntaba a otra cosa.",
    "Si el disco falla al guardar, el bot avisa pero ya no se cae en la "
    "ultima linea, cuando ya tenia todo el trabajo hecho.",
    "Los mensajes viejos de confirmacion ahora se borran de verdad del chat.",

    "Ahora leo los AVISOS escritos del profe, no solo los archivos.",
    "Un aviso urgente (suspension, clase online, cambio de fecha) suena "
    "aunque el ramo este callado y aunque sea de madrugada.",
    "Nuevo boton Avisos del profe y nuevo comando /avisos.",
    "Pendientes ahora se toca: abris uno, lees tu nota, lo marcas o lo borras.",
    "Todo boton que borra, completa o posterga avisa y deja un boton "
    "Deshacer, que desaparece cuando lo usas.",
    "Borrar un pendiente ahora pregunta antes.",
    "/recordar arreglado: dos apuntes del mismo minuto ya no se pisan y "
    "tus apuntes no aparecen mas como entregas del ramo.",
    "Entiendo pedidos armados como: hazme un recordatorio de levantarme "
    "en 2 minutos. Sin gastar IA.",
    "Nuevo boton Nuevo recordatorio en la pantalla principal.",
    "El aviso de actualizacion dice la hora y ya no se pierde si el "
    "mensaje no sale: primero manda, despues anota.",
    "Arreglado el aviso de 'cambio algo y no se que' que aparecia tres "
    "veces por dia sin que hubiera nada nuevo.",
    "Si la plataforma rechaza la clave, te lo digo y no insisto, para no "
    "bloquearte la cuenta.",
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
    "Entra a Ajustes y fijate que este el boton 'Cuando te hablo'. Ahi "
    "adentro cambia el dia y la hora del resumen.",
    "Aprieta +1 hora en una entrega de un profe. Tiene que decirte que la "
    "fecha de entrega no la toco, y esa entrega NO puede aparecer duplicada "
    "en la revision siguiente.",
    "Escribile 'que pendientes tengo?' como frase suelta. Tiene que "
    "contestarte de verdad, no tirarte la lista pelada.",
    "Apreta la campanita de un ramo. Tiene que decirte hasta que dia lo "
    "callo y ofrecerte /deshacer.",
    "Pedile 'hazme un recordatorio de levantarme en 2 minutos'. Tiene que "
    "quedar en SIN REVISAR, no en PARA ENTREGAR.",
    "Corre /avisos y fijate que el mas nuevo este arriba.",

    "Escribi: hazme un recordatorio de levantarme en 2 min",
    "Manda /recordar 20 min sacar la ropa y despues abri Pendientes",
    "En Pendientes, toca uno, escribile una nota y volve a abrirlo",
    "Borra un recordatorio y apreta Deshacer",
    "Manda /avisos y mira lo que escribio el profe",
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
