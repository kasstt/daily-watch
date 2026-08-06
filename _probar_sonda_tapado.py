# -*- coding: utf-8 -*-
# Prueba suelta: que la sonda no deje escapar el nombre del dueno.
# Usa la linea exacta que se escapo en el informe de verdad.
import os
import sonda as S

malas = []


def revisar(titulo, condicion, detalle=""):
    if not condicion:
        malas.append(titulo)
    print("%-4s %s%s" % ("OK" if condicion else "MAL", titulo,
                         "" if condicion else "  <- " + str(detalle)))


def limpiar():
    del S.TAPAR[:]
    del S.PALABRAS_TAPADAS[:]
    del S.LINEAS[:]
    S._PATRONES.clear()


# Nombre inventado, con la misma forma que el de verdad: cuatro partes y una
# tilde.  Aca no puede vivir ningun dato real.
NOMBRE = "Juan Andr\u00e9s Miranda Fuentes"
GRITADO = "JUAN ANDR\u00c9S MIRANDA FUENTES"
LINEA_DEL_CARTEL = ("Actualmente ha iniciado sesi\u00f3n como %s, necesita salir "
                    "antes de continuar" % GRITADO)

# ==================================== 1. tapa aunque este a los gritos
limpiar()
S.guardar_secreto(NOMBRE, "TU_NOMBRE")
salida = S.tapar(LINEA_DEL_CARTEL)
revisar("el nombre en may\u00fasculas queda tapado",
        "MIRANDA" not in salida.upper(), salida)
revisar("y en su lugar dice qu\u00e9 era", "TU_NOMBRE" in salida, salida)

# ==================================== 2. tapa aunque cambien las tildes
limpiar()
S.guardar_secreto("Oscar Gutierrez", "UN_PROFE")
con_tilde = S.tapar("anfitri\u00f3n: \u00f3scar Guti\u00e9rrez")
revisar("con tildes distintas, igual lo tapa",
        "scar" not in con_tilde and "rrez" not in con_tilde, con_tilde)

# ============ 3. aprende el nombre de la propia pagina, sin tenerlo escrito
limpiar()
S.aprender_nombre("<div class='modal'>Actualmente ha iniciado sesi\u00f3n como "
                  "%s, necesita salir antes de continuar.</div>" % GRITADO)
aprendido = S.tapar("hola %s, bienvenido" % NOMBRE)
revisar("aprende tu nombre de c\u00f3mo te saluda la plataforma",
        "Miranda" not in aprendido, aprendido)
revisar("y tambi\u00e9n tapa cada parte por separado",
        "Fuentes" not in S.tapar("trabajo de Fuentes"), S.tapar("trabajo de Fuentes"))

# ===== 4. lo importante: lo que ya estaba escrito ANTES tambien queda tapado
limpiar()
S.SALIDA = "/tmp/sonda_de_prueba.txt"
S.escribir("pagina 1: todo normal por aca")
S.escribir("pagina 2: %s aparece por primera vez" % GRITADO)   # todavia no sabe
S.aprender_nombre(LINEA_DEL_CARTEL)                            # recien lo aprende
S.escribir("pagina 30: y aca de nuevo %s" % NOMBRE)
S.volcar()
guardado = open(S.SALIDA, encoding="utf-8").read()
revisar("lo escrito antes de aprenderlo tambi\u00e9n queda tapado",
        "MIRANDA" not in guardado.upper() and "FUENTES" not in guardado.upper(),
        guardado)
revisar("y el informe sigue sirviendo para algo",
        "pagina 30" in guardado and "pagina 1" in guardado, guardado[:120])

# ============ 5. no se lleva puesto lo que SÍ tiene que verse
limpiar()
S.guardar_secreto(NOMBRE, "TU_NOMBRE")
util = S.tapar("TALLER DE PRUEBA - reuni\u00f3n 05-08-2026 12:40 clave 123456")
revisar("el nombre del ramo se sigue leyendo",
        "TALLER DE PRUEBA" in util, util)
revisar("y la hora de la clase tambi\u00e9n", "12:40" in util, util)

# ============ 6. el correo y la llave de sesión siguen tapados
limpiar()
correo = S.tapar("contacto: alguien@ejemplo.cl y sesskey='ABC123xyz'")
revisar("el correo no aparece", "@ejemplo" not in correo, correo)
revisar("la llave de sesi\u00f3n tampoco", "ABC123xyz" not in correo, correo)

print("\nresultado: %s" % ("TODO BIEN" if not malas else "%d MALAS" % len(malas)))
raise SystemExit(1 if malas else 0)
