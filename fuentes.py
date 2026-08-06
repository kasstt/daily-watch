# -*- coding: utf-8 -*-
"""CONFIGURACION.  Casi todo esto se puede cambiar despues desde el chat,
asi que no hace falta tocar este archivo salvo para cosas finas.

Nada de aca identifica a nadie.  Las direcciones, el usuario y la clave
viven en los Secrets, nunca en este archivo.
"""

# ---------------------------------------------------------------- fuentes
# modo "b64"   -> plataforma propia, manda la clave tambien en base64
# modo "aula"  -> plataforma educativa estandar, con token de sesion
FUENTES = [
    {
        "clave": "A",
        "modo": "b64",
        "activo": True,
        "env_url": "SITE_A_URL",
        "env_user": "SITE_A_USER",
        "env_pass": "SITE_A_PASS",
        "emoji": "\U0001F4D8",
    },
    {
        "clave": "B",
        "modo": "aula",
        "activo": True,
        "env_url": "SITE_B_URL",
        "env_user": "SITE_B_USER",
        "env_pass": "SITE_B_PASS",
        "emoji": "\U0001F4D7",
    },
]

# Enlaces privados con los plazos.  Podes poner uno por plataforma: las dos
# tienen calendario y cada una publica cosas que la otra no.  Si solo tenes
# uno, dejas el otro vacio.  Tambien se pueden meter varios enlaces en la
# misma variable, separados por coma.
ENV_AGENDA = ["CAL_URL", "CAL_URL_B"]

# ---------------------------------------------------------------- reloj
# El reloj de GitHub anda en UTC.  Nosotros decidimos todo con esta zona,
# que ya sabe sola cuando empieza y termina el horario de verano.
ZONA_HORARIA = "America/Santiago"

# Entre estas horas los avisos llegan sin sonido.  Un plazo suena igual.
SILENCIO = (0, 7)

# ---------------------------------------------------------------- avisos
# Cuantas horas antes de una entrega avisar, segun el perfil del ramo.
# "diario" = una vez por dia a la hora del resumen, hasta marcarla hecha.
PERFILES = {
    "suave":    [72, 12],
    "normal":   [72, 24, 3],
    "apretado": [168, 72, 24, 6, 2, 0.5],
    "diario":   "diario",
}
ORDEN_PERFILES = ["suave", "normal", "apretado", "diario"]
PERFIL_POR_DEFECTO = "normal"

# Resumen periodico.  Se cambia desde el panel.
RESUMEN = {"activo": True, "cada": "semana", "dia": "viernes", "hora": "20:00"}

# Latido: una linea por semana para saber que sigue vivo.
# Si un lunes no llega, algo pasa.  El silencio deja de ser ambiguo.
LATIDO_DIA = "lunes"
LATIDO_HORA = "09:00"

# Cuantos dias dura un ramo silenciado antes de volver solo.
DIAS_CALLADO = 14

# Cuantas revisiones seguidas tiene que faltar algo antes de alarmar.
# Las plataformas se reinician solas, esto evita el susto al pedo.
CONFIRMAR_FALLA = 3

MAX_POR_MENSAJE = 8
NOVEDADES_GUARDADAS = 120

# ------------------------------------------------------------- el panel
# Anclar deja un cartelito en el chat cada vez.  Apagado a proposito.
ANCLAR_PANEL = False

# ------------------------------------------------------- los adjuntos
# El bot baja el archivo y te lo manda al chat, asi no entras a la pagina
# solo para bajarlo.  En el chat pesa cero hasta que lo tocas.
ADJUNTAR = True
ADJUNTOS_POR_AVISO = 5       # cuantos archivos manda por novedad

# Cuando VOS pedis los archivos de un ramo, el alcance manda.  A fin de
# semestre "todo el ramo" son cientos de archivos, asi que por defecto va
# la ultima semana y lo demas se pide aparte.
ALCANCE_POR_DEFECTO = "semana"
DIAS_DE_ALCANCE = {"semana": 7, "mes": 30, "todo": 0}   # 0 = sin limite
ARCHIVOS_POR_TANDA = 5           # cuantos manda de una antes de respirar
PREGUNTAR_DESDE = 6              # de aca para arriba pide confirmacion
AVISAR_AVANCE_CADA = 10          # "van 20 de 63"
TOPE_ARCHIVOS_DE_UNA = 80        # techo duro, para no colgar la corrida
PESO_ADJUNTO_MB = 45         # el tope que aguanta la mensajeria es 50
ADJUNTAR_EXTENSIONES = [
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".txt", ".csv", ".zip", ".rar", ".odt", ".odp", ".ods",
]

# Si no marcaste una cosa como vista, te lo recuerda una vez, a las tantas
# horas.  Una sola vez: no es una alarma, es un empujoncito.
HORAS_PARA_RECORDAR_VISTO = 20

# ------------------------------------------------------- chat limpio
# El bot borra lo que no aporta: tus comandos, los toques de la botonera y
# sus propias confirmaciones cortas.  Los avisos de material NUNCA se borran.
LIMPIAR_CHAT = True
SEGUNDOS_BASURA = 25         # cuanto queda a la vista una confirmacion
SEGUNDOS_MIS_MENSAJES = 5    # cuanto queda a la vista lo que escribis vos
TECLADO_FIJO = True          # la botonera de abajo. Se prende con /atajos

# ---------------------------------------------------------------- ritmo
# La ventana despierta.  Mientras el bot esta despierto escucha el chat sin
# cortar, y los botones contestan en un segundo.  Fuera de la ventana solo
# se asoma cada tanto, revisa y se vuelve a dormir.
# Son horas locales.  (7, 2) es de las 7 de la manana a las 2 de la madrugada.
DESPIERTO = (7, 2)
HORAS_MAXIMAS = 5.5          # lo maximo que dura un turno seguido
MINUTOS_DORMIDO = 4          # cuanto vive una corrida fuera de la ventana

# --------------------------------------------------- que tan adentro mira
# La portada del ramo casi nunca muestra el archivo: muestra la actividad,
# y el archivo esta adentro.  Por eso entra un nivel mas.
PROFUNDIDAD = 1                  # cuantos niveles entra dentro del ramo
PAGINAS_POR_RAMO = 14            # tope de paginas por ramo, para no abusar
MINUTOS_EXPLORACION_PROFUNDA = 20  # cada cuanto vuelve a entrar adentro
TOPE_PRIMERA_TANDA = 10          # si la primera mirada honda trae mas, no grita

# El ultimo seguro: si la pagina del ramo cambio y no supe decir en que,
# igual te aviso.  Vale mas un aviso de mas que perderte una guia.
AVISAR_CAMBIO_CIEGO = True
# Antes esto era 6 y avisaba tres veces por dia por nada, porque la pagina
# cambia sola.  Ahora, como maximo, uno por dia y solo si el cambio se
# repite en dos revisiones seguidas.
HORAS_ENTRE_AVISOS_CIEGOS = 24
REVISIONES_PARA_AVISO_CIEGO = 2

SEGUNDOS_ENTRE_REVISIONES = 90   # cada cuanto mira las plataformas
ESPERA_CHAT = 20             # cuanto se queda escuchando el chat de una
ESPERA_RED = 25

# ---------------------------------------------------------------- IA
# proveedor: "gemini", "compatible" o "ninguno"
# "compatible" sirve para cualquier servicio que hable el formato de OpenAI,
# que hoy son casi todos.  Mudarse son estas tres lineas y una clave nueva.
IA = {
    "proveedor": "gemini",
    "modelo": "gemini-2.0-flash",
    # Si el de arriba no existe para tu clave, prueba estos, en orden.
    "modelos_de_repuesto": ["gemini-2.5-flash", "gemini-flash-latest",
                            "gemini-1.5-flash"],
    "url": "",                    # solo para "compatible"
    "largo_corto": 220,           # lo que se ve sin desplegar
    "largo_ampliado": 700,        # lo que aparece al tocar "mostrar mas"
    # Si el trabajo trae varios archivos, el resumen puede crecer.  Suma
    # esto por cada archivo de mas, hasta el techo.
    "extra_por_archivo": 300,
    "techo_ampliado": 1900,
    # Cuando le hablas vos, sin "/": puede explayarse un poco mas.
    "largo_charla": 900,
    "techo_charla": 1800,
    "archivos_maximos": 4,        # cuantos adjuntos entran en un resumen
    "paginas_maximas": 20,
    "peso_maximo_mb": 18,
    "fallas_para_apagar": 5,      # se cuenta POR CLAVE, no para todo el sistema
    "ramos_sin_ia": [],           # nombres o pedazos de nombre
    "tokens_maximos": 1200,       # para que no corte una frase a la mitad
    # Varias claves, en orden de preferencia.  La primera es la titular, las
    # otras son repuesto.  Alcanza con crear el Secret IA_KEY_2 y listo.
    "claves_env": ["IA_KEY", "IA_KEY_2", "IA_KEY_3", "IA_KEY_4", "IA_KEY_5"],
    "env_lista": "IA_KEYS",       # o todas juntas aca, separadas por coma
    # Cuanto descansa una clave segun por que fallo.
    "descanso_cupo_minutos": 60,  # se paso del cupo o le pegamos muy seguido
    "descanso_red_minutos": 5,    # se cayo el servicio o no hubo internet
    "cupo_hasta_manana": True,    # si se agoto el cupo del dia, hasta el otro dia
}

# Las etapas de la animacion.  Son reales, no relleno: si se traba en una,
# ya sabes donde esta el problema.
# Sin emoji a proposito: el cerebro va arriba, en el titulo, y abajo solo
# texto.  Dos emoji uno encima del otro quedan feos.
ETAPAS = {
    "buscando":   "buscando el material",
    "bajando":    "bajando %s",
    "leyendo":    "leyendo %s",
    "pensando":   "ordenando las ideas",
    "resumiendo": "resumiendo",
    "puliendo":   "puliendo",
}
ORDEN_ETAPAS = ["buscando", "bajando", "leyendo", "pensando", "resumiendo", "puliendo"]

# Relleno honesto para que la espera se sienta viva.  Van rotando abajo de
# la etapa real, con los puntos suspensivos moviendose.  No mienten sobre
# lo que esta pasando, solo acompanan.
FRASES = [
    "esto tarda un toque",
    "segui en lo tuyo",
    "ya casi",
    "aguantame",
    "laburando",
]
# Cuarta queja sobre lo mismo: tiene que sentirse una carga, no algo que va
# a explotar.  Todo lo que se mueva en el bot sale de estos tres numeros y de
# ningun numero suelto escrito a mano en otro archivo.
ANIM_SEGUNDOS = 9.0      # cada cuanto se mueve el texto
ANIM_PUNTOS = 3          # llega a tres puntos y vuelve a cero
ANIM_CADA_FRASE = 5      # las frases rotan mas lento que los puntos

# Cuando el recordatorio es tuyo (lo pediste con /recordar o hablando), suena
# UNA sola vez, a la hora que pediste.  Los perfiles de insistencia son para
# las entregas de los profesores, no para tus apuntes.
AVISOS_DE_MIS_RECORDATORIOS = [0]

# ---------------------------------------------------------------- filtros
# Ojo: aca NO va "#".  Un ancla suelta ya se descarta sola, y poner "#"
# tiraba a la basura cualquier direccion que tuviera un ancla al final,
# que es justo como algunas plataformas enlazan el material nuevo.
IGNORAR = [
    "/session/", "/perfil", "/logout", "/login", "/alumnos",
    "/calificaciones", "/meeting/", "/cursos/publicos",
    "/calendario", "/organizarcarpetas", "/crear_modulo",
]

PALABRAS_MENU = [
    "inicio", "cursos", "mis cursos", "portada", "portada del curso",
    "calendario", "calendario del curso", "participantes", "ver todos",
    "volver", "salir", "cerrar sesion", "cerrar sesi\u00f3n",
    "mi perfil", "mi bodega", "calificaciones", "notas", "videochat",
    "ayuda", "buscar", "siguiente", "anterior", "subir", "imprimir",
]

PALABRAS_TAREA = ["tarea", "trabajo", "entrega", "evaluacion",
                  "assign", "quiz", "cuestionario", "informe", "control"]

# Cosas que se agrupan en un solo aviso si aparecen juntas en el mismo ramo
# dentro de esta ventana.  Un trabajo con 3 PDF es UN aviso, no cuatro.
MINUTOS_PARA_AGRUPAR = 30

# ------------------------------------------------- clases por video
# Son pocas al semestre pero son las que no se pueden perder.  Por eso una
# clase por videoconferencia rompe todas las reglas: avisa aunque el ramo
# este silenciado y suena aunque sea de madrugada.
AVISAR_CLASES = True
CLASES_ROMPEN_SILENCIO = True    # avisa aunque el ramo este callado
CLASES_SUENAN_DE_NOCHE = True    # y suena aunque sea la franja silenciosa
CLASES_SIN_ENLACE = True         # tambien avisa si solo lo dice con palabras
HORAS_PARA_REPETIR_CLASE = 0     # 0 = nunca repite, se avisa una sola vez

# ------------------------------------------- el reloj de GitHub
# GitHub apaga solo el horario programado de un repositorio que lleva 60
# dias quieto.  En vacaciones eso pasa seguro.  A los 50 avisa, y si puede
# lo arregla solo moviendo un archivito de latido.
REVISAR_RELOJ = True
DIAS_PARA_AVISAR_QUIETO = 50
DIAS_QUE_APAGA_GITHUB = 60
DESPERTAR_RELOJ_SOLO = True      # si puede, lo arregla sin molestarte
HORA_REVISAR_RELOJ = "10:00"     # una vez por dia alcanza y sobra

# --------------------------------------------------- compartir material
# De fabrica NO se comparte nada.  Vos abris ramo por ramo y persona por
# persona.  Lo que llega de otras secciones no es prioridad: un aviso de
# una linea y se termina ahi.
# --- avisos escritos del profesor (v5.6) ---
# Lo que el profe escribe en el tablero de Avisos. No es un enlace, es texto,
# y era lo unico importante que el bot no miraba.
AVISAR_AVISOS = True
AVISOS_ROMPEN_SILENCIO = True
AVISOS_SUENAN_DE_NOCHE = True
AVISOS_POR_TANDA = 4
AVISOS_GUARDADOS = 400

# --- deshacer (v5.6) ---
# Todo boton que borra, completa o posterga algo se puede deshacer.
PERMITIR_DESHACER = True
MINUTOS_PARA_DESHACER = 30

# ------------------------------------------------------------- v5.7
# A los cuantos dias se archiva solo un aviso del profe.  Un aviso no tiene
# fecha de entrega, asi que sin esto se quedaba en Pendientes para siempre y
# en un semestre la lista quedaba inservible.  Con 0 no se archivan nunca.
DIAS_PARA_ARCHIVAR_AVISOS = 21

# Si los avisos de nivel 2 (prueba, entrega, asistencia) tambien suenan de
# madrugada.  Va en False a proposito: si todo suena, apagas las alarmas y el
# dia que hay una suspension de verdad no te enteras.  Ponelo en True si
# preferis que te despierte cualquier aviso que hable de fechas.
IMPORTANTES_SUENAN_DE_NOCHE = False

COMPARTIR = True
COMPARTIR_DE_FABRICA = []        # ningun ramo sale solo. A proposito.
MAXIMO_PERSONAS = 12             # circulo chico y cerrado
AVISOS_DE_AFUERA_SILENCIOSOS = True   # nunca suenan
RESUMIR_LO_DE_AFUERA = True      # una linea escrita por la IA
LARGO_RESUMEN_DE_AFUERA = 180    # y corta, que no es prioridad
AGRUPAR_LO_DE_AFUERA = True      # si llegan cinco cosas, va un solo aviso
# Lo de afuera NO entra en los perfiles de insistencia ni en el
# recordatorio de "no lo viste".  Esto no se puede prender: es la regla.
GUARDADOS_DE_AFUERA = 60

# ------------------------------------------------------------- v5.8
# Cuantas horas despues de vencido se olvida un recordatorio puesto por vos.
HORAS_PARA_OLVIDAR_MIO = 12

# La memoria guarda una huella por cada cosa vista.  Sin tope crecia para
# siempre: el gist se hacia gigante, tardaba en subir y un dia deja de subir.
# Un ano de huellas alcanza de sobra para no volver a avisar lo mismo.
DIAS_PARA_PODAR_HUELLAS = 400

# Cuantos pendientes ya cerrados se conservan.  Los viejos no le sirven a
# nadie y solo hacen mas pesada la memoria.
PENDIENTES_CERRADOS_GUARDADOS = 300


# ---------------------------------------------------------------- v5.9
# Como llega el material cuando pedis los archivos de un ramo.
# "auto": pocos archivos llegan sueltos, en su formato de siempre, y muchos
# llegan juntos en un solo paquete para no tapar el chat.
# "suelto": siempre uno por uno.   "paquete": siempre todo junto.
MODO_ENVIO_MATERIAL = "auto"
SUELTOS_HASTA = 4                # hasta esta cantidad van sueltos
NOMBRE_DEL_PAQUETE = "material"  # se le suma el ramo y la fecha

# Cuando el enlace no dice si es un archivo o una pagina, le preguntamos al
# servidor antes de decir que no hay nada.  Esto es lo que hacia que un ramo
# lleno de material apareciera vacio.
COMPROBAR_DUDOSOS = True
DUDOSOS_POR_PEDIDO = 25          # cuantos comprueba de una, para no colgarse
HORAS_QUE_VALE_LA_COMPROBACION = 72

# El dueño eligio: insistir hasta que lo marque visto, no un empujon solo.
INSISTIR_HASTA_VISTO = True
VECES_PARA_RECORDAR_VISTO = 4    # tope de empujones por cosa, para no cansar

# Primer arranque con la memoria vacia: un resumen corto de lo que encontro.
RESUMEN_DE_PRIMERA_VEZ = True
COSAS_EN_EL_RESUMEN_INICIAL = 8


# =====================================================================
#  v6.0 - lo que se aprendio mirando la plataforma de verdad
# =====================================================================

# Una de las plataformas publica un boton "Descargar Todo" que entrega UN
# solo archivo comprimido con todo el modulo adentro.  Si el bot te lo
# mandaba tal cual, pedias dos apuntes y recibias algo que hay que abrir en
# el computador.  Con esto el bot lo abre por vos y te manda lo de adentro.
DESARMAR_PAQUETES = True

# Si adentro del paquete hay mas que esto, te lo dejo cerrado: son
# demasiados mensajes seguidos.
ARCHIVOS_DE_UN_PAQUETE = 25

# Quien puede usar el bot.  Con esto en True, cualquiera que le escriba y no
# este autorizado queda afuera, y a vos te llega el aviso con los botones
# para dejarlo entrar o bloquearlo.
SOLO_GENTE_AUTORIZADA = True
AVISAR_DESCONOCIDOS = True
MAXIMO_AUTORIZADOS = 8
# Cuantas veces te aviso del MISMO desconocido antes de callarme (para que
# nadie te pueda llenar el chat escribiendole al bot).
AVISOS_POR_DESCONOCIDO = 1

# Cuantos minutos antes de una clase por videoconferencia queres
# el recordatorio.  Es el aviso que llega cuando todavia se puede
# hacer algo: el de la vispera se pierde entre los mensajes.
MINUTOS_ANTES_DE_LA_CLASE = 10
