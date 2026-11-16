# Sesión persistente y biometría (BoscoGest)

## Comportamiento previsto

- JWT de acceso de **30 minutos**: no se alarga arbitrariamente.
- Sesión renovable por dispositivo durante **30 días de inactividad**.
- Cada renovación cambia el secreto y revoca el anterior. PostgreSQL
  almacena únicamente su hash SHA-256.
- El cierre de sesión y el cambio/restablecimiento de contraseña revocan
  sesiones. Las cuentas desactivadas no pueden renovar sus tokens.
- En web: cookie de renovación HttpOnly/Secure/SameSite; no localStorage.
- En Android/iOS: almacén nativo cifrado (Keystore / Keychain).
- La biometría es optativa y se solicita al arrancar la aplicación. Si
  se cancela, puede introducirse la contraseña.
- BoscoGest nunca recoge ni almacena huellas ni datos faciales.

## Despliegue coordinado

1. Ejecutar CI Ruff, pytest y migraciones PostgreSQL.
2. Compilar Angular desde npm ci.
3. Crear snapshot RDS; desplegar backend primero (migración aditiva).
4. Publicar frontend web después y probar login, refresh y logout.
5. Construir versiones nuevas de Android/iOS desde la rama validada:

       cd boscoGest-front
       npm ci
       npm run cap:sync

6. Probar en dispositivos reales: sesión tras reiniciar, desbloqueo
   biométrico, cancelación, ausencia de sensor, modo avión, cambio de
   contraseña y cierre de sesión.
7. Distribuir la nueva compilación móvil por Play Store / App Store.

## Limitaciones

La biometría es una protección local de la apertura de sesión: no equivale
a una passkey o un autenticador registrado ante el servidor.
El token de renovación nunca debe guardarse en localStorage ni Capacitor
Preferences. Solo se guarda una preferencia no secreta para activar el
desbloqueo biométrico.
Los plugins nativos precisan sincronización Capacitor y compilaciones
firmadas nuevas; una publicación de Angular en CloudFront no instala
capacidades biométricas en apps móviles ya publicadas.
