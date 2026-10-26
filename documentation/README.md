# BoscoGest - Plataforma SaaS Multientidad

Plataforma de gestión para confederaciones, federaciones y asociaciones locales. Backend en FastAPI + PostgreSQL, frontend en Angular 20 + Angular Material 3, apps móviles Android/iOS con Capacitor.

---

## Requisitos previos

- **Python 3.11+**
- **Node.js 22+** y **npm**
- **PostgreSQL 15+**
- **Docker y Docker Compose** (opcional, para levantar todo con un comando)
- **Android Studio + SDK 34+** (opcional, para compilar app Android)
- **Xcode 15+** (opcional, para compilar app iOS, solo macOS)

---

## Opcion 1: Docker Compose (recomendado)

Levanta PostgreSQL, backend y frontend con un solo comando:

```bash
cd boscoGest
cp .env.example .env
docker-compose up --build
```

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost |
| Backend (API) | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

Las migraciones de Alembic se ejecutan automaticamente al arrancar el backend (`start.sh`).

### Credenciales por defecto

| Usuario | Password |
|---------|----------|
| `superadmin@boscogest.com` | `superadmin123` |

---

## Opcion 2: Desarrollo local (sin Docker)

### 1. Base de datos PostgreSQL

Instala PostgreSQL 15+ y crea la base de datos:

```bash
psql -U postgres
```

```sql
CREATE USER admin WITH PASSWORD 'admin123';
CREATE DATABASE boscogest OWNER admin;
\q
```

### 2. Backend (FastAPI)

```bash
cd boscoGest

# Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env si es necesario (por defecto apunta a localhost:5432)

# Ejecutar migraciones
alembic upgrade head

# Arrancar el servidor de desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El backend estara disponible en http://localhost:8000 y la documentacion Swagger en http://localhost:8000/docs.

### 3. Frontend (Angular)

```bash
cd boscoGest-front

# Instalar dependencias
npm install

# Arrancar servidor de desarrollo
npm start
```

El frontend estara disponible en http://localhost:4200. Por defecto conecta al backend en `http://localhost:8000` (configurado en `src/environments/environment.ts`).

---

## Variables de entorno del backend

El archivo `.env.example` contiene todas las variables necesarias:

| Variable | Descripcion | Valor por defecto |
|----------|-------------|-------------------|
| `DATABASE_URL` | Conexion a PostgreSQL (desarrollo local) | `postgresql+psycopg2://admin:admin123@localhost:5432/boscogest` |
| `DATABASE_URL_DOCKER` | Conexion a PostgreSQL (Docker) | `postgresql+psycopg2://admin:admin123@db:5432/boscogest` |
| `SECRET_KEY` | Clave para firmar tokens JWT (min 32 caracteres) | Cambiar en produccion |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duracion del token de acceso | `30` |
| `UPLOAD_DIR` | Directorio para archivos subidos | `uploads` |
| `STORAGE_BACKEND` | Backend de almacenamiento (`local` o `s3`) | `local` |
| `CORS_ORIGINS` | Origenes permitidos (separados por coma) | `http://localhost:4200,...` |

---

## Comandos utiles

### Backend

```bash
cd boscoGest
source .venv/bin/activate

# Ejecutar tests
python -m pytest

# Ejecutar un test especifico
python -m pytest app/tests/test_users.py -v

# Crear nueva migracion de Alembic
alembic revision --autogenerate -m "descripcion del cambio"

# Aplicar migraciones pendientes
alembic upgrade head

# Ver estado de migraciones
alembic current

# Linting
ruff check app/

# Type checking
mypy app/
```

### Frontend

```bash
cd boscoGest-front

# Servidor de desarrollo
npm start

# Build de produccion
npx ng build

# Ejecutar tests
npm test
```

### Apps moviles (Capacitor)

```bash
cd boscoGest-front

# Sincronizar build con proyectos nativos
npm run cap:sync

# Abrir proyecto en Android Studio / Xcode
npm run cap:android
npm run cap:ios

# Build + ejecutar en emulador/dispositivo
npm run cap:run:android
npm run cap:run:ios
```

Para documentacion detallada, ver [CAPACITOR.md](CAPACITOR.md).

---

## Estructura del proyecto

```
TFG/
├── boscoGest/                  # Backend (FastAPI)
│   ├── app/
│   │   ├── api/v1/             # Routers (controllers HTTP)
│   │   ├── services/           # Logica de negocio
│   │   ├── repositories/       # Acceso a datos (SQLAlchemy)
│   │   ├── models/             # Modelos SQLAlchemy
│   │   ├── schemas/            # Schemas Pydantic
│   │   ├── utils/              # Auth (JWT, passwords)
│   │   ├── database/           # Configuracion BD + seeders
│   │   └── tests/              # Tests pytest
│   ├── alembic/                # Migraciones de base de datos
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── boscoGest-front/            # Frontend (Angular 20) + Apps moviles (Capacitor)
│   ├── android/                # Proyecto Android Studio (auto-generado)
│   ├── ios/                    # Proyecto Xcode (auto-generado)
│   ├── capacitor.config.ts     # Configuracion de Capacitor
│   ├── src/app/
│   │   ├── auth/               # Login, guards, interceptor
│   │   ├── activities/         # Gestion de actividades
│   │   ├── communications/     # Noticias con workflow editorial
│   │   ├── entities/           # Gestion de entidades
│   │   ├── magazines/          # Revistas PDF
│   │   ├── resources/          # Recursos formativos
│   │   ├── notifications/      # Notificaciones in-app
│   │   ├── chat/               # Chat en tiempo real
│   │   ├── fees/               # Cuotas y asignaciones
│   │   ├── roles/              # Gestion de roles
│   │   ├── users/              # Gestion de usuarios
│   │   ├── settings/           # Branding y vistas
│   │   ├── utils/              # Utilidades cross-platform
│   │   └── models/             # Interfaces TypeScript
│   ├── Dockerfile
│   └── package.json
│
├── ARCHITECTURE.md             # Documentacion de arquitectura
├── ANALISIS_PROYECTO.md        # Analisis de requisitos vs implementacion
├── CAPACITOR.md                # Documentacion de apps moviles (Capacitor)
└── README.md                   # Este archivo
```

---

## Arquitectura

- **Backend:** Arquitectura de 3 capas (Router → Service → Repository)
- **Frontend:** Componentes standalone Angular con signals
- **Movil:** Capacitor 8 — mismo codebase Angular empaquetado como app nativa Android/iOS
- **Auth:** JWT con blacklist (JTI) para revocacion
- **Permisos:** RBAC jerarquico con herencia de permisos entre entidades padre/hijo
- **Notificaciones:** PostgreSQL (persistencia) + WebSocket (tiempo real)
- **Almacenamiento:** Local (desarrollo) o S3 (produccion)

Para mas detalle, ver [ARCHITECTURE.md](ARCHITECTURE.md).
