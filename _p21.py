# -*- coding: utf-8 -*-
"""Tanda 21: lo que aparecio usando el bot de verdad, mas la sonda.

Cada prueba de aca corresponde a algo que estaba roto o faltaba en la 5.8:
las claves de repuesto que nunca llegaban al bot que corre solo, el ramo que
decia no tener archivos teniendo cuatro cosas guardadas, el material que
tardaba horas en aparecer, como llegan los archivos al chat, la insistencia
hasta marcarlo visto, el primer arranque con la memoria vacia, y que la sonda
no pueda hacer dano ni delatarte.

Se corre sola, sin internet, sin claves de verdad y sin tocar tu cuenta:
    python3 _p21.py
"""
import io
import os
import re
import shutil
import tempfile
import time
import zipfile

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("CLAVE_COMPARTIR", "llave-de-prueba-nada-real")

import datetime as dt

import fuentes as CFG
import ia as IA
import notificar as N
import panel as P
import secretos as S
import sonda as SO
import version as VER
import watcher as W

FALLOS = []


def ok(cond, que):
    if cond:
        print("  ok   %s" % que)
    else:
        print("  MAL  %s" % que)
        FALLOS.append(que)


def titulo(t):
    print("\n" + t)
    print("-" * 50)


# ------------------------------------------------- mensajeria de mentira
MANDADOS = []
DOCS = []
AVISOS_DE_BOTON = []
ENVIO_FALLA = {"si": False}
DOC_FALLA = {"paquete": False}


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append({"texto": texto, "silencioso": silencioso,
                     "botones": botones})
    if ENVIO_FALLA["si"]:
        return None
    return len(MANDADOS)


def _editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    MANDADOS.append({"texto": texto, "botones": botones, "edito": mensaje_id})
    return mensaje_id


def _mandar_documento(nombre, datos, leyenda="", silencioso=True,
                      responde_a=None):
    ficha = {"nombre": nombre, "datos": datos, "leyenda": leyenda,
             "rechazado": False}
    DOCS.append(ficha)
    if DOC_FALLA["paquete"] and str(nombre).endswith(".zip"):
        ficha["rechazado"] = True
        return None
    return len(DOCS)


def _avisar_boton(consulta_id, texto=""):
    AVISOS_DE_BOTON.append(texto or "")
    return True


def _nada(*a, **k):
    return None


N.enviar = _enviar
N.editar = _editar
N.borrar = _nada
N.anclar = _nada
N.desanclar = _nada
N.avisar_boton = _avisar_boton
N.mandar_documento = _mandar_documento
N.mandar_archivo = _nada
N.publicar_menu = _nada
N.quitar_teclado = _nada


def limpiar():
    del MANDADOS[:]
    del DOCS[:]
    del AVISOS_DE_BOTON[:]
    ENVIO_FALLA["si"] = False
    DOC_FALLA["paquete"] = False


def todo_lo_mandado():
    return "\n".join(m["texto"] or "" for m in MANDADOS)


def sin_comentarios(nombre):
    """El codigo sin comentarios. Los comentarios cuentan como era ANTES, asi
    que buscar texto con ellos adentro da falsas alarmas."""
    salida = []
    with open(nombre, "r", encoding="utf-8") as f:
        for linea in f:
            salida.append(linea.split("#", 1)[0])
    return "\n".join(salida)


def numeros_de(v):
    """5.10 es MAYOR que 5.9, aunque como texto parezca al reves."""
    return tuple(int(x) for x in re.findall(r"\d+", str(v)))


HOY = W.ahora()
CLAVE = "A:1"


def bot_de_prueba(nombre_ramo="C\u00c1LCULO INTEGRAL"):
    b = W.Vigilante.__new__(W.Vigilante)
    b.estado = {
        "items": {}, "grupos": {
            CLAVE: {"nombre": nombre_ramo, "emoji": "\U0001F4D8",
                    "fuente": "A", "id": "1", "url": "http://x/curso/1",
                    "visto": "", "cantidad": 0},
        },
        "archivados": {}, "ausentes": {}, "avisos": {}, "tareas": {},
        "perfiles": {}, "callados": {}, "novedades": [], "pendientes_ia": [],
        "config": {}, "fallas": {}, "tg_offset": 0, "avisos_vistos": {},
        "deshacer": None, "personas": {}, "clases_avisadas": {},
        "version_avisada": VER.VERSION, "version_desde": "",
        "aviso_clave": {}, "basura": [], "de_afuera": [],
    }
    b.sesiones = {}
    b.bases = {}
    b.cache = {}
    b.modo = "gist"
    b.gist_nuevo = False
    b.guardar = lambda *a, **k: None
    return b


def acc_de_prueba(b):
    acc = dict(b._acciones())
    acc["dibujar_panel"] = lambda donde=None, mid=None: None
    acc["abrir_panel"] = lambda *a, **k: None
    acc["redibujar_tarjeta"] = lambda idt=None, mid=None: None
    return acc


# ------------------------------------------------- servidor de mentira
class RespuestaFalsa(object):
    def __init__(self, tipo="application/pdf", pegado="", codigo=200):
        self.status_code = codigo
        self.headers = {"Content-Type": tipo, "Content-Disposition": pegado}
        self.text = ""
        self.content = b"x"

    def close(self):
        pass


class SesionFalsa(object):
    """Contesta lo que le digas y anota cada visita, para poder revisar que el
    bot no le pregunte lo mismo cien veces."""

    def __init__(self, respuestas=None, revienta=False, sin_head=False):
        self.respuestas = respuestas or {}
        self.revienta = revienta
        self.sin_head = sin_head
        self.visitas = []

    def head(self, url, timeout=None, allow_redirects=True):
        self.visitas.append(("head", url))
        if self.revienta or self.sin_head:
            raise IOError("no acepta esa pregunta")
        return self.respuestas.get(url) or RespuestaFalsa("text/html")

    def get(self, url, timeout=None, allow_redirects=True, stream=False):
        self.visitas.append(("get", url))
        if self.revienta:
            raise IOError("sin red")
        return self.respuestas.get(url) or RespuestaFalsa("text/html")


# ===================================================================== 1
titulo("1. las claves de repuesto tienen que llegar al bot que corre solo")

wf = open(os.path.join(".github", "workflows", "watch.yml"),
          encoding="utf-8").read()
nombres = list(CFG.IA.get("claves_env", [])) + [CFG.IA.get("env_lista", "")]
for nombre in [n for n in nombres if n]:
    ok(nombre + ":" in wf,
       "el turno automatico le pasa %s al bot" % nombre)
    ok(nombre in S.CLAVES,
       "y en tu computadora tambien se puede cargar %s" % nombre)

ok(len(CFG.IA.get("claves_env", [])) >= 3,
   "hay lugar para varias claves, no una sola")

os.environ["IA_KEY"] = "clave-de-prueba-1"
os.environ["IA_KEY_2"] = "clave-de-prueba-2"
os.environ["IA_KEY_2_PROVEEDOR"] = "compatible"
os.environ["IA_KEY_2_URL"] = "http://no-existe.local/v1/chat/completions"
las_claves = IA.claves()
ok(len(las_claves) == 2, "con dos claves cargadas ve las dos")
ok(las_claves[1].get("proveedor") == "compatible",
   "y la de repuesto puede ser de otro servicio de IA")
for v in ("IA_KEY_2", "IA_KEY_2_PROVEEDOR", "IA_KEY_2_URL"):
    os.environ.pop(v, None)


# ===================================================================== 2
titulo("2. cuando se acaba el cupo del dia no sirve reintentar cada hora")

ok(IA._es_cupo_del_dia("You exceeded your quota: requests per day"),
   "reconoce el rechazo de 'ya usaste todo lo de hoy'")
ok(IA._es_cupo_del_dia("limite por dia alcanzado"),
   "tambien si lo dice en castellano")
ok(not IA._es_cupo_del_dia("too many requests, slow down"),
   "y no confunde 'vas muy rapido' con 'se acabo el dia'")

c = {"nombre": "IA_KEY", "clave": "clave-de-prueba-1", "proveedor": "gemini"}
estado_dia = {}
IA._penitencia(estado_dia, c, "cupo", "quota exceeded: requests per day")
falta_dia = list(estado_dia["ia_claves"].values())[0]["hasta"] - time.time()
ok(falta_dia > 2 * 3600,
   "si se acabo el cupo del dia espera hasta manana, no una hora")

estado_rato = {}
IA._penitencia(estado_rato, c, "cupo", "too many requests")
falta_rato = list(estado_rato["ia_claves"].values())[0]["hasta"] - time.time()
ok(falta_rato <= CFG.IA["descanso_cupo_minutos"] * 60 + 5,
   "y si solo fue apuro, descansa un rato corto")

ok("min" in IA._en_cuanto(600), "la espera corta se dice en minutos")
ok("hora" in IA._en_cuanto(4 * 3600), "la mediana en horas")
ok("ma\u00f1ana" in IA._en_cuanto(22 * 3600), "y la larga dice 'manana'")
ok(IA._segundos_hasta_manana() > 0,
   "sabe cuanto falta para el otro dia en tu hora, no en la de afuera")


# ===================================================================== 3
titulo("3. el aviso de que no hay resumen se entiende sin saber programar")

PROVEEDORES_DE_VERDAD = dict(IA.PROVEEDORES)


def _motor_sin_cupo(texto, pdfs, c):
    raise IA.SinCupo("You exceeded your current quota, requests per day")


IA.PROVEEDORES = dict(IA.PROVEEDORES)
IA.PROVEEDORES["gemini"] = _motor_sin_cupo

estado_ia = {}
texto_error = ""
try:
    IA._pedir(estado_ia, "resumime esto")
except RuntimeError as e:
    texto_error = str(e)

ok(texto_error, "cuando no hay ninguna clave que ande, avisa")
ok("clave de repuesto" in texto_error,
   "con una sola clave le dice que una segunda le arreglaria el problema")
for jerga in ("clave 1", "429", "quota", "Exception", "None", "RuntimeError",
              "SinCupo", "IA_KEY"):
    ok(jerga not in texto_error, "el aviso no dice '%s'" % jerga)
ok(estado_ia.get("ia_sin_claves"), "y queda anotado que se quedo sin claves")

b = bot_de_prueba()
b.estado["ia_claves"] = estado_ia["ia_claves"]
b.estado["ultimo_error_ia"] = texto_error
mensaje = b.por_que_no_hay_ia()
ok("cupo" in mensaje.lower(), "en el chat explica que se acabo el cupo")
ok("ma\u00f1ana" in mensaje, "y dice cuando vuelve")
ok("Prob\u00e1 de nuevo en un rato" not in mensaje,
   "sin prometerle que en un rato anda, cuando en realidad es manana")
for jerga in ("clave 1", "IA_KEY", "Secrets", "None"):
    ok(jerga not in mensaje, "el mensaje del chat no dice '%s'" % jerga)

ok("manana" in W.pelado(IA.cuando_vuelve(b.estado)),
   "la version corta tambien avisa que vuelve manana")
IA.PROVEEDORES = dict(PROVEEDORES_DE_VERDAD)
os.environ.pop("IA_KEY", None)


# ===================================================================== 4
titulo("4. un enlace de material sin extension ya no se tira a la basura")

b = bot_de_prueba()
ok(W.es_bajable("http://x/mod/resource/view.php?id=9"),
   "el enlace tipico del material de la plataforma cuenta como archivo")
ok(not W.es_bajable("http://x/mod/page/view.php?id=9"),
   "una pagina cualquiera no cuenta")
ok(b._dudoso("http://x/mod/page/view.php?id=9"),
   "pero queda en duda, para preguntarle al servidor")
ok(not b._dudoso("http://x/apunte.pdf"),
   "y lo que ya se sabe que es archivo no se pregunta al vicio")

ok(W._es_del_ramo("http://x/mod/page/view.php?id=5", "http://x", "77"),
   "entra a las actividades del ramo aunque el enlace no repita su numero")
ok(not W._es_del_ramo("http://otro/mod/page/view.php?id=5", "http://x", "77"),
   "y no se va a pasear a otro sitio")

W._ULTIMO_PROFUNDO.clear()
ok(W._toca_profundo("77", "firma-1", vacio=True)
   and W._toca_profundo("77", "firma-1", vacio=True),
   "un ramo donde no se ve ni un archivo se revisa por dentro siempre")
ok(not W._toca_profundo("77", "firma-1"),
   "y uno que ya tiene material no se revisa a cada rato")
W._ULTIMO_PROFUNDO.clear()


# ===================================================================== 5
titulo("5. cuando el enlace no dice de que es, le pregunta al servidor")

b = bot_de_prueba()
ARCH = "http://x/mod/page/view.php?id=11"
PAG = "http://x/mod/page/view.php?id=22"
servidor = SesionFalsa({ARCH: RespuestaFalsa("application/pdf"),
                        PAG: RespuestaFalsa("text/html; charset=utf-8")})
b.sesiones = {"A": servidor}
dudosos = [{"url": ARCH, "titulo": "Gu\u00eda 1"},
           {"url": PAG, "titulo": "Foro de consultas"}]
salida = b.comprobar_dudosos(CLAVE, dudosos)
ok([x["url"] for x in salida] == [ARCH],
   "el que esconde un archivo entra, el que es una pagina no")

visitas = len(servidor.visitas)
salida2 = b.comprobar_dudosos(CLAVE, dudosos)
ok(len(servidor.visitas) == visitas,
   "la segunda vez no vuelve a molestar al servidor: lo tiene anotado")
ok([x["url"] for x in salida2] == [ARCH], "y contesta lo mismo que antes")

tope_viejo = CFG.DUDOSOS_POR_PEDIDO
CFG.DUDOSOS_POR_PEDIDO = 2
b2 = bot_de_prueba()
servidor2 = SesionFalsa()
b2.sesiones = {"A": servidor2}
b2.comprobar_dudosos(CLAVE, [{"url": "http://x/mod/page/view.php?id=%d" % i,
                             "titulo": "c %d" % i} for i in range(6)])
ok(len(servidor2.visitas) == 2,
   "no le dispara cien preguntas de una a la plataforma")
CFG.DUDOSOS_POR_PEDIDO = tope_viejo

b3 = bot_de_prueba()
b3.sesiones = {"A": SesionFalsa(revienta=True)}
ok(b3.comprobar_dudosos(CLAVE, [{"url": ARCH, "titulo": "G"}]) == [],
   "si no pudo mirar, no lo da por archivo")
ok(ARCH not in b3.estado.get("tipos_de_enlace", {}),
   "y tampoco lo anota como descartado: lo va a reintentar despues")

b4 = bot_de_prueba()
b4.sesiones = {"A": SesionFalsa(
    {ARCH: RespuestaFalsa("application/octet-stream",
                          pegado='attachment; filename="guia.pdf"')},
    sin_head=True)}
ok([x["url"] for x in b4.comprobar_dudosos(CLAVE, [{"url": ARCH,
                                                   "titulo": "G"}])] == [ARCH],
   "si el servidor no acepta la pregunta corta, prueba de la otra forma")


# ===================================================================== 6
titulo("6. el ramo que decia no tener archivos teniendo cuatro cosas")

b = bot_de_prueba()
urls = ["http://x/mod/page/view.php?id=%d" % i for i in (1, 2, 3, 4)]
b.estado["novedades"] = [
    {"c": CLAVE, "u": u, "t": "Clase %d" % i, "tipo": "otro",
     "g": "C\u00c1LCULO INTEGRAL", "f": "2026-08-0%d 10:00" % i}
    for i, u in enumerate(urls, 1)]
servidor = SesionFalsa({u: RespuestaFalsa("application/pdf") for u in urls})
b.sesiones = {"A": servidor}
b.leer_ramo_ahora = lambda clave: []

lista = b.archivos_del_ramo(CLAVE)
ok(len(lista) == 4,
   "las 4 cosas guardadas aparecen como archivos que se pueden bajar")
visitas = len(servidor.visitas)
ok(b.cuantos_archivos(CLAVE) == 4,
   "el numero que muestra el panel dice lo mismo que la lista")
ok(len(servidor.visitas) == visitas,
   "y para contar no vuelve a preguntarle nada a la plataforma")


# ===================================================================== 7
titulo("7. como llegan los archivos al chat")

b = bot_de_prueba()
ok(not b.van_juntos(1), "un archivo solo va tal cual")
ok(not b.van_juntos(CFG.SUELTOS_HASTA),
   "hasta %d archivos van de a uno, asi se abren de una" % CFG.SUELTOS_HASTA)
ok(b.van_juntos(CFG.SUELTOS_HASTA + 1),
   "pasando de ahi van en un solo paquete, para no tapar el chat")
b.estado["config"]["material"] = "suelto"
ok(not b.van_juntos(20), "si elegis de a uno, siempre de a uno")
b.estado["config"]["material"] = "paquete"
ok(b.van_juntos(2), "si elegis paquete, siempre paquete")
b.estado["config"]["material"] = "auto"

paquete, como = b.armar_paquete("C\u00c1LCULO INTEGRAL", [
    ("clase.pdf", b"uno", {}), ("clase.pdf", b"dos", {}),
    ("otro.pdf", b"tres", {})])
adentro = zipfile.ZipFile(io.BytesIO(paquete))
ok(sorted(adentro.namelist()) == ["clase (2).pdf", "clase.pdf", "otro.pdf"],
   "adentro del paquete no se pisan dos archivos con el mismo nombre")
ok(adentro.read("clase (2).pdf") == b"dos",
   "y cada uno lleva su propio contenido")
ok(como.endswith(".zip") and " " not in como and "calculo" in como.lower(),
   "el paquete se llama con el ramo y lo abre cualquier telefono")


def bot_con_archivos(cuantos):
    b = bot_de_prueba()
    b.sesiones = {"A": SesionFalsa()}
    b.animar = lambda titulo_a: (_nada, _cerrar)
    b._bajar_uno = lambda ses, a: (
        ("contenido de " + a["url"]).encode("utf-8"), "", RespuestaFalsa())
    elegidos = [{"url": "http://x/clase%d.pdf" % i, "titulo": "Clase %d" % i}
                for i in range(1, cuantos + 1)]
    return b, elegidos


def _cerrar(texto="", botones=None):
    MANDADOS.append({"texto": texto, "silencioso": True, "botones": botones})
    return len(MANDADOS)


limpiar()
b, elegidos = bot_con_archivos(3)
ok(b.mandar_archivos(CLAVE, elegidos) == 3, "tres archivos se mandan")
ok(len(DOCS) == 3 and not any(d["nombre"].endswith(".zip") for d in DOCS),
   "y llegan en su formato de siempre, uno por uno")

limpiar()
b, elegidos = bot_con_archivos(6)
ok(b.mandar_archivos(CLAVE, elegidos) == 6, "seis archivos tambien llegan")
paquetes = [d for d in DOCS if d["nombre"].endswith(".zip")]
ok(len(DOCS) == 1 and len(paquetes) == 1,
   "pero en un solo paquete, no en seis mensajes")
ok("6 archivos" in (paquetes[0]["leyenda"] or ""),
   "y el paquete dice cuantas cosas trae")
informe = todo_lo_mandado()
ok("paquete" in informe and "Ajustes" in informe,
   "le cuenta que puede cambiarlo desde los ajustes")
ok("zip" not in informe.lower(),
   "sin nombrarle formatos de archivo en el mensaje")

limpiar()
DOC_FALLA["paquete"] = True
b, elegidos = bot_con_archivos(6)
ok(b.mandar_archivos(CLAVE, elegidos) == 6,
   "si el paquete no se puede mandar, no perdes ningun archivo")
ok(len([d for d in DOCS if not d["rechazado"]]) == 6,
   "llegan los seis de a uno como respaldo")

limpiar()
b, elegidos = bot_con_archivos(6)
b.estado["config"]["material"] = "suelto"
b.mandar_archivos(CLAVE, elegidos)
ok(not any(d["nombre"].endswith(".zip") for d in DOCS),
   "y si elegiste de a uno, no te arma ningun paquete")


# ===================================================================== 8
titulo("8. lo que no marcaste visto te lo vuelve a recordar")


def bot_con_pendiente(idt="n1", recordado_viejo=False):
    b = bot_de_prueba()
    b.en_pausa = lambda: False
    b.en_silencio = lambda: False
    b.callado = lambda clave="": False
    viejo = HOY - dt.timedelta(hours=CFG.HORAS_PARA_RECORDAR_VISTO + 2)
    ficha = {"titulo": "Gu\u00eda 3", "url": "http://x/g3.pdf",
             "grupo": "C\u00c1LCULO INTEGRAL", "clave": CLAVE, "hecho": False,
             "es_tarea": False, "nacio": viejo.strftime("%Y-%m-%d %H:%M")}
    if recordado_viejo:
        ficha["recordado"] = True
    b.estado["tareas"][idt] = ficha
    return b, viejo


limpiar()
b, viejo = bot_con_pendiente()
b.recordar_sin_ver()
ok(len(MANDADOS) == 1, "lo que quedo sin revisar te lo muestra")
ok(b.estado["tareas"]["n1"].get("empujones") == 1,
   "y queda anotado que te lo mostro una vez")

limpiar()
b.recordar_sin_ver()
ok(len(MANDADOS) == 0, "pero no te lo repite cinco minutos despues")

limpiar()
b.estado["tareas"]["n1"]["ultimo_empujon"] = viejo.strftime("%Y-%m-%d %H:%M")
b.recordar_sin_ver()
ok(len(MANDADOS) == 1, "al otro dia insiste")
ok(b.estado["tareas"]["n1"].get("empujones") == 2, "y lleva la cuenta")

limpiar()
b.estado["tareas"]["n1"]["empujones"] = CFG.VECES_PARA_RECORDAR_VISTO
b.estado["tareas"]["n1"]["ultimo_empujon"] = viejo.strftime("%Y-%m-%d %H:%M")
b.recordar_sin_ver()
ok(len(MANDADOS) == 0,
   "no insiste para siempre: despues de %d veces para"
   % CFG.VECES_PARA_RECORDAR_VISTO)

limpiar()
b, viejo = bot_con_pendiente(recordado_viejo=True)
b.recordar_sin_ver()
ok(len(MANDADOS) == 1 and b.estado["tareas"]["n1"].get("empujones") == 2,
   "una memoria vieja no vuelve a empezar la cuenta de cero")

limpiar()
ENVIO_FALLA["si"] = True
b, viejo = bot_con_pendiente()
b.recordar_sin_ver()
ok(not b.estado["tareas"]["n1"].get("empujones"),
   "si el mensaje no salio, no lo marca como avisado")
ENVIO_FALLA["si"] = False

antes = CFG.INSISTIR_HASTA_VISTO
CFG.INSISTIR_HASTA_VISTO = False
limpiar()
b, viejo = bot_con_pendiente()
b.estado["tareas"]["n1"]["empujones"] = 1
b.estado["tareas"]["n1"]["ultimo_empujon"] = viejo.strftime("%Y-%m-%d %H:%M")
b.recordar_sin_ver()
ok(len(MANDADOS) == 0, "y si no querés que insista, no insiste")
CFG.INSISTIR_HASTA_VISTO = antes


# ===================================================================== 9
titulo("9. el primer arranque no inunda ni se queda callado")

limpiar()
b = bot_de_prueba()
b.estado["novedades"] = [
    {"c": CLAVE, "u": "http://x/a%d.pdf" % i, "t": "Cosa %d" % i,
     "g": "C\u00c1LCULO INTEGRAL" if i % 2 else "F\u00cdSICA",
     "f": "2026-08-01 10:00"} for i in range(1, 13)]
b.avisar_primera_vez()
ok(len(MANDADOS) == 1, "manda un resumen, no doce mensajes")
resumen = MANDADOS[0]["texto"]
ok(MANDADOS[0]["silencioso"], "y llega sin sonido, por si es de madrugada")
ok(resumen.count("\u2022") <= CFG.COSAS_EN_EL_RESUMEN_INICIAL,
   "con pocas cosas, no con todo lo viejo")
ok("4 cosas m" in resumen, "dice cuantas quedaron guardadas sin mostrar")
ok(len(resumen) < N.LARGO_MAXIMO,
   "y entra en un mensaje solo, sin que la app lo rechace")
ok("p:nov" in str(MANDADOS[0]["botones"]),
   "deja el boton para ver el resto cuando quiera")

limpiar()
antes = CFG.RESUMEN_DE_PRIMERA_VEZ
CFG.RESUMEN_DE_PRIMERA_VEZ = False
b.avisar_primera_vez()
ok(len(MANDADOS) == 0, "y se puede apagar")
CFG.RESUMEN_DE_PRIMERA_VEZ = antes


# ==================================================================== 10
titulo("10. los botones nuevos del panel")

b = bot_de_prueba()
acc = acc_de_prueba(b)
estado = b.estado
ok(P.reconoce("t:material") and P.reconoce("t:nocheimp"),
   "el panel reconoce los dos botones nuevos")

avisos_cortos = []
aviso, _pantalla = P.toque(estado, "t:material", acc, HOY)
avisos_cortos.append(aviso)
ok(estado["config"]["material"] == "suelto" and "de a uno" in aviso,
   "tocando una vez elige que lleguen de a uno")
aviso, _pantalla = P.toque(estado, "t:material", acc, HOY)
avisos_cortos.append(aviso)
ok(estado["config"]["material"] == "paquete" and "paquete" in aviso,
   "otra vez, en paquete")
aviso, _pantalla = P.toque(estado, "t:material", acc, HOY)
avisos_cortos.append(aviso)
ok(estado["config"]["material"] == "auto",
   "y otra vez vuelve a que decida solo")

antes = P._suenan_importantes(estado)
aviso, _pantalla = P.toque(estado, "t:nocheimp", acc, HOY)
avisos_cortos.append(aviso)
ok(P._suenan_importantes(estado) != antes,
   "el interruptor de los avisos de madrugada cambia de verdad")
ok("madrugada" in aviso, "y explica con palabras que va a pasar")

for a in avisos_cortos:
    ok(len(a) <= 190, "el aviso del boton entra en lo que la app deja mostrar")
    for jerga in ("cfg", "config", "True", "False", "None"):
        ok(jerga not in a, "y no dice '%s'" % jerga)

ok("t:material" in str(P.pantalla(estado, "p:mas", acc)),
   "la pantalla de Mas trae el boton para elegir como llega el material")
ok("t:nocheimp" in str(P.pantalla(estado, "p:avisos", acc)),
   "y la de avisos trae el de las pruebas y entregas de madrugada")
ok("noche_importantes" not in str(P.pantalla(estado, "p:avisos", acc)),
   "sin mostrarle nombres internos en la pantalla")

b.estado["config"]["noche_importantes"] = True
ok(b.cfg().get("noche_importantes") is True,
   "lo que elegiste queda guardado y el aviso lo respeta")


# ==================================================================== 11
titulo("11. la sonda no puede romper nada ni delatarte")

fuente_sonda = sin_comentarios("sonda.py")
# Esta prueba antes pedia que la sonda no mandara NINGUN dato a la pagina.
# Estaba mal medida, y por eso se cambia en vez de borrarla: lo que hay que
# garantizar es que la sonda no CAMBIE nada, no que no pregunte nada.  La
# segunda plataforma esconde la lista de ramos y solo la entrega si se le
# pregunta de esa forma; es la misma pregunta de solo lectura que hace la
# pagina sola al abrirla, y sin ella el informe vuelve a decir "0 ramos".
ok(fuente_sonda.count(".post(") <= 1,
   "la sonda casi no le habla a la plataforma")
ok(".post(" not in fuente_sonda or "get_enrolled_courses" in fuente_sonda,
   "y si le habla, es solo para pedirle la lista de ramos")
# Segunda correccion de esta misma prueba, por el mismo motivo que la de
# arriba: buscar palabras sueltas en el codigo vuelve a medir mal.  Desde
# esta version la sonda tiene una lista de enlaces prohibidos que NOMBRA
# esas palabras justamente para no abrirlos nunca.  O sea que la linea que
# la hace segura era la que hacia fallar la prueba.  Se saca esa lista del
# texto, y despues se comprueba de verdad que la lista funcione.
sin_lista = re.sub(r"RE_PELIGROSO = re\.compile\(.*?re\.I\)", "",
                   fuente_sonda, flags=re.S)
ok(len(sin_lista) < len(fuente_sonda),
   "la sonda lleva una lista de enlaces que no toca ni por error")
for peligro in ("edit.php", "delete", "upload", "logout", "unenrol"):
    ok(peligro not in sin_lista.lower(),
       "la sonda no le escribe nada a las plataformas (%s)" % peligro)
for malo in ("https://x.cl/curso/9/crear_modulo",
             "https://x.cl/login/logout.php?sesskey=1",
             "https://x.cl/enrol/unenrol.php?id=2",
             "https://x.cl/curso/9/editar",
             "https://x.cl/curso/borrar/9"):
    ok(SO.peligroso(malo), "y ni se acerca a ese enlace (%s)" % malo[-14:])
for bueno in ("https://x.cl/curso/9", "https://x.cl/curso/9/alumnos",
              "https://x.cl/pluginfile.php/1/apunte.pdf"):
    ok(not SO.peligroso(bueno),
       "pero si mira lo que solo se lee (%s)" % bueno[-12:])
ok("notificar" not in fuente_sonda and "N.enviar" not in fuente_sonda,
   "no te manda mensajes por su cuenta")
ok("almacen" not in fuente_sonda, "ni toca la memoria del bot")
ok("import secretos" in fuente_sonda,
   "lee tus datos del mismo archivo de siempre")
# Los nombres van partidos a proposito: el programa los compara enteros
# igual, pero en este archivo no queda escrito ninguno completo.
for palabra in ("moo" "dle", "ade" "cca", "ubio" "bio", "alum" "nos"):
    ok(palabra not in fuente_sonda.lower(),
       "la sonda no nombra ninguna plataforma ni universidad")

del SO.TAPAR[:]
SO.guardar_secreto("https://aula.ejemplo.cl", "PLATAFORMA_B")
SO.guardar_secreto("nombre.apellido", "USUARIO_OCULTO")
ok(SO.tapar("mira https://aula.ejemplo.cl/curso/1")
   == "mira PLATAFORMA_B/curso/1",
   "en el informe la direccion de la plataforma sale tapada")
ok("aula.ejemplo.cl" not in SO.tapar("aula.ejemplo.cl/archivo.php"),
   "tambien cuando aparece pelada, sin el http")
ok("nombre.apellido" not in SO.tapar("entro nombre.apellido"),
   "y tu usuario nunca queda escrito")
ok(SO.tapar("http://x/y?sesskey=abc123&id=2") == "http://x/y?sesskey=OCULTO&id=2",
   "la llave de la sesion se oculta")
ok("@" not in SO.tapar("escribile a alguien@ejemplo.cl"),
   "y los correos tambien")

carpeta = tempfile.mkdtemp()
SO.SALIDA = os.path.join(carpeta, "sonda.txt")
del SO.LINEAS[:]
SO.escribir("entro a https://aula.ejemplo.cl/curso/1")
SO.volcar()
guardado = open(SO.SALIDA, encoding="utf-8").read()
ok("PLATAFORMA_B" in guardado and "aula.ejemplo.cl" not in guardado,
   "lo que queda escrito en el informe ya viene anonimo")
shutil.rmtree(carpeta, ignore_errors=True)


# ==================================================================== 12
titulo("12. la version y la lista de cambios")

ok(numeros_de(VER.VERSION) > (5, 8),
   "la version subio (dice %s)" % VER.VERSION)
ok(len(VER.CAMBIOS) >= 5, "y trae la lista de que cambio")
todos = " ".join(VER.CAMBIOS).lower()
for jerga in ("zip", "http", "head", "cache", "json", "except", "api",
              "callback", "token"):
    ok(jerga not in todos, "la lista de cambios no dice '%s'" % jerga)

for archivo in ("_p16.py", "_p17.py", "_p18.py", "_p19.py", "_p20.py",
                "_p21.py"):
    fuente = sin_comentarios(archivo)
    ok('"%s"' % VER.VERSION not in fuente
       and "'%s'" % VER.VERSION not in fuente,
       "%s no tiene el numero de version escrito a mano" % archivo)


# ==================================================================== fin
print("\n" + "=" * 50)
if FALLOS:
    print("fallaron %d cosas:" % len(FALLOS))
    for f in FALLOS:
        print("  - %s" % f)
    raise SystemExit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
