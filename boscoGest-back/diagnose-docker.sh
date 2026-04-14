#!/bin/bash

# Script de diagnóstico para problemas de Docker en EC2

echo "========================================="
echo "  Diagnóstico de Docker en EC2          "
echo "========================================="
echo ""

echo "1. Verificando versión de Docker..."
docker --version
echo ""

echo "2. Verificando conectividad básica desde el host..."
ping -c 3 8.8.8.8
echo ""

echo "3. Verificando DNS desde el host..."
nslookup deb.debian.org
echo ""

echo "4. Verificando configuración de Docker..."
sudo cat /etc/docker/daemon.json 2>/dev/null || echo "No existe daemon.json"
echo ""

echo "5. Probando pull de imagen base..."
docker pull python:3.11-slim
echo ""

echo "6. Probando apt-get dentro de contenedor..."
echo "Esto puede fallar - es lo que estamos diagnosticando..."
docker run --rm python:3.11-slim sh -c "apt-get update && echo 'SUCCESS: apt-get funciona'" 2>&1
RESULT=$?
echo ""

if [ $RESULT -eq 0 ]; then
    echo "✅ apt-get funciona correctamente"
else
    echo "❌ apt-get falla con código: $RESULT"
    echo ""
    echo "Intentando con DNS manual..."
    docker run --rm --dns 8.8.8.8 --dns 8.8.4.4 python:3.11-slim sh -c "apt-get update && echo 'SUCCESS con DNS manual'" 2>&1
fi
echo ""

echo "7. Verificando configuración de red de Docker..."
docker network ls
echo ""

echo "8. Inspeccionando red bridge..."
docker network inspect bridge | grep -A 5 "Config"
echo ""

echo "========================================="
echo "  Fin del diagnóstico                   "
echo "========================================="
