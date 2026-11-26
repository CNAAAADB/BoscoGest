# Entornos de BoscoGest: DEV y PROD

## Estado (20/11/2026)

| Componente | Desarrollo | Producción |
|---|---|---|
| Rama | `develop` | `main` |
| Frontend | https://dev.boscogest.com | https://boscogest.com |
| API | https://api-dev.boscogest.com | https://api.boscogest.com |
| S3 | `boscogest-frontend-dev` | `boscogest-frontend` |
| CloudFront | `E3ADF31ZVJ509O` | `E34CSQ092X6U3D` |
| EC2 | `i-0e1aef4dd9cd5ee83` (t3.small) | `i-0255523213e09540c` (t3.micro) |
| ECR | `boscogest-back-dev` | `boscogest-back` |
| Base de datos | PostgreSQL 15 local, volumen cifrado en EC2 DEV | RDS `boscogest-db` |
| Despliegue | `.github/workflows/development-deploy.yml` | Workflows de frontend y backend de producción |

**Nunca conectar DEV con RDS, los buckets o las credenciales de producción.**
No se han copiado datos personales de socios a DEV. Las credenciales de JWT y de la base de datos de DEV se generan y almacenan exclusivamente en `/opt/boscogest-dev/.env` de la instancia DEV (permisos 0600).
Los emails y los push están desactivados en DEV, para impedir notificaciones accidentales a socios.

## Flujo habitual

1. Crear una rama de funcionalidad desde `develop`.
2. Abrir una pull request hacia `develop` y validar lint, pruebas y build.
3. Integrar en `develop`: GitHub Actions prueba backend con PostgreSQL efímero y compila Angular contra `https://api-dev.boscogest.com`.
4. Si todo pasa, publica la imagen de backend DEV, la arranca a través de Systems Manager, verifica su `/healthz` y publica Angular en el S3 DEV; invalida CloudFront DEV.
5. Probar manualmente la funcionalidad en https://dev.boscogest.com con datos ficticios.
6. Tras validación, abrir una nueva PR de `develop` a `main`, revisar y desplegar mediante los procesos independientes existentes de producción.

## Medidas de seguridad

- Instancia DEV distinta de producción y sin SSH público; administración por AWS Systems Manager.
- Grupo de seguridad DEV: solo puertos 80 (ACME/redirect) y 443 (HTTPS).
- Rol EC2 DEV: Systems Manager y lectura de ECR; sin acceso a secretos de producción.
- Rol OIDC de GitHub `BoscoGest-GitHub-Dev-Deployer` solo acepta la rama `develop` y permite escribir exclusivamente en S3, ECR, CloudFront y SSM de DEV.
- Bucket DEV privado con Block Public Access, cifrado y versionado.
- Caddy gestiona el certificado HTTPS de `api-dev.boscogest.com`.
- Base de datos DEV sin credenciales de producción y con almacenamiento cifrado.
- Solo datos sintéticos. No restaurar backups de producción en DEV.
- `dev.boscogest.com` es un entorno de prueba: no introducir datos personales reales.
- Restringir las publicaciones a `main` mediante protecciones de rama y aprobaciones de revisión en la configuración de GitHub si se dispone de esa funcionalidad.

## Diagnóstico

1. GitHub > Actions > **DEV - verify and deploy isolated environment**.
2. AWS Systems Manager > Fleet Manager > `i-0e1aef4dd9cd5ee83`.
3. En sesión administrativa SSM: `cd /opt/boscogest-dev && sudo docker compose -f compose.yml ps`.
4. `https://api-dev.boscogest.com/healthz` debe responder `{"status":"ok","database":"ok"}`.
5. GitHub Actions no publica el frontend DEV si el backend no está sano.

## Coste y mantenimiento

DEV añade una instancia EC2 t3.small, un volumen EBS cifrado de 24 GiB, una IPv4 pública, una distribución CloudFront, almacenamiento S3 y ECR.
Revisar costes reales mensualmente. El equipo puede detener la EC2 DEV cuando no se necesite, teniendo en cuenta que el backend de pruebas quedará inaccesible durante ese periodo.
Configurar snapshots periódicos del volumen DEV solo si los datos de prueba necesitan conservación; su pérdida no debe afectar a producción.
