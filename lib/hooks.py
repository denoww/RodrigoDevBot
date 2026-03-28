import os
import subprocess
import json as json_mod

from lib.config import BOT_NOME, BOT_SERVICE, BOT_REPO_DIR
from lib.utils import rodar


def carregar_hooks(cwd):
    """Carrega hooks do .remotedev.json do projeto."""
    config_path = os.path.join(cwd, ".remotedev.json")
    if not os.path.exists(config_path):
        return []
    try:
        with open(config_path) as f:
            data = json_mod.load(f)
        return data.get("hooks", [])
    except (json_mod.JSONDecodeError, OSError):
        return []


def git_remote_hash(cwd):
    """Retorna o hash do remote origin/main."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        return res.stdout.strip() if res.returncode == 0 else None
    except Exception:
        return None


def detectar_eventos(cwd, hash_antes):
    """Detecta eventos comparando estado do git antes e depois."""
    eventos = set()
    if hash_antes:
        subprocess.run(["git", "fetch", "--quiet"], cwd=cwd, capture_output=True, timeout=10)
        hash_depois = git_remote_hash(cwd)
        if hash_depois and hash_depois != hash_antes:
            eventos.add("git_pushed")
    return eventos


def executar_hooks(cwd, eventos):
    """Verifica hooks do projeto e executa os que casam com eventos detectados."""
    hooks = carregar_hooks(cwd)
    resultados = []
    for hook in hooks:
        trigger = hook.get("trigger", "")
        if trigger and trigger in eventos:
            run_cmd = hook.get("run", "")
            msg = hook.get("msg", f"Hook executado: {run_cmd}")
            if run_cmd:
                rodar(run_cmd, cwd=cwd, timeout=30)
                resultados.append(msg)
    return resultados


async def pos_push(update_or_msg, cwd, res):
    """Hooks e auto-restart após push bem-sucedido."""
    msg = (
        getattr(update_or_msg, 'message', None)
        or getattr(getattr(update_or_msg, 'callback_query', None), 'message', None)
    )
    if not res or res["code"] != 0:
        return
    if not msg:
        return
    for h in executar_hooks(cwd, {"git_pushed"}):
        await msg.reply_text(h)
    if os.path.realpath(cwd) == os.path.realpath(BOT_REPO_DIR):
        # Reinicia todos os bots remotedev da máquina, não só o atual
        try:
            res_units = subprocess.run(
                ["systemctl", "--user", "list-units", "remotedev-*", "--no-legend", "--plain"],
                capture_output=True, text=True, timeout=10,
            )
            services = [line.split()[0] for line in res_units.stdout.strip().splitlines() if line.strip()]
        except Exception:
            services = [BOT_SERVICE]
        if not services:
            services = [BOT_SERVICE]
        nomes = ", ".join(s.replace("remotedev-", "").replace(".service", "") for s in services)
        await msg.reply_text(f"🔄 Reiniciando {nomes}...")
        restart_cmd = " && ".join(f"systemctl --user restart {s}" for s in services)
        subprocess.Popen(f"sleep 2 && {restart_cmd}", shell=True)
