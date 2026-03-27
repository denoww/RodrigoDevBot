# RodrigoDevBot

Telegram Bot para controle remoto multiprojeto via desktop.

## Instalação

Caso não tenha o `python3-venv` instalado:

```bash
sudo apt install python3-venv
```

Crie um ambiente virtual e instale as dependências:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Setup

### 1. Criar o bot no Telegram

Abra o Telegram, fale com [@BotFather](https://t.me/BotFather) e envie `/newbot`. Siga as instruções e copie o **TOKEN** que ele gerar.

### 2. Salvar o TOKEN no bashrc

Adicione o token no seu `~/.bashrc` para ficar disponível em todos os terminais:

```bash
echo 'export TELEGRAM_BOT_DEV_TOKEN="cole_seu_token_aqui"' >> ~/.bashrc
source ~/.bashrc
```

Se já existir uma linha com `TELEGRAM_BOT_DEV_TOKEN` no bashrc, atualize o valor ao invés de adicionar uma nova linha.

### 3. Descobrir seu CHAT_ID

Rode o bot em modo discovery:

```bash
python3 telegram_desktop_bot.py --get-chat-id
```

Abra o Telegram e mande **qualquer mensagem** pro seu bot. O terminal vai mostrar seu `CHAT_ID`. Copie-o.

### 4. Salvar o CHAT_ID no bashrc

```bash
echo 'export TELEGRAM_DEV_CHAT_ID="seu_chat_id"' >> ~/.bashrc
source ~/.bashrc
```

Se já existir uma linha com `TELEGRAM_DEV_CHAT_ID` no bashrc, atualize o valor ao invés de adicionar uma nova linha.

### 5. Rodar o bot

```bash
python3 telegram_desktop_bot.py
```

### 6. (Opcional) Configurar projetos

Edite o dict `PROJETOS` no arquivo `telegram_desktop_bot.py` com os caminhos dos seus projetos.

## Comandos disponíveis

| Comando | Descrição |
|---------|-----------|
| `/start` | Menu de ajuda |
| `/p` | Trocar projeto (botões) |
| `/p erp` | Trocar projeto direto |
| `/bash comando` | Executa qualquer comando |
| `/claude prompt` | Claude Code no projeto |
| `/git args` | Git (pull, push, status...) |
| `/rails args` | Rails runner/console |
| `/rake task` | Rake task |
| `/log N` | Últimas N linhas do log |
| `/ping` | Verifica se desktop está online |
| `/id` | Mostra seu chat_id |
