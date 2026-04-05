import asyncio
import json
import os
import re
import html

from telegram import Update
from telegram.ext import ContextTypes

from lib.utils import autorizado, exigir_projeto, projeto_path, projeto_label

NGROK_API = "http://localhost:4040/api/tunnels"


def _porta_do_projeto(projeto_dir: str) -> int | None:
    """Detecta a porta do projeto lendo package.json (script dev) ou ecosystem.config.cjs."""
    # 1) package.json → scripts.dev: "vinext dev --port 5000"
    pkg_path = os.path.join(projeto_dir, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path) as f:
                pkg = json.load(f)
            dev = pkg.get("scripts", {}).get("dev", "")
            m = re.search(r"--port\s+(\d+)", dev)
            if m:
                return int(m.group(1))
        except Exception:
            pass

    # 2) ecosystem.config.cjs → env.PORT
    eco_path = os.path.join(projeto_dir, "ecosystem.config.cjs")
    if os.path.exists(eco_path):
        try:
            with open(eco_path) as f:
                conteudo = f.read()
            m = re.search(r"PORT['\"]?\s*:\s*(\d+)", conteudo)
            if m:
                return int(m.group(1))
        except Exception:
            pass

    return None


async def _curl(args: list[str], timeout: int = 10) -> bytes:
    """Executa curl de forma async e retorna stdout."""
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return out


async def get_tunnel(nome: str) -> dict | None:
    """Retorna os dados do tunnel ngrok pelo nome, ou None se não existir."""
    try:
        out = await _curl([f"{NGROK_API}/{nome}"])
        data = json.loads(out)
        if "public_url" in data:
            return data
    except Exception:
        pass
    return None


async def listar_tunnels() -> list[dict]:
    """Retorna todos os tunnels ngrok ativos."""
    try:
        out = await _curl([NGROK_API])
        return json.loads(out).get("tunnels", [])
    except Exception:
        return []


async def criar_tunnel(nome: str, addr: str) -> str | None:
    """Cria (ou recria) um tunnel ngrok. Retorna a URL pública ou None."""
    # Remove tunnel antigo com mesmo nome, se existir
    try:
        await _curl(["-X", "DELETE", f"{NGROK_API}/{nome}"], timeout=5)
        await asyncio.sleep(1)
    except Exception:
        pass

    payload = json.dumps({"addr": addr, "proto": "http", "name": nome})
    try:
        out = await _curl(["-X", "POST", NGROK_API, "-H", "Content-Type: application/json", "-d", payload])
        data = json.loads(out)
        return data.get("public_url")
    except Exception:
        return None


async def remover_tunnel(nome: str) -> bool:
    """Remove um tunnel ngrok pelo nome."""
    try:
        await _curl(["-X", "DELETE", f"{NGROK_API}/{nome}"], timeout=5)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════
# HANDLER DO BOT
# ══════════════════════════════════════════════════════════════════════

@autorizado
async def cmd_ngrok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ngrok           → URL do projeto atual
    /ngrok start     → cria tunnel (detecta porta automaticamente)
    /ngrok start <porta> → cria tunnel na porta especificada
    /ngrok stop      → remove tunnel do projeto atual
    /ngrok list      → lista todos os tunnels ativos
    """
    args = context.args or []
    sub = args[0].lower() if args else "url"

    # /ngrok list — não precisa de projeto
    if sub == "list":
        tunnels = await listar_tunnels()
        if not tunnels:
            await update.message.reply_text("Nenhum tunnel ngrok ativo.")
            return
        linhas = [f"• <b>{t['name']}</b>: {t['public_url']}" for t in tunnels]
        await update.message.reply_text(
            "Tunnels ativos:\n" + "\n".join(linhas),
            parse_mode="HTML",
        )
        return

    # Demais subcomandos precisam de projeto
    if not await exigir_projeto(update):
        return

    chat_id = update.effective_chat.id
    cwd = projeto_path(chat_id)
    nome = os.path.basename(cwd)
    label = projeto_label(chat_id)

    if sub in ("url", "status"):
        tunnel = await get_tunnel(nome)
        if tunnel:
            await update.message.reply_text(
                f"🌐 <b>{label}</b>\n{tunnel['public_url']}",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                f"⚠️ <b>{label}</b> sem tunnel ativo.\n"
                "Use /ngrok start para criar.",
                parse_mode="HTML",
            )

    elif sub == "start":
        # Porta: argumento explícito ou detectada do projeto
        porta = None
        if len(args) > 1:
            try:
                porta = int(args[1])
            except ValueError:
                await update.message.reply_text("Porta inválida. Uso: /ngrok start [porta]")
                return
        if not porta:
            porta = _porta_do_projeto(cwd)
        if not porta:
            await update.message.reply_text(
                "Não consegui detectar a porta do projeto.\n"
                "Especifique: /ngrok start <porta>"
            )
            return

        addr = f"http://localhost:{porta}"
        await update.message.reply_text(f"⏳ Criando tunnel {nome} → porta {porta}...")
        url = await criar_tunnel(nome, addr)

        if url:
            await update.message.reply_text(
                f"✅ <b>{label}</b>\n{url}",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                f"❌ <b>{label}</b> Falha ao criar tunnel.\n\n"
                "Possíveis causas:\n"
                "• Agente ngrok não está rodando\n"
                "• Auth token não configurado\n"
                "• Limite de tunnels do plano atingido",
                parse_mode="HTML",
            )

    elif sub == "stop":
        ok = await remover_tunnel(nome)
        if ok:
            await update.message.reply_text(f"🛑 <b>{label}</b> tunnel encerrado.", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ Falha ao encerrar tunnel de <b>{label}</b>.", parse_mode="HTML")

    else:
        await update.message.reply_text(
            "Uso:\n"
            "/ngrok — URL do projeto atual\n"
            "/ngrok start [porta] — cria tunnel\n"
            "/ngrok stop — encerra tunnel\n"
            "/ngrok list — lista todos os tunnels",
        )
