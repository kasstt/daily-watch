# -*- coding: utf-8 -*-
"""Aplica el parche y lo sube solo.  No hay que configurar nada a mano.

Que hace, en orden:
  1. si le falta algun dato, te lo pregunta aca mismo y lo guarda solo
  2. busca el zip del parche mas nuevo (en esta carpeta o en Descargas)
  3. guarda una copia de seguridad de lo que tenes ahora
  4. descomprime el parche encima de tu carpeta
  5. sube al repositorio solo los archivos que cambiaron
  6. le pide a GitHub que arranque el bot al toque

Se usa con doble clic en ACTUALIZAR.bat.
"""
import base64
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile

try:
    import requests
except Exception:
    print("[!] falta requests.  Abri una consola y corre:  pip install requests")
    input("\nEnter para cerrar.")
    sys.exit(1)

import secretos

AQUI = os.path.dirname(os.path.abspath(__file__))
RESPALDOS = os.path.join(AQUI, "respaldos")
DATOS = os.path.join(AQUI, "mis_datos.txt")
API = "https://api.github.com"

# lo privado y lo que no tiene por que viajar
FUERA = {"mis_datos.txt", "MI_CALENDARIO_PRIVADO.txt", ".env",
         "__pycache__", ".git", "respaldos", ".DS_Store", "estado"}

# solo se sube lo que es parte del proyecto.  Asi ningun archivo suelto que
# tengas en la carpeta termina publicado sin querer.
EXTENSIONES_OK = (".py", ".md", ".yml", ".yaml")
NOMBRES_OK = {"requirements.txt", ".gitignore", "ACTUALIZAR.bat"}


def titulo(t):
    print("\n" + "=" * 62)
    print(t)
    print("=" * 62)


def preguntar(texto):
    try:
        return input(texto).strip()
    except EOFError:
        return ""


# =====================================================================
#  los datos, sin que tengas que editar archivos
# =====================================================================
def normalizar_repo(crudo):
    """Acepta lo que sea y deja 'usuario/repositorio'.
    Sirve para 'https://github.com/uno/dos', 'github.com/uno/dos.git',
    'uno/dos' y hasta con barras de mas."""
    t = (crudo or "").strip().strip("<>").strip()
    if not t:
        return ""
    t = re.sub(r"^https?://", "", t, flags=re.I)
    t = re.sub(r"^(www\.)?github\.com/", "", t, flags=re.I)
    t = re.sub(r"^git@github\.com:", "", t, flags=re.I)
    t = t.split("?")[0].split("#")[0]
    t = re.sub(r"\.git$", "", t.strip("/"))
    partes = [p for p in t.split("/") if p]
    if len(partes) < 2:
        return ""
    return "%s/%s" % (partes[0], partes[1])


def guardar_dato(nombre, valor):
    """Escribe el dato en mis_datos.txt por vos.  Si ya estaba, lo reemplaza."""
    lineas = []
    if os.path.isfile(DATOS):
        with open(DATOS, encoding="utf-8-sig") as f:
            lineas = f.read().splitlines()
    puesto = False
    for i, l in enumerate(lineas):
        if l.strip().startswith(nombre + "="):
            lineas[i] = "%s=%s" % (nombre, valor)
            puesto = True
            break
    if not puesto:
        if lineas and lineas[-1].strip():
            lineas.append("")
        lineas.append("%s=%s" % (nombre, valor))
    with open(DATOS, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    os.environ[nombre] = valor


def cabeceras(token):
    return {"Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def quien_es(token):
    """Devuelve (usuario, permisos) o (None, motivo)."""
    try:
        r = requests.get(API + "/user", headers=cabeceras(token), timeout=30)
    except Exception as e:
        return None, "no pude conectarme (%s)" % type(e).__name__
    if r.status_code == 401:
        return None, "la clave no sirve o esta vencida"
    if r.status_code != 200:
        return None, "GitHub contesto %s" % r.status_code
    permisos = r.headers.get("x-oauth-scopes", "")
    return r.json().get("login", ""), permisos


def explicar_token():
    print("""
  Como sacar la clave, paso a paso:

   1. entra a  https://github.com/settings/tokens
   2. boton  Generate new token  y elegi  Generate new token (classic)
   3. en Note escribi cualquier cosa, por ejemplo  bot
   4. en Expiration elegi  No expiration
   5. marca las casillas   repo    gist    workflow
   6. abajo de todo  Generate token  y copia lo que aparece
""")


def pedir_token():
    explicar_token()
    while True:
        t = preguntar("  Pega aca la clave y apreta Enter (o Enter solo para salir): ")
        if not t:
            return ""
        usuario, info = quien_es(t)
        if not usuario:
            print("  [!] esa clave no anduvo: %s.  Proba de nuevo.\n" % info)
            continue
        guardar_dato("GH_TOKEN", t)
        print("  [ok] clave guardada. Sos %s." % usuario)
        return t


def repos_del_usuario(token):
    salida = []
    for pagina in (1, 2):
        try:
            r = requests.get(API + "/user/repos", headers=cabeceras(token),
                             params={"per_page": 100, "page": pagina,
                                     "affiliation": "owner", "sort": "updated"},
                             timeout=30)
        except Exception:
            break
        if r.status_code != 200:
            break
        datos = r.json()
        salida += [(d["full_name"], d.get("default_branch", "main")) for d in datos]
        if len(datos) < 100:
            break
    return salida


def mirar_repo(token, repo):
    """Devuelve la rama principal si lo puedo tocar, o None."""
    try:
        r = requests.get("%s/repos/%s" % (API, repo), headers=cabeceras(token),
                         timeout=30)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    return r.json().get("default_branch", "main")


def elegir_repo(token):
    """Busca el repositorio del bot solo.  Si hay dudas, te muestra una lista
    numerada y elegis con un numero.  Nada de escribir rutas."""
    lista = repos_del_usuario(token)
    if not lista:
        print("  [!] no vi ningun repositorio tuyo. Puede que a la clave le")
        print("      falte la casilla  repo.")
        return "", ""

    # el que se llame parecido al bot va primero
    pistas = ("watch", "bot", "daily", "vigil")
    ordenada = sorted(lista, key=lambda x: (
        0 if any(p in x[0].lower() for p in pistas) else 1, x[0].lower()))

    if len(ordenada) == 1:
        print("  [ok] encontre uno solo: %s" % ordenada[0][0])
        return ordenada[0]

    print("\n  Cual es el repositorio del bot?\n")
    for i, (nombre, _) in enumerate(ordenada[:15], 1):
        print("   %2d) %s" % (i, nombre))
    print()
    while True:
        n = preguntar("  Escribi el numero y apreta Enter: ")
        if not n:
            return "", ""
        if n.isdigit() and 1 <= int(n) <= min(15, len(ordenada)):
            return ordenada[int(n) - 1]
        print("  [!] poner solo el numero de la izquierda.")


def preparar():
    """Deja token, repo y rama listos.  Pregunta solo lo que falte."""
    token = os.environ.get("GH_TOKEN", "").strip()
    repo = normalizar_repo(os.environ.get("GH_REPO", ""))
    rama = os.environ.get("GH_RAMA", "").strip()

    if token:
        usuario, info = quien_es(token)
        if not usuario:
            print("  [!] la clave guardada no anda: %s" % info)
            token = ""
        else:
            permisos = info
            if permisos and "repo" not in permisos.split(", "):
                print("  [!] la clave anda pero le falta el permiso de")
                print("      repositorio, asi que no puede subir archivos.")
                token = ""
    if not token:
        token = pedir_token()
    if not token:
        return "", "", ""

    # el repo guardado, si de verdad existe y lo puedo tocar
    if repo:
        principal = mirar_repo(token, repo)
        if principal:
            return token, repo, (rama or principal)
        print("  [!] no pude entrar a '%s', lo busco solo." % repo)

    repo, principal = elegir_repo(token)
    if not repo:
        return token, "", ""
    guardar_dato("GH_REPO", repo)
    guardar_dato("GH_RAMA", principal or "main")
    return token, repo, (principal or "main")


# =====================================================================
#  el parche
# =====================================================================
def sha_git(ruta):
    datos = open(ruta, "rb").read()
    return hashlib.sha1(("blob %d\0" % len(datos)).encode() + datos).hexdigest()


def buscar_parche():
    lugares = [AQUI, os.path.join(os.path.expanduser("~"), "Downloads"),
               os.path.join(os.path.expanduser("~"), "Descargas"),
               os.path.join(os.path.expanduser("~"), "OneDrive", "Descargas"),
               os.path.join(os.path.expanduser("~"), "OneDrive", "Downloads")]
    candidatos = []
    for d in lugares:
        for patron in ("parche*.zip", "watcher*.zip"):
            candidatos += glob.glob(os.path.join(d, patron))
    if not candidatos:
        return None
    return max(candidatos, key=os.path.getmtime)


def respaldar():
    marca = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    destino = os.path.join(RESPALDOS, marca)
    os.makedirs(destino, exist_ok=True)
    copiados = 0
    for nombre in os.listdir(AQUI):
        if nombre in FUERA or nombre.endswith(".zip"):
            continue
        origen = os.path.join(AQUI, nombre)
        try:
            if os.path.isfile(origen):
                shutil.copy2(origen, os.path.join(destino, nombre))
                copiados += 1
            elif os.path.isdir(origen):
                shutil.copytree(origen, os.path.join(destino, nombre),
                                dirs_exist_ok=True)
                copiados += 1
        except Exception:
            pass
    for v in sorted(glob.glob(os.path.join(RESPALDOS, "*")))[:-10]:
        shutil.rmtree(v, ignore_errors=True)
    return destino, copiados


def aplicar(zip_ruta):
    tocados = []
    with zipfile.ZipFile(zip_ruta) as z:
        nombres = [i.filename for i in z.infolist() if not i.is_dir()]
        # si todo viene adentro de una sola carpeta, la saco
        raices = set(n.replace("\\", "/").split("/")[0]
                     for n in nombres if "/" in n.replace("\\", "/"))
        sola = raices.pop() if len(raices) == 1 and len(nombres) == len(
            [n for n in nombres if "/" in n.replace("\\", "/")]) else None
        for info in z.infolist():
            if info.is_dir():
                continue
            nombre = info.filename.replace("\\", "/")
            if sola and nombre.startswith(sola + "/"):
                nombre = nombre[len(sola) + 1:]
            if not nombre or os.path.basename(nombre) in FUERA:
                continue
            destino = os.path.join(AQUI, *nombre.split("/"))
            carpeta = os.path.dirname(destino)
            if carpeta:
                os.makedirs(carpeta, exist_ok=True)
            with z.open(info) as fuente, open(destino, "wb") as salida:
                shutil.copyfileobj(fuente, salida)
            tocados.append(nombre)
    return tocados


def del_proyecto(rel):
    base = os.path.basename(rel)
    if base in NOMBRES_OK:
        return True
    if rel.startswith(".github/") and rel.endswith((".yml", ".yaml")):
        return True
    return base.endswith(EXTENSIONES_OK) and not base.startswith("_")


def archivos_para_subir():
    salida = []
    for raiz, carpetas, archivos in os.walk(AQUI):
        carpetas[:] = [c for c in carpetas if c not in FUERA]
        for a in archivos:
            if a in FUERA or a.endswith((".pyc", ".zip")):
                continue
            rel = os.path.relpath(os.path.join(raiz, a), AQUI).replace("\\", "/")
            if del_proyecto(rel):
                salida.append(rel)
    return sorted(salida)


class Repo(object):
    def __init__(self, token, repo, rama):
        self.repo, self.rama, self.h = repo, rama, cabeceras(token)

    def sha_remoto(self, ruta):
        r = requests.get("%s/repos/%s/contents/%s" % (API, self.repo, ruta),
                         params={"ref": self.rama}, headers=self.h, timeout=30)
        return r.json().get("sha") if r.status_code == 200 else None

    def subir(self, ruta, mensaje):
        entero = os.path.join(AQUI, *ruta.split("/"))
        cuerpo = {"message": mensaje, "branch": self.rama,
                  "content": base64.b64encode(open(entero, "rb").read()).decode()}
        sha = self.sha_remoto(ruta)
        if sha:
            if sha == sha_git(entero):
                return "igual", ""
            cuerpo["sha"] = sha
        r = requests.put("%s/repos/%s/contents/%s" % (API, self.repo, ruta),
                         headers=self.h, data=json.dumps(cuerpo), timeout=60)
        if r.status_code in (200, 201):
            return "subido", ""
        return "falla", "%s %s" % (r.status_code, r.text[:120])

    def arrancar(self):
        """Le pide a GitHub que corra el bot ahora, sin esperar al reloj."""
        for wf in ("watch.yml", "watch.yaml"):
            try:
                r = requests.post(
                    "%s/repos/%s/actions/workflows/%s/dispatches" % (API, self.repo, wf),
                    headers=self.h, data=json.dumps({"ref": self.rama}), timeout=30)
            except Exception:
                return False
            if r.status_code in (200, 204):
                return True
        return False


# =====================================================================
def main():
    titulo("ACTUALIZADOR DEL BOT")
    secretos.cargar(silencioso=True)
    solo_local = "--solo-local" in sys.argv

    # ------------------------------------------------------- 1. el parche
    zip_ruta = None
    for a in sys.argv[1:]:
        if a.lower().endswith(".zip"):
            zip_ruta = a
    zip_ruta = zip_ruta or buscar_parche()

    destino, n = respaldar()
    print("[1] copia de seguridad guardada en respaldos\\%s (%d cosas)"
          % (os.path.basename(destino), n))

    if zip_ruta and os.path.isfile(zip_ruta):
        tocados = aplicar(zip_ruta)
        print("[2] parche aplicado: %s" % os.path.basename(zip_ruta))
        print("    archivos reemplazados: %s" % ", ".join(tocados))
    else:
        print("[2] no encontre ningun zip de parche. Subo lo que ya tenes.")

    try:
        import importlib
        import version as VER
        importlib.reload(VER)
        print("    version local: v%s (%s)" % (VER.VERSION, VER.TITULO))
    except Exception:
        pass

    if solo_local:
        print("\nListo. No subi nada porque me pediste solo local.")
        return 0

    # -------------------------------------------------------- 2. los datos
    print("\n[3] revisando el acceso a GitHub")
    token, repo, rama = preparar()
    if not token or not repo:
        print("\n[!] Sin acceso a GitHub no puedo subir, pero el parche ya")
        print("    quedo aplicado en tu computadora y tenes el respaldo.")
        print("    Volve a correr esto cuando tengas la clave.")
        return 1
    print("    repositorio: %s   rama: %s" % (repo, rama))

    # ------------------------------------------------------------ 3. subir
    r = Repo(token, repo, rama)
    marca = dt.datetime.now().strftime("%d-%m %H:%M")
    subidos, iguales, fallados = [], [], []

    print("\n[4] subiendo")
    for ruta in archivos_para_subir():
        try:
            estado, detalle = r.subir(ruta, "parche %s" % marca)
        except Exception as e:
            estado, detalle = "falla", "%s %s" % (type(e).__name__, e)
        if estado == "subido":
            subidos.append(ruta)
            print("    subido    %s" % ruta)
        elif estado == "igual":
            iguales.append(ruta)
        else:
            fallados.append((ruta, detalle))
            print("    FALLO     %s   %s" % (ruta, detalle))
            # GitHub protege aparte la carpeta del reloj: si a la clave le
            # falta esa casilla contesta "no existe", que confunde muchisimo
            # porque el archivo SI existe.
            if "404" in str(detalle) and ruta.replace("\\", "/").startswith(
                    ".github/"):
                print("              (no es que falte: a la clave le falta")
                print("               la casilla  workflow  para tocar esto)")

    titulo("RESULTADO")
    print("subidos: %d" % len(subidos))
    print("ya estaban iguales: %d" % len(iguales))

    if fallados:
        print("fallaron: %d" % len(fallados))
        for ruta, detalle in fallados[:6]:
            print("  %s -> %s" % (ruta, detalle))
        print("\nSi dice 403: a la clave le falta la casilla  repo.")
        print("Si dice 409: alguien toco el repositorio, volve a correr esto.")
        print("Si dice 404 en un archivo de  .github/workflows :")
        print("  el archivo existe; lo que falta es la casilla  workflow")
        print("  en tu clave. Marcala y volve a correr esto, o abri ese")
        print("  archivo en la web de GitHub y pega el contenido a mano.")
        print("Si dice 404 en cualquier otro archivo: revisa que el nombre")
        print("  del repositorio este bien escrito.")
        return 1

    if subidos:
        if r.arrancar():
            print("\nLe pedi a GitHub que arranque el bot ahora mismo.")
        else:
            print("\nSubido. El bot va a tomar la version nueva en la")
            print("proxima vuelta, dentro de unos minutos.")
            print("(para que arranque al toque, la clave necesita tambien")
            print(" la casilla  workflow)")
        print("Cuando arranque te va a mandar al chat el aviso de")
        print("actualizacion con la lista de lo que cambio.")
    else:
        print("\nNo habia nada nuevo para subir: alla ya estaba todo igual.")
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    except KeyboardInterrupt:
        codigo = 1
    except Exception as e:
        print("\n[!] se rompio algo: %s %s" % (type(e).__name__, e))
        print("    tu respaldo esta en la carpeta respaldos.")
        codigo = 1
    if os.name == "nt":
        input("\nApreta Enter para cerrar.")
    sys.exit(codigo)
