# Problemas y quejas

Aca se anota todo lo que no funciona o no gusta. Los chats se pierden, los
archivos no. Si un dia le pedis ayuda a otra IA, pasale este archivo.

Formato: fecha, que paso, estado.
Estados: `abierto`, `en eso`, `resuelto`, `no se va a arreglar`.

---

## Abiertos

_(nada por ahora)_

---

## Resueltos

| Fecha | Problema | Como se resolvio |
|---|---|---|
| 03/08 | avisaba de `Inicio`, `Mis Cursos` y otros del menu | lista `PALABRAS_MENU` |
| 03/08 | clasificaba mal las guias como material | se arreglo `tipo_de()` |
| 03/08 | los cuatro FALTA de `probar_local.py` | no era falla, faltaba cargar los datos, se agrego `secretos.py` |
| 03/08 | un trabajo con 3 PDF llegaba como 4 avisos | ahora se agrupan en uno solo |
| 03/08 | anclaba hasta la pantalla de Ajustes | cuando el texto no cambiaba, la mensajeria devolvia error, el bot creia que fallo y mandaba un panel nuevo y lo anclaba. Ahora ese caso cuenta como exito y se ancla una sola vez |
| 03/08 | los botones tardaban entre 5 y 20 minutos | el bot ahora queda despierto de 07:00 a 02:00 y contesta en un segundo |
| 03/08 | el anclado molestaba igual | se apago del todo, `ANCLAR_PANEL = False` en `fuentes.py` |
| 03/08 | tocar el titulo abria la pagina y habia que bajar el archivo a mano | ahora el bot baja el archivo y te lo deja en el chat |
| 03/08 | los .docx y .pptx se quedaban sin resumen | se les saca el texto solo, sin instalar nada |

---

## Como anotar algo

Agrega una linea arriba de todo en **Abiertos**, con la fecha y lo que viste.
Si tenes el mensaje del bot o el registro de GitHub, pegalo abajo.

Ejemplo:

```
### 15/09 - no me aviso de una guia
El profe subio la guia 4 a las 10:00 y me llego recien a las 11:30.
Estado: abierto
```

---

## Ideas para mas adelante

No son problemas, son cosas que quedaron pensadas y sin hacer.

- avisar cuando cambia una nota, leyendo la pagina de calificaciones
- detectar el mismo archivo subido a las dos plataformas y avisar una vez
- estadisticas del semestre: que ramo sube mas material, en que dias
- exportar los pendientes a un calendario
