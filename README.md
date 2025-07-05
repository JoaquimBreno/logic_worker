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
    "input_bucket_path": "benchmarks-musicai-gt/all-5stems-gtr-separate-channels/Ariana_Grande_-_Greedy_(24_Stems)",
    "output_bucket_path": "benchmarks-musicai-gt/teste",
    "callback_url": "https://webhook.site/your-webhook-id"
  }'
```

**Resposta:**
```json
{
  "execution_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "queued",
  "message": "Job created successfully",
  "input_bucket_path": "benchmarks-musicai-gt/all-5stems-gtr-separate-channels/Ariana_Grande_-_Greedy_(24_Stems)",
  "output_bucket_path": "benchmarks-musicai-gt/teste"
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
  "input_bucket_path": "benchmarks-musicai-gt/all-5stems-gtr-separate-channels/Ariana_Grande_-_Greedy_(24_Stems)",
  "output_bucket_path": "benchmarks-musicai-gt/teste",
  "errors": [],
  "results": [
    {
      "status": "success",
      "message": "Processing and export completed successfully",
      "export_verified": true
    }
  ],
  "created_at": "2023-12-01T10:00:00",
  "callback_url": "https://webhook.site/your-webhook-id"
}
```

### 5. Scan de Bucket (Preview)

```bash
curl "http://localhost:3000/scan?bucket_path=benchmarks-musicai-gt/all-5stems-gtr-separate-channels/Ariana_Grande_-_Greedy_(24_Stems)"
```

## Endpoints da API

- `POST /process` - Criar novo job de processamento
- `GET /status/{execution_id}` - Verificar status do job
- `GET /scan` - Escanear bucket para preview
- `GET /health` - Health check
- `GET /` - Informações da API

## Funcionamento

1. **Recepção**: API recebe paths dos buckets de entrada/saída e callback URL opcional
2. **Escaneamento**: Sistema verifica se o bucket de entrada contém os arquivos necessários
3. **Validação**: Valida a estrutura dos arquivos no bucket de entrada
4. **Fila**: Job é adicionado à fila BullMQ (1 processo por vez)
5. **Processamento**: Robot abre Logic Pro, executa stem splitting e exporta
6. **Verificação**: Confirma se arquivos foram exportados corretamente
7. **Upload**: Faz upload dos arquivos processados para o bucket de saída
8. **Callback**: Quando concluído, envia resultado para callback URL (se fornecido)
9. **Limpeza**: Em caso de erro, limpa arquivos temporários

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
- **Falhas críticas**: Limpeza automática dos arquivos temporários
- **Timeouts**: Configuráveis no `config.json`
- **Fila**: Apenas 1 processo simultâneo para evitar conflitos

## Estrutura do Bucket de Entrada

O bucket de entrada deve conter os arquivos necessários para o processamento. O sistema validará a estrutura antes de iniciar o processamento.

## Exemplo de Callback

Quando o processamento é concluído, o sistema envia um POST para a callback URL:

```json
{
  "execution_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "input_bucket_path": "benchmarks-musicai-gt/all-5stems-gtr-separate-channels/Ariana_Grande_-_Greedy_(24_Stems)",
  "output_bucket_path": "benchmarks-musicai-gt/teste",
  "errors": [],
  "results": [
    {
      "status": "success",
      "message": "Processing and export completed successfully",
      "export_verified": true
    }
  ],
  "completed_at": "2023-12-01T10:30:00"
}
```

## Verificação de Exportação

O sistema verifica automaticamente se os arquivos foram exportados corretamente antes de fazer o upload para o bucket de saída. Se a verificação falhar, o job é marcado como erro mesmo que o processamento tenha aparentemente funcionado. 