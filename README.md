# RodrigoDevBot

Telegram Bot para controle remoto multiprojeto via desktop. Suporta múltiplos bots rodando em paralelo.

## Instalação

```bash
sudo apt install python3-venv   # se necessário
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Instalar um bot

O script interativo pede nome, token e descobre o CHAT_ID automaticamente:

```bash
./bot.sh install
```

Passo a passo que o script executa:
1. Pergunta o **nome** do bot (ex: `dev`, `prod`)
2. Pede o **TOKEN** (que você copia do [@BotFather](https://t.me/BotFather))
3. Descobre o **CHAT_ID** — basta mandar uma mensagem pro bot no Telegram
4. Salva tudo no `~/.bashrc` e cria o serviço systemd
5. Inicia o bot automaticamente

Para adicionar outro bot, rode `./bot.sh install` novamente com outro nome.

## Registrar comandos no Telegram

Fale com [@BotFather](https://t.me/BotFather), envie `/setcommands`, selecione seu bot e cole:

```
start - Menu de ajuda
p - Trocar projeto
bash - Executar comando no terminal
claude - Claude Code no projeto
git - Comandos git
rails - Rails runner/console
rake - Rake task
log - Ultimas linhas do log
ping - Verifica se desktop esta online
id - Mostra seu chat_id
restart - Reinicia o bot
```

## Gerenciar bots

```bash
./bot.sh list                 # lista bots instalados
./bot.sh status               # status de todos os bots
./bot.sh restart dev           # reinicia o bot dev
./bot.sh stop dev              # para o bot dev
./bot.sh start dev             # inicia o bot dev
./bot.sh logs dev              # logs do serviço
./bot.sh logs-claude dev       # logs do Claude
./bot.sh logs-claude dev scsip # filtra por projeto
./bot.sh uninstall             # lista bots e remove o escolhido
```

## Comandos disponíveis no Telegram

| Comando | Descrição |
|---------|-----------|
| `/start` | Menu de ajuda |
| `/p` | Trocar projeto (botões) |
| `/p nome` | Trocar projeto direto |
| `/bash comando` | Executa qualquer comando |
| `/claude prompt` | Claude Code no projeto |
| `/git args` | Git (pull, push, status...) |
| `/rails args` | Rails runner/console |
| `/rake task` | Rake task |
| `/log N` | Últimas N linhas do log |
| `/ping` | Verifica se desktop está online |
| `/id` | Mostra seu chat_id |
| `/restart` | Reinicia o bot |
