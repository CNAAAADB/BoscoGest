# DEPLOY_FEATURES.md

Guia para desplegar nuevas features en un entorno ya existente. Para crear un entorno desde cero, ver [INFRASTRUCTURE.md](INFRASTRUCTURE.md).

---

## 1. Tipos de despliegue

| Cambio | Backend | Frontend | Ambos |
|--------|---------|----------|-------|
| Nuevo endpoint / logica de negocio | Si | - | - |
| Nueva migracion de BD | Si | - | - |
| Cambio en UI / componentes | - | Si | - |
| Feature completa (API + UI) | - | - | Si |
| Cambio en variables de entorno | Reinicio | - | - |

---

## 2. Deploy del backend

> **Desde el 26 oct 2026 el EC2 usa `deploy/docker-compose.prod.yml`** (back
> sin puertos publicados, solo `expose: 8000`; Caddy delante con TLS;
> `init: true`). `/opt/boscogest/docker-compose.yml` es un enlace a
> `docker-compose.prod.yml`, así que `docker compose …` sin `-f` usa el bueno.
> El puerto 8000 ya no está publicado ni abierto en el security group: la API
> solo se alcanza por `https://api.boscogest.com`. Para comprobarla desde el
> EC2: `sudo docker compose exec back curl -s localhost:8000/healthz`.
>
> **Forma recomendada:** `./deploy/deploy.sh` (build, push con el SHA del
> commit como etiqueta, copia del compose/Caddyfile/.env y reinicio). Usa
> `deploy/.env.prod` local, que el 26 oct estaba sincronizado con el del
> servidor. La imagen que se arranca la decide `DOCKER_IMAGE` en el `.env` del
> servidor, **no** `:latest`: si se despliega a mano, actualizar esa línea.

### 2.1 Build y push de la imagen

Desde tu maquina local:

```bash
cd boscoGest

# 1. Login en ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin 909186483504.dkr.ecr.eu-west-1.amazonaws.com

# 2. Build (cross-compile para x86_64 desde Apple Silicon)
# --load es necesario en Mac para cargar la imagen en el daemon local
docker buildx build --platform linux/amd64 --load -t boscogest-back .

# 3. Tag y push
docker tag boscogest-back:latest 909186483504.dkr.ecr.eu-west-1.amazonaws.com/boscogest-back:latest
docker push 909186483504.dkr.ecr.eu-west-1.amazonaws.com/boscogest-back:latest
```

### 2.2 Actualizar en el EC2

```bash
# SSH al EC2
ssh -i ~/.ssh/boscogest-key.pem ec2-user@<ELASTIC_IP>

# Renovar token ECR (expira cada 12h)
aws ecr get-login-password --region eu-west-1 | \
  sudo docker login --username AWS --password-stdin 909186483504.dkr.ecr.eu-west-1.amazonaws.com

# Pull nueva imagen y reiniciar
cd /opt/boscogest
sudo docker compose pull
sudo docker compose down && sudo docker compose up -d
```

> **El acceso SSH esta restringido por IP** en el grupo de seguridad
> `sg-07e4bbd92f3bc061c`. Si el `ssh` da timeout, tu IP no esta en la lista:
> actualiza la regla **"Carlos SSH"** con tu IP actual. Esa regla es
> permanente: no se borra al terminar. La instancia **no tiene agente de
> SSM**, asi que no hay Session Manager como alternativa.
>
> **Recrear solo `back`** (`docker compose pull back && docker compose up -d
> back`): el `docker-compose.yml` del EC2 no es el del repo y Caddy, con sus
> certificados, corre en el mismo proyecto; un `down` lo para tambien.

### 2.3 Ejecutar migraciones (si las hay)

Las migraciones **se aplican solas al arrancar el contenedor**: `start.sh`
llama a `alembic upgrade head`. El paso manual suele ser solo para comprobar.

Si hace falta forzarlas:

```bash
sudo docker compose exec back alembic upgrade head
```

Verificar que se aplicaron:

```bash
sudo docker compose exec back alembic current
```

### 2.4 Verificar

```bash
# Logs del contenedor
sudo docker compose logs --tail 30 back

# Probar la API (el 8000 ya no está publicado en el host)
sudo docker compose exec back curl -s localhost:8000/healthz
```

Desde fuera, comprobar que los endpoints nuevos existen de verdad:

```bash
curl -s https://api.boscogest.com/openapi.json | python3 -c \
  "import sys,json; print(list(json.load(sys.stdin)['paths'])[:5])"
```

---

## 3. Deploy del frontend

Desde tu maquina local:

```bash
cd boscoGest-front

# 1. Build de produccion
#    Necesita .env.build (ver .env.build.example) para generar
#    src/environments/environment.prod.ts, que no se commitea.
npm run build

# 2. Subir a S3 (reemplaza todo el contenido)
aws s3 sync dist/boscoGest-front/browser/ s3://boscogest-frontend --delete

# 3. Invalidar la cache de CloudFront — IMPRESCINDIBLE
aws cloudfront create-invalidation --distribution-id E34CSQ092X6U3D --paths "/*"
```

**El paso 3 no es opcional.** El sitio se sirve tras CloudFront
(`d1l130nd7prh9g.cloudfront.net`), que cachea `index.html`. Sin invalidar, S3
tiene la version nueva pero los visitantes siguen recibiendo la anterior; y
como `aws s3 sync --delete` borra los bundles viejos, se puede llegar a servir
un `index.html` que apunta a ficheros que ya no existen.

Comprobar que ha surtido efecto:

```bash
curl -s https://boscogest.com/ | grep -oE 'main-[A-Z0-9]+\.js'
```

Tiene que coincidir con el `main-*.js` que hay en
`dist/boscoGest-front/browser/`.

> **Nota:** el navegador puede seguir mostrando una version antigua por cache
> local; hard refresh (Cmd+Shift+R / Ctrl+Shift+R).

---

## 4. Deploy completo (backend + frontend)

Cuando una feature afecta a ambos, desplegar en este orden:

1. **Backend primero** (para que los nuevos endpoints esten disponibles)
2. **Migraciones** (si las hay)
3. **Frontend despues** (para que la UI use los nuevos endpoints)

El orden importa: el frontend nuevo llama a endpoints que el backend viejo no
tiene, y al reves solo sobra API sin usar.

```bash
# === BACKEND ===
cd boscoGest
docker buildx build --platform linux/amd64 --load -t boscogest-back .
docker tag boscogest-back:latest 909186483504.dkr.ecr.eu-west-1.amazonaws.com/boscogest-back:latest
docker push 909186483504.dkr.ecr.eu-west-1.amazonaws.com/boscogest-back:latest

# En el EC2:
ssh -i ~/.ssh/boscogest-key.pem ec2-user@<ELASTIC_IP>
aws ecr get-login-password --region eu-west-1 | sudo docker login --username AWS --password-stdin 909186483504.dkr.ecr.eu-west-1.amazonaws.com
cd /opt/boscogest
sudo docker compose pull
sudo docker compose down && sudo docker compose up -d
sudo docker compose exec back alembic current   # comprobar la revision

# === FRONTEND ===
cd boscoGest-front
npm run build
aws s3 sync dist/boscoGest-front/browser/ s3://boscogest-frontend --delete
aws cloudfront create-invalidation --distribution-id E34CSQ092X6U3D --paths "/*"
```

---

## 5. Antes de una migracion sobre datos reales

Instantanea manual de la RDS, que tarda un minuto y evita depender solo de los
backups automaticos:

```bash
aws rds create-db-snapshot --region eu-west-1 \
  --db-instance-identifier boscogest-db \
  --db-snapshot-identifier boscogest-db-pre-$(date +%Y%m%d)
```

---

## 6. Publicar una nueva versión de la app Android (descarga interna)

La pantalla «Descargar app» llama a `GET /downloads/apk`, que devuelve una URL
firmada (15 min) a `s3://boscogest-uploads-prod/apks/boscogest.apk`. Publicar
una versión es sustituir ese objeto.

```bash
cd boscoGest-front

# 1. Subir versionCode (+1 siempre) y versionName en android/app/build.gradle

# 2. Build web + sync — npm run cap:sync regenera environment.prod.ts
#    (incluido androidPush, según exista android/app/google-services.json)
npm run cap:sync

# 3. APK firmado (y AAB para Google Play). Firma con android/key.properties
cd android && ./gradlew assembleRelease bundleRelease && cd ..

# 4. Comprobar que el certificado es el mismo que el publicado: si cambia,
#    Android no deja actualizar encima y hay que desinstalar.
apksigner verify --print-certs android/app/build/outputs/apk/release/app-release.apk

# 5. Copia de la versión anterior y subida de la nueva
aws s3 cp s3://boscogest-uploads-prod/apks/boscogest.apk \
          s3://boscogest-uploads-prod/apks/boscogest-<versión-anterior>.apk
aws s3 cp android/app/build/outputs/apk/release/app-release.apk \
          s3://boscogest-uploads-prod/apks/boscogest.apk \
          --content-type application/vnd.android.package-archive --sse AES256
```

Historial: 1.0.0 (29 sep 2026, cerraba la app al iniciar sesión por falta de
`google-services.json`) → 1.1.0 (26 oct 2026).
