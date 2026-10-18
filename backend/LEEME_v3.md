# Servidor v3 (etapa 2 del plan)

El servidor de Render ahora recibe a los padres v3, avisa por WhatsApp sin repetir y avisa si un nodo deja de reportar. Las rutas viejas siguen funcionando. Las tablas nuevas (`red_nodos` y `red_alertas`) se crean solas al arrancar, y las que ya tienes no se tocan.

## Qué hace

- **`POST /api/v3/latido`**: cada padre manda, cada 60 s, su estado y el de todos sus hijos (señal, % de entrega, sensores, batería, si el hijo está en su padre de respaldo).
- **`POST /api/v3/alerta`**: aviso de incendio o de prueba.
  - La misma alerta puede llegar varias veces: por reintentos, o por el padre principal y el de respaldo a la vez. El servidor la reconoce por (nodo, arranque, n° de alerta, tipo) y **avisa una sola vez**.
  - Responde OK al padre solo cuando Twilio aceptó al menos un WhatsApp. Si nada salió en 5 s, responde error y el padre avisa directo.
  - Si el padre ya avisó directo, lo registra sin repetir el aviso.
- **A quién avisa:**

  | Aviso | Va por WhatsApp a |
  |---|---|
  | Incendio | Todos los suscriptores |
  | Prueba (`MODO_PRUEBA`, botón BOOT) | `AVISOS_TECNICOS_WA` (si está vacío, todos los suscriptores) |
  | Técnico (sin señal, respaldo, batería) | Solo `AVISOS_TECNICOS_WA`: nunca al público. Sin esa variable, los avisos técnicos no salen |

- **Vigilancia cada minuto.** Avisa una vez en cada caso:
  - un nodo lleva 10 min sin reportar (si cae un padre, sus hijos van en el mismo mensaje);
  - un hijo lleva 2 min en su padre de respaldo, y cuando vuelve al principal;
  - la batería baja de 3,4 V;
  - un nodo vuelve a reportar.
- **Web:** la tarjeta nueva "Red de nodos" muestra cada padre e hijo, con estado, nivel, padre, señal, sensores, batería y hace cuánto se vio, más los últimos avisos. Además, cada nodo aparece en el mapa y en "Estado de nodos" (gris si está sin señal), y sus lecturas se guardan cada 5 min en la tabla de siempre.

## Cambios que se notan

- **Claves.** Antes cualquiera podía:
  - cambiar los umbrales;
  - ver los teléfonos de los suscriptores;
  - mandar un ROJO falso a `/api/sensors/lectura`, que disparaba WhatsApp a todos.

  Ahora:
  - Los padres usan la cabecera `X-Api-Key`.
  - La web pide la clave de administrador una vez (guardar umbrales, "Marcar atendida") y la recuerda en ese navegador.
  - En `https://…onrender.com/docs`, el botón **Authorize** acepta las dos claves.
- `/api/sensors/lectura` (nodos v2) pide `X-Api-Key`. Si todavía tienes nodos v2 funcionando, pon `PERMITIR_LECTURA_SIN_CLAVE=1` mientras tanto.
- `/api/sensors/{id}/lecturas` devuelve las últimas 1000 (`?limite=` para más). Antes devolvía todo, y la web lo pedía cada 10 s.
- El mapa ya no vuelve a centrarse cada 10 s, cambia el color de un sensor cuando cambia su nivel y no dibuja nodos sin coordenadas.
- `simulator.py` necesita la misma clave: antes de correrlo, `$env:DEVICE_API_KEY = "..."` en PowerShell. Sus lecturas aparecen en la web (incluidas las alertas), pero ya no mandan WhatsApp a los suscriptores.
- `requirements.txt` trae `tzdata`. Sin ese paquete, en Windows el servidor no arranca, porque no encuentra la zona horaria de Chile. En Render no cambia nada.

## Variables de entorno en Render (Environment)

| Variable | Qué es |
|---|---|
| `DEVICE_API_KEY` | **Obligatoria.** La misma clave que `API_KEY_DISPOSITIVO` en el `secrets.h` de cada padre |
| `ADMIN_API_KEY` | **Obligatoria.** La clave que pide la web para cambiar cosas |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_MSG_SVC_SID` | Ya las tienes (WhatsApp a suscriptores). Con el token nuevo |
| `TWILIO_FROM_WA` | Solo si no usas Messaging Service (sandbox: `whatsapp:+14155238886`) |
| `TWILIO_CONTENT_SID` | Plantilla aprobada para incendios y pruebas (ver abajo). La misma va en el `secrets.h` del padre |
| `TWILIO_CONTENT_SID_TECNICO` | Plantilla aprobada para los avisos técnicos (ver abajo) |
| `AVISOS_TECNICOS_WA` | **Necesaria para los avisos técnicos.** Tus números (y los de quien mantenga la red), separados por coma: `+569...,+569...` |
| `MINUTOS_SIN_SENAL` | 10 por defecto |
| `BATERIA_BAJA_MV` | 3400 por defecto |
| `PERMITIR_LECTURA_SIN_CLAVE` | `1` solo mientras queden nodos v2 |

Para crear una clave: `python -c "import secrets; print(secrets.token_urlsafe(24))"`.

### WhatsApp: por qué hace falta una plantilla

WhatsApp solo entrega mensajes libres a quien le escribió al número en las últimas 24 h. En el sandbox de Twilio, además, cada persona tiene que volver a mandar el código `join` cuando su sesión vence. Una alerta de incendio llega días después de la suscripción, así que sin plantilla puede no llegar (error 63016 en Twilio). Como solo usas WhatsApp, las plantillas son obligatorias para el uso real.

Con un número de WhatsApp propio en Twilio:
1. Ve a Content Template Builder.
2. Crea una plantilla de categoría **Utility** con este texto:

   ```
   🔥 Forest Fire: {{1}}
   Nodo: {{2}}
   Hora: {{3}}
   Ubicación: {{4}}
   Sensores: {{5}}
   Si confirmas fuego: Bomberos 132 · CONAF 130
   ```

3. Crea una segunda plantilla, también **Utility**, para los avisos técnicos:

   ```
   ⚠️ Forest Fire, aviso técnico: {{1}}
   ```

4. Mándalas a aprobación. Cuando queden aprobadas, pon sus SID (`HX…`) en `TWILIO_CONTENT_SID` y `TWILIO_CONTENT_SID_TECNICO`. El primero también va en el `secrets.h` de cada padre, para su aviso directo.

Sin esas variables, el servidor manda el texto completo, como hasta ahora (solo sirve dentro de las 24 h).

## Cómo publicarlo

1. Copia estos archivos a tu repositorio, en las mismas rutas:

   | Carpeta | Archivos |
   |---|---|
   | raíz | `requirements.txt`, `simulator.py`, `forest_fire_alerta_demo.py` |
   | `backend/` (ejemplo) | `.env.example`: no reemplaza tu `.env`, solo muestra qué variables lleva |
   | `backend/` | `main.py`, `database.py`, `horario.py`, `seguridad.py`, `avisos_v3.py`, `notifications.py`, `models/red.py`, `schemas/schemas.py`, `routers/red.py`, `routers/config.py`, `routers/alerts.py`, `routers/sensors.py`, `routers/suscriptores.py`, `pruebas/` |
   | `frontend/` | la carpeta completa: `index.html`, `css/style.css` y los 8 archivos de `js/` |

   El frontend que subiste el 18/10 era igual a la base de estos cambios, así que puedes reemplazar la carpeta `frontend/` entera. `notifications.py`, `schemas.py` e `ia.js` traen los cambios del 11/10, que tu copia aún no tenía; `routers/sensors.py` los necesita. Las versiones anteriores quedaron en `_respaldo_2026-10-11/` y `_respaldo_2026-10-18/`.
2. En Render, agrega `DEVICE_API_KEY`, `ADMIN_API_KEY` y `AVISOS_TECNICOS_WA` **antes** de hacer push.
3. Haz push. Render y Netlify se actualizan solos. Revisa que `…/docs` muestre la sección "Red v3".
4. En cada padre:
   - en `secrets.h`, `API_KEY_DISPOSITIVO` igual a `DEVICE_API_KEY`;
   - en `config.h`, `USAR_SERVIDOR 1`.
5. Prueba: aprieta BOOT en un hijo. Debe llegar "PRUEBA DE ENLACE" por WhatsApp a los números técnicos y el aviso debe aparecer en la web, en "Últimos avisos".
6. Opcional: un monitor gratis (UptimeRobot o cron-job.org) que abra `…/api/v3/revisar` cada 5 min.
   - Mientras algún padre reporta, Render no se duerme, y el aviso de "sin señal" sale a los 10 min, antes de que se duerma a los 15.
   - El monitor sirve para que nunca se duerma.

Cada nodo nuevo crea su propio sensor en la tabla `sensores`. Si quieres que el padre v3 use el sensor que ya existe (por ejemplo, el n° 1 de los gráficos), haz `PUT /api/v3/nodos/{codigo}` con `{"sensor_id": 1}` en `/docs`. Con la misma ruta pones una ubicación en texto o coordenadas a mano para un hijo sin `HIJO_LAT`. `DELETE` da de baja un nodo que ya no existe.

## Pruebas en el PC

Para correr el servidor en tu PC, copia `backend/.env.example` como `backend/.env` y llénalo. El servidor no usa `TWILIO_PHONE_NUMBER`, `TWILIO_WHATSAPP_NUMBER` ni `ALERT_PHONE_NUMBER`; puedes borrarlas.

```
pip install -r requirements.txt pytest httpx
sh firmware/herramientas/simulacion_v3/ejecutar.sh      # opcional: genera lo que mandan los padres simulados
python -m pytest backend/pruebas -q
```

Usa SQLite y no manda nada de verdad. Hoy pasan **36 de 36**:
- 18 del servidor: claves, alerta que llega 3 veces y avisa 1, dos padres a la vez, el padre que ya avisó directo, WhatsApp caído, pruebas a técnicos, plantillas, avisos técnicos que nunca van al público, el fuego que sigue, nodos sin señal y de vuelta, respaldo, batería, edición de nodos.
- 18 que repiten contra el servidor real todo lo que mandaron los `.ino` en cada escenario de la simulación. El servidor decide igual que el modelo de la simulación en cada aviso.

No probé aquí la conexión real con Twilio ni con el Postgres de Render.
