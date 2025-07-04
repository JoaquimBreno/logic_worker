# Logic Worker - Automated Music Processing System

Sistema automatizado para processamento de áudio usando Logic Pro com stem splitting e exportação.

## Arquitetura

- **Robot** (`robot/logic.py`): Automação assíncrona do Logic Pro
- **Worker** (`worker/logic_worker.py`): Processamento de filas com BullMQ
- **Webhook Server** (`webhook_server.py`): API REST para criar jobs e verificar status

## Instalação

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Instalar Redis
```bash
brew install redis
brew services start redis
```

### 3. Configurar permissões do macOS
- Permitir automação para Python/Terminal no System Preferences > Security & Privacy > Privacy > Accessibility

## Configuração

O arquivo `config.json` contém as configurações:

```json
{
  "cleanup_folder": "/Users/moises/Music/Logic",
  "log_folder": "./logs",
  "redis_url": "redis://localhost:6379",
  "webhook_port": 3000,
  "processing_timeout": 300000,
  "export_timeout": 60000,
  "stem_split_timeout": 240000
}
```

## Uso

### 1. Iniciar o Worker
```bash
python -m worker.logic_worker
```

### 2. Iniciar o Webhook Server
```bash
python webhook_server.py
```

### 3. Criar um Job de Processamento

```bash
curl -X POST "http://localhost:3000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input_folder": "/Users/moises/Documents/logic_processa/Tracklib - Won't Be Around_mix",
    "callback_url": "http://your-callback-url.com/webhook"
  }'
```

**Resposta:**
```json
{
  "execution_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "queued",
  "message": "Job created successfully. Processing folder: Tracklib - Won't Be Around_mix",
  "folder_name": "Tracklib - Won't Be Around_mix"
}
```

### 4. Verificar Status do Job

```bash
curl "http://localhost:3000/status/123e4567-e89b-12d3-a456-426614174000"
```

**Resposta:**
```json
{
  "execution_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "input_folder": "/Users/moises/Documents/logic_processa/Tracklib - Won't Be Around_mix",
  "folder_name": "Tracklib - Won't Be Around_mix",
  "errors": [],
  "results": [
    {
      "status": "success",
      "folder": "Tracklib - Won't Be Around_mix",
      "message": "Processing and export completed successfully",
      "export_verified": true
    }
  ],
  "created_at": "2023-12-01T10:00:00",
  "callback_url": "http://your-callback-url.com/webhook"
}
```

### 5. Scan de Pasta (Preview)

```bash
curl "http://localhost:3000/scan?folder_path=/Users/moises/Documents/logic_processa/Tracklib - Won't Be Around_mix"
```

## Endpoints da API

- `POST /process` - Criar novo job de processamento
- `GET /status/{execution_id}` - Verificar status do job
- `GET /scan` - Escanear pasta para preview
- `GET /health` - Health check
- `GET /` - Informações da API

## Funcionamento

1. **Recepção**: API recebe pasta com arquivo `_mix.wav` e callback URL opcional
2. **Escaneamento**: Sistema verifica se a pasta contém apenas um arquivo `_mix.wav`
3. **Validação**: Só processa se a pasta contém apenas arquivos `_mix.wav` (sem outros `.wav`)
4. **Fila**: Job é adicionado à fila BullMQ (1 processo por vez)
5. **Processamento**: Robot abre Logic Pro, executa stem splitting e exporta
6. **Verificação**: Confirma se arquivos foram exportados para `/Users/moises/Music/Logic`
7. **Callback**: Quando concluído, envia resultado para callback URL (se fornecido)
8. **Limpeza**: Em caso de erro, limpa pasta `/Users/moises/Music/Logic`

## Status Possíveis

- `queued` - Job na fila aguardando processamento
- `processing` - Job em processamento
- `completed` - Job concluído com sucesso
- `completed_with_errors` - Job concluído mas com alguns erros
- `error` - Job falhou completamente

## Logs

Os logs são salvos em:
- `robot_automation.log` - Logs da automação do Logic Pro
- `worker.log` - Logs do worker
- `webhook_server.log` - Logs do servidor webhook

## Tratamento de Erros

- **Erros de automação**: Repassados no JSON como "error"
- **Verificação de exportação**: Confirma se arquivos foram exportados corretamente
- **Falhas críticas**: Limpeza automática da pasta configurada
- **Timeouts**: Configuráveis no `config.json`
- **Fila**: Apenas 1 processo simultâneo para evitar conflitos

## Estrutura de Pasta Esperada

```
/Tracklib - Won't Be Around_mix/
└── Tracklib - Won't Be Around_mix.wav
```

O sistema agora processa uma única pasta que contém um arquivo `_mix.wav`. O nome da pasta é salvo no JSON para controle futuro.

## Exemplo de Callback

Quando o processamento é concluído, o sistema envia um POST para a callback URL:

```json
{
  "execution_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "folder_name": "Tracklib - Won't Be Around_mix",
  "errors": [],
  "results": [
    {
      "status": "success",
      "folder": "Tracklib - Won't Be Around_mix",
      "message": "Processing and export completed successfully",
      "export_verified": true
    }
  ],
  "completed_at": "2023-12-01T10:30:00"
}
```

## Verificação de Exportação

O sistema agora verifica automaticamente se os arquivos foram exportados corretamente para a pasta `/Users/moises/Music/Logic`. Se a verificação falhar, o job é marcado como erro mesmo que o processamento tenha aparentemente funcionado. 