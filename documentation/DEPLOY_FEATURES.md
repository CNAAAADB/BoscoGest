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

### 2.1 Build y push de la imagen

Desde tu maquina local:

```bash
cd boscoGest

# 1. Login en ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin 909186483504.dkr.ecr.eu-west-1.amazonaws.com

# 2. Build (cross-compile para x86_64 desde Apple Silicon)
docker buildx build --platform linux/amd64 -t boscogest-back .

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

### 2.3 Ejecutar migraciones (si las hay)

Si la feature incluye nuevas migraciones de Alembic:

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

# Probar la API
curl http://localhost:8000/docs
```

---

## 3. Deploy del frontend

Desde tu maquina local:

```bash
cd boscoGest-front

# 1. Build de produccion
npm run build

# 2. Subir a S3 (reemplaza todo el contenido)
aws s3 sync dist/boscoGest-front/browser/ s3://boscogest-frontend --delete
```

El despliegue es inmediato — no hay contenedores que reiniciar.

> **Nota:** Si el navegador muestra una version antigua, hacer hard refresh (Cmd+Shift+R / Ctrl+Shift+R) o vaciar cache.

---

## 4. Deploy completo (backend + frontend)

Cuando una feature afecta a ambos, desplegar en este orden:

1. **Backend primero** (para que los nuevos endpoints esten disponibles)
2. **Migraciones** (si las hay)
3. **Frontend despues** (para que la UI use los nuevos endpoints)

```bash
# === BACKEND ===
cd boscoGest
docker buildx build --platform linux/amd64 -t boscogest-back .
docker tag boscogest-back:latest 909186483504.dkr.ecr.eu-west-1.amazonaws.com/boscogest-back:latest
docker push 909186483504.dkr.ecr.eu-west-1.amazonaws.com/boscogest-back:latest

# En el EC2:
ssh -i ~/.ssh/boscogest-key.pem ec2-user@<ELASTIC_IP>
aws ecr get-login-password --region eu-west-1 | sudo docker login --username AWS --password-stdin 909186483504.dkr.ecr.eu-west-1.amazonaws.com
cd /opt/boscogest
sudo docker compose pull
sudo docker compose down && sudo docker compose up -d
sudo docker compose exec back alembic upgrade head  # si hay migraciones

# === FRONTEND ===
cd boscoGest-front
npm run build
aws s3 sync dist/boscoGest-front/browser/ s3://boscogest-frontend --delete
```

---

## 5. Cambios en variables de entorno

Si solo necesitas cambiar una variable de entorno (ej: CORS_ORIGINS):

```bash
ssh -i ~/.ssh/boscogest-key.pem ec2-user@<ELASTIC_IP>
cd /opt/boscogest

# Editar .env
sudo nano .env

# Reiniciar (down + up para re-leer .env)
sudo docker compose down && sudo docker compose up -d
```

> **Importante:** `docker compose restart` NO re-lee el `.env`. Usar siempre `down && up`.

---

## 6. Rollback

### Backend: volver a una imagen anterior

```bash
# En el EC2, volver a la imagen anterior (ECR conserva las ultimas 10)
cd /opt/boscogest

# Ver imagenes disponibles
aws ecr list-images --repository-name boscogest-back --region eu-west-1

# Editar docker-compose.yml para apuntar a un tag especifico
sudo nano docker-compose.yml
# Cambiar image: .../:latest por image: .../:sha-xxx

sudo docker compose pull
sudo docker compose down && sudo docker compose up -d
```

### Backend: rollback de migraciones

```bash
# Bajar una migracion
sudo docker compose exec back alembic downgrade -1

# Bajar a una revision especifica
sudo docker compose exec back alembic downgrade <revision_id>
```

### Frontend: volver a un build anterior

Reconstruir desde el commit anterior y redesplegar:

```bash
cd boscoGest-front
git checkout <commit_anterior>
npm run build
aws s3 sync dist/boscoGest-front/browser/ s3://boscogest-frontend --delete
git checkout main  # volver a la rama actual
```

---

## 7. Checklist de deploy

- [ ] Tests pasan en local (`pytest` para backend, `npm test` para frontend)
- [ ] Build de produccion compila sin errores
- [ ] Si hay migraciones: probadas en local con `alembic upgrade head` + `alembic downgrade -1`
- [ ] Login en ECR renovado (tokens expiran cada 12h)
- [ ] Imagen construida con `--platform linux/amd64`
- [ ] `docker compose pull` + `down` + `up` (no solo `restart`)
- [ ] Migraciones ejecutadas en produccion si aplica
- [ ] Verificar logs del contenedor tras deploy
- [ ] Verificar funcionalidad en el navegador (hard refresh)
