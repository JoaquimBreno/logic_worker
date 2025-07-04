#!/bin/bash

# Logic Worker - Script de Inicialização
echo "🎵 Logic Worker - Automated Music Processing System"
echo "=================================================="

# Verificar se o Redis está rodando
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis não está rodando. Iniciando Redis..."
    brew services start redis
    sleep 2
fi

# Verificar se o Redis está acessível
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis está rodando"
else
    echo "❌ Erro: Redis não está acessível"
    exit 1
fi

# Criar pasta de logs se não existir
mkdir -p logs

# Função para cleanup ao sair
cleanup() {
    echo ""
    echo "🛑 Parando serviços..."
    if [ ! -z "$WORKER_PID" ]; then
        kill $WORKER_PID 2>/dev/null
    fi
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
    fi
    echo "✅ Serviços parados"
    exit 0
}

# Configurar trap para cleanup
trap cleanup SIGINT SIGTERM

# Iniciar o Worker em background
echo "🚀 Iniciando Worker..."
python -m worker.logic_worker &
WORKER_PID=$!

# Aguardar um pouco para o worker inicializar
sleep 3

# Iniciar o Webhook Server em background
echo "🌐 Iniciando Webhook Server..."
python webhook_server.py &
SERVER_PID=$!

# Aguardar um pouco para o servidor inicializar
sleep 3

echo ""
echo "✅ Sistema inicializado com sucesso!"
echo "🌐 API disponível em: http://localhost:3000"
echo "📚 Documentação: http://localhost:3000/docs"
echo ""
echo "Comandos úteis:"
echo "  curl http://localhost:3000/health  # Health check"
echo "  curl http://localhost:3000/        # Informações da API"
echo ""
echo "Pressione Ctrl+C para parar os serviços"
echo ""

# Aguardar indefinidamente (ou até Ctrl+C)
wait 