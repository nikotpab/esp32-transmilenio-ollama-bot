#!/bin/bash

set -e

echo "============================================================"
echo "  BOT TELEGRAM TRANSMILENIO/SITP - PROXY SERVER"
echo "============================================================"

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no esta instalado"
    exit 1
fi

echo "Python: $(python3 --version)"

if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Instalando dependencias..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo "No se encontro .env, copiando desde .env.example..."
    cp ../.env.example .env
    echo "EDITA .env CON TUS CREDENCIALES ANTES DE CONTINUAR"
fi

echo "Verificando Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama esta corriendo"
else
    echo "Ollama no esta corriendo. Iniciando..."
    ollama serve &
    sleep 3
fi

MODEL=${OLLAMA_MODEL:-llama3.2}
echo "Verificando modelo: $MODEL"
if ! ollama list | grep -q "$MODEL"; then
    echo "Descargando modelo $MODEL..."
    ollama pull "$MODEL"
fi

echo ""
echo "============================================================"
echo "  INICIANDO SERVIDOR..."
echo "============================================================"
echo ""
echo "  URL: http://0.0.0.0:5000"
echo "  API Docs: http://localhost:5000/docs"
echo ""
echo "  Presiona Ctrl+C para detener"
echo "============================================================"
echo ""

python app.py
