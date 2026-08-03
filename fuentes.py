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
HORAS_ENTRE_AVISOS_CIEGOS = 6

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
    "fallas_para_apagar": 5,
    "ramos_sin_ia": [],           # nombres o pedazos de nombre
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
ANIM_SEGUNDOS = 6.5      # cada cuanto se mueve el texto
ANIM_PUNTOS = 3          # llega a tres puntos y vuelve a cero
ANIM_CADA_FRASE = 3      # cada cuantos movimientos cambia la frase

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
