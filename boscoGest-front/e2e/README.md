# Pruebas end-to-end

Cubren lo que un test unitario no puede: que la aplicación **renderiza y
reacciona**. Importa especialmente aquí porque todos los componentes usan
`OnPush`, donde un componente que no se marca como sucio muestra contenido
obsoleto o vacío mientras la build sigue en verde.

## Requisitos

Necesitas tres cosas levantadas:

**1. Base de datos con datos sembrados**

```bash
docker run -d --name bg-e2e \
  -e POSTGRES_USER=bg -e POSTGRES_PASSWORD=bg -e POSTGRES_DB=boscogest \
  -p 55433:5432 postgres:15
```

**2. Backend**

```bash
cd ../boscoGest
source .venv/bin/activate
export DATABASE_URL="postgresql+psycopg2://bg:bg@localhost:55433/boscogest"
export SECRET_KEY="e2e-secret-key-de-al-menos-32-caracteres-aqui"
export CORS_ORIGINS="http://localhost:4200"
export STORAGE_BACKEND=local

alembic upgrade head
SEED_SUPERADMIN_PASSWORD="VerificaLocal123" python -m app.database.seeds.initial_seeder
docker exec -i bg-e2e psql -U bg -d boscogest -q < scripts/seed_salesian_entities.sql

uvicorn app.main:app --host 127.0.0.1 --port 8000
```

> En macOS, `localhost` resuelve primero a IPv6. Si tienes el `docker-compose`
> del proyecto levantado, su contenedor ocupa `[::]:8000` y el navegador hablará
> con **ese** backend, no con el tuyo. Párralo antes: `docker stop boscoGest_back`.

**3. Frontend**

```bash
npm start
```

## Ejecutar

```bash
npm run e2e            # sin interfaz
npm run e2e:headed     # viendo el navegador
npm run e2e:ui         # modo interactivo de Playwright
```

### Qué se ejecuta en el CI y qué no

Las pruebas marcadas `@local` se saltan cuando `CI` está definido. Son las que
en el CI no pueden pasar, por dos motivos ajenos al código:

- **Las líneas base visuales están generadas en macOS**, con nombres
  `*-chromium-darwin.png`. El CI corre en Linux, donde Playwright busca
  `*-chromium-linux.png`, no encuentra ninguna y falla siempre.
- **Algunas necesitan un centenar de socios** —búsqueda, paginación, el
  diálogo de borrado— y allí solo existe el usuario del seeder.

En local sí se ejecutan, que es donde sirven de red de seguridad. Un job
permanentemente en rojo no lo mira nadie y acaba tapando fallos de verdad.

```bash
npm run e2e              # todo, incluidas las @local
CI=true npm run e2e      # lo mismo que ejecuta el CI
```

Para que las visuales pasaran también en el CI harían falta dos cosas: un
script que siembre datos de prueba, y generar las líneas base en Linux dentro
de un contenedor. Mientras no existan, viven aquí.

### Generadores de capturas

`play-shots`, `guide-shots`, `guide2-shots`, `guide2-updates` y `screenshots`
no son pruebas: escriben las imágenes de la guía de usuario y de las fichas de
Google Play y App Store. Están fuera de `npm run e2e` por dos motivos — fallan
si la base de datos no tiene contenido de demostración, y cuando arrancan
sobrescriben imágenes ya revisadas con lo que haya en ese momento.

```bash
npm run e2e:shots -- play-shots     # solo las de la ficha
npm run e2e:shots                   # todas
```

Revisa siempre el diff de las imágenes antes de commitear.

Con `E2E_START_SERVER=1` Playwright arranca `npm start` por su cuenta.

## Variables

| Variable | Por defecto | Para qué |
|---|---|---|
| `E2E_BASE_URL` | `http://localhost:4200` | Dónde escucha el frontend |
| `E2E_API_URL` | `http://localhost:8000` | Dónde escucha la API |
| `E2E_USER` | `superadmin@boscogest.com` | Usuario con el que iniciar sesión |
| `E2E_PASSWORD` | `VerificaLocal123` | Su contraseña |
| `E2E_START_SERVER` | (sin definir) | Que Playwright levante el frontend |

## Comparación visual

`visual.spec.ts` y `visual-states.spec.ts` comparan capturas contra líneas base
versionadas. Son la red que permitió quitar los 55 `!important` de `styles.css`
verificando que nada cambiaba, en lugar de a ojo.

Tras un cambio visual **intencionado**, regenera las líneas base:

```bash
npm run e2e -- visual --update-snapshots
```

y revisa el diff de las imágenes antes de commitear. Hazlo con la base de
datos que usaste para generarlas la primera vez: si la regeneras contra una
instalación recién sembrada, las líneas base pasan a mostrar tablas vacías y
dejan de detectar nada.

> **Pendiente.** `desktop entities` y `mobile entities` están desfasadas: el
> arreglo de interlineado de `.page-title` bajó el contenido 28px. El cambio es
> intencionado y hay que regenerarlas, pero solo desde un entorno con los datos
> con los que se hicieron.

> **Cuidado con `threshold`.** El valor por defecto de Playwright (0.2) es
> demasiado permisivo para cambios de tono: blanco `(255,255,255)` frente al
> gris de superficie de Material `(239,237,240)` queda por debajo del umbral, y
> un panel entero cambiando de color se contaba como idéntico. Estas specs usan
> `threshold: 0.02`.

## Notas

- La sesión se obtiene **una vez** por la API en `auth.setup.ts` y se reutiliza.
  Rellenar el formulario de login en cada prueba haría que toda la suite fallara
  por un único motivo ajeno.
- La suite corre con un solo worker y sin paralelismo: habla con un backend real
  y las pruebas comparten estado.
- El listado de usuarios necesita **más de 25 usuarios** para que las pruebas de
  paginación tengan sentido, y al menos uno con apellido acentuado (`Muñoz`,
  `García`) para la búsqueda sin tildes.
