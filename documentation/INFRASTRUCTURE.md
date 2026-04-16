# INFRASTRUCTURE.md

Documentacion de la infraestructura cloud (AWS) del proyecto BoscoGest, gestionada con Terraform.

---

## 1. Arquitectura general

```
                        ┌──────────────────────────────────────────────────┐
                        │                   AWS Cloud                      │
                        │                                                  │
   Usuarios ──────────► │  ┌──────────────┐       S3 Static Website       │
   (navegador)          │  │  CloudFront   │◄──── boscogest-frontend       │
   boscogest.com        │  │  HTTPS + CDN  │      (Angular build)          │
                        │  └──────────────┘                                │
                        │                                                  │
                        │  ┌───────────────────┐                           │
                        │  │  ECR               │                           │
                        │  │  boscogest-back    │─── docker pull ──┐       │
                        │  └───────────────────┘                   │       │
                        │                                          ▼       │
                        │  ┌──────────────────────────────────────────┐    │
                        │  │             VPC  10.0.0.0/16             │    │
                        │  │                                          │    │
   API requests ──────► │  │  ┌─────────────────────────────────┐     │    │
   (:8000)              │  │  │  Subnet publica  10.0.1.0/24    │     │    │
                        │  │  │                                  │     │    │
                        │  │  │  ┌───────────────────────────┐   │     │    │
                        │  │  │  │  EC2  t3.micro            │   │     │    │
                        │  │  │  │  Amazon Linux 2023        │   │     │    │
                        │  │  │  │  Elastic IP (IP fija)     │   │     │    │
                        │  │  │  │  IAM: ECR + S3 Uploads    │   │     │    │
                        │  │  │  │  Docker + Docker Compose  │   │     │    │
                        │  │  │  │  ┌─────────────────────┐  │   │     │    │
                        │  │  │  │  │ boscogest-back      │  │   │     │    │
                        │  │  │  │  │ FastAPI :8000       │──┼───┼──►  │    │
                        │  │  │  │  └─────────┬───────────┘  │   │  │  │    │
                        │  │  │  └────────────┼──────────────┘   │  │  │    │
                        │  │  └───────────────┼──────────────────┘  │  │    │
                        │  │                  │                     │  │    │
                        │  │  ┌───────────────▼─────────────────┐   │  │    │
                        │  │  │  S3 Bucket (Uploads privado)    │   │  │    │
                        │  │  │  boscogest-uploads-prod         │   │  │    │
                        │  │  │  Cifrado AES256, presigned URLs │   │  │    │
                        │  │  └─────────────────────────────────┘   │  │    │
                        │  │                                        │  │    │
                        │  │  ┌─────────────────────────────────┐   │  │    │
                        │  │  │  Subnets privadas               │   │  │    │
                        │  │  │  10.0.10.0/24 + 10.0.11.0/24    │   │  │    │
                        │  │  │                                  │   │  │    │
                        │  │  │  ┌───────────────────────────┐   │   │  │    │
                        │  │  │  │  RDS  PostgreSQL 15       │◄──┼───┘  │    │
                        │  │  │  │  db.t3.micro (free tier)  │   │      │    │
                        │  │  │  │  20 GB gp2                │   │      │    │
                        │  │  │  │  Puerto 5432              │   │      │    │
                        │  │  │  └───────────────────────────┘   │      │    │
                        │  │  └──────────────────────────────────┘      │    │
                        │  └────────────────────────────────────────────┘    │
                        └──────────────────────────────────────────────────┘
```

| Componente | Servicio AWS | Tipo | Ubicacion |
|------------|-------------|------|-----------|
| **Backend API** | EC2 + Elastic IP | t3.micro | Subnet publica (HTTP :8000 + WebSocket :8000) |
| **Base de datos** | RDS PostgreSQL 15 | db.t3.micro (free tier) | Subnets privadas |
| **Almacenamiento archivos** | S3 | Bucket privado (presigned URLs) | Regional |
| **Registro Docker** | ECR | boscogest-back | Regional |
| **Frontend SPA** | S3 | Static Website Hosting | Global |
| **CDN + HTTPS** | CloudFront | Distribucion (PriceClass_100: US+EU) | Global |
| **Certificado SSL** | ACM | Wildcard `*.boscogest.com` | us-east-1 |

> **Nota sobre apps moviles:** Las apps Android e iOS se generan localmente con Capacitor (`npm run cap:run:android`, `npm run cap:run:ios`). No requieren infraestructura cloud adicional — usan la misma API desplegada en EC2. Para distribucion en tiendas (Google Play / App Store), el build se genera con Android Studio / Xcode en la maquina del desarrollador. Ver [CAPACITOR.md](CAPACITOR.md) para detalles.

---

## 2. Backend — `boscoGest/infra/`

### 2.1 Recursos creados

| Recurso | Archivo | Descripcion |
|---------|---------|-------------|
| VPC | `main.tf` | Red virtual aislada `10.0.0.0/16` con DNS habilitado |
| Internet Gateway | `main.tf` | Acceso a internet desde subnets publicas |
| 2 Subnets publicas | `main.tf` | `10.0.1.0/24` y `10.0.2.0/24` en AZs distintas (EC2) |
| 2 Subnets privadas | `main.tf` | `10.0.10.0/24` y `10.0.11.0/24` en AZs distintas (RDS) |
| Route Table publica | `main.tf` | Ruta `0.0.0.0/0` hacia Internet Gateway |
| Security Group EC2 | `security_groups.tf` | SSH (22), HTTP (80), HTTPS (443), API+WebSocket (8000) |
| Security Group RDS | `security_groups.tf` | PostgreSQL (5432) solo desde el SG del EC2 |
| EC2 Instance | `ec2.tf` | t3.micro, Amazon Linux 2023, disco 30GB gp3 |
| Elastic IP | `ec2.tf` | IP publica estatica asociada al EC2 (no cambia al reiniciar) |
| RDS PostgreSQL | `rds.tf` | PostgreSQL 15, db.t3.micro, 20GB, sin backups automaticos (free tier) |
| DB Subnet Group | `rds.tf` | Agrupa las subnets privadas para RDS |
| ECR Repository | `ecr.tf` | Registro Docker privado para la imagen del backend |
| ECR Lifecycle Policy | `ecr.tf` | Conserva las ultimas 10 imagenes, elimina las antiguas |
| S3 Bucket Uploads | `s3.tf` | Almacenamiento privado de archivos (revistas, imagenes, logos) |
| S3 Encryption | `s3.tf` | Cifrado AES256 server-side para todos los objetos |
| S3 Public Access Block | `s3.tf` | Bloquea todo acceso publico al bucket |
| S3 CORS | `s3.tf` | Permite GET desde cualquier origen (para presigned URLs en `<img>`) |
| ACM Certificate | `cloudfront.tf` | Certificado SSL wildcard para dominio personalizado (us-east-1) |
| CloudFront Distribution | `cloudfront.tf` | CDN con HTTPS, SPA routing (403/404 → index.html), redirect HTTP→HTTPS |
| IAM Role EC2 | `iam.tf` | Rol con permisos de lectura en ECR y read/write en S3 uploads |
| IAM Policy S3 Uploads | `iam.tf` | `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket` |
| IAM Instance Profile | `iam.tf` | Perfil asociado a la instancia EC2 |

### 2.2 Ficheros

```
boscoGest/infra/
├── main.tf                   # VPC, subnets, gateway, route tables
├── ec2.tf                    # Instancia EC2 + Elastic IP con user_data
├── rds.tf                    # RDS PostgreSQL + subnet group
├── ecr.tf                    # ECR repository + lifecycle policy
├── s3.tf                     # S3 bucket uploads (privado, cifrado, CORS)
├── iam.tf                    # IAM role + instance profile (ECR pull + S3 uploads)
├── security_groups.tf        # SGs para EC2 y RDS
├── cloudfront.tf             # ACM certificate + CloudFront distribution (dominio custom)
├── user_data.sh              # Script de bootstrap del EC2
├── variables.tf              # Variables de entrada
├── outputs.tf                # Valores de salida
├── terraform.tfvars.example  # Ejemplo de configuracion
└── .gitignore                # Excluye .terraform, *.tfstate, *.tfvars
```

### 2.3 Seguridad de red

```
Internet ──► EC2 (SG: boscogest-ec2-sg)
               Ingress: 22/tcp (SSH, restringido), 80/tcp, 443/tcp, 8000/tcp
               Egress:  todo

             EC2 ──► RDS (SG: boscogest-rds-sg)
                      Ingress: 5432/tcp solo desde boscogest-ec2-sg
                      Egress:  todo

Internet ──✗ RDS (no accesible desde internet)
```

La RDS **no es accesible desde internet** (`publicly_accessible = false`). Solo acepta conexiones desde la instancia EC2 a traves de la referencia entre Security Groups.

### 2.4 ECR (Elastic Container Registry)

El repositorio ECR `boscogest-back` se crea automaticamente con Terraform y se usa como registro privado para las imagenes Docker del backend.

| Caracteristica | Valor |
|----------------|-------|
| Nombre | `boscogest-back` |
| Tag mutability | MUTABLE (permite sobreescribir `latest`) |
| Scan on push | Activado (escaneo de vulnerabilidades) |
| Lifecycle policy | Conserva las ultimas 10 imagenes |

La instancia EC2 tiene un **IAM Instance Profile** con la politica `AmazonEC2ContainerRegistryReadOnly`, que le permite hacer `docker pull` desde ECR sin necesidad de credenciales manuales. El script `user_data.sh` ejecuta automaticamente `aws ecr get-login-password` al arrancar.

> **Nota:** Los tokens de ECR expiran a las **12 horas**. Si haces `docker pull` manualmente en el EC2, renueva el token antes:
> ```bash
> aws ecr get-login-password --region eu-west-1 | sudo docker login --username AWS --password-stdin <ECR_URL>
> ```

### 2.5 S3 (Almacenamiento de archivos)

El bucket S3 `boscogest-uploads-{environment}` almacena todos los archivos subidos por los usuarios: revistas (PDF), imagenes de actividades y comunicaciones, logos de entidades y recursos formativos (documentos/imagenes).

| Caracteristica | Valor |
|----------------|-------|
| Nombre | `{project_name}-uploads-{environment}` |
| Acceso | **Privado** (block_public_acls, block_public_policy, ignore_public_acls, restrict_public_buckets) |
| Cifrado | AES256 server-side (aws:kms no necesario para este caso) |
| CORS | GET desde cualquier origen (para que `<img src="presigned_url">` funcione en el navegador) |
| Versionado | Desactivado |
| force_destroy | `true` (permite `terraform destroy` con objetos dentro) |

**Patron de acceso:** El backend almacena en BD solo la **S3 key** (ej: `magazines/uuid.pdf`). Al servir archivos:
- **Descargas** (revistas, recursos): el endpoint genera una **presigned URL** y devuelve `RedirectResponse`
- **Imagenes en JSON** (actividades, comunicaciones, logos): la S3 key se convierte a presigned URL antes de devolver la respuesta

La instancia EC2 accede a S3 via **IAM Instance Profile** (sin credenciales hardcoded). La policy permite `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` y `s3:ListBucket` sobre el bucket de uploads.

### 2.6 Bootstrap del EC2 (`user_data.sh`)

Al arrancar la instancia por primera vez, el script:

1. Actualiza el sistema (`yum update`)
2. Instala Docker y Docker Compose v2
3. Instala Git
4. Crea el directorio `/opt/boscogest` con el fichero `.env` (con las credenciales de RDS, config S3 y JWT inyectadas por Terraform)
5. Genera un `docker-compose.yml` de produccion que usa la imagen Docker del backend y apunta a la RDS
6. Ejecuta `docker compose pull && docker compose up -d`

Las variables sensibles (`DATABASE_URL`, `SECRET_KEY`) se inyectan via `templatefile()` de Terraform y nunca se almacenan en el repositorio. Las variables de almacenamiento (`STORAGE_BACKEND=s3`, `S3_BUCKET_NAME`, `AWS_REGION`) se configuran automaticamente.

> **Importante:** El `user_data.sh` solo se ejecuta en el primer arranque de la instancia. Si la imagen Docker aun no existe en ECR en ese momento, `docker compose pull` fallara. En ese caso, hay que hacer pull y up manualmente tras subir la imagen (ver seccion 4.4).

> **Nota sobre `templatefile()`:** Las variables shell que usen `${}` deben escaparse como `$${}` en el script para que Terraform no las interprete. Ejemplo: `$${DOCKER_COMPOSE_VERSION}`.

### 2.7 WebSocket (Notificaciones en tiempo real)

El sistema de notificaciones usa WebSocket nativo de FastAPI (`/api/v1/notifications/ws`) que corre en el mismo proceso y puerto que la API REST (:8000). **No requiere infraestructura adicional** — el Security Group del EC2 ya permite trafico en el puerto 8000, que transporta tanto HTTP como WebSocket (upgrade de protocolo HTTP → WS).

| Aspecto | Detalle |
|---------|---------|
| Protocolo | `ws://` (o `wss://` si se anade TLS) en puerto 8000 |
| Autenticacion | JWT via query param (`?token=...`) |
| Escalabilidad | Single-node (suficiente para t3.micro con ~100 conexiones concurrentes) |
| Persistencia | Las notificaciones se persisten en PostgreSQL (RDS); WebSocket solo entrega en tiempo real |

> **Nota:** Si en el futuro se necesita escalar a multiples instancias EC2 (ej: con un ALB), se requerira un broker de mensajes (Redis Pub/Sub o similar) para sincronizar las conexiones WebSocket entre nodos. Para el scope actual del proyecto, el enfoque single-node es suficiente.

### 2.8 Variables

| Variable | Descripcion | Default | Sensible |
|----------|-------------|---------|----------|
| `aws_region` | Region AWS | `eu-west-1` | No |
| `project_name` | Nombre del proyecto | `boscogest` | No |
| `instance_type` | Tipo de instancia EC2 | `t3.micro` | No |
| `key_name` | Nombre del key pair SSH | (obligatorio) | No |
| `allowed_ssh_cidrs` | CIDRs permitidos para SSH | `["0.0.0.0/0"]` | No |
| `db_name` | Nombre de la base de datos | `boscogest` | No |
| `db_username` | Usuario master de RDS | `boscogest_admin` | No |
| `db_password` | Password master de RDS | (obligatorio) | Si |
| `db_instance_class` | Clase de instancia RDS | `db.t3.micro` | No |
| `secret_key` | Clave secreta JWT | (obligatorio) | Si |
| `cors_origins` | Origenes CORS permitidos | `*` | No |
| `docker_image` | Imagen Docker del backend | (obligatorio) | No |
| `domain_name` | Dominio personalizado (ej: `boscogest.com`). Vacio = sin CloudFront/ACM | `""` | No |
| `frontend_bucket_name` | Nombre del bucket S3 del frontend | `boscogest-frontend` | No |

> **Nota sobre `db_username`:** No usar `admin` — es una palabra reservada en PostgreSQL en RDS. El default es `boscogest_admin`.

> **Nota sobre `cors_origins`:** No se puede usar `*` si el backend usa `allow_credentials=True` en CORS. Usar la URL exacta del frontend S3 (ej: `http://boscogest-frontend.s3-website-eu-west-1.amazonaws.com`). Atencion al formato de la URL: S3 usa guiones (`s3-website-eu-west-1`), no puntos.

### 2.9 Outputs

| Output | Descripcion |
|--------|-------------|
| `ec2_public_ip` | IP publica estatica del EC2 (Elastic IP) |
| `ec2_public_dns` | DNS publico del EC2 |
| `api_url` | URL completa de la API (`http://<eip>:8000`) |
| `rds_endpoint` | Endpoint de la RDS (host:puerto) |
| `database_url` | URL de conexion a la BD (password enmascarado) |
| `vpc_id` | ID de la VPC creada |
| `ecr_repository_url` | URL del repositorio ECR |
| `ecr_push_commands` | Comandos para build, tag y push a ECR |
| `s3_bucket_name` | Nombre del bucket S3 de uploads |
| `s3_bucket_arn` | ARN del bucket S3 de uploads |
| `cloudfront_domain` | Dominio de la distribucion CloudFront (`d1234.cloudfront.net`) |
| `cloudfront_distribution_id` | ID de la distribucion (para invalidar cache) |
| `acm_dns_validation_records` | Registros CNAME para validar el certificado SSL |
| `dns_records_to_add` | Instrucciones de los registros DNS a configurar en el registrador |
| `frontend_url_with_domain` | URL final del frontend (`https://boscogest.com` o URL S3) |

---

## 3. Frontend — `boscoGest-front/infra/`

### 3.1 Recursos creados

| Recurso | Descripcion |
|---------|-------------|
| S3 Bucket | Almacena los ficheros del build de Angular |
| Website Configuration | `index.html` como index y error document (SPA routing) |
| Public Access Block | Permite acceso publico de lectura |
| Bucket Policy | `s3:GetObject` para todo el mundo (`Principal: *`) |
| CORS Configuration | Permite `GET` y `HEAD` desde cualquier origen |

### 3.2 Ficheros

```
boscoGest-front/infra/
├── main.tf                   # S3 bucket, website, policy, CORS
├── variables.tf              # Variables de entrada
├── outputs.tf                # URL del sitio, comando de deploy
├── terraform.tfvars.example  # Ejemplo de configuracion
└── .gitignore                # Excluye .terraform, *.tfstate, *.tfvars
```

### 3.3 SPA Routing

El `error_document` apunta a `index.html`, lo que permite que Angular maneje todas las rutas. Cuando un usuario navega directamente a `/dashboard` o `/resources/1`, S3 devuelve `index.html` en lugar de un 404, y Angular Router se encarga del enrutamiento en el cliente.

### 3.4 Variables

| Variable | Descripcion | Default |
|----------|-------------|---------|
| `aws_region` | Region AWS | `eu-west-1` |
| `project_name` | Nombre del proyecto | `boscogest` |
| `bucket_name` | Nombre del bucket S3 (debe ser unico globalmente) | (obligatorio) |

### 3.5 Outputs

| Output | Descripcion |
|--------|-------------|
| `website_url` | URL del sitio estatico S3 |
| `bucket_name` | Nombre del bucket creado |
| `bucket_arn` | ARN del bucket |
| `deploy_command` | Comando `aws s3 sync` listo para ejecutar |

---

## 4. Guia de despliegue inicial (entorno desde cero)

### 4.0 Requisitos previos

- **Terraform** >= 1.0 instalado (`brew install terraform`)
- **AWS CLI** configurado con credenciales (`aws configure`)
- **Docker** con soporte buildx (para cross-compile desde Apple Silicon)
- **Key Pair SSH** creado en la region AWS elegida (`aws ec2 create-key-pair --key-name boscogest-key --region eu-west-1`)

### 4.1 Crear la infraestructura backend

```bash
cd boscoGest/infra

# 1. Copiar y rellenar la configuracion
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con los valores reales
# IMPORTANTE: db_username NO puede ser "admin" (palabra reservada en RDS)

# 2. Inicializar y aplicar (crea VPC, EC2, RDS, ECR, S3, Elastic IP)
terraform init
terraform plan
terraform apply

# 3. Anotar la URL del ECR y la IP del EC2
terraform output ecr_repository_url
terraform output ec2_public_ip
```

### 4.2 Publicar la imagen Docker del backend en ECR

```bash
cd boscoGest/

# 1. Login en ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin <ECR_URL>

# 2. Build para linux/amd64 (obligatorio desde Apple Silicon)
docker buildx build --platform linux/amd64 -t boscogest-back .

# 3. Tag y push
docker tag boscogest-back:latest <ECR_URL>:latest
docker push <ECR_URL>:latest
```

> **Importante:** Si desarrollas en un Mac con Apple Silicon (M1/M2/M3/M4), debes usar `docker buildx build --platform linux/amd64` para compilar la imagen para la arquitectura del EC2 (x86_64). Sin esto, `docker compose pull` dara error `no matching manifest for linux/amd64`.

### 4.3 Arrancar el backend en el EC2

El `user_data.sh` intenta hacer `docker compose pull` en el primer arranque, pero si la imagen aun no existia en ECR, habra fallado. Hay que hacerlo manualmente:

```bash
# SSH a la instancia
ssh -i ~/.ssh/boscogest-key.pem ec2-user@<ec2_public_ip>

# Renovar token ECR (expiran cada 12h)
aws ecr get-login-password --region eu-west-1 | \
  sudo docker login --username AWS --password-stdin <ECR_URL>

# Pull y arrancar
cd /opt/boscogest
sudo docker compose pull
sudo docker compose up -d

# Verificar que el contenedor esta corriendo
sudo docker compose ps
```

### 4.4 Ejecutar migraciones

Las migraciones de Alembic crean las tablas y el seed inicial (superadmin user, roles, permisos):

```bash
sudo docker compose exec back alembic upgrade head
```

Verificar que el seed se aplico:

```bash
sudo docker compose exec back python -c "
from app.database import SyncSessionLocal
from app.models.user_model import User
db = SyncSessionLocal()
user = db.query(User).first()
print(f'User: {user.email}' if user else 'No users found')
db.close()
"
```

Debe mostrar `User: superadmin@boscogest.com`. Credenciales iniciales: `superadmin@boscogest.com` / `superadmin123`.

### 4.5 Verificar el backend

```bash
# Desde el EC2
curl http://localhost:8000/docs

# Desde tu maquina local
curl http://<ec2_public_ip>:8000/docs
```

### 4.6 Desplegar el frontend

```bash
cd boscoGest-front/infra

# 1. Copiar y rellenar la configuracion
cp terraform.tfvars.example terraform.tfvars

# 2. Crear la infraestructura S3
terraform init
terraform apply

# 3. Anotar la URL del sitio
terraform output website_url
```

### 4.7 Configurar apiUrl y subir el build

```bash
cd boscoGest-front

# 1. Actualizar la URL de la API en environment.prod.ts
#    apiUrl: 'http://<ELASTIC_IP>:8000'

# 2. Compilar para produccion
npm run build

# 3. Subir a S3
aws s3 sync dist/boscoGest-front/browser/ s3://<bucket_name> --delete
```

### 4.8 Configurar CORS del backend

Actualizar el `.env` en el EC2 con la URL exacta del frontend S3:

```bash
ssh -i ~/.ssh/boscogest-key.pem ec2-user@<ec2_public_ip>
cd /opt/boscogest

# Editar .env: CORS_ORIGINS=http://<bucket>.s3-website-<region>.amazonaws.com
sudo nano .env

# Reiniciar para aplicar
sudo docker compose down && sudo docker compose up -d
```

> **Atencion al formato de la URL S3:** Usar guiones, no puntos: `s3-website-eu-west-1` (correcto) vs `s3-website.eu-west-1` (incorrecto). Verificar la URL exacta en la barra del navegador.

> **Importante:** Usar `docker compose down && docker compose up -d` en vez de `docker compose restart` para que se re-lea el `.env`.

### 4.9 Migrar archivos locales a S3 (opcional)

Si hay archivos existentes en el volumen local `uploads/`, migrarlos a S3:

```bash
sudo docker compose exec back python -m scripts.migrate_uploads_to_s3
```

---

## 5. Resumen del flujo completo

```
1. cd boscoGest/infra && terraform apply       → VPC + EC2 + EIP + RDS + ECR + S3 uploads
2. docker buildx build --platform linux/amd64  → Build imagen para x86_64
3. docker tag + push a ECR                     → Imagen del backend en ECR
4. SSH al EC2: docker compose pull && up       → Backend corriendo
5. alembic upgrade head                        → Tablas + seed creados
6. cd boscoGest-front/infra && terraform apply → S3 bucket frontend
7. Actualizar environment.prod.ts con la EIP
8. npm run build                               → Build de produccion
9. aws s3 sync dist/... s3://bucket            → Frontend desplegado
10. Actualizar CORS_ORIGINS en .env del EC2    → CORS configurado
11. (Opcional) terraform apply -var="domain_name=boscogest.com"
                                               → CloudFront + ACM + HTTPS
12. Validar certificado y configurar DNS       → Dominio activo
```

---

## 6. Dominio personalizado (CloudFront + ACM)

Si se dispone de un dominio propio (ej: `boscogest.com`), se puede configurar CloudFront como CDN con HTTPS gratuito via ACM. Todos los recursos se crean condicionalmente — si `domain_name` esta vacio, no se crea nada.

### 6.1 Aplicar Terraform con dominio

```bash
cd boscoGest/infra
terraform plan -var="domain_name=boscogest.com"
terraform apply -var="domain_name=boscogest.com"
```

O anadir `domain_name = "boscogest.com"` al fichero `terraform.tfvars`.

Terraform creara:
- **Certificado ACM** en us-east-1 (wildcard `*.boscogest.com`) — requisito de CloudFront
- **Distribucion CloudFront** apuntando al bucket S3 del frontend con:
  - Redirect HTTP → HTTPS
  - SPA routing (403/404 → `/index.html`)
  - `PriceClass_100` (US + Europa, la opcion mas economica)

### 6.2 Validar el certificado SSL

El certificado queda en estado **pendiente de validacion**. Terraform muestra los registros CNAME necesarios:

```bash
terraform output acm_dns_validation_records
```

Anadir esos registros CNAME en el panel del registrador de dominio. Ejemplo:

| Tipo | Nombre | Valor |
|------|--------|-------|
| CNAME | `_abc123.boscogest.com` | `_xyz.acm-validations.aws.` |

AWS valida automaticamente en unos minutos tras detectar el registro DNS.

### 6.3 Configurar DNS del dominio

Una vez el certificado este validado y CloudFront desplegado (~5 min):

```bash
terraform output dns_records_to_add
```

Anadir en el registrador de dominio:

| Tipo | Nombre | Valor |
|------|--------|-------|
| **CNAME** | `www` | `d1234abcd.cloudfront.net` |
| **ALIAS/ANAME** | `@` (raiz) | `d1234abcd.cloudfront.net` |

> **Nota:** Si el registrador no soporta registros ALIAS/ANAME para el dominio raiz, las opciones son:
> - Migrar los nameservers a **Route 53** (soporta ALIAS nativo)
> - Usar solo `www.boscogest.com` y configurar un redirect del raiz en el registrador

### 6.4 Actualizar CORS del backend

```bash
ssh -i ~/.ssh/boscogest-key.pem ec2-user@<ELASTIC_IP>
cd /opt/boscogest
sudo nano .env

# Cambiar CORS_ORIGINS:
# CORS_ORIGINS=https://boscogest.com,https://www.boscogest.com

sudo docker compose down && sudo docker compose up -d
```

### 6.5 Invalidar cache de CloudFront

Tras cada deploy del frontend, CloudFront puede servir la version cacheada. Para forzar la actualizacion:

```bash
aws cloudfront create-invalidation \
  --distribution-id $(terraform output -raw cloudfront_distribution_id) \
  --paths "/*"
```

O usar el ID directamente:

```bash
aws cloudfront create-invalidation --distribution-id E1234ABCD --paths "/*"
```

### 6.6 Arquitectura con dominio personalizado

```
Usuarios ──► boscogest.com (DNS)
                  │
                  ▼
            CloudFront (HTTPS, cache, CDN)
                  │
                  ▼
            S3 boscogest-frontend (HTTP, static website)

API ──────► <ELASTIC_IP>:8000 (sin dominio, directo al EC2)
```

> **Nota:** La API sigue accesible por IP directa. Si se quiere `api.boscogest.com`, anadir un registro DNS tipo A apuntando a la Elastic IP del EC2, y configurar un certificado SSL en el EC2 con Let's Encrypt (fuera del scope actual de Terraform).

---

## 7. Costes estimados (capa gratuita AWS)

| Servicio | Free Tier | Fuera de Free Tier (aprox.) |
|----------|-----------|----------------------------|
| EC2 t3.micro | 750 h/mes durante 12 meses | ~8 USD/mes |
| Elastic IP | Gratis si esta asociada a instancia corriendo | 3.65 USD/mes si no esta asociada |
| RDS db.t3.micro | 750 h/mes durante 12 meses | ~15 USD/mes |
| ECR | 500 MB/mes almacenamiento | ~0.10 USD/GB/mes |
| S3 (hosting frontend) | 5 GB almacenamiento, 20k GET | ~0.50 USD/mes |
| S3 (uploads) | 5 GB incluidos en free tier | ~0.023 USD/GB/mes |
| Transferencia datos | 100 GB/mes salida | 0.09 USD/GB |
| CloudFront | 1 TB/mes transferencia (12 meses) | ~0.085 USD/GB |
| ACM | Gratis siempre | Gratis |

**Total durante Free Tier: ~0.50 USD/mes** (solo S3 si se excede el free tier).
**Total fuera de Free Tier: ~27 USD/mes** aproximadamente (sin CloudFront) o ~30 USD/mes (con CloudFront, tras free tier).

---

## 8. Destruir la infraestructura

```bash
# Destruir frontend
cd boscoGest-front/infra
terraform destroy

# Destruir backend (destruye VPC, EC2, EIP, RDS y todos los datos)
cd boscoGest/infra
terraform destroy
```

> **Atencion:** `terraform destroy` en el backend eliminara la RDS y todos sus datos. La opcion `skip_final_snapshot = true` esta configurada, por lo que no se creara un snapshot final. Cambiala a `false` en produccion si necesitas conservar los datos.
>
> El bucket S3 de uploads (`force_destroy = true`) tambien se eliminara con todos los archivos subidos (revistas, imagenes, logos). Si necesitas conservar los archivos, descargalos antes con `aws s3 sync s3://bucket ./backup`.

---

## 9. Troubleshooting

### El contenedor no arranca / esta en restart loop

```bash
sudo docker compose logs --tail 30 back
```

Causa comun: el `start.sh` no puede conectar a la base de datos. Verificar que la `DATABASE_URL` en `.env` es correcta y que el Security Group de RDS permite conexiones desde el EC2.

### `docker compose pull` da error de autenticacion

Los tokens de ECR expiran cada 12 horas:

```bash
aws ecr get-login-password --region eu-west-1 | \
  sudo docker login --username AWS --password-stdin <ECR_URL>
```

### Error CORS en el navegador

1. Verificar que `CORS_ORIGINS` en `.env` coincide **exactamente** con la URL del navegador (incluido protocolo y formato)
2. Usar `docker compose down && docker compose up -d` (no `restart`) para re-leer `.env`
3. No se puede usar `CORS_ORIGINS=*` porque el backend usa `allow_credentials=True`

### Imagen Docker: `no matching manifest for linux/amd64`

La imagen fue compilada para ARM (Apple Silicon). Recompilar con:

```bash
docker buildx build --platform linux/amd64 -t boscogest-back .
```

### Las migraciones fallan con errores de columnas

El seeder usa SQL puro (no modelos ORM) para evitar incompatibilidades entre el esquema del momento de la migracion y los modelos actuales. Si aparecen errores de columnas en migraciones seed, verificar que los INSERT solo referencian columnas que existen en ese punto de la cadena de migraciones.
