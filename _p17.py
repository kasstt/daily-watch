# -*- coding: utf-8 -*-
"""La tanda de pruebas de la v5.5.

Tres cosas nuevas y ninguna se puede probar en la plataforma de verdad sin
esperar meses, asi que todo se prueba aca, en seco:

  1. Las clases por videoconferencia (punto 8).
  2. El reloj de GitHub y el aviso a los 50 dias (punto A3).
  3. Compartir material, cifrado de claves y duplicados (puntos B3 y C2).

No toca internet, no necesita claves y no manda un solo mensaje de verdad.
Se corre con:  python3 _p17.py
"""
import datetime as dt
import os
import sys

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("CLAVE_COMPARTIR", "llave-de-prueba-nada-real")

import clases as CL          # noqa: E402
import comandos as C         # noqa: E402
import compartir as CO       # noqa: E402
import fuentes as CFG        # noqa: E402
import ia as IA              # noqa: E402
import notificar as N        # noqa: E402
import panel as P            # noqa: E402
import salud as S            # noqa: E402
import version as VER        # noqa: E402
import watcher as W          # noqa: E402

FALLOS = []


def ok(cond, que):
    if cond:
        print("  ok   %s" % que)
    else:
        print("  FALLA %s" % que)
        FALLOS.append(que)


def titulo(t):
    print("\n== %s" % t)


# ------------------------------------------------- el chat, de mentira
MANDADOS = []


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append({"texto": texto, "silencioso": silencioso,
                     "botones": botones})
    return len(MANDADOS)


def _editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    MANDADOS.append({"texto": texto, "silencioso": True, "botones": botones})
    return mensaje_id


def _nada(*a, **k):
    return True


N.enviar = _enviar
N.editar = _editar
N.borrar = _nada
N.anclar = _nada
N.desanclar = _nada
N.avisar_boton = _nada
N.mandar_documento = lambda *a, **k: True
N.mandar_archivo = lambda *a, **k: True
N.publicar_menu = _nada
N.quitar_teclado = _nada


def limpiar():
    del MANDADOS[:]


def ultimo():
    return MANDADOS[-1]["texto"] if MANDADOS else ""


def todo_lo_mandado():
    return "\n".join(m["texto"] for m in MANDADOS)


def filas_de(b):
    if not b:
        return []
    return (b or {}).get("inline_keyboard", [])


def datos_de_botones(b):
    return [x.get("callback_data", "") for fila in filas_de(b) for x in fila]


# OJO: la maquina anda en UTC y el bot en la zona de Chile.  Si se usa
# datetime.now() las fechas se van un dia y las pruebas fallan sin motivo.
HOY = W.ahora()
CLAVE = "A:1"
OTRA = "A:2"


def bot_de_prueba():
    b = W.Vigilante.__new__(W.Vigilante)
    b.estado = {
        "items": {}, "grupos": {
            CLAVE: {"nombre": "C\u00e1lculo", "emoji": "\U0001F4D8",
                    "fuente": "A", "id": "1", "url": "", "visto": "",
                    "cantidad": 0},
            OTRA: {"nombre": "Contabilidad", "emoji": "\U0001F4D8",
                   "fuente": "A", "id": "2", "url": "", "visto": "",
                   "cantidad": 0},
        },
        "tareas": {}, "novedades": [], "avisos": {}, "callados": {},
        "perfiles": {}, "fallas": {}, "ausentes": {}, "archivados": {},
        "pendientes_ia": [], "config": {}, "tg_offset": 0,
        "esperando_nota": None, "_chat": "9999",
    }
    b.sesiones = {}
    b.bases = {}
    b.cache = {}
    b.modo = "gist"
    b.gist_nuevo = False
    b.guardar = lambda *a, **k: None
    return b


# =====================================================================
titulo("1. clases por videoconferencia: reconocer las salas")

CASOS_SI = [
    ("https://meet.google.com/abc-defg-hij", "Meet"),
    ("https://us02web.zoom.us/j/8412345678?pwd=xx", "Zoom"),
    ("https://teams.microsoft.com/l/meetup-join/19%3ameeting_x", "Teams"),
    ("https://meet.jit.si/ClaseDeCalculo", "Jitsi"),
    ("https://empresa.webex.com/meet/profesor", "Webex"),
    ("https://join.skype.com/abc123", "Skype"),
]
for url, marca in CASOS_SI:
    ok(CL.marca_de(url) == marca, "reconoce %s en %s" % (marca, url[:40]))

CASOS_NO = [
    "https://plataforma.local/curso/1/modulo/9/archivo/3",
    "https://plataforma.local/pluginfile.php/1/mod_resource/guia.pdf",
    "https://www.youtube.com/watch?v=xxxx",
    "",
]
for url in CASOS_NO:
    ok(not CL.es_sala(url), "NO confunde con sala: %r" % url[:45])

ok(CL.marca_de("https://plataforma.local/b/sala-de-clases") == "",
   "el atajo /b/ solo no alcanza para ser sala")
ok(CL.marca_de("https://bbb.plataforma.local/b/abc-123") == "Sala virtual",
   "pero /b/ con bbb adelante s\u00ed")


titulo("2. clases: sacar el enlace del texto del profesor")

texto_profe = ("Estimados, la clase del jueves ser\u00e1 por videoconferencia. "
               "El enlace es https://meet.google.com/qwe-rtyu-iop y empieza "
               "puntual.")
enlaces = CL.enlaces_de_video(texto_profe)
ok(enlaces == ["https://meet.google.com/qwe-rtyu-iop"],
   "saca el enlace de adentro del aviso")

ok(CL.enlaces_de_video("entren a www.zoom.us/j/999888777 a las 10")
   == ["https://www.zoom.us/j/999888777"],
   "le pone https a una direcci\u00f3n escrita sin protocolo")

ok(CL.enlaces_de_video("vayan a https://meet.google.com/aaa-bbb-ccc.")
   == ["https://meet.google.com/aaa-bbb-ccc"],
   "no se traga el punto final de la oraci\u00f3n")

dos = CL.enlaces_de_video("https://meet.google.com/a-b-c y "
                          "https://meet.google.com/a-b-c de nuevo")
ok(len(dos) == 1, "no repite el mismo enlace dos veces")


titulo("3. clases: decidir si es clase o no")

ficha = CL.detectar("Clase por Meet", "https://meet.google.com/x-y-z", "")
ok(ficha and ficha["clase"] and ficha["seguro"], "con enlace: es clase y es segura")
ok(ficha["sala"] == "Meet", "y dice que es un Meet")

ficha2 = CL.detectar("Aviso", "https://plataforma.local/curso/1/aviso/4",
                     "La clase del martes ser\u00e1 clase online, despu\u00e9s paso "
                     "el enlace.")
ok(ficha2 and ficha2["clase"], "sin enlace pero con palabras: igual la detecta")
ok(ficha2 and not ficha2["seguro"], "y la marca como no segura")

ficha3 = CL.detectar("Gu\u00eda 4", "https://plataforma.local/archivo/9.pdf",
                     "Ejercicios resueltos del cap\u00edtulo 2")
ok(ficha3 is None, "un PDF com\u00fan no es una clase")

ficha4 = CL.detectar("Aviso importante", "https://plataforma.local/aviso/1",
                     "Se suspende la clase del jueves por paro.")
ok(ficha4 and ficha4["suspension"], "detecta una suspensi\u00f3n")
ok(ficha4 and not ficha4["clase"], "y una suspensi\u00f3n sola no es una clase")

ficha5 = CL.detectar("Cambio", "https://meet.google.com/n-u-e",
                     "Se reprograma la clase, ahora es por este enlace.")
ok(ficha5 and ficha5["clase"] and ficha5["suspension"],
   "clase nueva y aviso de cambio a la vez")

ok(CL.prioritaria(ficha) is True, "una clase con enlace es prioritaria")
ok(CL.prioritaria(ficha2) is False, "una sin enlace no rompe el silencio")
ok(CL.prioritaria(None) is False, "nada no es prioritario")


titulo("4. clases: el filtro de enlaces no se las come")

ok("/meeting/" in CFG.IGNORAR, "la lista de ignorados sigue teniendo /meeting/")
ok(W.ignorar("https://plataforma.local/meeting/chat/22") is True,
   "el chat interno se sigue ignorando")
ok(W.ignorar("https://meet.google.com/abc-defg-hij") is False,
   "pero una sala de verdad NO se ignora")
ok(W.ignorar("https://plataforma.local/mod/bigbluebuttonbn/view.php?id=9") is False,
   "la sala virtual de la plataforma B tampoco se ignora")


titulo("5. clases: el aviso que llega al chat")

b = bot_de_prueba()
limpiar()
frescos = [{"titulo": "Clase por videoconferencia",
            "url": "https://meet.google.com/abc-defg-hij",
            "tipo": "archivo", "descripcion": "Nos vemos el jueves a las 10."}]
cuantas = b.clases_nuevas(CLAVE, "C\u00e1lculo", frescos, HOY)
ok(cuantas == 1, "avisa la clase una vez")
ok("Clase por Meet" in ultimo(), "el t\u00edtulo dice que es un Meet")
ok("C\u00e1lculo" in ultimo(), "dice de qu\u00e9 ramo es")
ok("meet.google.com" in ultimo(), "y trae el enlace para entrar")

cuantas2 = b.clases_nuevas(CLAVE, "C\u00e1lculo", frescos, HOY)
ok(cuantas2 == 0, "la misma clase no se avisa dos veces")


titulo("6. clases: rompen el silencio del ramo")

b = bot_de_prueba()
b.estado["callados"][CLAVE] = {"hasta": (HOY + dt.timedelta(days=30)
                                        ).strftime("%Y-%m-%d"),
                              "cuenta": 0}
ok(b.callado(CLAVE) is True, "el ramo qued\u00f3 callado de verdad")
limpiar()
b._avisar(CLAVE, [{"titulo": "Clase por Zoom",
                   "url": "https://us02web.zoom.us/j/8412345678",
                   "tipo": "archivo", "descripcion": ""}])
ok(any("Zoom" in m["texto"] for m in MANDADOS),
   "con el ramo silenciado, la clase igual avisa")

b2 = bot_de_prueba()
b2.estado["callados"][CLAVE] = {"hasta": (HOY + dt.timedelta(days=30)
                                          ).strftime("%Y-%m-%d"),
                               "cuenta": 0}
limpiar()
b2._avisar(CLAVE, [{"titulo": "Gu\u00eda 7", "url": "https://plataforma.local/g7.pdf",
                    "tipo": "archivo", "descripcion": ""}])
ok(not MANDADOS, "pero un PDF com\u00fan en un ramo callado NO avisa")


titulo("7. el reloj de GitHub: la cuenta de los d\u00edas")

ok(S.dias_quieto("2026-06-01T10:00:00Z",
                 dt.datetime(2026, 7, 21, 9, 0)) == 50,
   "del 1 de junio al 21 de julio son 50 d\u00edas")
ok(S.dias_quieto("2026-08-03T10:00:00Z",
                 dt.datetime(2026, 8, 3, 23, 0)) == 0,
   "el mismo d\u00eda son 0")
ok(S.dias_quieto("", HOY) is None, "sin fecha no inventa un n\u00famero")
ok(S.dias_quieto("cualquier cosa", HOY) is None, "con basura tampoco")
ok(S.dias_quieto("2026-08-10T10:00:00Z",
                 dt.datetime(2026, 8, 3)) == 0,
   "una fecha futura no da negativo")

ok(S.leer_fecha_github("2026-06-01T10:00:00Z") is not None,
   "lee el formato de GitHub")
ok(S.leer_fecha_github("2026-06-01T10:00:00+00:00") is not None,
   "y tambi\u00e9n con la zona escrita aparte")


titulo("8. el reloj: cu\u00e1ndo avisar y cu\u00e1ndo callarse")

ok(S.hay_que_avisar(49, "", HOY) is False, "a los 49 d\u00edas no molesta")
ok(S.hay_que_avisar(50, "", HOY) is True, "a los 50 avisa")
ok(S.hay_que_avisar(58, "", HOY) is True, "a los 58 tambi\u00e9n")
ok(S.hay_que_avisar(None, "", HOY) is False, "si no sabe, no avisa")
ok(S.hay_que_avisar(52, HOY.strftime("%Y-%m-%d"), HOY) is False,
   "si ya avis\u00f3 hoy, no repite")
ok(S.hay_que_avisar(52, (HOY - dt.timedelta(days=8)).strftime("%Y-%m-%d"),
                    HOY) is True,
   "pero a los 8 d\u00edas lo recuerda una vez")
ok(S.hay_que_avisar(52, "fecha rota", HOY) is True,
   "si la fecha guardada est\u00e1 rota, avisa igual")

texto = S.texto_del_aviso(52, 60)
ok("52" in texto and "8" in texto, "el aviso dice los d\u00edas y los que faltan")
ok("Despertar el reloj" in texto, "y dice qu\u00e9 bot\u00f3n tocar")
ok("60" in texto, "y a los cu\u00e1ntos se apaga")


titulo("9. el reloj: la revisi\u00f3n completa, sin internet")

estado = {}
quieto = (HOY - dt.timedelta(days=55)).strftime("%Y-%m-%dT%H:%M:%SZ")
tocado = {"veces": 0}


def falso_consultar():
    return quieto, ""


def falso_tocar():
    tocado["veces"] += 1
    return True, ""


texto, botones = S.revisar(estado, HOY, consultar_fn=falso_consultar,
                           tocar_fn=falso_tocar)
ok(bool(texto), "a los 55 d\u00edas dice algo")
ok(tocado["veces"] == 1, "y lo arregla solo, sin molestarte")
ok("Ya lo resolv" in texto, "el mensaje avisa que ya est\u00e1 resuelto")
ok(estado.get("repo_dias") == 0, "y la cuenta vuelve a cero")

texto2, _ = S.revisar(estado, HOY, consultar_fn=falso_consultar,
                      tocar_fn=falso_tocar)
ok(texto2 == "", "no vuelve a avisar el mismo d\u00eda")

estado3 = {}
texto3, botones3 = S.revisar(
    estado3, HOY, consultar_fn=falso_consultar,
    tocar_fn=lambda: (False, "la llave no alcanza"))
ok("no pude" in texto3, "si no lo puede arreglar, lo dice")
ok("a:tocar" in str(botones3), "y deja el bot\u00f3n para hacerlo a mano")

estado4 = {}
texto4, _ = S.revisar(estado4, HOY,
                      consultar_fn=lambda: ((HOY - dt.timedelta(days=3)
                                             ).strftime("%Y-%m-%dT%H:%M:%SZ"), ""),
                      tocar_fn=falso_tocar)
ok(texto4 == "", "con 3 d\u00edas quieto no dice nada")
ok(estado4.get("repo_dias") == 3, "pero igual anota los d\u00edas")

estado5 = {}
texto5, _ = S.revisar(estado5, HOY,
                      consultar_fn=lambda: ("", "no tengo la llave de GitHub"),
                      tocar_fn=falso_tocar)
ok("no pude revisar" in texto5.lower(), "si no puede preguntar, lo dice una vez")
texto6, _ = S.revisar(estado5, HOY,
                      consultar_fn=lambda: ("", "no tengo la llave de GitHub"),
                      tocar_fn=falso_tocar)
ok(texto6 == "", "y no lo repite todos los d\u00edas")

ok("Reloj de GitHub" in S.linea_de_estado(estado), "aparece en el diagn\u00f3stico")


titulo("10. el reloj: enganchado al bot")

b = bot_de_prueba()
limpiar()
S_consultar = S.consultar
S_tocar = S.tocar
S.consultar = falso_consultar
S.tocar = lambda *a, **k: (True, "")
try:
    b.estado["ultimo_reloj"] = ""
    salida = b.revisar_reloj(forzado=True)
    ok(bool(salida), "el bot revisa el reloj y avisa")
    ok(any("resolv" in m["texto"] for m in MANDADOS), "y el aviso sale al chat")

    limpiar()
    b.accion("tocar")
    ok(any("mov\u00ed el repositorio" in m["texto"] for m in MANDADOS),
       "el bot\u00f3n Despertar el reloj contesta")

    ok("Reloj de GitHub" in b.texto_diagnostico(),
       "el diagn\u00f3stico muestra el reloj")
finally:
    S.consultar = S_consultar
    S.tocar = S_tocar


titulo("11. compartir: el cifrado de las claves")

secreto = "clave-de-prueba-que-no-existe-1234567890"
paquete = CO.cifrar(secreto)
ok(secreto not in paquete, "la clave no se ve dentro del paquete")
ok(CO.descifrar(paquete) == secreto, "y se puede volver a abrir")

uno = CO.cifrar(secreto)
otro = CO.cifrar(secreto)
ok(uno != otro, "dos veces la misma clave dan paquetes distintos")
ok(CO.descifrar(uno) == CO.descifrar(otro) == secreto,
   "pero las dos abren en lo mismo")

adulterado = paquete[:-4] + ("aaaa" if not paquete.endswith("aaaa") else "bbbb")
ok(CO.descifrar(adulterado) == "", "si alguien lo toca, no abre")
ok(CO.descifrar(paquete, "otra llave distinta") == "",
   "con la llave equivocada tampoco")
ok(CO.descifrar("cualquier basura") == "", "con basura no revienta, devuelve vac\u00edo")
ok(CO.descifrar("") == "", "con vac\u00edo tampoco revienta")

largo = "x" * 5000
ok(CO.descifrar(CO.cifrar(largo)) == largo, "aguanta un texto largo")
acentos = "clave-con-\u00f1-y-tildes-\u00e1\u00e9\u00ed"
ok(CO.descifrar(CO.cifrar(acentos)) == acentos, "y acentos y e\u00f1es")


titulo("12. compartir: la clave no se puede ver ni listar")

estado = {}
bien, motivo = CO.guardar_clave(estado, "555", secreto)
ok(bien, "guarda la clave de una persona")
ok(CO.hay_clave(estado, "555"), "y sabe que la tiene")

volcado = repr(estado)
ok(secreto not in volcado, "la clave NO aparece en la memoria en claro")
ok(secreto not in CO.resumen_de_claves(estado),
   "ni en el resumen que se muestra")
ok("555" not in CO.resumen_de_claves(estado),
   "el resumen no dice ni de qui\u00e9n es")
ok("1 persona" in CO.resumen_de_claves(estado), "solo dice cu\u00e1ntas hay")
ok(CO.usar_clave(estado, "555") == secreto,
   "el bot s\u00ed la puede usar para hablar con la IA")
ok(CO.usar_clave(estado, "otro") == "", "de alguien que no existe, vac\u00edo")

ok(CO.guardar_clave(estado, "555", "corta")[0] is False,
   "no acepta una clave demasiado corta")
ok(CO.guardar_clave(estado, "555", "clave con espacios adentro")[0] is False,
   "ni una que venga cortada con espacios")
ok(CO.guardar_clave(estado, "", secreto)[0] is False, "ni sin saber de qui\u00e9n es")

ok(CO.tapada(secreto).count(secreto) == 0, "tapada nunca muestra la clave entera")
ok(CO.tapada("") == "ninguna", "y sin clave lo dice")

ok(CO.borrar_clave(estado, "555") is True, "se puede borrar")
ok(not CO.hay_clave(estado, "555"), "y despu\u00e9s ya no est\u00e1")


titulo("13. compartir: el permiso es tuyo y es por ramo")

estado = {"novedades": []}
ficha, motivo = CO.agregar(estado, "111", "Juan")
ok(ficha is not None, "se puede agregar una persona")
ok(CO.ramos_abiertos(estado, "111") == [],
   "de f\u00e1brica NO ve ning\u00fan ramo tuyo")
ok(CO.puede_ver(estado, "111", CLAVE) is False, "o sea, no ve nada")

abierto, bien = CO.alternar_ramo(estado, "111", CLAVE)
ok(abierto and bien, "le abr\u00eds un ramo")
ok(CO.puede_ver(estado, "111", CLAVE) is True, "y ahora ve ESE ramo")
ok(CO.puede_ver(estado, "111", OTRA) is False, "pero NO ve el otro")

cerrado, bien = CO.alternar_ramo(estado, "111", CLAVE)
ok(cerrado is False and bien, "se lo pod\u00e9s cerrar")
ok(CO.puede_ver(estado, "111", CLAVE) is False, "y deja de verlo en el acto")

CO.alternar_ramo(estado, "111", CLAVE)
CO.alternar_ramo(estado, "111", OTRA)
ok(len(CO.ramos_abiertos(estado, "111")) == 2, "pod\u00e9s abrirle dos")
CO.bloquear(estado, "111", True)
ok(CO.puede_ver(estado, "111", CLAVE) is False,
   "si la bloque\u00e1s, no ve nada aunque tenga ramos abiertos")
CO.bloquear(estado, "111", False)

ok(CO.cerrar_todo(estado) == 2, "el bot\u00f3n de p\u00e1nico cierra todo")
ok(CO.ramos_abiertos(estado, "111") == [], "y no queda nada abierto")

ok(CO.puede_ver(estado, "no-existe", CLAVE) is False,
   "alguien que no est\u00e1 anotado no ve nada")
ok(CO.sacar(estado, "111") is True, "se puede sacar a una persona")
ok(CO.puede_ver(estado, "111", CLAVE) is False, "y pierde el acceso al toque")


titulo("14. compartir: nunca sale nada personal")

estado = {"novedades": [
    {"f": "2026-08-01 10:00", "c": CLAVE, "g": "C\u00e1lculo",
     "t": "Gu\u00eda 3", "u": "https://plataforma.local/g3.pdf", "tipo": "archivo"},
    {"f": "2026-08-01 11:00", "c": OTRA, "g": "Contabilidad",
     "t": "Balance", "u": "https://plataforma.local/b.pdf", "tipo": "archivo"},
]}
CO.agregar(estado, "111", "Juan")
CO.alternar_ramo(estado, "111", CLAVE)

paquete = CO.paquete_para(estado, "111")
ok(len(paquete) == 1, "solo sale lo del ramo que abriste")
ok(paquete[0]["t"] == "Gu\u00eda 3", "y es el que corresponde")
ok("Balance" not in str(paquete), "lo del otro ramo NO sale")
ok(CO.revisar_fuga(paquete) == [], "el control de salida no encuentra nada raro")

sucia = {"t": "Tarea 1", "u": "x", "tipo": "tarea", "nota": "me fue mal",
         "hecho": True, "vence": "2026-08-10", "usuario": "alguien"}
limpia = CO.limpiar_item(sucia)
ok("nota" not in limpia, "la nota privada no sale")
ok("hecho" not in limpia, "si lo hiciste o no, tampoco")
ok("vence" not in limpia, "ni tus vencimientos")
ok("usuario" not in limpia, "ni tu usuario")
ok(set(limpia) <= set(CO.CAMPOS_QUE_SALEN), "solo salen los campos permitidos")

CO.bloquear(estado, "111", True)
ok(CO.paquete_para(estado, "111") == [], "a una persona bloqueada no le sale nada")
CO.bloquear(estado, "111", False)
ok(CO.paquete_para(estado, "nadie") == [], "a un desconocido tampoco")


titulo("15. compartir: reconocer los duplicados")

ok(CO.huella_de_material("Gu\u00eda 3.pdf")
   == CO.huella_de_material("guia_3.PDF"),
   "la misma gu\u00eda con otro nombre es la misma")
ok(CO.huella_de_material("Gu\u00eda 3")
   == CO.huella_de_material("Guia 3 v2"),
   "y con un n\u00famero de versi\u00f3n pegado tambi\u00e9n")
ok(CO.huella_de_material("Gu\u00eda 3")
   != CO.huella_de_material("Gu\u00eda 4"),
   "pero la gu\u00eda 4 es otra cosa")
ok(CO.huella_de_material("Certamen 1")
   != CO.huella_de_material("Certamen 2"),
   "y el certamen 2 no es el 1")


titulo("16. compartir: lo que llega de otras secciones")

estado = {"novedades": [
    {"f": "2026-08-01 10:00", "c": CLAVE, "g": "C\u00e1lculo secci\u00f3n 1",
     "t": "Gu\u00eda 3.pdf", "u": "https://plataforma.local/mio/g3.pdf",
     "tipo": "archivo"},
]}
CO.agregar(estado, "222", "Ana", HOY)

llega = [
    {"t": "guia_3.pdf", "u": "https://plataforma.local/otra/g3.pdf",
     "tipo": "archivo", "ramo": "C\u00e1lculo secci\u00f3n 2"},
    {"t": "Apunte extra de integrales", "u": "https://plataforma.local/otra/ap.pdf",
     "tipo": "archivo", "ramo": "C\u00e1lculo secci\u00f3n 2"},
]
nuevos, repetidos = CO.recibir(estado, "222", llega, HOY)
ok(repetidos == 1, "la gu\u00eda que ya ten\u00e9s cuenta como repetida")
ok(len(nuevos) == 1, "y solo se avisa lo que de verdad es nuevo")
ok(nuevos[0]["t"] == "Apunte extra de integrales", "que es el apunte extra")

guardados = estado["de_afuera"]
repe = [x for x in guardados if x["repetido"]]
ok(len(repe) == 1, "lo repetido igual se guarda, por si lo quer\u00e9s mirar")
ok(repe[0]["igual_a"] == "Gu\u00eda 3.pdf", "y dice a cu\u00e1l de los tuyos se parece")
ok(repe[0]["igual_en"] == "C\u00e1lculo secci\u00f3n 1", "y de qu\u00e9 ramo tuyo")

pantalla_afuera = CO.texto_de_afuera(estado)
ok("ya lo ten" in pantalla_afuera, "la pantalla marca el repetido")
ok("C\u00e1lculo secci\u00f3n 1" in pantalla_afuera, "y dice de d\u00f3nde lo ten\u00e9s")

nuevos2, _ = CO.recibir(estado, "222", llega, HOY)
ok(nuevos2 == [], "si lo mandan de nuevo, no vuelve a avisar")

aviso = CO.aviso_corto(nuevos)
ok("Ana" in aviso, "el aviso dice de qui\u00e9n vino")
ok("compartido" in aviso, "y que es material compartido")
ok(aviso.count("\n") == 0, "y es UNA sola l\u00ednea")

varios = CO.aviso_corto([
    {"de": "Ana", "ramo": "X", "t": "a", "u": ""},
    {"de": "Ana", "ramo": "X", "t": "b", "u": ""},
    {"de": "Ana", "ramo": "X", "t": "c", "u": ""},
    {"de": "Ana", "ramo": "X", "t": "d", "u": ""},
])
ok("4 cosas" in varios, "si llegan varias, van juntas en un aviso")

CO.bloquear(estado, "222", True)
nuevos3, _ = CO.recibir(estado, "222", [
    {"t": "algo nuevo", "u": "", "tipo": "archivo"}], HOY)
ok(nuevos3 == [], "de alguien bloqueado no entra nada")


titulo("17. lo de afuera es de segunda: sin bot\u00f3n y sin insistir")

b = bot_de_prueba()
b.estado["novedades"] = [
    {"f": "2026-08-01 10:00", "c": CLAVE, "g": "C\u00e1lculo",
     "t": "Gu\u00eda 3.pdf", "u": "https://plataforma.local/g3.pdf",
     "tipo": "archivo"}]
CO.agregar(b.estado, "333", "Pedro", HOY)
limpiar()
IA_disponible = IA.disponible
IA.disponible = lambda *a, **k: False
try:
    cuantos = b.avisar_de_afuera("333", [
        {"t": "Apunte nuevo", "u": "https://plataforma.local/x.pdf",
         "tipo": "archivo", "ramo": "C\u00e1lculo secci\u00f3n 3"},
        {"t": "guia 3.pdf", "u": "https://plataforma.local/y.pdf",
         "tipo": "archivo", "ramo": "C\u00e1lculo secci\u00f3n 3"},
    ])
finally:
    IA.disponible = IA_disponible

ok(cuantos == 1, "avisa solo lo que no ten\u00e9s")
ok(len(MANDADOS) == 1, "y manda un solo mensaje")
ok(MANDADOS[0]["silencioso"] is True, "que llega sin sonido")
ok(MANDADOS[0]["botones"] is None, "sin ning\u00fan bot\u00f3n")
salida = ultimo()
ok("basta" not in salida.lower(), "sin bot\u00f3n de dejar de recordar")
ok("silenciar" not in salida.lower(), "sin bot\u00f3n de silenciar")
ok("visto" not in salida.lower(), "y sin preguntarte si lo viste")

antes = len(b.estado.get("tareas", {}))
ok(antes == 0, "lo de afuera NO se convierte en un pendiente tuyo")
ok(not b.estado.get("avisos"), "y no entra en el sistema de insistencia")


titulo("18. las pantallas nuevas del panel")

b = bot_de_prueba()
CO.agregar(b.estado, "444", "Sof\u00eda", HOY)
acc = b._acciones()

for donde in ("p:mas", "p:comp", "p:clases", "p:afuera", "p:per:444",
              "p:ajustes", "p:raiz", "p:diag"):
    texto, botones = P.pantalla(b.estado, donde, acc)
    ok(bool(texto), "la pantalla %s dice algo" % donde)
    ok("se rompi" not in texto, "la pantalla %s no revienta" % donde)
    ok(len(filas_de(botones)) <= 6,
       "la pantalla %s no pasa de 6 filas" % donde)
    for fila in filas_de(botones):
        ok(len(fila) <= 2, "la pantalla %s no pone m\u00e1s de 2 por fila" % donde)

texto, botones = P.pantalla(b.estado, "p:ajustes", acc)
ok("p:mas" in datos_de_botones(botones), "desde Ajustes se llega a M\u00e1s")

texto, botones = P.pantalla(b.estado, "p:mas", acc)
datos = datos_de_botones(botones)
for esperado in ("p:clases", "p:comp", "p:afuera", "a:reloj", "p:ajustes"):
    ok(esperado in datos, "M\u00e1s tiene el bot\u00f3n %s" % esperado)

texto, botones = P.pantalla(b.estado, "p:per:444", acc)
datos = datos_de_botones(botones)
ok(any(d.startswith("tc:444:") for d in datos),
   "la ficha de la persona deja abrir ramos uno por uno")
ok("tq:444" in datos, "y deja sacarla")
ok(datos[-1] == "p:comp", "y el Volver va \u00faltimo")

texto, _ = P.pantalla(b.estado, "p:per:no-existe", acc)
ok("ya no est" in texto, "una persona que no existe no rompe nada")


titulo("19. los botones de compartir funcionan")

b = bot_de_prueba()
CO.agregar(b.estado, "444", "Sof\u00eda", HOY)
acc = b._acciones()

aviso, donde = P.toque(b.estado, "tc:444:" + CLAVE, acc, HOY)
ok(CO.puede_ver(b.estado, "444", CLAVE) is True, "el bot\u00f3n le abre el ramo")
ok(donde == "p:per:444", "y vuelve a la ficha de la persona")
ok("ahora ve" in aviso.lower(), "y avisa qu\u00e9 pas\u00f3")

aviso, donde = P.toque(b.estado, "tc:444:" + CLAVE, acc, HOY)
ok(CO.puede_ver(b.estado, "444", CLAVE) is False, "y el mismo bot\u00f3n se lo cierra")
ok("ya no ve" in aviso.lower(), "y tambi\u00e9n lo avisa")

aviso, donde = P.toque(b.estado, "tq:444", acc, HOY)
ok("444" not in b.estado.get("personas", {}), "el bot\u00f3n Sacar la saca")
ok(donde == "p:comp", "y vuelve a la lista")

aviso, donde = P.toque(b.estado, "tc:no-existe:" + CLAVE, acc, HOY)
ok("ya no est" in aviso.lower(), "tocar el ramo de alguien que no est\u00e1 no rompe")


titulo("20. los comandos nuevos")

nombres = [c for c, _d in C.MENU]
for esperado in ("clases", "compartir", "afuera", "reloj", "miclave"):
    ok(esperado in nombres, "/%s est\u00e1 en el men\u00fa" % esperado)
ok(len(nombres) == len(set(nombres)), "no hay comandos repetidos")

ayuda = C.texto_ayuda()
for esperado in ("clases", "compartir", "afuera", "reloj", "miclave"):
    ok(esperado in ayuda, "/%s aparece en la ayuda" % esperado)

b = bot_de_prueba()
CO.agregar(b.estado, "555", "Marcos", HOY)
acc = b._acciones()

respuesta = C._compartir(b.estado, "con Marcos c\u00e1lculo", acc)
ok(CO.puede_ver(b.estado, "555", CLAVE) is True,
   "/compartir con Marcos c\u00e1lculo le abre el ramo")
ok("ahora ve" in respuesta, "y contesta que se lo abri\u00f3")

respuesta = C._compartir(b.estado, "con Marcos c\u00e1lculo", acc)
ok(CO.puede_ver(b.estado, "555", CLAVE) is False, "y de nuevo se lo cierra")

respuesta = C._compartir(b.estado, "con Nadie c\u00e1lculo", acc)
ok("No tengo a nadie" in respuesta, "con alguien que no existe lo dice")

respuesta = C._compartir(b.estado, "con Marcos ramo-que-no-existe", acc)
ok("No encontr" in respuesta, "con un ramo que no existe tambi\u00e9n")

respuesta = C._compartir(b.estado, "", acc)
ok(bool(respuesta), "sin argumentos igual contesta algo")


titulo("21. las acciones nuevas existen de verdad")

b = bot_de_prueba()
acc = b._acciones()
for nombre in ("texto_clases", "texto_compartir", "texto_afuera", "personas",
               "ramos_abiertos", "alternar_ramo", "sacar_persona",
               "cerrar_todo", "resumen_de_claves", "nombre", "lista_ramos"):
    ok(nombre in acc, "la acci\u00f3n %s est\u00e1 conectada" % nombre)
    ok(callable(acc[nombre]), "y %s se puede llamar" % nombre)

ok(bool(acc["texto_clases"]()), "texto_clases contesta")
ok(bool(acc["texto_compartir"]()), "texto_compartir contesta")
ok(bool(acc["texto_afuera"]()), "texto_afuera contesta")
ok(bool(acc["texto_diagnostico"]()), "el diagn\u00f3stico sigue funcionando")
ok(bool(acc["tablero"]()), "el tablero sigue funcionando")


titulo("22. la configuraci\u00f3n nueva est\u00e1 puesta")

ok(CFG.DIAS_PARA_AVISAR_QUIETO == 50, "avisa a los 50 d\u00edas, como pediste")
ok(CFG.DIAS_QUE_APAGA_GITHUB == 60, "y sabe que GitHub apaga a los 60")
ok(CFG.DIAS_PARA_AVISAR_QUIETO < CFG.DIAS_QUE_APAGA_GITHUB,
   "el aviso llega ANTES del apag\u00f3n")
ok(CFG.COMPARTIR_DE_FABRICA == [], "de f\u00e1brica no se comparte ning\u00fan ramo")
ok(CFG.AVISOS_DE_AFUERA_SILENCIOSOS is True, "lo de afuera nunca suena")
ok(CFG.AVISAR_CLASES is True, "las clases por video est\u00e1n prendidas")
ok(CFG.CLASES_ROMPEN_SILENCIO is True, "y rompen el silencio")


titulo("23. la versi\u00f3n")

ok(bool(VER.VERSION) and "." in VER.VERSION, "la versi\u00f3n est\u00e1 puesta")
ok(len(VER.CAMBIOS) >= 8, "y trae la lista de cambios")
ok(len(VER.A_PROBAR) >= 5, "y qu\u00e9 probar")
b = bot_de_prueba()
ok(VER.VERSION in b.texto_version(), "el bot informa la versi\u00f3n nueva")


titulo("24. no se rompi\u00f3 nada de lo viejo")

b = bot_de_prueba()
acc = b._acciones()
limpiar()
b.estado["novedades"] = [
    {"f": HOY.strftime("%Y-%m-%d %H:%M"), "c": CLAVE, "g": "C\u00e1lculo",
     "t": "Gu\u00eda 1", "u": "https://plataforma.local/g1.pdf", "tipo": "archivo"}]
for donde in ("p:raiz", "p:ramos", "p:rec", "p:avisos", "p:nov", "p:pen",
              "p:sem", "p:ayuda", "p:perfiles", "p:version", "p:ajustes"):
    texto, botones = P.pantalla(b.estado, donde, acc)
    ok("se rompi" not in texto, "la pantalla vieja %s sigue bien" % donde)

ok(bool(b.texto_novedades()), "las novedades siguen saliendo")
ok(bool(b.texto_pendientes()), "los pendientes tambi\u00e9n")
ok(bool(b.texto_semana()), "y la semana")

b2 = bot_de_prueba()
limpiar()
b2._avisar(CLAVE, [{"titulo": "Trabajo 2", "url": "https://plataforma.local/t2",
                    "tipo": "tarea", "descripcion": "Entregar el 20 de agosto"}])
ok(len(MANDADOS) >= 1, "un aviso normal sigue llegando")
ok(len(b2.estado["tareas"]) == 1, "y sigue creando el pendiente")


# =====================================================================
print("")
if FALLOS:
    print("%d cosas fallaron:" % len(FALLOS))
    for f in FALLOS:
        print("  - %s" % f)
    sys.exit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
