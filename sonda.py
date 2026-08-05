# -*- coding: utf-8 -*-
"""Sonda v2: el mapa completo de las plataformas.

Que hace, en una linea: entra igual que el bot, recorre TODO lo que
encuentra --portada del ramo, cada seccion, cada enlace de adentro, los
paquetes que arma la propia plataforma-- y escribe un informe largo en
sonda.txt.

Por que existe: el bot solo cuenta lo que entendio.  Cuando el bot dice "no
hay archivos" y vos ves archivos en la pagina, hace falta ver la pagina con
los ojos del bot, sin filtrar nada.  De eso se trata esto.

Tres reglas que no se rompen:
  1. NO toca la memoria del bot, no manda mensajes y no baja material a
     ningun lado.  Solo mira y escribe un archivo de texto.
  2. Ningun dato tuyo aparece en el informe: usuario, clave, direcciones,
     correo y el nombre de la universidad salen tapados.
  3. Si algo falla, lo anota y sigue.  Nunca se corta a la mitad.

Se usa asi, en la misma carpeta del bot y con tu mis_datos.txt al lado:

    python3 sonda.py

Y despues me pasas el archivo sonda.txt que queda al lado.
"""

import io
import os
import re
import time
import zipfile
import collections

SALIDA = "sonda.txt"
LINEAS = []
TAPAR = []

# Cuanto se permite mirar.  Son topes altos a proposito: esto se corre una
# vez, a mano, y lo que interesa es que no se escape nada.
ENLACES_POR_RAMO = 400
ADENTRO_POR_RAMO = 60          # cuantas paginas internas se abren por ramo
PAQUETES_POR_RAMO = 12
AVISOS_POR_RAMO = 8
ESQUELETOS_POR_RAMO = 4        # cuantos volcados de estructura por ramo
LARGO_ESQUELETO = 90           # lineas de estructura por pagina
TOPE_INFORME = 600000          # caracteres; si se pasa, se corta avisando

# Palabras que se tapan en todo el informe.  Empieza VACIA a proposito: aca no
# va escrito el nombre de la universidad ni el de las plataformas, porque este
# archivo vive en el repositorio y el repositorio no tiene por que decir donde
# estudias.  La lista se llena sola con los pedazos de tus propias direcciones.
PALABRAS_TAPADAS = []

# Pedazos que aparecen en cualquier direccion y no dicen nada de vos.
PEDAZOS_COMUNES = ("http", "https", "www", "com", "org", "net", "edu", "gov",
                   "php", "html", "index", "login", "course", "curso", "user",
                   "file", "download", "view", "page", "site", "web")


def tapar_los_pedazos(valor):
    """Guarda tambien los pedazos sueltos de una direccion o un usuario.

    Sirve para cuando el nombre de la universidad aparece escrito en el texto
    de la pagina y no como direccion: ahi el reemplazo entero no alcanza.
    """
    for pedazo in re.split(r"[^A-Za-z0-9]+", str(valor or "")):
        chico = pedazo.lower()
        if (len(chico) >= 3 and chico not in PEDAZOS_COMUNES
                and not chico.isdigit() and chico not in PALABRAS_TAPADAS):
            PALABRAS_TAPADAS.append(chico)


def cargar_palabras_extra():
    """Palabras que solo vos sabes y NO pueden vivir en el repositorio.

    Van en mis_datos.txt, en la linea PALABRAS_A_TAPAR, separadas por
    comas: por ejemplo la sigla de tu universidad, que aparece escrita en
    los avisos aunque no este en la direccion de la pagina.  Ese archivo
    no se sube a ningun lado, asi que el nombre nunca queda guardado
    dentro del proyecto.
    """
    for palabra in (os.environ.get("PALABRAS_A_TAPAR") or "").split(","):
        chico = palabra.strip().lower()
        if len(chico) >= 2 and chico not in PALABRAS_TAPADAS:
            PALABRAS_TAPADAS.append(chico)


def guardar_secreto(valor, etiqueta):
    """Anota un dato para taparlo despues en todo el informe."""
    valor = (valor or "").strip()
    if len(valor) >= 4:
        TAPAR.append((valor, etiqueta))
        # La misma direccion sin el principio: en el HTML muchas veces aparece
        # pelada y asi no se escapa.
        pelado = valor.split("://")[-1].rstrip("/")
        if pelado and pelado != valor:
            TAPAR.append((pelado, etiqueta))
        if "." in valor:
            tapar_los_pedazos(pelado)
        # Las mas largas primero: si una direccion contiene a la otra, se tapa
        # la larga y no queda un pedazo suelto a la vista.
        TAPAR.sort(key=lambda x: len(x[0]), reverse=True)


def tapar(texto):
    """Saca del texto todo lo que pueda identificarte."""
    t = str(texto)
    for valor, etiqueta in TAPAR:
        if valor:
            t = t.replace(valor, etiqueta)
    for palabra in PALABRAS_TAPADAS:
        t = re.sub(re.escape(palabra), "OCULTO", t, flags=re.I)
    # Un correo suelto que se haya colado en el HTML.
    t = re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "CORREO_OCULTO", t)
    # La llave con la que la pagina reconoce tu sesion: no sirve para arreglar
    # nada y con ella alguien podria hacerse pasar por vos mientras dura.
    t = re.sub(r"(sesskey[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9]+", r"\1OCULTO", t)
    return t


def escribir(texto=""):
    LINEAS.append(tapar(texto))


def titulo(t):
    escribir("")
    escribir("=" * 66)
    escribir(t)
    escribir("=" * 66)


def subtitulo(t):
    escribir("")
    escribir("-" * 60)
    escribir(t)
    escribir("-" * 60)


def volcar():
    texto = "\n".join(LINEAS)
    if len(texto) > TOPE_INFORME:
        texto = (texto[:TOPE_INFORME]
                 + "\n\n[...] el informe se corto aca para que se pueda "
                   "mandar. Avisame y lo parto en dos.")
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(texto)
    return len(texto)


def peso(n):
    if n is None:
        return "?"
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f kB" % (n / 1024.0)
    return "%.1f MB" % (n / (1024.0 * 1024))


# ------------------------------------------------------------------ mirar
def bajar(s, url, limite=900000):
    """Trae una pagina y devuelve todo lo que se sabe de ella."""
    ficha = {"url": url, "codigo": 0, "tipo": "", "peso": 0, "html": "",
             "falla": "", "segundos": 0.0, "final": url}
    t0 = time.time()
    try:
        r = s.get(url, timeout=45, allow_redirects=True)
        ficha["codigo"] = r.status_code
        ficha["tipo"] = (r.headers.get("Content-Type") or "").split(";")[0]
        ficha["final"] = r.url
        crudo = r.content or b""
        ficha["peso"] = len(crudo)
        if "text" in ficha["tipo"] or "html" in ficha["tipo"] or "json" in ficha["tipo"]:
            ficha["html"] = crudo[:limite].decode("utf-8", "ignore")
        else:
            ficha["crudo"] = crudo
    except Exception as e:
        ficha["falla"] = type(e).__name__
    ficha["segundos"] = round(time.time() - t0, 1)
    return ficha


RE_ETIQUETA = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)")
RE_CLASE = re.compile(r"class=[\"']([^\"']{1,120})[\"']")
RE_SCRIPT_SRC = re.compile(r"<script[^>]+src=[\"']([^\"']+)[\"']", re.I)
RE_ENLACE = re.compile(r"href=[\"']([^\"'#]+)[\"']", re.I)
RE_FORM = re.compile(r"<form[^>]*action=[\"']([^\"']*)[\"']", re.I)
# Senales de que el contenido no viene en el HTML sino que lo dibuja el
# programa del navegador despues.  Si esto aparece, el bot nunca lo va a ver
# leyendo el HTML y hay que buscar de donde saca los datos.
SENALES_DE_PROGRAMA = ["application/json", "data-react", "ng-app", "vue",
                       "jstree", "datatable", "ajax", "fetch(", "XMLHttpRequest",
                       "webservice", "sesskey", "require([", "M.cfg"]


def inventario(html):
    """Que hay adentro de esta pagina, contado."""
    etiquetas = collections.Counter(e.lower() for e in RE_ETIQUETA.findall(html))
    clases = collections.Counter()
    for c in RE_CLASE.findall(html):
        for una in c.split():
            clases[una[:40]] += 1
    scripts = RE_SCRIPT_SRC.findall(html)
    formularios = RE_FORM.findall(html)
    senales = [p for p in SENALES_DE_PROGRAMA if p.lower() in html.lower()]
    return etiquetas, clases, scripts, formularios, senales


def esqueleto(html, tope=LARGO_ESQUELETO):
    """La estructura de la pagina sin los textos: para ver donde estaria el
    material si estuviera."""
    limpio = re.sub(r"<script.*?</script>", "<script/>", html,
                    flags=re.S | re.I)
    limpio = re.sub(r"<style.*?</style>", "<style/>", limpio,
                    flags=re.S | re.I)
    filas, hondo = [], 0
    for trozo in re.findall(r"<[^>]{1,200}>|[^<]{1,120}", limpio):
        trozo = trozo.strip()
        if not trozo:
            continue
        if trozo.startswith("</"):
            hondo = max(0, hondo - 1)
            continue
        if trozo.startswith("<"):
            nombre = RE_ETIQUETA.findall(trozo)
            nombre = nombre[0].lower() if nombre else "?"
            clase = RE_CLASE.findall(trozo)
            enlace = RE_ENLACE.findall(trozo)
            fila = "%s<%s%s%s>" % (
                " " * min(hondo, 12), nombre,
                (" ." + clase[0][:45]) if clase else "",
                (" -> " + enlace[0][:70]) if enlace else "")
            filas.append(fila)
            if not trozo.endswith("/>") and nombre not in (
                    "br", "img", "input", "meta", "link", "hr"):
                hondo += 1
        else:
            if len(trozo) > 2:
                filas.append("%s%s" % (" " * min(hondo, 12), trozo[:90]))
        if len(filas) >= tope:
            filas.append("   [...] (sigue)")
            break
    return filas


def mirar_paquete(ficha):
    """Si esto que bajamos es un paquete de la plataforma, decir que trae."""
    crudo = ficha.get("crudo") or b""
    if not crudo or crudo[:2] != b"PK":
        return None
    try:
        z = zipfile.ZipFile(io.BytesIO(crudo))
        return [(i.filename, i.file_size) for i in z.infolist()][:60]
    except Exception as e:
        return [("no se pudo abrir: " + type(e).__name__, 0)]


# --------------------------------------------------------------- un ramo
def informe_de_ramo(W, CFG, s, base, ficha_ramo, etiqueta):
    nombre = ficha_ramo.get("nombre", "?")
    raiz = ficha_ramo.get("url", "")
    subtitulo("RAMO: %s" % nombre)
    escribir("portada    : %s" % raiz.replace(base, etiqueta))

    portada = bajar(s, raiz)
    escribir("respuesta  : %s | %s | %s | %ss"
             % (portada["codigo"], portada["tipo"] or "?",
                peso(portada["peso"]), portada["segundos"]))
    if portada["falla"]:
        escribir("no se pudo abrir la portada: %s" % portada["falla"])
        return
    html = portada["html"]
    etiquetas, clases, scripts, formularios, senales = inventario(html)
    escribir("etiquetas  : %s" % ", ".join(
        "%s=%d" % (k, v) for k, v in etiquetas.most_common(12)))
    escribir("clases     : %s" % ", ".join(
        "%s=%d" % (k, v) for k, v in clases.most_common(14)))
    escribir("programas  : %d externos%s"
             % (len(scripts),
                (" | " + ", ".join(x.split("/")[-1][:40] for x in scripts[:8]))
                if scripts else ""))
    escribir("formularios: %d %s" % (len(formularios),
                                     ", ".join(formularios[:4])))
    escribir("senales de contenido dibujado por programa: %s"
             % (", ".join(senales) if senales else "ninguna"))

    # ---- todos los enlaces, sin filtrar
    try:
        items = W.cosas_de_la_pagina(html, base, propia=raiz)
    except Exception as e:
        items = []
        escribir("[!] no pude leer los enlaces de la portada: %s" % type(e).__name__)
    crudos = []
    vistos = set()
    for u in RE_ENLACE.findall(html):
        if u.startswith("javascript") or u.startswith("mailto"):
            continue
        entero = u if u.startswith("http") else (base + u if u.startswith("/")
                                                 else raiz.rstrip("/") + "/" + u)
        if entero not in vistos:
            vistos.add(entero)
            crudos.append(entero)
    escribir("")
    escribir("enlaces en la portada: %d en total, %d los entendio el bot"
             % (len(crudos), len(items)))

    bajables, internos, paquetes, otros = [], [], [], []
    for u in crudos[:ENLACES_POR_RAMO]:
        bajo = u.lower()
        if "download_zip" in bajo or "/zip" in bajo:
            paquetes.append(u)
        elif W.es_bajable(u, ""):
            bajables.append(u)
        elif any(p in bajo for p in W.PISTAS_DE_ACTIVIDAD) and base in u:
            internos.append(u)
        else:
            otros.append(u)
    escribir("  bajables directos : %d" % len(bajables))
    escribir("  secciones adentro : %d" % len(internos))
    escribir("  paquetes armados  : %d" % len(paquetes))
    escribir("  el resto          : %d" % len(otros))
    escribir("")
    escribir("LISTA COMPLETA DE ENLACES DE LA PORTADA")
    for u in crudos[:ENLACES_POR_RAMO]:
        marca = ("PAQUETE" if u in paquetes else
                 "BAJABLE" if u in bajables else
                 "ADENTRO" if u in internos else "otro   ")
        escribir("  [%s] %s" % (marca, u.replace(base, etiqueta)))

    # ---- entrar a cada seccion y mirar que hay de verdad
    escribir("")
    escribir("ADENTRO DE CADA SECCION")
    esqueletos = 0
    encontrados_adentro = 0
    for u in internos[:ADENTRO_POR_RAMO]:
        dentro = bajar(s, u)
        escribir("")
        escribir("  > %s" % u.replace(base, etiqueta))
        escribir("    respuesta: %s | %s | %s | %ss"
                 % (dentro["codigo"], dentro["tipo"] or "?",
                    peso(dentro["peso"]), dentro["segundos"]))
        if dentro["falla"]:
            escribir("    no se pudo abrir: %s" % dentro["falla"])
            continue
        if dentro["final"] != u:
            escribir("    me mando a: %s" % dentro["final"].replace(base, etiqueta))
        hd = dentro["html"]
        if not hd:
            escribir("    esto no es una pagina: es un archivo")
            continue
        et, cl, sc, fo, se = inventario(hd)
        nuevos = []
        for x in RE_ENLACE.findall(hd):
            entero = x if x.startswith("http") else (
                base + x if x.startswith("/") else "")
            if entero and entero not in vistos:
                nuevos.append(entero)
        bajables_dentro = [x for x in nuevos if W.es_bajable(x, "")]
        paquetes_dentro = [x for x in nuevos if "download_zip" in x.lower()]
        encontrados_adentro += len(bajables_dentro)
        escribir("    enlaces nuevos: %d | bajables: %d | paquetes: %d"
                 % (len(nuevos), len(bajables_dentro), len(paquetes_dentro)))
        escribir("    clases: %s" % ", ".join(
            "%s=%d" % (k, v) for k, v in cl.most_common(8)))
        if se:
            escribir("    dibujado por programa: %s" % ", ".join(se))
        for x in (bajables_dentro + paquetes_dentro)[:20]:
            escribir("      * %s" % x.replace(base, etiqueta))
        for x in nuevos[:25]:
            if x not in bajables_dentro and x not in paquetes_dentro:
                escribir("      . %s" % x.replace(base, etiqueta))
        for x in nuevos:
            if "download_zip" in x.lower() and x not in paquetes:
                paquetes.append(x)
        # Si la seccion parece vacia, se vuelca su estructura: ahi se ve si el
        # material esta escondido detras de un programa del navegador.
        if not bajables_dentro and esqueletos < ESQUELETOS_POR_RAMO:
            esqueletos += 1
            escribir("    --- como esta armada esta pagina ---")
            for fila in esqueleto(hd):
                escribir("    | " + fila)

    # ---- los paquetes que arma la propia plataforma
    escribir("")
    escribir("PAQUETES QUE ARMA LA PLATAFORMA")
    if not paquetes:
        escribir("  no encontre ninguno en este ramo")
    for u in paquetes[:PAQUETES_POR_RAMO]:
        p = bajar(s, u)
        escribir("  > %s" % u.replace(base, etiqueta))
        escribir("    respuesta: %s | %s | %s"
                 % (p["codigo"], p["tipo"] or "?", peso(p["peso"])))
        adentro = mirar_paquete(p)
        if adentro is None:
            escribir("    no vino como paquete")
            continue
        escribir("    trae %d archivo(s):" % len(adentro))
        for nombre_a, tam in adentro:
            escribir("      - %s (%s)" % (nombre_a, peso(tam)))

    escribir("")
    escribir("RESUMEN DEL RAMO: %d bajables en la portada, %d adentro de las "
             "secciones, %d paquetes"
             % (len(bajables), encontrados_adentro, len(paquetes)))


# ------------------------------------------------- la plataforma tipo aula
CAMINOS_DE_AULA = [
    "/my/",
    "/my/courses.php",
    "/course/index.php",
    "/course/",
    "/user/profile.php",
    "/calendar/view.php?view=month",
    "/message/index.php",
    "/grade/report/overview/index.php",
]


def probar_aula(W, s, base, etiqueta):
    """La segunda plataforma dice que entro bien pero no encuentra ni un ramo.
    Aca se prueba camino por camino para ver donde estan escondidos."""
    subtitulo("BUSQUEDA DE RAMOS EN LA SEGUNDA PLATAFORMA")
    llave = ""
    for camino in CAMINOS_DE_AULA:
        f = bajar(s, base + camino)
        escribir("")
        escribir("> %s%s" % (etiqueta, camino))
        escribir("  respuesta: %s | %s | %s | %ss"
                 % (f["codigo"], f["tipo"] or "?", peso(f["peso"]), f["segundos"]))
        if f["falla"]:
            escribir("  no se pudo abrir: %s" % f["falla"])
            continue
        if f["final"] != base + camino:
            escribir("  me mando a: %s" % f["final"].replace(base, etiqueta))
        html = f["html"] or ""
        if "login" in f["final"]:
            escribir("  ojo: me devolvio a la pantalla de entrar")
        cursos = sorted(set(re.findall(r"course/view\.php\?id=(\d+)", html)))
        escribir("  ramos que se ven aca: %d %s"
                 % (len(cursos), ", ".join(cursos[:20])))
        nombres = re.findall(r"coursename[^>]*>([^<]{3,80})<", html)
        if nombres:
            escribir("  nombres sueltos: %s" % " | ".join(n.strip() for n in nombres[:8]))
        if not llave:
            m = re.search(r"sesskey[\"']?\s*[:=]\s*[\"']([A-Za-z0-9]+)", html)
            if m:
                llave = m.group(1)
        et, cl, sc, fo, se = inventario(html)
        escribir("  clases: %s" % ", ".join(
            "%s=%d" % (k, v) for k, v in cl.most_common(10)))
        if se:
            escribir("  dibujado por programa: %s" % ", ".join(se))
        if not cursos and camino in ("/my/", "/my/courses.php"):
            escribir("  --- como esta armada esta pagina ---")
            for fila in esqueleto(html, 70):
                escribir("  | " + fila)

    # El camino que usa la propia pagina para pedir la lista de ramos.
    if llave:
        escribir("")
        escribir("La pagina pide sus ramos por un camino interno. Lo pruebo.")
        cuerpo = [{"index": 0, "methodname":
                   "core_course_get_enrolled_courses_by_timeline_classification",
                   "args": {"offset": 0, "limit": 50, "classification": "all",
                            "sort": "fullname"}}]
        try:
            r = s.post(base + "/lib/ajax/service.php?sesskey=" + llave,
                       json=cuerpo, timeout=45)
            texto = (r.text or "")[:4000]
            escribir("  respuesta: %s | %s" % (r.status_code, peso(len(r.content or b""))))
            cuantos = len(re.findall(r'"fullname"', texto))
            escribir("  ramos que contesto: %d" % cuantos)
            escribir("  primeros datos: %s" % texto[:700])
        except Exception as e:
            escribir("  no pude preguntar: %s" % type(e).__name__)
    else:
        escribir("")
        escribir("No encontre la llave interna de la pagina, asi que no puedo "
                 "probar el camino que usa ella misma para pedir los ramos.")


# ------------------------------------------------------------------ main
def main():
    import secretos as SEC
    try:
        SEC.cargar(silencioso=True)
    except Exception:
        pass
    import watcher as W
    import fuentes as CFG
    import version as VER

    cargar_palabras_extra()

    for nombre_env, etiqueta in (("SITE_A_USER", "USUARIO_OCULTO"),
                                 ("SITE_A_PASS", "CLAVE_OCULTA"),
                                 ("SITE_B_USER", "USUARIO_OCULTO"),
                                 ("SITE_B_PASS", "CLAVE_OCULTA"),
                                 ("CAL_URL", "CALENDARIO_OCULTO"),
                                 ("CAL_URL_B", "CALENDARIO_OCULTO"),
                                 ("TG_TOKEN", "OCULTO"), ("TG_CHAT", "OCULTO"),
                                 ("GH_TOKEN", "OCULTO"), ("GIST_ID", "OCULTO"),
                                 ("GH_REPO", "OCULTO")):
        guardar_secreto(os.environ.get(nombre_env, ""), etiqueta)

    titulo("SONDA v2 - mapa completo de las plataformas")
    escribir("version del bot : %s" % VER.VERSION)
    escribir("fecha de la sonda: %s" % W.ahora().strftime("%d-%m-%Y %H:%M"))
    escribir("zona horaria     : %s" % getattr(CFG, "ZONA_HORARIA", "?"))
    escribir("")
    escribir("Esto NO toca la memoria del bot ni manda mensajes: solo mira.")

    # La sonda mira hondo aunque el bot ande liviano.
    CFG.MINUTOS_EXPLORACION_PROFUNDA = 0
    CFG.PROFUNDIDAD = max(3, getattr(CFG, "PROFUNDIDAD", 1))
    CFG.PAGINAS_POR_RAMO = max(60, getattr(CFG, "PAGINAS_POR_RAMO", 14))
    try:
        W._ULTIMO_PROFUNDO.clear()
    except Exception:
        pass

    letras = "AB"
    for i, f in enumerate(CFG.FUENTES):
        etiqueta = "PLATAFORMA_%s" % (letras[i] if i < len(letras) else i)
        titulo("%s (modo %s)" % (etiqueta, f.get("modo")))
        if not f.get("activo"):
            escribir("esta plataforma esta apagada en la configuracion")
            continue
        base = os.environ.get(f["env_url"], "").strip().rstrip("/")
        usuario = os.environ.get(f["env_user"], "").strip()
        clave = os.environ.get(f["env_pass"], "")
        if not (base and usuario and clave):
            escribir("faltan los datos de entrada de esta plataforma")
            continue
        guardar_secreto(base, etiqueta)
        guardar_secreto(base.replace("https://", "").replace("http://", ""),
                        etiqueta)

        s = W.sesion()
        entrar, leer = W.ADAPTADORES[f["modo"]]
        t0 = time.time()
        try:
            entro = entrar(s, base, usuario, clave)
        except Exception as e:
            entro = False
            escribir("reviento al entrar: %s" % type(e).__name__)
        escribir("entrada : %s (%.1f s)" % ("ok" if entro else "NO PUDE",
                                            time.time() - t0))
        if not entro:
            continue

        if f.get("modo") == "aula":
            probar_aula(W, s, base, etiqueta)

        t0 = time.time()
        grupos, viejos = {}, {}
        try:
            grupos, viejos = leer(s, base)
        except Exception as e:
            escribir("reviento leyendo los ramos: %s" % type(e).__name__)
        escribir("ramos activos : %d | ramos viejos : %d | tardo %.1f s"
                 % (len(grupos or {}), len(viejos or {}), time.time() - t0))

        for clave_g, ficha in list((grupos or {}).items()):
            try:
                informe_de_ramo(W, CFG, s, base, ficha, etiqueta)
            except Exception as e:
                escribir("[!] este ramo reviento: %s" % type(e).__name__)

    titulo("FIN")
    escribir("Si el informe quedo corto, avisame: se puede mirar mas hondo.")
    largo = volcar()
    print("listo: %s (%d caracteres)" % (SALIDA, largo))
    print("revisalo antes de mandarmelo, no deberia tener ningun dato tuyo.")


if __name__ == "__main__":
    main()
