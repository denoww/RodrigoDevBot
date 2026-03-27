#!/bin/bash
#
# Remove o serviço RodrigoDevBot do systemd
#

SERVICE_NAME="rodrigodevbot"
SERVICE_DIR="$HOME/.config/systemd/user"

echo "🗑️  Removendo serviço $SERVICE_NAME..."

systemctl --user stop "$SERVICE_NAME" 2>/dev/null
systemctl --user disable "$SERVICE_NAME" 2>/dev/null
rm -f "$SERVICE_DIR/$SERVICE_NAME.service"
rm -f "$SERVICE_DIR/$SERVICE_NAME.env"
systemctl --user daemon-reload

echo "✅ Serviço removido."
