#!/bin/bash
set -e

echo "🚀 Trieste Business Tycoon - Deploy Script"
echo "==========================================="

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "❌ Docker non trovato. Installa Docker prima di continuare."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose non trovato. Installa Docker Compose prima di continuare."
    exit 1
fi

# Check .env
if [ ! -f .env ]; then
    echo "⚠️  File .env non trovato. Creo da .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "📝 Creato .env da .env.example"
        echo "⚠️  IMPORTANTE: Modifica .env e inserisci il tuo BOT_TOKEN!"
    else
        echo "❌ .env.example non trovato!"
        exit 1
    fi
fi

# Build and start
echo "🏗️  Build dei container..."
docker-compose build

echo "🚀 Avvio dei servizi..."
docker-compose up -d

echo ""
echo "✅ Deploy completato!"
echo ""
echo "📋 Stato servizi:"
docker-compose ps
echo ""
echo "📝 Log del bot:"
echo "   docker-compose logs -f bot"
echo ""
echo "🌐 WebApp disponibile su:"
echo "   http://localhost (se nginx attivo)"
echo ""
echo "🛑 Per fermare: docker-compose down"
