# SOFTWARE REQUIREMENTS SPECIFICATION

## BoscoGest -- Plataforma SaaS Multientidad

**Version 1.0 aprobada**

Confederacion Nacional de Espana de AA.AA de DB

Fecha: 12/08/2025

---

## Revision History

| Nombre | Fecha | Motivo del cambio | Version |
|---|---|---|---|
| Clara Contreras | 12/08/2025 | Primera entrega a desarrollo | 1.0 |

---

## Indice general

1. [Introduccion](#1-introduccion)
2. [Descripcion general](#2-descripcion-general)
3. [Requisitos de Interfaces Externas](#3-requisitos-de-interfaces-externas)
4. [Caracteristicas del sistema](#4-caracteristicas-del-sistema)
5. [Otros requisitos no funcionales](#5-otros-requisitos-no-funcionales)
6. [Otros requisitos (abierto a cambios)](#6-otros-requisitos-abierto-a-cambios)
7. [Apendices](#7-apendices)

---

## 1 Introduccion

### 1.1. Proposito

Este documento especifica de forma formal y verificable los requisitos del producto BoscoGest -- Plataforma SaaS Multientidad (version 1.0 para entrega a desarrollo). Cubre el alcance del MVP incluyendo: personalizacion de vistas, gestion de roles y permisos por nivel, formularios de inscripcion, calculo de cuotas (incluida cuota reversible) y plan de implantacion. Este SRS describe el sistema completo.

### 1.2. Convenciones del documento

- **Idioma:** espanol (ES).
- **Identificacion de requisitos:** REQ-{MODULO}-{n} (p.ej., REQ-CAL-01). Los requisitos marcados como TBD indican definicion pendiente.
- **Prioridad:** Alta (A), Media (M), Baja (B).
- **Roles y permisos** se refieren a una lista maestra de acciones: ver, crear, editar, eliminar, publicar, moderar, gestionar_permisos, configurar_vistas, gestionar_entidades, ver_datos_sensibles, gestionar_pagos, ver_dash_*, exportar_RGPD.

### 1.3. Audiencia prevista y sugerencias de lectura

Este SRS esta dirigido a: patrocinadores (confederacion/federaciones), equipo de producto, UX, desarrollo, QA, soporte e implantacion. Se recomienda:

1. Cap. 2 (Descripcion general) para contexto y alcance.
2. Cap. 3--4 para interfaces y funcionalidades detalladas.
3. Cap. 5 para requisitos no funcionales y reglas de negocio.
4. Apendices para modelo de datos, roadmap e implantacion.

### 1.4. Alcance del proyecto

**Aplicaciones:** Web y app movil.

**Tenancy:** aislamiento logico por entidad; alta de entidades por Superadmin. Vistas activables/desactivables (salvo Perfil), renombrables y reordenables por entidad. Gestion de usuarios extendida, contenidos (Calendario/Actividades con inscripcion, Noticias, Revista en PDF, Recursos), Chat, Tienda basica, Dashboard/Organigrama. Pagos basicos (pasarela opcional o justificante) y cuotas. Notificaciones in-app/email/push y boletin trimestral. Importacion legada y exportacion RGPD. Remesas SEPA: TBD en esta version. Objetivos medibles incluyen: numero de asociaciones, nuevos socios por curso y por local, actividades locales, socios por local.

### 1.5. Referencias

- Normativa RGPD y derechos ARCO-P.
- WCAG 2.1 AA (accesibilidad).
- Esquemas SEPA pain.008/pain.001 (TBD).

---

## 2 Descripcion general

### 2.1. Perspectiva del producto

BoscoGest es una plataforma multientidad (multitenant) para confederaciones, federaciones y asociaciones locales. Es un producto nuevo, auto-contenido, que reemplaza procesos dispersos (hojas de calculo, mensajeria y herramientas de terceros) y centraliza gestion de miembros, contenidos, actividades y cuotas con personalizacion por entidad (branding, subdominio y vistas).

### 2.2. Funciones del producto

A alto nivel, el sistema permite:

- Tenancy y branding por entidad (subdominios, logo, colores).
- Gestion de usuarios y roles/permisos por nivel organizativo.
- Vistas de contenido: Calendario/Actividades (con inscripcion y pagos), Noticias, Revista (PDF), Recursos formativos, Chat, Tienda, Perfil (obligatoria), Dashboard/Organigrama, Pagos (remesas TBD), Crear, Custom.
- Cuotas: importe fijo por socio; cuota reversible.
- Notificaciones in-app, email, push y boletin trimestral.
- Datos: importacion/exportacion CSV.

### 2.3. Clases de usuario y caracteristicas

- Superadmin (plataforma).
- Admin Confederacion (admin general de su entidad).
- Admin Federacion, Admin Local.
- Editor/Comunicaciones (Secretario), Tesorero, Moderador.
- Socio/Usuario, Invitado.

El Admin general puede definir roles personalizados marcando permisos desde la lista maestra. La visibilidad por defecto se limita al nivel de alta (local o federal). Se admite multi-pertenencia con roles distintos por entidad.

### 2.4. Entorno operativo

Aplicaciones Web (navegadores: Chrome, Firefox, Samsung Internet, Safari iOS, MI/Xiaomi) y App movil (iOS/Android). Idiomas: ES (inicial), posteriormente EN e IT. Accesibilidad: WCAG 2.1 AA.

### 2.5. Restricciones de diseno e implementacion

- Aislamiento de datos por tenant.
- Sin 2FA en el MVP; politicas de contrasena estandar.
- Adjuntos de hasta 100 MB (configurable por entidad).
- Concurrencia esperada: 100 usuarios simultaneos.
- Remesas SEPA: TBD en MVP.

### 2.6. Documentacion de usuario

Manual por rol (Superadmin, Admin confederacion, Admin federacion, Admin local, Secretario/Editor, Tesorero), guias rapidas A4, videos cortos (<=3 min) por tarea critica.

### 2.7. Suposiciones y dependencias

- Estructura por defecto: Confederacion -> Federaciones -> Locales, personalizable.
- Perfil siempre visible; resto de vistas activables/desactivables.
- Facturacion avanzada y logistica e-commerce fuera del MVP.
- SEPA, analitica avanzada, feature flags, SLAs y backups detallados: TBD.

---

## 3 Requisitos de Interfaces Externas

### 3.1. Interfaces de usuario

Interfaz web y movil con navegacion por pestanas (vistas). Estandares:

- Consistencia de componentes (botones primarios/secundarios, avisos, formularios con validacion).
- Estilos por entidad (logo, colores y nombre de pestanas).
- Accesibilidad: contraste alto, texto ampliable, etiquetas y descripciones; soporte lector de pantalla.

### 3.2. Interfaces de hardware

Dispositivos moviles iOS/Android y ordenadores de sobremesa/portatiles. No se requieren perifericos especificos.

### 3.3. Interfaces de software

- Pasarela(s) de pago (TBD), email (SMTP/API), push (APNs/FCM), almacenamiento de ficheros.
- Exportacion RGPD (formato estandar descargable).

### 3.4. Interfaces de comunicaciones

HTTP/HTTPS para clientes; cifrado en transito (TLS). Notificaciones push via APNs/FCM. Dominios por entidad: {entidad}.tuapp.es.

---

## 4 Caracteristicas del sistema

### 4.1. TENANCY, branding y vistas

#### 4.1.1. Descripcion y prioridad

Multientidad con aislamiento logico y personalizacion de branding/vistas. **Prioridad: A.**

#### 4.1.2. Secuencias estimulo/respuesta

Creacion de entidad por Superadmin -> asignacion de Admin(s) generales -> configuracion de branding y vistas.

#### 4.1.3. Requisitos funcionales

- **REQ-TEN-01 (A):** Aislamiento de datos por entidad (usuarios, contenidos, pagos, configuracion).
- **REQ-TEN-02 (A):** Superadmin puede crear entidades y asignar Admins generales.
- **REQ-TEN-03 (M):** Subdominio por entidad y branding (logo/colores/nombre de pestanas).
- **REQ-TEN-04 (A):** Vistas activables/desactivables (todas salvo Perfil); renombrables y reordenables por entidad.
- **REQ-TEN-05 (M):** Estructura de niveles configurable: anadir/retirar niveles y renombrarlos.

### 4.2. Gestion de usuarios

#### 4.2.1. Descripcion y prioridad

Altas, estados y perfil con campos ampliados. **Prioridad: A.**

#### 4.2.2. Secuencias

- Solicitud en app -> seleccion de entidad/nivel -> formulario -> validacion por secretario/admin local o admin general.
- Registro manual por secretario/admin local o admin general.

#### 4.2.3. Requisitos

- **REQ-USR-01 (A):** Campos obligatorios: nombre, apellidos, email, telefono, direccion, fecha de nacimiento, DNI (privado), foto, descripcion (opcional), IBAN (privado), consentimientos (incl. RGPD), talla, rol por nivel (si aplica).
- **REQ-USR-02 (A):** Estados: Activo; Honorifico (insignia Plata/Oro) asignable por admin confederal o equivalente.
- **REQ-USR-03 (A):** Alta via app con validacion local; alta directa por admin local/federal/confederal.
- **REQ-USR-04 (M):** Filtro: texto libre, rol, estado, entidad/nivel.
- **REQ-USR-05 (M):** Multi-pertenencia con roles distintos por entidad.

### 4.3. Roles y permisos

#### 4.3.1. Descripcion y prioridad

Lista maestra de permisos y roles base; roles personalizados por entidad. **Prioridad: A.**

#### 4.3.2. Requisitos

- **REQ-ROL-01 (A):** Roles base: Superadmin, Admin Confederacion, Admin Federacion, Admin Local, Editor/Comunicaciones, Tesorero, Moderador, Socio/Usuario, Invitado.
- **REQ-ROL-02 (A):** Permisos: ver, crear, editar, eliminar, publicar, moderar, gestionar_permisos, configurar_vistas, gestionar_entidades, ver_datos_sensibles, gestionar_pagos, ver_dash_*, exportar_RGPD.
- **REQ-ROL-03 (M):** Definicion de roles personalizados por Admin general marcando permisos desde lista maestra.
- **REQ-ROL-04 (A):** Visibilidad por defecto al nivel de alta (local/federal); ampliable por invitacion.

### 4.4. Calendario y actividades

#### 4.4.1. Descripcion y prioridad

Gestion de actividades con inscripcion, aforo, lista de espera y pagos opcionales. **Prioridad: A.**

#### 4.4.2. Secuencias

Creacion de actividad -> configuracion de formulario y estado -> publicacion -> inscripciones -> recordatorios.

#### 4.4.3. Requisitos

- **REQ-CAL-01 (A):** Tipos de actividad configurables por admins (etiquetas).
- **REQ-CAL-02 (A):** Form builder con campos (texto, numero, fecha, seleccion, adjunto, consentimiento, etc.) y condicionales.
- **REQ-CAL-03 (M):** Estado: Activo/Cerrado; aforo y lista de espera opcionales.
- **REQ-CAL-04 (M):** Invitaciones a usuarios de otros niveles.
- **REQ-CAL-05 (M):** Pagos en inscripcion, codigos de descuento, opcion de emitir factura (mostrable/ocultable por actividad).
- **REQ-CAL-06 (M):** Recordatorios in-app.

### 4.5. Noticias

#### 4.5.1. Descripcion y prioridad

Gestion editorial con workflow completo. **Prioridad: M.**

#### 4.5.2. Requisitos

- **REQ-NEW-01 (M):** Workflow: Borrador -> Revision -> Publicacion -> Archivado.
- **REQ-NEW-02 (M):** Programacion de publicacion; buscador, categorias/etiquetas, comentarios, "me gusta", compartir; adjuntos (video/PDF).

### 4.6. Revista (ediciones PDF)

#### 4.6.1. Descripcion y prioridad

Ediciones periodicas con miniatura y visualizacion PDF en app. **Prioridad: M.**

#### 4.6.2. Requisitos

- **REQ-REV-01 (M):** Gestion de ediciones con miniatura, PDF y fecha.
- **REQ-REV-02 (M):** Render/visualizacion PDF dentro de la app.

### 4.7. Recursos formativos

#### 4.7.1. Descripcion y prioridad

Catalogo de videos, enlaces y PDFs por categorias/etiquetas. **Prioridad: M.**

#### 4.7.2. Requisitos

- **REQ-REC-01 (M):** Alta de recursos (tipo, titulo, URL/archivo, etiquetas).
- **REQ-REC-02 (M):** Busqueda y filtrado por etiquetas/categorias.

### 4.8. Chat

#### 4.8.1. Descripcion y prioridad

Mensajeria 1:1, grupos y canales con moderacion. **Prioridad: M.**

#### 4.8.2. Requisitos

- **REQ-CHAT-01 (M):** Conversaciones 1:1, grupos (por entidad/rol/evento) y canales.
- **REQ-CHAT-02 (M):** Moderacion, reportes y bloqueo; menciones; envio de archivos; notificaciones in-app/email/push.

### 4.9. Tienda (basica)

#### 4.9.1. Descripcion y prioridad

Catalogo de merchandising con pago por app o justificante de transferencia. Logistica fuera de la plataforma. **Prioridad: B.**

#### 4.9.2. Requisitos

- **REQ-SHP-01 (B):** Productos (nombre, precio, IVA aplicado/opcional).
- **REQ-SHP-02 (B):** Pago por pasarela opcional o adjuntar justificante de transferencia.
- **REQ-SHP-03 (B):** Gestion fiscal minima (mostrar precio final con/sin desglose).

### 4.10. Cuotas

#### 4.10.1. Descripcion y prioridad

Cuota fija por socio configurable por entidad, con vigencia e historico; renovacion automatica y avisos. **Prioridad: A.**

#### 4.10.2. Requisitos

- **REQ-FEE-01 (A):** Importe fijo por socio definido por Admin general y configurable por entidad.
- **REQ-FEE-02 (A):** Vigencia con fecha de efecto e historico de cambios.
- **REQ-FEE-03 (M):** Renovacion automatica por pasarela/remesa (cuando este definida); avisos previos y recibos.

### 4.11. Cuota reversible

#### 4.11.1. Descripcion y prioridad

Reasignacion de superavit al cierre por eleccion del usuario (destino configurado). **Prioridad: M.**

#### 4.11.2. Secuencias

Calculo de importes -> notificacion con deadline -> pantalla de eleccion (opcion unica o reparto porcentual si se habilita) -> valor por defecto si no elige -> auditoria y reportes.

#### 4.11.3. Requisitos

- **REQ-REVF-01 (M):** Destinos posibles: entidad/fondo externo, fondos de confederacion, federacion, asociacion local, saldo positivo en cuenta.
- **REQ-REVF-02 (M):** Reglas de calculo por entidad y plazo configurable de respuesta.
- **REQ-REVF-03 (M):** Valor por defecto configurable si no hay eleccion a tiempo.
- **REQ-REVF-04 (M):** Auditoria y reporte por nivel.

### 4.12. Notificaciones

#### 4.12.1. Descripcion y prioridad

Canales in-app, email y push; boletin trimestral. **Prioridad: A.**

#### 4.12.2. Requisitos

- **REQ-NOT-01 (A):** Contenido editable por entidad; preferencias por usuario (activadas por defecto).
- **REQ-NOT-02 (M):** Disparadores: alta de socio, publicacion, mencion/chat, inscripciones/pagos, cuota reversible, etc.
- **REQ-NOT-03 (B):** Boletin trimestral automatico por entidad.

### 4.13. Dashboard y organigrama

#### 4.13.1. Descripcion y prioridad

KPIs por nivel, informe anual y organigrama exportable. **Prioridad: M.**

#### 4.13.2. Requisitos

- **REQ-DSH-01 (M):** KPIs: socios activos, altas/bajas, ventas tienda, participacion en actividades, engagement en noticias/chat (por nivel).
- **REQ-DSH-02 (M):** Informe anual visualizable/exportable.
- **REQ-DSH-03 (M):** Organigrama generado desde roles; exportable (PNG/PDF).

### 4.14. Pagos y remesas

#### 4.14.1. Descripcion y prioridad

Pagos basicos y remesas SEPA. **Prioridad: B (SEPA TBD).**

#### 4.14.2. Requisitos

- **REQ-PAY-01 (M):** Metodos: pasarela opcional; justificante de transferencia.
- **REQ-PAY-02 (TBD):** Remesas SEPA (mandatos, ficheros pain.008/pain.001, conciliacion, reintentos).

### 4.15. Crear y Custom

#### 4.15.1. Descripcion y prioridad

Creacion de estructura/roles y vistas; paginas personalizadas. **Prioridad: M.**

#### 4.15.2. Requisitos

- **REQ-CRT-01 (M):** Confirmar niveles y configurar roles por nivel (recursivo).
- **REQ-CRT-02 (M):** Crear vistas (calendario, noticias, usuarios, tienda, custom).
- **REQ-CUS-01 (M):** Paginas custom con tipos de campo (texto enriquecido, numero, fecha, select, archivos); buscador; permisos por rol; versionado opcional.

---

## 5 Otros requisitos no funcionales

### 5.1. Rendimiento

- **NFR-PERF-01:** Soportar 100 concurrentes con tiempos de respuesta percibidos < 1.5 s en operaciones habituales.
- **NFR-PERF-02:** Carga de PDF y recursos estandar < 3 s en redes 4G/WiFi medias.

### 5.2. Seguridad

- **NFR-SEC-01:** Aislamiento por tenant; cifrado en transito (TLS) y en reposo cuando aplique.
- **NFR-SEC-02:** Acceso a logs y alertas solo para Superadmin (plataforma).
- **NFR-SEC-03:** Registro de actividad, trazabilidad y backups: deseables; priorizar en roadmap.
- **NFR-SEC-04:** Politicas de contrasena estandar; sin 2FA en MVP.

### 5.3. Calidad del software

- **NFR-QLT-01:** Accesibilidad WCAG 2.1 AA.
- **NFR-QLT-02:** Usabilidad con lenguaje claro y soporte a usuarios mayores (tipografias y contrastes).
- **NFR-QLT-03:** Internacionalizacion: ES inicial; EN e IT posteriores.

### 5.4. Reglas de negocio

- **BR-01:** Perfil es vista obligatoria; el resto son configurables.
- **BR-02:** Visibilidad limitada al nivel de alta salvo invitacion explicita.
- **BR-03:** Exportacion generica no requerida; solo exportacion RGPD.

---

## 6 Otros requisitos (abierto a cambios)

### 6.1. Implantacion y soporte

Metodologia train-the-trainers para Admins generales, federales y secretarios locales; sesiones presenciales regionales; materiales impresos y videos cortos; accesibilidad reforzada. Mesa de ayuda con primera respuesta <= 48 h en lanzamiento; captura de feedback en app; metricas de adopcion (altas por local, usuarios activos/mes, retencion, participacion, uso de chat).

### 6.2. Roadmap y entregables

| Fase | Fechas | Entregables (principales) |
|---|---|---|
| **F1 -- Desarrollo base** | 15/07--10/10 | Usuarios completos, Perfil, Calendario/Actividades (sin pagos) con Form builder y condicionales, Noticias, Revista (PDF), Recursos, Personalizacion de vistas, Roles/Permisos (lista maestra), Tenancy (alta entidades, branding, subdominios), notificaciones basicas, importacion CSV. |
| **F2 -- Intermedio + Testing** | 10/10--30/11 | Chat (1:1, grupos, canales; moderacion), Busqueda/Filtro usuarios, Notificaciones ampliadas, Dashboard/Organigrama con KPIs base e informe anual, mejoras UX. Testing con locales piloto. |
| **F3 -- Avanzado + Implantacion** | 08/10--10/04 | Pagos en inscripciones (descuentos, factura opcional), Tienda (merch + justificante), Cuotas (importe fijo + cuota reversible). Puesta en marcha en asambleas federales y visitas de adopcion. |
| **F4 -- Cierre y despliegue** | 10/01--10/06 | Correccion de errores y mejoras; implantacion general; preparacion para Remesas SEPA (TBD) y analitica/feature flags. |

### 6.3. Criterios de aceptacion (ejemplos)

- **Alta multi-nivel:** solicitud -> validacion por admin local -> acceso con rol Socio.
- **Visibilidad:** usuario dado de alta por admin federal no ve contenidos locales salvo invitacion.
- **Form builder:** actividad con condicionales, codigo de descuento y pago.
- **Revista:** apertura de edicion => render PDF en app.
- **Cuota reversible:** notificacion, eleccion de destino, auditoria y reporte.
- **Personalizacion de vistas:** activar/desactivar/renombrar/reordenar.

---

## 7 Apendices

### Apendice A: Glosario

- **Tenant:** Entidad aislada logicamente dentro de la plataforma.
- **Cuota reversible:** Mecanismo de reasignacion de superavit a destinos configurables.
- **SEPA:** Estandares de pagos en la zona unica de pagos en euros.

### Apendice B: Modelos de analisis (alto nivel)

**Modelo de datos (entidades principales):**

- `Entidad(id, nombre, nivel, parent_id, dominio, branding, toggles_vistas, politicas, config_cuotas, config_pagos, notificaciones...)`
- `Usuario(id, nombre, apellidos, email, telefono, direccion, fecha_nacimiento, dni[privado], foto, descripcion, iban[privado], talla, consentimientos, estado, ...)`
- `Membresia(usuario_id, entidad_id, rol_id, fecha_alta, estado)`
- `Rol(id, entidad_id[plantilla], nombre, permisos[])`
- `Noticia(id, entidad_id, titulo, cuerpo, etiquetas, workflow, programada_en, autor_id)`
- `RevistaEdicion(id, entidad_id, titulo, miniatura, pdf_url, fecha)`
- `Recurso(id, entidad_id, tipo, titulo, url, etiquetas)`
- `Actividad(id, entidad_id, titulo, descripcion, fecha, etiquetas, visibilidad, invitaciones, pagos_habilitados, factura_opcional, estado)`
- `Formulario(id, actividad_id, esquema_json, aforo, lista_espera)`
- `Inscripcion(id, actividad_id, usuario_id, respuestas_json, estado, pago_id, descuento, factura_emitida)`
- `Producto(id, entidad_id, nombre, precio, iva_aplicado)`
- `Pedido(id, entidad_id, usuario_id, total, metodo, justificante_url, estado)`
- `Pago(id, entidad_id, usuario_id, importe, concepto, metodo, estado, ref_externa)`
- `CuotaConfig(id, entidad_id, importe_fijo, vigente_desde, vigente_hasta, reglas_reversible_json)`
- `CuotaAsignacion(id, usuario_id, periodo, importe, estado, destino_reversible)`
- `Chat(conversacion, mensaje, adjuntos, reportes)`
- `AdsConfig(entidad_id, ubicaciones, categorias, frecuencia)`
- `PreferenciasNotificacion(usuario_id, canal, tipo_evento, activo)`

### Apendice C: Lista de TBD

1. Definicion completa de remesas SEPA (mandatos, ficheros pain.008/pain.001, conciliacion, reintentos).
2. Analitica avanzada y feature flags.
3. Rendimiento/SLAs detallados, retencion y backups (RPO/RTO).
4. Destino por defecto de la cuota reversible si no hay eleccion en plazo.
