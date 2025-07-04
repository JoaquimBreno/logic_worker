# 🚀 Logic Worker - Guia de Início Rápido

## 🎯 O que é?
Sistema automatizado que processa uma pasta contendo um arquivo de música `_mix.wav` usando Logic Pro, executando stem splitting e exportação automaticamente através de uma API REST.

## 📋 Pré-requisitos

1. **macOS** (necessário para Logic Pro)
2. **Logic Pro** instalado
3. **Python 3.8+**
4. **Redis** instalado
5. **Permissões de acessibilidade** configuradas

## ⚡ Instalação Rápida

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Instalar Redis (se não tiver)
brew install redis
brew services start redis

# 3. Configurar permissões
# Vá em: System Preferences > Security & Privacy > Privacy > Accessibility
# Adicione Python/Terminal às aplicações permitidas
```

## 🏃‍♂️ Iniciar o Sistema

### Opção 1: Usar o script de inicialização
```bash
./start.sh
```

### Opção 2: Usar o main.py
```bash
python main.py
```

### Opção 3: Iniciar manualmente
```bash
# Terminal 1: Worker
python -m worker.logic_worker

# Terminal 2: API Server
python webhook_server.py
```

## 🧪 Testar o Sistema

```bash
# Verificar se está funcionando
curl http://localhost:3000/health

# Executar testes automatizados
python test_system.py
```

## 🎵 Usar o Sistema

### 1. Preparar sua música
```
/Tracklib - Won't Be Around_mix/
└── Tracklib - Won't Be Around_mix.wav
```

**Importante**: O sistema agora processa uma única pasta que contém um arquivo `_mix.wav`. O nome da pasta é salvo no JSON para controle futuro.

### 2. Escanear a pasta (preview)
```bash
curl "http://localhost:3000/scan?folder_path=/Users/moises/Documents/logic_processa/Tracklib - Won't Be Around_mix"
```

### 3. Criar um job de processamento
```bash
curl -X POST "http://localhost:3000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input_folder": "/Users/moises/Documents/logic_processa/Tracklib - Won't Be Around_mix",
    "callback_url": "http://seu-webhook.com/callback"
  }'
```

### 4. Verificar o status
```bash
curl "http://localhost:3000/status/SEU-EXECUTION-ID"
```

## 📊 Monitoramento

- **API**: http://localhost:3000
- **Documentação**: http://localhost:3000/docs
- **Logs**: `./logs/`

## 🔧 Configurações

Edite `config.json` conforme necessário:

```json
{
  "cleanup_folder": "/Users/moises/Music/Logic",
  "webhook_port": 3000,
  "redis_url": "redis://localhost:6379"
}
```

## 🎯 Exemplo Completo

```bash
# 1. Iniciar o sistema
./start.sh

# 2. Em outro terminal, processar uma pasta
curl -X POST "http://localhost:3000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input_folder": "/Users/moises/Documents/logic_processa/Tracklib - Won't Be Around_mix",
    "callback_url": "https://meusite.com/webhook"
  }'

# Resposta:
# {
#   "execution_id": "abc123...",
#   "status": "queued",
#   "message": "Job created successfully. Processing folder: Tracklib - Won't Be Around_mix",
#   "folder_name": "Tracklib - Won't Be Around_mix"
# }

# 3. Verificar progresso
curl "http://localhost:3000/status/abc123..."
```

## 📝 Status Possíveis

- `queued` - Na fila
- `processing` - Processando
- `completed` - Concluído
- `completed_with_errors` - Concluído com erros
- `error` - Erro fatal

## 🆘 Solução de Problemas

### Redis não conecta
```bash
brew services restart redis
```

### Permissões negadas
- Configurar Accessibility permissions
- Reiniciar Terminal/Python

### Logic Pro não abre
- Verificar se Logic Pro está instalado
- Verificar permissões de automação

### API não responde
```bash
# Verificar se está rodando
curl http://localhost:3000/health

# Verificar logs
tail -f logs/worker.log
tail -f webhook_server.log
```

## 🔄 Parar o Sistema

```bash
# Pressione Ctrl+C no terminal onde iniciou
# Ou:
pkill -f "python.*worker"
pkill -f "python.*webhook"
```

## 💡 Dicas

- Use o endpoint `/scan` para preview antes de processar
- Monitore os logs para debugging
- O sistema processa 1 pasta por vez (não simultâneo)
- Em caso de erro, a pasta Logic é limpa automaticamente
- Callback URL é opcional
- Pastas que já têm outros .wav são rejeitadas
- Sistema verifica se arquivos foram exportados corretamente

## 📞 Exemplo com Python

```python
import asyncio
from example_usage import create_job, check_status

async def main():
    execution_id = await create_job("/Users/moises/Documents/logic_processa/Tracklib - Won't Be Around_mix")
    status = await check_status(execution_id)
    print(f"Status: {status['status']}")
    print(f"Folder: {status['folder_name']}")

asyncio.run(main())
```

## ✅ Verificações Automáticas

O sistema agora inclui:
- **Validação de entrada**: Verifica se a pasta contém apenas arquivo `_mix.wav`
- **Controle de pasta**: Nome da pasta é salvo no JSON para controle
- **Verificação de exportação**: Confirma se arquivos foram exportados para `/Users/moises/Music/Logic`
- **Limpeza automática**: Remove arquivos da pasta Logic em caso de erro

Agora você está pronto para usar o Logic Worker! 🎉 