# Despliegue del backend de BoscoGest con GitHub Actions y AWS Systems Manager

Este procedimiento sustituye el SSH utilizado para actualizar el backend. El
frontend sigue publicándose por separado en S3/CloudFront. **No fusionar PR #7
hasta confirmar primero la nueva API**, porque el frontend se publica
automáticamente al fusionarlo.

## 1. Activar una vez Systems Manager en EC2

La instancia `i-0255523213e09540c` tiene la política de instancia
`AmazonSSMManagedInstanceCore`. A fecha 13/11/2026 todavía **no aparece
conectada** en SSM. En la máquina Amazon Linux 2023, desde un acceso SSH de
administración ya autorizado:

```bash
sudo rpm -q amazon-ssm-agent || sudo dnf install -y amazon-ssm-agent
sudo systemctl enable --now amazon-ssm-agent
sudo systemctl is-active amazon-ssm-agent
```

No hay que abrir el puerto 22 a todo Internet ni reiniciar la instancia. Si
el servicio funciona pero no aparece Online, inspeccionar:
`sudo journalctl -u amazon-ssm-agent -n 100 --no-pager`. No compartir logs
que contengan credenciales o identificadores personales.

Comprobar en AWS Systems Manager > Fleet Manager que el nodo esté **Online**
en `eu-west-1`.

## 2. Fusionar el PR #8, no el PR #7

El PR #8 añade un workflow **manual** en la rama main:
`.github/workflows/backend-release.yml`. Fusionarlo no publica el backend
ni modifica la web. Solo habilita el procedimiento.

## 3. Publicar primero el backend del PR #7

En GitHub > Actions > **Backend - verify and release via SSM** > Run workflow:

- Branch: `main`, para que el token OIDC corresponda a la confianza IAM.
- source_ref: SHA verificado del commit **más reciente** del PR #7. No usar
  una etiqueta mutable para un despliegue en producción.

El workflow verifica pytest, Ruff y migraciones PostgreSQL 15, exige SSM
Online, crea y espera un snapshot manual de RDS, construye la imagen amd64 en
ECR con el SHA completo y sustituye únicamente `back` en Docker Compose.

El script remoto conserva el archivo `/opt/boscogest/.env`, las credenciales
de Firebase, y el contenedor Caddy con sus certificados. Si la nueva imagen
no alcanza el estado `healthy`, restaura la imagen anterior. **Las
migraciones de base de datos no se revierten automáticamente:** el cambio
de DNI nullable del PR #7 es aditivo y compatible con la versión anterior.

## 4. Verificación y frontend

Confirmar que la ejecución termina en verde y que
`https://api.boscogest.com/healthz` responde correctamente. Verificar una
alta administrativa sin datos de contacto en un entorno de prueba antes de
usar datos reales. Solo después fusionar PR #7: su workflow publicará
automáticamente el frontend.

## 5. Reversión

Si la nueva imagen falla su healthcheck, el script remoto vuelve a la imagen
anterior. Si se detecta un fallo funcional después del healthcheck, ejecutar
un despliegue manual de la versión anterior mediante el mismo workflow
seleccionando el SHA anterior, o usar SSM con el procedimiento documentado.

El snapshot es para recuperación extraordinaria de datos, no una reversión
automática: restaurar un snapshot puede perder escrituras posteriores y
requiere una intervención planificada.
