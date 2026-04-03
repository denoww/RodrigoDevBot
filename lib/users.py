"""
Gerenciamento de usuários autorizados do bot.
Persistência em JSON, menu interativo com inline buttons, e helpers de autorização.
Suporta múltiplos owners via campo 'role' no registro do usuário.
"""

import json
import os

from lib.config import BOT_NOME, BOT_REPO_DIR, OWNER_CHAT_ID

# ── Persistência ──────────────────────────────────────────────────────

_USERS_FILE = os.path.join(BOT_REPO_DIR, f".users-{BOT_NOME}.json")


def _carregar_users() -> dict:
    """Carrega usuários autorizados do disco. Migra registros antigos sem 'role'."""
    try:
        with open(_USERS_FILE, "r") as f:
            dados = json.load(f)
        users = {}
        for k, v in dados.items():
            uid = int(k)
            if "role" not in v:
                v["role"] = "owner" if uid == OWNER_CHAT_ID else "user"
            users[uid] = v
        return users
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {}


def _salvar_users():
    """Persiste usuários autorizados no disco."""
    try:
        with open(_USERS_FILE, "w") as f:
            json.dump(USERS_AUTORIZADOS, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


USERS_AUTORIZADOS: dict = _carregar_users()
# Garante que o super-owner (env) sempre está na lista como owner
if OWNER_CHAT_ID:
    if OWNER_CHAT_ID not in USERS_AUTORIZADOS:
        USERS_AUTORIZADOS[OWNER_CHAT_ID] = {"nome": "owner", "adicionado_por": "env", "role": "owner"}
        _salvar_users()
    elif USERS_AUTORIZADOS[OWNER_CHAT_ID].get("role") != "owner":
        USERS_AUTORIZADOS[OWNER_CHAT_ID]["role"] = "owner"
        _salvar_users()


# ── Helpers ───────────────────────────────────────────────────────────

def chat_ids_autorizados() -> set:
    return set(USERS_AUTORIZADOS.keys())


def adicionar_user(chat_id: int, nome: str, adicionado_por: str = "owner", role: str = "user"):
    USERS_AUTORIZADOS[chat_id] = {"nome": nome, "adicionado_por": adicionado_por, "role": role}
    _salvar_users()


def remover_user(chat_id: int) -> bool:
    """Remove usuário. Não permite remover o super-owner (env)."""
    if chat_id == OWNER_CHAT_ID:
        return False
    if chat_id in USERS_AUTORIZADOS:
        del USERS_AUTORIZADOS[chat_id]
        _salvar_users()
        return True
    return False


def promover_user(chat_id: int) -> bool:
    if chat_id in USERS_AUTORIZADOS:
        USERS_AUTORIZADOS[chat_id]["role"] = "owner"
        _salvar_users()
        return True
    return False


def rebaixar_user(chat_id: int) -> bool:
    """Rebaixa owner a user. Não permite rebaixar o super-owner (env)."""
    if chat_id == OWNER_CHAT_ID:
        return False
    if chat_id in USERS_AUTORIZADOS and USERS_AUTORIZADOS[chat_id].get("role") == "owner":
        USERS_AUTORIZADOS[chat_id]["role"] = "user"
        _salvar_users()
        return True
    return False


def is_owner(chat_id: int) -> bool:
    info = USERS_AUTORIZADOS.get(chat_id)
    return info is not None and info.get("role") == "owner"


def is_autorizado(chat_id: int) -> bool:
    return chat_id in USERS_AUTORIZADOS


# ── Estado pendente para fluxos conversacionais ──────────────────────

user_pendente = {}  # chat_id → {"acao": "add"|"remove"|"promover"|"rebaixar"}


# ── Handlers Telegram ─────────────────────────────────────────────────

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


def _montar_lista_users() -> str:
    """Monta texto HTML da lista de usuários."""
    linhas = []
    for uid, info in USERS_AUTORIZADOS.items():
        tag = " 👑" if info.get("role") == "owner" else " 👤"
        linhas.append(f"  <code>{uid}</code> — {info.get('nome', '?')}{tag}")
    return f"👥 <b>Usuários autorizados ({len(USERS_AUTORIZADOS)}):</b>\n" + "\n".join(linhas)


def _teclado_users(chat_id: int):
    """Monta teclado inline. Botões de gestão só para owners."""
    if not is_owner(chat_id):
        return None
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Adicionar", callback_data="users:add"),
            InlineKeyboardButton("➖ Remover", callback_data="users:remove"),
        ],
        [
            InlineKeyboardButton("⬆ Promover", callback_data="users:promover"),
            InlineKeyboardButton("⬇ Rebaixar", callback_data="users:rebaixar"),
        ],
    ])


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/users — lista usuários e mostra menu de gestão (owners)."""
    chat_id = update.effective_chat.id
    texto = _montar_lista_users()
    teclado = _teclado_users(chat_id)
    await update.message.reply_text(texto, parse_mode="HTML", reply_markup=teclado)


async def callback_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback dos botões do menu /users."""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id

    if not is_owner(chat_id):
        await query.edit_message_text("⛔ Apenas owners podem gerenciar usuários.")
        return

    acao = query.data.split(":")[1]  # add, remove, promover, rebaixar

    instrucoes = {
        "add": "Envie o <b>chat_id</b> e opcionalmente o <b>nome</b>:\n\n<code>123456 João</code>\n\nPara adicionar como owner, adicione <code>owner</code> no final:\n<code>123456 João owner</code>",
        "remove": "Envie o <b>chat_id</b> do usuário a remover:\n\n<code>123456</code>",
        "promover": "Envie o <b>chat_id</b> do usuário a promover para owner:\n\n<code>123456</code>",
        "rebaixar": "Envie o <b>chat_id</b> do owner a rebaixar para user:\n\n<code>123456</code>",
    }

    user_pendente[chat_id] = {"acao": acao}
    await query.edit_message_text(
        f"{instrucoes[acao]}\n\n/cancelar para voltar.",
        parse_mode="HTML",
    )


async def processar_user_pendente(chat_id: int, texto: str, message, bot) -> bool:
    """
    Processa resposta de um fluxo pendente de gestão de users.
    Retorna True se havia pendência (consumida), False se não.
    """
    if chat_id not in user_pendente:
        return False

    acao = user_pendente.pop(chat_id)["acao"]

    if acao == "add":
        partes = texto.split()
        try:
            new_id = int(partes[0])
        except (ValueError, IndexError):
            await message.reply_text("⚠️ chat_id deve ser um número. Tente novamente com /users.")
            return True

        role = "user"
        nome_partes = partes[1:]
        if nome_partes and nome_partes[-1].lower() == "owner":
            role = "owner"
            nome_partes = nome_partes[:-1]
        nome = " ".join(nome_partes) if nome_partes else f"user_{new_id}"

        adicionar_user(new_id, nome, adicionado_por=str(chat_id), role=role)
        role_label = "👑 owner" if role == "owner" else "👤 user"
        await message.reply_text(
            f"✅ Usuário adicionado!\n\n"
            f"Chat ID: <code>{new_id}</code>\n"
            f"Nome: {nome}\nRole: {role_label}",
            parse_mode="HTML",
        )
        try:
            await bot.send_message(
                chat_id=new_id,
                text=f"🎉 Você foi autorizado no bot {BOT_NOME}!\nDigite /menu para ver os comandos.",
            )
        except Exception:
            pass

    elif acao == "remove":
        try:
            rm_id = int(texto.split()[0])
        except (ValueError, IndexError):
            await message.reply_text("⚠️ chat_id deve ser um número. Tente novamente com /users.")
            return True
        if rm_id == OWNER_CHAT_ID:
            await message.reply_text("⚠️ Não é possível remover o super-owner.")
        elif remover_user(rm_id):
            await message.reply_text(f"✅ Usuário {rm_id} removido.")
        else:
            await message.reply_text(f"⚠️ Usuário {rm_id} não encontrado.")

    elif acao == "promover":
        try:
            uid = int(texto.split()[0])
        except (ValueError, IndexError):
            await message.reply_text("⚠️ chat_id deve ser um número. Tente novamente com /users.")
            return True
        if promover_user(uid):
            nome = USERS_AUTORIZADOS[uid].get("nome", "?")
            await message.reply_text(f"✅ {nome} (<code>{uid}</code>) agora é owner 👑", parse_mode="HTML")
        else:
            await message.reply_text(f"⚠️ Usuário {uid} não encontrado.")

    elif acao == "rebaixar":
        try:
            uid = int(texto.split()[0])
        except (ValueError, IndexError):
            await message.reply_text("⚠️ chat_id deve ser um número. Tente novamente com /users.")
            return True
        if uid == OWNER_CHAT_ID:
            await message.reply_text("⚠️ Não é possível rebaixar o super-owner.")
        elif rebaixar_user(uid):
            nome = USERS_AUTORIZADOS[uid].get("nome", "?")
            await message.reply_text(f"✅ {nome} (<code>{uid}</code>) agora é user 👤", parse_mode="HTML")
        else:
            await message.reply_text(f"⚠️ Usuário {uid} não é owner ou não está na lista.")

    return True
