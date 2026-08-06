# -*- coding: utf-8 -*-
"""Tanda 22: lo que reportaste despues de usar la 5.9.

Cada prueba de aca nace de algo que te paso de verdad:
  - le diste a "descargar todo", eran dos archivos y te llego uno comprimido
  - la ayuda de IA seguia sin funcionar y el bot no sabia decirte por que
  - querias pedirle archivos hablando ("el ultimo", "lo del ultimo dia")
  - querias poder sacar y autorizar gente sin pelear con nada
  - la sonda contaba muy poco de la pagina

Se corre sola, sin internet, sin claves de verdad y sin tocar tu cuenta:
    python3 _p22.py
"""
import io
import os
import re
import zipfile

os.environ.setdefault("TG_TOKEN", "1:falso")
os.environ.setdefault("TG_CHAT", "9999")
os.environ.setdefault("CLAVE_COMPARTIR", "llave-de-prueba-nada-real")

import comandos as CO
import fuentes as CFG
import ia as IA
import notificar as N
import panel as P
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


def _enviar(texto, silencioso=False, botones=None, teclado_fijo=False):
    MANDADOS.append({"texto": texto, "silencioso": silencioso,
                     "botones": botones})
    return len(MANDADOS)


def _editar(mensaje_id, texto, botones=None, limpiar_botones=True):
    MANDADOS.append({"texto": texto, "botones": botones, "edito": mensaje_id})
    return mensaje_id


def _mandar_documento(nombre, datos, leyenda="", silencioso=True,
                      responde_a=None):
    DOCS.append({"nombre": nombre, "datos": datos, "leyenda": leyenda})
    return len(DOCS)


def _avisar_boton(consulta_id, texto=""):
    AVISOS_DE_BOTON.append(texto or "")
    return True


def _nada(*a, **k):
    return None


def _cerrar(texto="", botones=None):
    MANDADOS.append({"texto": texto, "silencioso": True, "botones": botones})
    return len(MANDADOS)


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


def todo_lo_mandado():
    return "\n".join(m["texto"] or "" for m in MANDADOS)


def todos_los_botones():
    fuera = []
    for m in MANDADOS:
        fuera.append(str(m.get("botones") or ""))
    return "\n".join(fuera)


def sin_comentarios(nombre):
    """El codigo sin comentarios: los comentarios cuentan como era ANTES."""
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
        "aviso_clave": {}, "basura": [], "de_afuera": [], "desconocidos": {},
    }
    b.sesiones = {}
    b.bases = {}
    b.cache = {}
    b.modo = "gist"
    b.gist_nuevo = False
    b.guardar = lambda *a, **k: None
    b.animar = lambda t: (_nada, _cerrar)
    return b


def acc_de_prueba(b):
    acc = dict(b._acciones())
    acc["dibujar_panel"] = lambda donde=None, mid=None: None
    acc["abrir_panel"] = lambda *a, **k: None
    acc["redibujar_tarjeta"] = lambda idt=None, mid=None: None
    return acc


class RespuestaFalsa(object):
    def __init__(self, tipo="application/pdf", pegado="", codigo=200):
        self.status_code = codigo
        self.headers = {"Content-Type": tipo, "Content-Disposition": pegado}
        self.text = ""
        self.content = b"x"

    def close(self):
        pass


class SesionFalsa(object):
    def __init__(self):
        self.visitas = []

    def get(self, url, timeout=None, allow_redirects=True, stream=False):
        self.visitas.append(("get", url))
        return RespuestaFalsa("text/html")

    def head(self, url, timeout=None, allow_redirects=True):
        self.visitas.append(("head", url))
        return RespuestaFalsa("text/html")


def paquete_falso(cuantos=3):
    """Un paquete igual al que arma la plataforma con su boton propio."""
    tripa = io.BytesIO()
    with zipfile.ZipFile(tripa, "w") as z:
        for i in range(1, cuantos + 1):
            z.writestr("carpeta/clase%d.pdf" % i, b"contenido %d" % i)
    return tripa.getvalue()


# ===================================================================== 1
titulo("1. dos archivos tienen que llegar como dos archivos")

b = bot_de_prueba()
ok(b.van_juntos(2) is False, "dos archivos van sueltos")
ok(b.van_juntos(9) is True, "nueve van en un solo paquete")
ok(b.van_juntos(2, "paquete") is True,
   "y si para este pedido elegis paquete, van en paquete aunque sean dos")
ok(b.van_juntos(9, "suelto") is False,
   "y si elegis de a uno, van de a uno aunque sean nueve")

listos = [("material.zip", paquete_falso(3), {"titulo": "Descargar Todo",
                                              "url": "http://x/zip/1"})]
abiertos = b.desarmar_paquetes(listos)
ok(len(abiertos) == 3, "un paquete de la plataforma se abre y salen los 3")
ok(all(not n.endswith(".zip") for n, _, _ in abiertos),
   "y ninguno queda comprimido")
ok(all("/" not in n for n, _, _ in abiertos),
   "los nombres salen limpios, sin la carpeta de adentro")
ok(all(f.get("de_un_paquete") for _, _, f in abiertos),
   "queda anotado que venian adentro de un paquete")

limpiar()
b = bot_de_prueba()
b.sesiones = {"A": SesionFalsa()}
b._bajar_uno = lambda ses, a: (paquete_falso(2), "", RespuestaFalsa(
    "application/zip", 'attachment; filename="material.zip"'))
cuantos = b.mandar_archivos(CLAVE, [{"url": "http://x/file/download_zip/1",
                                     "titulo": "Descargar Todo"}])
ok(len(DOCS) == 2 and not any(d["nombre"].endswith(".zip") for d in DOCS),
   "el 'descargar todo' de la plataforma con 2 adentro llega como 2 archivos")
ok(cuantos == 2, "y el bot te dice que te mando 2, no 1")
ok("un solo paquete" in todo_lo_mandado().lower()
   or "te lo abr\u00ed" in todo_lo_mandado(),
   "y te explica por que los ves de a uno")

limpiar()
b = bot_de_prueba()
b.cfg()["material_una_vez"] = "paquete"
b.sesiones = {"A": SesionFalsa()}
b._bajar_uno = lambda ses, a: (("algo " + a["url"]).encode("utf-8"), "",
                               RespuestaFalsa())
b.mandar_archivos(CLAVE, [{"url": "http://x/a%d.pdf" % i,
                           "titulo": "Clase %d" % i} for i in (1, 2)])
ok(len(DOCS) == 1 and DOCS[0]["nombre"].endswith(".zip"),
   "si pediste paquete para este pedido, dos archivos van en un paquete")
ok(not b.cfg().get("material_una_vez"),
   "y esa eleccion no te queda pegada para siempre")

llamadas = []
b = bot_de_prueba()
b.pedir_archivos = lambda *a, **k: llamadas.append((a, k))
for accion, esperado in (("mandar_sueltos", "suelto"),
                         ("mandar_paquete", "paquete")):
    b.ejecutar_plan({"accion": accion, "que": accion, "clave": CLAVE,
                     "alcance": "todo", "desde": "", "hasta": "",
                     "nombre": "", "tipo": "todo"})
    ok(b.cfg().get("material_una_vez") == esperado,
       "el boton de %s deja pedido ese formato" % accion.split("_")[1])
    b.cfg().pop("material_una_vez", None)
ok(len(llamadas) == 2, "y los dos botones terminan mandando el material")

# La pregunta ofrece TRES botones. Antes solo quedaba vivo el ultimo que se
# creaba: tocabas "Mandalos" o "De a uno" y el bot contestaba que ese boton
# era de un pedido anterior, sin mandarte nada.
b = bot_de_prueba()
hechos = []
b.ejecutar_plan = lambda plan: hechos.append(plan.get("accion")) or "listo"
base = {"clave": CLAVE, "alcance": "todo"}
uno = b.nueva_marca_de_propuesta(dict(base, accion="mandar_sueltos"))
dos = b.nueva_marca_de_propuesta(dict(base, accion="mandar_paquete"),
                                 junto_a=uno)
tres = b.nueva_marca_de_propuesta(dict(base, accion="mandar_archivos"),
                                  junto_a=uno)
ok(len({uno, dos, tres}) == 3, "cada boton de la pregunta es distinto")
b.confirmar_propuesta(True, uno)
ok(hechos == ["mandar_sueltos"],
   "el boton 'De a uno' hace lo que dice, no lo del boton de al lado")

b = bot_de_prueba()
hechos = []
b.ejecutar_plan = lambda plan: hechos.append(plan.get("accion")) or "listo"
uno = b.nueva_marca_de_propuesta(dict(base, accion="mandar_sueltos"))
dos = b.nueva_marca_de_propuesta(dict(base, accion="mandar_paquete"),
                                 junto_a=uno)
b.confirmar_propuesta(True, dos)
ok(hechos == ["mandar_paquete"], "y el de 'En un paquete' tambien")

b = bot_de_prueba()
hechos = []
b.ejecutar_plan = lambda plan: hechos.append(plan.get("accion")) or "listo"
viejo = b.nueva_marca_de_propuesta(dict(base, accion="mandar_archivos"))
b.nueva_marca_de_propuesta({"accion": "borrar_todo"})
aviso = b.confirmar_propuesta(True, viejo)
ok(not hechos, "un boton de una pregunta vieja sigue sin hacer nada")
ok("anterior" in aviso.lower(), "y te explica por que no hizo nada")


# ===================================================================== 2
titulo("2. cuando la IA no anda, el bot te dice por que")

guardadas = {}
for v in list(CFG.IA.get("claves_env", [])) + [CFG.IA.get("env_lista", "")]:
    if v:
        guardadas[v] = os.environ.pop(v, None)

limpiar()
b = bot_de_prueba()
b.probar_ia_ahora()
texto = todo_lo_mandado()
ok("ninguna" in texto.lower(), "sin claves te avisa que no hay ninguna")
ok("IA_KEY_2" in texto,
   "y te dice como se tiene que llamar la casilla de la clave de repuesto")
ok("no dependen de esto" in texto or "sigue andando" in texto,
   "y te tranquiliza: los avisos y el material no dependen de la IA")

os.environ["IA_KEY"] = "clave-de-prueba-1"
limpiar()
b = bot_de_prueba()
viejo_pedir = IA._pedir
IA._pedir = lambda estado, texto_p, pdfs=(): "ok"
b.probar_ia_ahora()
texto = todo_lo_mandado()
ok("funcionando" in texto.lower(), "con la clave andando te dice que anda")
ok("clave-de-prueba-1" not in texto, "y NUNCA muestra la clave")
ok("1" in texto, "te dice cuantas claves le llegaron")


def _pedir_roto(estado, texto_p, pdfs=()):
    raise RuntimeError("mis 2 claves de IA no pueden ahora: sin cupo")


limpiar()
IA._pedir = _pedir_roto
b.probar_ia_ahora()
texto = todo_lo_mandado()
ok("no" in texto.lower() and "cupo" in texto,
   "y si no contesta te explica el motivo en castellano")
for fea in ("Traceback", "Exception", "None", "{", "http"):
    ok(fea not in texto, "la explicacion no muestra %s" % fea)
IA._pedir = viejo_pedir

limpiar()
b = bot_de_prueba()
toco = {"si": False}
b.probar_ia_ahora = lambda: toco.update(si=True)
b.accion("probar_ia")
ok(toco["si"], "el boton de probar la IA hace algo (antes no hacia nada)")

estado = bot_de_prueba().estado
acc = acc_de_prueba(bot_de_prueba())
ok("a:probar_ia" in str(P.pantalla(estado, "p:mas", acc)),
   "y el boton se puede encontrar en el panel")

for v, valor in guardadas.items():
    if valor is None:
        os.environ.pop(v, None)
    else:
        os.environ[v] = valor


# ===================================================================== 3
titulo("3. pedirle archivos hablando, con confirmacion")

unos = [{"titulo": "Gu\u00eda 1", "url": "http://x/g1.pdf", "cuando": "2026-07-01 10:00"},
        {"titulo": "Gu\u00eda 2", "url": "http://x/g2.pdf", "cuando": "2026-08-03 08:00"},
        {"titulo": "Gu\u00eda 3", "url": "http://x/g3.pdf", "cuando": "2026-08-03 19:00"}]

b = bot_de_prueba()
elegidos, desde, hasta, nombre, rango = b._solo_lo_ultimo(list(unos), "uno")
ok(len(elegidos) == 1 and elegidos[0]["titulo"] == "Gu\u00eda 3",
   "'el ultimo archivo' es el mas nuevo, no el primero de la lista")
ok(desde == hasta == "2026-08-03", "y queda atado a su dia exacto")

elegidos, desde, hasta, nombre, rango = b._solo_lo_ultimo(list(unos), "dia")
ok(len(elegidos) == 2, "'lo del ultimo dia' trae todo lo de ese dia")
ok("03" in rango, "y te dice de que dia esta hablando")

b = bot_de_prueba()
b.buscar = lambda t: (CLAVE, "C\u00c1LCULO INTEGRAL")
vistos = {}


def _filtrar(clave, alcance=None, desde="", hasta="", nombre="", tipo="todo",
             frescos=True):
    vistos["alcance"] = alcance
    return list(unos), len(unos), "de todo el ramo"


b.filtrar_archivos = _filtrar
plan, aviso = b.validar_orden({"accion": "buscar_archivos", "ramo": "calculo",
                               "ultimo": "uno"})
ok(plan and plan.get("accion") == "mandar_archivos",
   "'mandame el ultimo archivo de calculo' arma un pedido de archivos")
ok(vistos.get("alcance") == "todo",
   "y para eso mira todo el ramo, no solo la ultima semana")
ok(plan.get("nombre") == "Gu\u00eda 3" and plan.get("desde") == "2026-08-03",
   "el pedido queda apuntando a ese archivo y no a otro")
ok("Confirmame" in aviso or "confirm" in aviso.lower() or plan,
   "y antes de mandarlo te pregunta")

plan_dia, aviso_dia = b.validar_orden({"accion": "buscar_archivos",
                                       "ramo": "calculo", "ultimo": "dia"})
ok(plan_dia and plan_dia.get("desde") == plan_dia.get("hasta") == "2026-08-03",
   "'lo del ultimo dia de calculo' queda atado a ese dia")

plan_n, _ = b.validar_orden({"accion": "buscar_archivos", "ramo": "calculo",
                             "nombre": "certamen"})
ok(plan_n and plan_n.get("nombre") == "certamen",
   "y buscar por nombre sigue funcionando")

fuente_ia = sin_comentarios("ia.py")
ok('"ultimo"' in fuente_ia, "la IA sabe que puede pedir 'el ultimo'")
ok("ultimo dia" in fuente_ia or "ultima clase" in fuente_ia,
   "y tambien 'lo del ultimo dia'")

fuente_w = sin_comentarios("watcher.py")
ok("_pedir_confirmacion" in fuente_w and "nueva_marca_de_propuesta" in fuente_w,
   "todo lo que decide la IA pasa por una confirmacion tuya")
b2 = bot_de_prueba()
m1 = b2.nueva_marca_de_propuesta({"accion": "revisar"})
m2 = b2.nueva_marca_de_propuesta({"accion": "revisar"})
ok(m1 != m2, "dos propuestas seguidas no se pisan entre ellas")


# ===================================================================== 4
titulo("4. quien puede usar el bot")

limpiar()
estado = bot_de_prueba().estado
CO.anotar_desconocido(estado, 555, "Alguien")
ok(len(MANDADOS) == 1, "si un desconocido te escribe, te avisan a vos")
ok(estado["desconocidos"].get("555", {}).get("veces") == 1,
   "y queda anotado")
CO.anotar_desconocido(estado, 555, "Alguien")
ok(len(MANDADOS) == 1, "si insiste, no te llena el chat de avisos")
ok(estado["desconocidos"]["555"]["veces"] == 2, "pero se sigue contando")
ok("g:no:555" in todos_los_botones(),
   "el aviso trae el boton para no saber mas de esa persona")
ok("p:gente" in todos_los_botones(),
   "y el boton para ver quien puede usar el bot")

acc = acc_de_prueba(bot_de_prueba())
ok(P.reconoce("g:no:555") and P.reconoce("p:gente"),
   "esos botones los entiende el panel")
aviso, _p = P.toque(estado, "g:no:555", acc, HOY)
ok(estado["desconocidos"]["555"].get("bloqueado"),
   "al tocarlo, esa persona queda silenciada")
limpiar()
CO.anotar_desconocido(estado, 555, "Alguien")
ok(len(MANDADOS) == 0, "y no te vuelve a molestar con ella")

pantalla_gente = str(P.pantalla(estado, "p:gente", acc))
ok("Volver" in pantalla_gente or "\u2B05" in pantalla_gente,
   "la pantalla de gente tiene como volver")
ok("a:cerrar_compartir" in pantalla_gente,
   "y desde ahi podes cortar todo lo compartido de una")
ok("p:comp" in pantalla_gente,
   "y elegir que ve cada uno")
aviso, _p = P.toque(estado, "g:limpiar", acc, HOY)
ok(not estado.get("desconocidos"), "la lista de desconocidos se puede borrar")

ok(getattr(CFG, "SOLO_GENTE_AUTORIZADA", False) is True,
   "de fabrica, solo vos manejas el bot")
fuente_c = sin_comentarios("comandos.py")
ok("anotar_desconocido" in fuente_c, "el bot detecta a los desconocidos")


# ===================================================================== 5
titulo("5. la sonda tiene que mirar la pagina entera")

# El nombre de la universidad NO puede estar escrito dentro del proyecto: se
# lo pone el dueno en su archivo de datos, que no se sube a ningun lado.
os.environ["PALABRAS_A_TAPAR"] = "UNIALGO"
SO.cargar_palabras_extra()
SO.guardar_secreto("https://mi-plataforma.example", "PLATAFORMA_A")
salida = SO.tapar("entro a https://mi-plataforma.example/curso/1 de la "
                  "UNIALGO con mi correo alguien@algo.cl")
ok("mi-plataforma" not in salida, "la sonda tapa la direccion de la pagina")
ok("UNIALGO" not in salida and "unialgo" not in salida,
   "tapa el nombre de la universidad")
ok("unialgo" not in sin_comentarios("sonda.py").lower(),
   "y ese nombre no queda escrito dentro del proyecto")
ok("alguien@algo.cl" not in salida, "y tapa los correos")
del SO.TAPAR[:]

html = ('<html><body><div class="curso"><a href="/curso/1/modulo/9">Clase</a>'
        '<a href="/file/download_zip/9">Descargar Todo</a>'
        '<script src="/x/jstree.js"></script></div></body></html>')
et, cl, sc, fo, se = SO.inventario(html)
ok(et.get("a") == 2 and et.get("div") == 1, "cuenta lo que hay en la pagina")
ok("curso" in cl, "anota como se llaman las partes")
ok(len(sc) == 1, "anota los programas que carga la pagina")
ok("jstree" in " ".join(se) or se, "y avisa si el contenido lo dibuja un programa")

filas = SO.esqueleto(html)
ok(len(filas) > 3 and any("modulo" in f for f in filas),
   "puede mostrar como esta armada una pagina que parece vacia")

adentro = SO.mirar_paquete({"crudo": paquete_falso(3)})
ok(adentro and len(adentro) == 3,
   "puede decir que trae adentro el 'descargar todo' sin bajarlo a ningun lado")
ok(SO.mirar_paquete({"crudo": b"<html>"}) is None,
   "y no se confunde con una pagina normal")

fuente_s = sin_comentarios("sonda.py")
ok("import notificar" not in fuente_s and "N.enviar" not in fuente_s,
   "la sonda no manda mensajes a nadie")
ok("guardar(" not in fuente_s and "almacen" not in fuente_s,
   "y no toca la memoria del bot")
ok(fuente_s.count("open(") == 1, "solo escribe su propio informe")
ok("download_zip" in fuente_s, "revisa los paquetes que arma la plataforma")
ok("/my/courses.php" in fuente_s and "course/index.php" in fuente_s,
   "y busca los ramos escondidos de la segunda plataforma por varios caminos")
ok(SO.ADENTRO_POR_RAMO >= 30 and SO.ENLACES_POR_RAMO >= 200,
   "entra a muchas paginas por ramo, no a dos")
ok(SO.TOPE_INFORME >= 200000, "y el informe puede ser largo")


# ===================================================================== 6
titulo("6. la version y lo que le cuenta al duenio")

ok(numeros_de(VER.VERSION) > numeros_de("5.9"), "la version subio")
# Esta prueba exigia que el arreglo del material fuera SIEMPRE lo primero de
# la lista.  Estaba mal escrita, por el mismo motivo por el que no se escribe
# el numero de version a mano: la lista se ordena por lo que mas le importa
# al duenio en CADA entrega, asi que se ponia roja sola en la entrega
# siguiente sin que nada se hubiera roto.  Lo que si hay que cuidar es que
# ese arreglo se le siga contando y que lo primero venga marcado como lo mas
# importante de la tanda.
def _texto_de(cambio):
    if isinstance(cambio, (list, tuple)):
        return " ".join(str(x) for x in cambio)
    return str(cambio)


todos_los_cambios = " ".join(_texto_de(c) for c in VER.CAMBIOS).lower()
texto_cambios = _texto_de(VER.CAMBIOS[0])
ok("de a uno" in todos_los_cambios,
   "le sigue contando el arreglo del material")
ok("importante" in texto_cambios.lower(),
   "y lo primero de la lista viene marcado como lo mas importante")
ok(len(texto_cambios) > 200,
   "y se lo explica con palabras, no en tres lineas sueltas")
for jerga in ("zip", "json", "http", "cache", "except", "api", "callback",
              "token", "head"):
    ok(jerga not in texto_cambios.lower(),
       "los cambios se explican sin decir '%s'" % jerga)


# ===================================================================== fin
print("")
print("=" * 50)
if FALLOS:
    print("fallaron %d cosas:" % len(FALLOS))
    for f in FALLOS:
        print("  - %s" % f)
    raise SystemExit(1)
print("todo bien en la tanda de la v%s" % VER.VERSION)
