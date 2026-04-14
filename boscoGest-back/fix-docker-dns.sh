#!/bin/bash

# Script para configurar DNS en Docker y resolver problemas de red en EC2

echo "========================================="
echo "  Configurando DNS para Docker          "
echo "========================================="
echo ""

# Verificar si somos root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script necesita ejecutarse con sudo"
    echo "Ejecuta: sudo bash fix-docker-dns.sh"
    exit 1
fi

# Backup del archivo existente si existe
if [ -f /etc/docker/daemon.json ]; then
    echo "📋 Haciendo backup de daemon.json existente..."
    cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backup creado"
    echo ""
fi

# Crear directorio si no existe
mkdir -p /etc/docker

# Configurar DNS
echo "🔧 Configurando DNS en Docker daemon..."
cat > /etc/docker/daemon.json << 'EOF'
{
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"],
  "dns-opts": ["timeout:3", "attempts:3"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

echo "✅ Configuración DNS aplicada"
echo ""

# Mostrar configuración
echo "📄 Configuración actual:"
cat /etc/docker/daemon.json
echo ""

# Reiniciar Docker
echo "🔄 Reiniciando Docker daemon..."
systemctl restart docker

if [ $? -eq 0 ]; then
    echo "✅ Docker reiniciado exitosamente"
else
    echo "❌ Error al reiniciar Docker"
    exit 1
fi
echo ""

# Esperar a que Docker esté listo
echo "⏳ Esperando a que Docker esté listo..."
sleep 5

# Verificar estado
echo "🔍 Verificando estado de Docker..."
systemctl status docker --no-pager | head -10
echo ""

# Probar conectividad
echo "🧪 Probando conectividad dentro de contenedor..."
docker run --rm python:3.11-slim sh -c "apt-get update && echo '✅ SUCCESS: apt-get funciona correctamente'" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "  ✅ Configuración exitosa               "
    echo "========================================="
    echo ""
    echo "Ahora puedes ejecutar: ./deploy.sh"
else
    echo ""
    echo "========================================="
    echo "  ⚠️  Aún hay problemas                  "
    echo "========================================="
    echo ""
    echo "Verifica:"
    echo "1. Security groups permiten tráfico saliente"
    echo "2. NACLs de la subnet permiten tráfico saliente"
    echo "3. No hay proxy corporativo bloqueando"
    echo ""
    echo "Ejecuta: bash diagnose-docker.sh"
fi
