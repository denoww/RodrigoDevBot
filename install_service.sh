#!/bin/bash
#
# Instala o RodrigoDevBot como serviço systemd (inicia com o sistema)
#

set -e

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="rodrigodevbot"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/$SERVICE_NAME.service"
ENV_FILE="$SERVICE_DIR/$SERVICE_NAME.env"

echo "📦 Instalando RodrigoDevBot como serviço..."
echo "   Diretório: $BOT_DIR"
echo ""

# Verificar venv
if [ ! -f "$BOT_DIR/venv/bin/python3" ]; then
    echo "❌ venv não encontrado. Rode antes:"
    echo "   python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Verificar variáveis de ambiente
if [ -z "$TELEGRAM_BOT_DEV_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_DEV_TOKEN não definido. Veja o README (passos 2)."
    exit 1
fi

if [ -z "$TELEGRAM_DEV_CHAT_ID" ]; then
    echo "❌ TELEGRAM_DEV_CHAT_ID não definido. Veja o README (passos 3 e 4)."
    exit 1
fi

# Criar diretório do systemd
mkdir -p "$SERVICE_DIR"

# Criar arquivo de variáveis
cat > "$ENV_FILE" << EOF
TELEGRAM_BOT_DEV_TOKEN=$TELEGRAM_BOT_DEV_TOKEN
TELEGRAM_DEV_CHAT_ID=$TELEGRAM_DEV_CHAT_ID
EOF
echo "✅ Variáveis salvas em $ENV_FILE"

# Criar serviço
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=RodrigoDevBot - Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python3 telegram_desktop_bot.py
Restart=always
RestartSec=5
EnvironmentFile=$ENV_FILE

[Install]
WantedBy=default.target
EOF
echo "✅ Serviço criado em $SERVICE_FILE"

# Ativar e iniciar
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"
loginctl enable-linger "$USER"

echo ""
echo "✅ Bot instalado e rodando!"
echo ""
echo "   Ver status:  systemctl --user status $SERVICE_NAME"
echo "   Ver logs:    journalctl --user -u $SERVICE_NAME -f"
echo "   Reiniciar:   systemctl --user restart $SERVICE_NAME"
echo "   Parar:       systemctl --user stop $SERVICE_NAME"
