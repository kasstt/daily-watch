# -*- coding: utf-8 -*-
"""Prueba todo en tu computadora antes de subirlo.

Se corre asi, parado en la carpeta:

    python probar_local.py

No avisa de material nuevo, solo revisa que cada pieza funcione.
"""
import os
import sys
import time

import secretos


def titulo(t):
    print("\n" + "=" * 56)
    print(t)
    print("=" * 56)


def main():
    secretos.cargar()

    import fuentes as CFG
    import ia as IA
    import notificar as N
    import watcher as W

    titulo("REVISION PREVIA")
    listas = []
    for f in CFG.FUENTES:
        hay = all(os.environ.get(f[k], "").strip()
                  for k in ("env_url", "env_user", "env_pass"))
        print("fuente %s        : %s" % (f["clave"], "ok" if hay else "FALTA"))
        if hay:
            listas.append(f)
    cals = [n for n in ("CAL_URL", "CAL_URL_B") if os.environ.get(n)]
    print("agenda de plazos: %s" % ("%d calendario(s)" % len(cals) if cals
                                    else "sin calendarios (es opcional)"))
    print("mensajeria      : %s" % ("ok" if N.listo() else "FALTA"))
    print("memoria en gist : %s" % ("ok" if os.environ.get("GH_TOKEN") else "FALTA"))
    print("resumen con IA  : %s" % ("ok" if os.environ.get("IA_KEY") else "FALTA"))

    if not N.listo():
        print("")
        print("Sin TG_TOKEN y TG_CHAT no puedo probar nada.")
        print("Abri mis_datos.txt, completalos y volve a correr esto.")
        return 1

    titulo("1) probando el mensaje")
    mid = N.enviar("Prueba. Si ves esto, la mensajeria anda.", teclado_fijo=True)
    print("mandado" if mid else
          "NO se pudo. Revisa el token y el chat, y escribile vos primero al bot.")

    titulo("2) probando el formato de una tarjeta")
    ejemplo = ("\U0001F4D8 <b>RAMO DE PRUEBA</b>\n"
               + N.enlace("Trabajo 1", "https://example.com") + "\n"
               + N.enlace("Anexo A", "https://example.com") + "\n"
               "\u23F3 entrega vie 14 ago 23:55\n"
               + N.cita("\U0001F9E0 Informe grupal sobre balances de energia. "
                        "Se entrega en equipo de tres.\n\n"
                        "- Cubre los capitulos 3 y 4\n"
                        "- Pide graficos hechos a mano\n"
                        "- Descuenta un punto por dia de atraso",
                        plegable=True)
               + "\n<i>20:41</i>")
    N.enviar(ejemplo, botones=N.teclado([[
        ("\u2705 hecho", "hecho:demo"), ("\u23F0 3h", "dormir:demo"),
        ("\U0001F4DD nota", "nota:demo"), ("\U0001F515", "basta:demo")]]))
    print("mandado. Fijate que la cita se pueda desplegar.")

    titulo("3) probando la animacion")
    v = W.Vigilante()
    avisar, cerrar = v.animar("Guia de prueba")
    for etapa in CFG.ORDEN_ETAPAS:
        texto = CFG.ETAPAS[etapa]
        avisar(texto % "2 archivos" if "%s" in texto else texto)
        time.sleep(1.2)
    cerrar("Asi queda cuando termina.")
    print("listo")

    titulo("4) probando la entrada a las plataformas")
    for f in listas:
        s, base = v._entrar(f)
        print("fuente %s: %s" % (f["clave"], "entre bien" if s else "NO pude entrar"))
        if not s:
            continue
        _, leer = W.ADAPTADORES[f["modo"]]
        grupos, viejos = leer(s, base)
        print("  ramos activos: %d   anteriores: %d"
              % (len(grupos or []), len(viejos)))
        for g in (grupos or [])[:8]:
            cant = "no pude leer" if g.get("items") is None else "%d cosas" % len(g["items"])
            print("   - %-42s %s" % (g["nombre"][:42], cant))

    titulo("5) probando la agenda de plazos")
    eventos = W.leer_agenda()
    print("%d plazos leidos" % len(eventos))
    for e in eventos[:5]:
        print("   - %s  %s" % (e["vence"].strftime("%d/%m %H:%M"), e["titulo"][:50]))

    titulo("6) probando la memoria")
    print("modo: %s" % v.modo)
    if v.modo == "repo" and os.environ.get("GH_TOKEN"):
        print("Pusiste GH_TOKEN pero quedo en el repositorio, algo fallo.")

    titulo("7) probando la IA")
    if not IA.disponible(v.estado):
        print("apagada. El bot funciona igual, sin la linea del cerebro.")
    else:
        r = IA.resumir(v.estado, None, {
            "grupo": "Prueba", "titulo": "Trabajo 2",
            "descripcion": ("Elaborar un informe de laboratorio sobre el ciclo "
                            "de Rankine. Se entrega en grupos de tres personas, "
                            "a mas tardar el viernes 14 a las 23:55. Debe incluir "
                            "portada, marco teorico, calculos y conclusiones. "
                            "Se descuenta un punto por cada dia de atraso."),
            "vence": "", "archivos": []})
        if r:
            print("corto : %s" % r["corto"])
            print("largo : %s" % (r["largo"][:200] or "(vacio, no hizo falta)"))
        else:
            print("no contesto. Revisa IA_KEY o el nombre del modelo.")

    titulo("8) abriendo el panel")
    v.abrir_panel(saludar=True)
    print("mandado. Toca los botones y despues corre watcher.py para que los atienda.")

    print("")
    print("Terminado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
