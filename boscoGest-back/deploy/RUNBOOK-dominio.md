# Runbook: poner el dominio en producción

Secuencia para pasar de la instalación actual (IP pública, HTTP en claro,
bucket público) a dominio propio con TLS de extremo a extremo.

El orden **no es negociable**: hay dependencias cruzadas entre los dos estados
de Terraform, y varios pasos tienen latencia que no controlamos (propagación
DNS, emisión de certificados). Saltarse el orden deja el sitio caído.

Sustituye `EJEMPLO.es` por el dominio real en todo el documento.

---

## Antes de empezar

| Requisito | Comprobación |
|---|---|
| Dominio registrado | Acceso al panel del registrador para cambiar nameservers |
| Credenciales AWS | `aws sts get-caller-identity` |
| Clave SSH | `~/.ssh/boscogest-key.pem` |
| `deploy/.env.prod` | Copiado de `.env.prod.example` y relleno |

---

## Paso 1 — Crear la zona DNS y arrancar la propagación

Es lo primero porque la propagación de nameservers puede tardar hasta 48 h y
**todo lo demás depende de ella**: el certificado ACM no se valida, y Caddy no
puede emitir el suyo, hasta que el dominio resuelva contra AWS.

En `boscoGest/infra/terraform.tfvars`:

```hcl
domain_name         = "EJEMPLO.es"
create_route53_zone = true
dmarc_report_email  = "tu-correo@EJEMPLO.es"
```

```bash
cd boscoGest/infra
terraform apply -target=aws_route53_zone.main
terraform output route53_nameservers
```

Copia esos cuatro nameservers al panel del registrador, sustituyendo los que
tenga. A partir de aquí, el reloj corre solo.

Comprobar la propagación:

```bash
dig +short NS EJEMPLO.es
```

Cuando devuelva los de AWS (`ns-....awsdns-...`), continúa. Suele tardar entre
minutos y unas horas; el TTL del registrador manda.

> No sigas hasta que esto resuelva. El paso 2 crea el certificado, y ACM no
> puede validarlo si el dominio todavía apunta al registrador.

---

## Paso 2 — Certificado, CloudFront y registros

```bash
cd boscoGest/infra
terraform apply
```

Esto crea, en orden y encadenado por Terraform:

1. Certificado ACM en `us-east-1` para `EJEMPLO.es` y `*.EJEMPLO.es`
2. Los registros CNAME de validación en Route 53
3. `aws_acm_certificate_validation` — espera a que ACM emita el certificado
4. La distribución de CloudFront con OAC y las cabeceras de seguridad
5. Los ALIAS: apex, `www`, y el **wildcard** `*.EJEMPLO.es` (REQ-TEN-03)
6. `api.EJEMPLO.es` → Elastic IP de la EC2
7. Identidad SES del dominio con DKIM, más SPF y DMARC

CloudFront tarda entre 10 y 20 minutos en desplegarse. Terraform espera.

---

## Paso 3 — Cerrar el bucket del frontend

Solo ahora, **con CloudFront ya existiendo**. Hacerlo antes deja el sitio sin
servir, porque hoy se sirve desde el endpoint público del bucket.

```bash
cd boscoGest/infra
terraform output cloudfront_distribution_arn
```

En `boscoGest-front/infra/terraform.tfvars`:

```hcl
cloudfront_distribution_arn = "arn:aws:cloudfront::909186483504:distribution/E..."
```

```bash
cd boscoGest-front/infra
terraform apply
```

El bucket queda privado y solo accesible desde esa distribución.

---

## Paso 4 — Reconstruir y publicar el frontend

El bundle lleva la URL de la API dentro, así que hay que regenerarlo.

```bash
cd boscoGest-front
echo "APP_DOMAIN=EJEMPLO.es" > .env.build
npm run build

aws s3 sync dist/boscoGest-front/browser/ s3://boscogest-frontend/ --delete
aws cloudfront create-invalidation \
  --distribution-id "$(cd ../boscoGest/infra && terraform output -raw cloudfront_distribution_id)" \
  --paths '/*'
```

Comprobar que no queda rastro de la IP anterior:

```bash
grep -r "52.51.49.110" dist/ && echo "TODAVÍA HAY IPs" || echo "limpio"
```

---

## Paso 5 — TLS en la API

Caddy pide el certificado a Let's Encrypt al arrancar, mediante un desafío
HTTP-01. Para que funcione, `api.EJEMPLO.es` tiene que resolver ya contra la
Elastic IP (paso 2) y los puertos 80 y 443 estar abiertos.

```bash
dig +short api.EJEMPLO.es    # debe devolver 52.51.49.110
```

En `boscoGest/deploy/.env.prod`:

```
API_DOMAIN=api.EJEMPLO.es
ACME_EMAIL=tu-correo@EJEMPLO.es
CORS_ORIGINS=https://EJEMPLO.es,https://www.EJEMPLO.es
APP_BASE_URL=https://EJEMPLO.es
SES_SENDER_EMAIL=noreply@EJEMPLO.es
SES_CONFIGURATION_SET=boscogest-transactional
```

```bash
cd boscoGest
./deploy/deploy.sh
```

Verificar:

```bash
curl -I https://api.EJEMPLO.es/healthz     # 200, con Strict-Transport-Security
curl -I http://api.EJEMPLO.es/healthz      # redirección a https
```

> **Límite de Let's Encrypt:** 5 certificados por semana y por hostname. Si
> Caddy falla repetidamente (normalmente porque el DNS aún no resuelve), para
> el contenedor y arregla el DNS antes de reintentar, o agotarás la cuota.

---

## Paso 6 — Cerrar el puerto 8000

El compose de producción ya no publica el 8000 en el host, así que la regla del
security group sobra y deja la API accesible sin TLS.

En `boscoGest/infra/security_groups.tf`, eliminar el bloque de ingress del 8000
y aplicar. Comprobar después:

```bash
curl --max-time 5 http://52.51.49.110:8000/   # debe agotar el tiempo
```

---

## Paso 7 — Reset de la base de datos

Con TLS ya en marcha, para que la primera sesión no viaje en claro.

```bash
cd boscoGest
export SEED_SUPERADMIN_PASSWORD="$(python3 -c 'import secrets;print(secrets.token_urlsafe(16))')"
echo "Guarda esta contraseña: $SEED_SUPERADMIN_PASSWORD"
./scripts/reset-prod-db.sh --with-salesian
```

Si además quieres cifrado en reposo — **este es el único momento barato, porque
exige recrear la instancia** — antes de lo anterior, en
`boscoGest/infra/terraform.tfvars`:

```hcl
db_storage_encrypted  = true
restore_from_snapshot = ""   # imprescindible: si no, vuelven los datos viejos
db_apply_immediately  = true
```

y `terraform apply`. La instancia se recrea vacía y cifrada, con backups desde
el primer minuto. El endpoint **cambia**: actualiza `DATABASE_URL` en
`deploy/.env.prod` y vuelve a desplegar.

---

## Paso 8 — Rotar la clave de firma

La `SECRET_KEY` de producción sigue siendo el marcador de ejemplo del
repositorio, lo que significa que cualquiera puede fabricar un token de
superadmin. Después del reset no hay ninguna sesión que preservar, así que
rotarla no cuesta nada.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Ponla en `deploy/.env.prod` y `./deploy/deploy.sh`.

---

## Paso 9 — Correo

Con el dominio verificado, el remitente pasa a ser legítimo: DKIM firma con el
dominio propio, y SPF y DMARC ya están publicados por Terraform. Se acabaron
los correos en spam.

```bash
aws sesv2 get-email-identity --email-identity EJEMPLO.es --region eu-west-1 \
  --query '{Verified:VerifiedForSendingStatus,DKIM:DkimAttributes.Status}'
```

Cuando diga `Verified: true` y `DKIM: SUCCESS`, envía la solicitud de salida del
sandbox indicando `https://EJEMPLO.es` como URL. AWS tarda 24-48 h. Hasta que
la aprueben solo se puede enviar a direcciones verificadas.

---

## Comprobación final

```bash
curl -I https://EJEMPLO.es                    # 200, HSTS y CSP presentes
curl -I https://api.EJEMPLO.es/healthz        # 200
curl -I http://boscogest-frontend.s3-website-eu-west-1.amazonaws.com  # 403
curl --max-time 5 http://52.51.49.110:8000/   # timeout
```

Y en la aplicación: entrar como superadmin, cambiar la contraseña forzada, dar
de alta un usuario y confirmar que le llega el correo de bienvenida.

---

## Si algo se tuerce

| Síntoma | Causa habitual |
|---|---|
| ACM se queda en `PENDING_VALIDATION` | Los nameservers aún no han propagado (paso 1) |
| Caddy no consigue certificado | `api.EJEMPLO.es` no resuelve, o el 80 está cerrado |
| El frontend da 403 en todo | El bucket se cerró antes de existir CloudFront (paso 3 antes del 2) |
| La API responde 502 tras Caddy | El contenedor `back` no está sano — `docker compose logs back` |
| El backend no arranca | Falta alguna variable obligatoria; `app/config.py` falla en el arranque a propósito y dice cuál |
| Errores de CORS | `CORS_ORIGINS` no incluye el origen exacto, con esquema y sin barra final |
