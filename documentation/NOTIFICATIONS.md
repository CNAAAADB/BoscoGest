# Sistema de Notificaciones

## Descripción general

BoscoGest implementa un sistema de notificaciones en tiempo real que combina persistencia en PostgreSQL con entrega instantánea vía WebSocket. Los usuarios reciben notificaciones sobre eventos relevantes (publicaciones, actividades, inscripciones, etc.) tanto en tiempo real cuando están conectados como en modo catch-up cuando vuelven a la aplicación tras estar offline.

---

## Arquitectura

```
┌─────────────┐     notify()      ┌─────────────────────┐
│  Service     │ ─────────────────>│ NotificationService  │
│ (Magazine,   │                   │                      │
│  Activity,   │                   │  1. Resolve recipients│
│  Comment…)   │                   │  2. Filter preferences│
└─────────────┘                   │  3. Bulk insert DB    │
                                  │  4. Enqueue WS push   │
                                  └──────────┬────────────┘
                                             │
                         enqueue() ──────────┤
                   (thread-safe bridge)      │
                                             ▼
                                  ┌──────────────────────┐
                                  │ NotificationManager   │
                                  │  (singleton)          │
                                  │                       │
                                  │  asyncio.Queue        │
                                  │  ──> dispatch loop    │
                                  │  ──> WebSocket send   │
                                  └──────────────────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │  WebSocket clients    │
                                  │  /notifications/ws    │
                                  └──────────────────────┘
```

### Componentes clave

| Componente | Ubicación | Responsabilidad |
|-----------|-----------|-----------------|
| `Notification` (modelo) | `app/models/notification_model.py` | Persistencia de notificaciones en PostgreSQL |
| `NotificationPreference` (modelo) | `app/models/notification_model.py` | Preferencias de notificación por usuario y tipo de evento |
| `NotificationRepository` | `app/repositories/notification_repository.py` | Queries: listado, conteo, marcado como leído, borrado |
| `NotificationService` | `app/services/notification_service.py` | Lógica de negocio: resolución de destinatarios, filtrado por preferencias, emisión |
| `NotificationManager` | `app/services/notification_manager.py` | Singleton: gestión de conexiones WebSocket, cola async, dispatch en tiempo real |
| `notification_router` | `app/api/v1/notification_router.py` | Endpoints REST + WebSocket |

### Puente sync → async

Los servicios de negocio (MagazineService, ActivityService, etc.) se ejecutan en threads del pool de Uvicorn (sincronos). El NotificationManager opera en el event loop async de la aplicación. El puente entre ambos mundos se realiza mediante:

```python
self._loop.call_soon_threadsafe(self._queue.put_nowait, (user_id, payload))
```

Este mecanismo es thread-safe y permite que los servicios síncronos encolen notificaciones sin bloquear ni generar condiciones de carrera.

---

## Tipos de notificación (EventType)

| Evento | Clave | Descripción | Servicio emisor | Destinatarios |
|--------|-------|-------------|-----------------|---------------|
| Revista publicada | `magazine_published` | Se publica una nueva revista | `MagazineService.create_magazine()` | Todos los miembros de la entidad |
| Actividad creada | `activity_created` | Se crea una nueva actividad | `ActivityService.create_activity()` | Todos los miembros de la entidad |
| Actividad actualizada | `activity_updated` | Se modifica una actividad existente | `ActivityService.update_activity()` | Todos los miembros de la entidad |
| Inscripción aceptada | `registration_accepted` | Se acepta la inscripción de un usuario en una actividad | `ActivityService.accept_registration()` | El usuario inscrito |
| Inscripción rechazada | `registration_rejected` | Se rechaza la inscripción de un usuario en una actividad | `ActivityService.reject_registration()` | El usuario inscrito |
| Comunicación publicada | `communication_published` | Se publica una nueva comunicación | `CommunicationService.create_communication()` | Todos los miembros de la entidad |
| Nuevo comentario | `comment_added` | Se añade un comentario a una comunicación | `CommentService.create_comment()` | Autor de la comunicación + comentaristas previos |
| Recurso publicado | `resource_published` | Se publica un nuevo recurso formativo | `ResourceService.create_resource_*()` | Todos los miembros de la entidad |
| Membresía creada | `membership_created` | Se crea una membresía para un usuario | `MembershipService.create_membership()` | El usuario añadido |
| Mensaje de chat recibido | `chat_message_received` | Se envía un mensaje en una conversación de chat | `ChatService.send_message()` / `send_file_message()` | Miembros offline de la conversación que no la tengan silenciada |
| Solicitud de alta recibida | `membership_request_created` | Un usuario solicita unirse a una entidad | `MembershipRequestService.create_request()` | Usuarios con `memberships:review` en la entidad |
| Solicitud de alta aceptada | `membership_request_accepted` | Un admin acepta la solicitud de alta | `MembershipRequestService.accept_request()` | El usuario solicitante |
| Solicitud de alta rechazada | `membership_request_rejected` | Un admin rechaza la solicitud de alta | `MembershipRequestService.reject_request()` | El usuario solicitante |
| Cuota asignada | `fee_generated` | Se generan asignaciones de una cuota a socios | `FeeService.generate_assignments()` | Los socios seleccionados a los que se generó la cuota |
| Cuota pagada | `fee_paid` | Un admin marca una asignación como pagada | `FeeService.update_assignment_status()` | El socio de la cuota |
| Cuota vencida | `fee_overdue` | El mantenimiento diario marca una cuota pendiente como vencida | `FeeService.run_maintenance()` (sistema) | El socio de la cuota |
| Recordatorio de cuota | `fee_reminder` | Aviso `reminder_days` antes del vencimiento | `FeeService.run_maintenance()` (sistema) | El socio de la cuota |
| Cuota renovada | `fee_renewed` | Renovación automática del siguiente período | `FeeService.run_maintenance()` (sistema) | Los socios renovados |

> Las notificaciones de mantenimiento (`fee_overdue`/`fee_reminder`/`fee_renewed`) son **de sistema**: `notify()` se llama con `actor=None` (la columna `actor_id` es nullable).

---

## Resolución de destinatarios

Existen dos estrategias de resolución de destinatarios:

### 1. Por membresía en la entidad (por defecto)
Cuando no se pasa `recipient_ids` a `notify()`, el servicio resuelve automáticamente todos los usuarios con membresía activa en la entidad, excluyendo al actor que generó el evento.

**Se usa en:** `magazine_published`, `activity_created`, `activity_updated`, `communication_published`, `resource_published`

### 2. Destinatarios explícitos
Cuando se pasa `recipient_ids`, las notificaciones se envían únicamente a esos usuarios (siempre excluyendo al actor).

**Se usa en:**
- `registration_accepted` / `registration_rejected` → el usuario inscrito
- `comment_added` → autor de la comunicación + comentaristas previos
- `membership_created` → el usuario añadido
- `membership_request_created` → usuarios con `memberships:review` en la entidad (resueltos en `_get_entity_reviewer_ids()`)
- `membership_request_accepted` / `membership_request_rejected` → el usuario solicitante
- `fee_generated` → los socios seleccionados al generar las asignaciones
- `fee_paid` / `fee_overdue` / `fee_reminder` → el socio de la cuota; `fee_renewed` → los socios renovados

---

## Preferencias de usuario

Cada usuario puede habilitar o deshabilitar notificaciones por tipo de evento. Por defecto, todas las notificaciones están habilitadas.

### Modelo `NotificationPreference`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user_id` | FK → users | Usuario |
| `event_type` | String(50) | Tipo de evento (clave del enum) |
| `in_app_enabled` | Boolean | Habilitar notificación in-app (default: true) |
| `email_enabled` | Boolean | Habilitar notificación por email (default: false, reservado para futuro) |

Si un usuario tiene `in_app_enabled = false` para un tipo de evento, no recibirá notificaciones de ese tipo.

---

## API REST

Todos los endpoints requieren autenticación JWT.

### Listado y lectura

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/notifications/` | Listar notificaciones del usuario. Params: `unread` (bool), `event_type` (str), `skip`, `limit` |
| `GET` | `/notifications/unread-count` | Número de notificaciones no leídas |
| `GET` | `/notifications/event-types` | Lista de tipos de evento disponibles con etiquetas |

### Acciones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `PUT` | `/notifications/{id}/read` | Marcar una notificación como leída |
| `PUT` | `/notifications/read-all` | Marcar todas las notificaciones como leídas |
| `DELETE` | `/notifications/{id}` | Eliminar una notificación |

### Preferencias

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/notifications/preferences` | Obtener preferencias del usuario |
| `PUT` | `/notifications/preferences` | Actualizar preferencias |

#### Ejemplo: Actualizar preferencias
```json
PUT /notifications/preferences
{
    "preferences": [
        {
            "event_type": "magazine_published",
            "in_app_enabled": false,
            "email_enabled": false
        },
        {
            "event_type": "comment_added",
            "in_app_enabled": true,
            "email_enabled": false
        }
    ]
}
```

---

## WebSocket

### Conexión

```
ws://host/api/v1/notifications/ws?token=<JWT>
```

El servidor valida el JWT en el handshake. Si el token es inválido o el usuario no existe, cierra con código `4001`.

### Mensajes entrantes (cliente → servidor)

| Mensaje | Descripción |
|---------|-------------|
| `ping` | Keepalive. El servidor responde con `pong` |

### Mensajes salientes (servidor → cliente)

Cada notificación se envía como JSON:

```json
{
    "id": 42,
    "event_type": "activity_created",
    "resource_type": "activities",
    "resource_id": 15,
    "entity_id": 3,
    "title": "Nueva actividad: Campamento de verano",
    "body": null,
    "data": null,
    "actor": {
        "id": 1,
        "name": "Juan",
        "surname": "García"
    },
    "is_read": false,
    "created_at": "2026-02-15T12:30:00"
}
```

### Ciclo de vida

1. El cliente establece la conexión WebSocket con su JWT
2. El servidor registra la conexión en `NotificationManager`
3. Cuando un servicio emite una notificación:
   - Se persiste en DB
   - Se encola en `NotificationManager._queue`
   - El dispatch loop envía el JSON a las conexiones activas del destinatario
4. Al desconectarse, el servidor elimina la referencia

---

## Modelo de datos

### Tabla `notifications`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | Serial PK | Identificador |
| `recipient_id` | FK → users | Usuario destinatario |
| `actor_id` | FK → users (nullable) | Usuario que generó el evento |
| `event_type` | String(50) | Tipo de evento |
| `resource_type` | String(50) | Tipo de recurso (activities, magazines, etc.) |
| `resource_id` | Integer (nullable) | ID del recurso relacionado |
| `entity_id` | FK → entities | Entidad asociada |
| `title` | String(255) | Título de la notificación |
| `body` | Text (nullable) | Cuerpo adicional |
| `data` | JSON (nullable) | Datos arbitrarios extras |
| `is_read` | Boolean | Leída o no |
| `read_at` | Timestamp (nullable) | Fecha de lectura |
| `created_at` | Timestamp | Fecha de creación (server default) |

**Índice compuesto:** `(recipient_id, is_read, created_at)` para consultas eficientes del inbox.

### Tabla `notification_preferences`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | Serial PK | Identificador |
| `user_id` | FK → users | Usuario |
| `event_type` | String(50) | Tipo de evento |
| `in_app_enabled` | Boolean | Habilitar in-app (default: true) |
| `email_enabled` | Boolean | Habilitar email (default: false) |

**Constraint único:** `(user_id, event_type)`

---

## Permisos

Se han creado los permisos RBAC para el recurso `notifications`:

- `notifications_create_permission`
- `notifications_list_permission`
- `notifications_read_permission`
- `notifications_update_permission`
- `notifications_delete_permission`
- `notifications_assign_permission`
- `notifications_manage_permission`

Asignación por rol:
- **superadmin / admin:** todos los permisos
- **socio:** solo `list` y `read`

---

## Extensibilidad

### Añadir un nuevo tipo de notificación

1. Añadir el valor al enum `EventType` en `app/services/notification_service.py`
2. Añadir la etiqueta en español en `EVENT_TYPE_LABELS`
3. Llamar a `self.notification_service.notify()` desde el servicio correspondiente

### Email (futuro)

El campo `email_enabled` en `NotificationPreference` está preparado para una futura integración con AWS SES. Cuando se implemente, el servicio de notificaciones podrá enviar emails además de las notificaciones in-app, respetando las preferencias del usuario.

### Chat (implementado)

El módulo de chat usa su propio `ChatManager` (singleton independiente, mismo patrón que `NotificationManager`) para la entrega de mensajes en tiempo real vía WebSocket. Adicionalmente, `ChatService` delega en `NotificationService` para emitir `chat_message_received` a los usuarios que están offline o con la conversación silenciada, de modo que les llegue la notificación in-app cuando no están activos en el chat.


---

## Notificaciones push (backend)

Canal adicional al WebSocket, para avisar a quien no tiene la aplicación
abierta. **Implementado en el servidor; falta la parte del cliente y las
credenciales.**

### Cómo encaja

`notify()` sigue haciendo lo mismo —resolver destinatarios, filtrar por
preferencias, persistir y encolar el WebSocket— y al final llama a `_push()`:

```
notify()
  ├── bulk_create + commit          (siempre)
  ├── notification_manager.enqueue  (WebSocket, a los conectados)
  └── _push()                       (FCM, solo a los desconectados)
```

Solo a los desconectados a propósito: a quien tiene la aplicación abierta ya le
ha llegado por WebSocket, y recibir las dos cosas a la vez es lo que hace que la
gente acabe apagando las notificaciones.

### Componentes

| Componente | Ubicación |
|-----------|-----------|
| `DeviceToken` (modelo) | `app/models/notification_model.py` |
| `DeviceTokenRepository` | `app/repositories/notification_repository.py` |
| `push_service` | `app/services/push_service.py` |
| Endpoints de alta/baja | `POST` y `DELETE /notifications/devices` |
| Preferencia `push_enabled` | `NotificationPreference` |
| Migración | `a1b2c3d4e5f6_push_notification_devices.py` |

### Por qué FCM y no APNs directamente

En iOS el push lo entrega APNs obligatoriamente y en Android lo entrega FCM, así
que hacen falta los dos de todas formas. FCM sabe hablar con APNs, de modo que
usarlo para ambos deja un solo camino de código y un solo juego de credenciales
en el servidor.

### Sin credenciales no pasa nada

`FCM_PROJECT_ID` y `FCM_CREDENTIALS_FILE` vacíos ⇒ no se envía nada y queda un
aviso en el log, igual que el correo cuando falta `SES_SENDER_EMAIL`. El
desarrollo local y los tests no necesitan un proyecto de Firebase.

### Decisiones que conviene no deshacer

- **El aviso no lleva datos personales.** En `data` van solo identificadores, y
  el título y el cuerpo son genéricos: la notificación se ve en la pantalla
  bloqueada, a la vista de cualquiera que coja el móvil.
- **Un fallo de push nunca tumba la operación que lo originó.** La notificación
  ya está guardada y se verá al abrir la aplicación.
- **Los tokens que FCM rechaza se borran**, pero solo los que declara muertos
  (`UNREGISTERED`, `INVALID_ARGUMENT`, 404). Un 500 o un corte de red son
  transitorios y el dispositivo se conserva.
- **El token es único, no el usuario.** Un móvil puede cambiar de dueño; el
  registro se reasigna en vez de duplicarse, o el anterior seguiría recibiendo
  los avisos de quien usa ahora ese teléfono.
- **Las rutas `/devices` van declaradas antes que `/{notification_id}`**, o
  FastAPI las casa por ahí y responde 422.

### Lo que falta

1. **Proyecto de Firebase**: crear, descargar el JSON de la cuenta de servicio
   y rellenar las dos variables de entorno.
2. **Clave APNs** (`.p8`) del portal de Apple, subida a Firebase, para iOS.
3. **`google-services.json`** en `android/app/`, para Android. Sin él, el
   `register()` del plugin lanza en Java «Default FirebaseApp is not
   initialized» y **cierra la aplicación**: le pasó a la versión del 29 de
   septiembre en cada inicio de sesión con las notificaciones permitidas.
   Desde el 26 de octubre `npm run config` comprueba si el fichero existe y lo
   anota en `environment.prod.ts` (`androidPush`); sin él, la app no pide
   token en Android y avisa por consola. Hay que ponerlo **antes** de
   `npm run cap:sync`, o la compilación saldrá sin push aunque el fichero
   esté.
4. **Capacidad Push** en el target de iOS y su entitlement.
5. **Cliente**: `@capacitor/push-notifications`, permiso, registro del token
   contra `POST /notifications/devices`, baja al cerrar sesión y navegación al
   tocar el aviso.
6. **Política de privacidad**: Apple y Google pasan a ser encargados del
   tratamiento, con tráfico fuera del EEE. El texto actual dice lo contrario y
   hay que corregirlo antes de publicar con push activo.
