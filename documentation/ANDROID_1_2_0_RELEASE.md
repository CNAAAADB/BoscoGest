# BoscoGest Android 1.2.0 — prueba cerrada de Google Play

- Android applicationId: `com.boscogest.app` (sin cambios).
- Nueva versión: `versionName = 1.2.0`, `versionCode = 5`.
- Canal recomendado: **la misma prueba cerrada** ya activa en Play Console. No crear una prueba ni una aplicación nuevas.

## Novedades para los testers

- Barra de navegación inferior exclusiva de la aplicación instalada: Inicio, Usuarios, Actividades, Calendario y Mensajes.
- Calendario mensual de actividades.
- Directorio de socios para contactar por chat y filtros por asociación.
- Mejoras de sesión persistente y acceso biométrico opcional.
- Avisos de datos incompletos e identificación DNI/NIE para administradores autorizados.

## Preparación y publicación

1. Ejecutar el workflow GitHub Actions **Android - prepare Google Play bundle** en la rama principal tras superar las pruebas.
2. Descargar el artefacto `boscogest-android-1.2.0-signed` si aparece. Solo un AAB **firmado con la clave de subida registrada** se puede cargar en Play Console.
3. Si el artefacto es `...-unsigned`, **no subirlo a Play**: firmar con la clave original (no generar otra). Para habilitar CI, configurar los secretos de repositorio `ANDROID_UPLOAD_KEYSTORE_BASE64`, `ANDROID_UPLOAD_STORE_PASSWORD`, `ANDROID_UPLOAD_KEY_ALIAS` y `ANDROID_UPLOAD_KEY_PASSWORD`, sin incluir su valor en Git ni en chats. Volver a ejecutar el workflow. Alternativamente, usar Android Studio con el `key.properties` y el almacén de claves ya utilizados para la versión anterior.
4. Comprobar que en Play Console el mayor `versionCode` ya publicado sea menor que 5. Si es 5 o más, aumentar `versionCode` a uno libre antes de generar y publicar el AAB.
5. Subir a **Pruebas > Prueba cerrada**, en el mismo track y con el mismo grupo de testers, para conservar su participación continuada. No eliminar la prueba.
6. Confirmar que Play acepta la firma de subida, revisar la versión y publicar la actualización en la prueba cerrada.

## Pruebas en dispositivos reales (antes de aprobar la distribución)

- [ ] App instalada desde Play se actualiza sobre la anterior sin perder la sesión.
- [ ] Barra inferior aparece **solo** en Android/iOS nativos; no aparece en Chrome/Safari.
- [ ] Los cinco botones abren rutas correctas y la pestaña activa se resalta.
- [ ] Mensajes muestra el contador de no leídos y actualiza al entrar.
- [ ] Barra inferior no tapa botones al hacer scroll ni los gestos de navegación.
- [ ] Calendario carga las actividades, muestra las fechas y abre cada detalle.
- [ ] Usuarios accede al directorio general, no a ADMIN.
- [ ] Persistencia de sesión y, opcionalmente, desbloqueo biométrico.
- [ ] Se reciben notificaciones push con la aplicación cerrada.

## Texto breve sugerido para novedades en Play (es-ES)

Nuevos accesos rápidos en la parte inferior de la app para Inicio, Usuarios, Actividades, Calendario y Mensajes. Consulta actividades por fecha, encuentra socios de otras asociaciones e inicia conversaciones más fácilmente. Mejoras de acceso y navegación.

## Notas de seguridad

El almacén de claves `.jks`, el archivo `key.properties` y sus contraseñas nunca deben subirse a Git. La firma de actualización debe usar **la clave de subida original**; la configuración de GitHub no puede sustituirla por una nueva.
