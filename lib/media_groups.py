"""
Buffer de mensagens com media_group_id do Telegram.

Quando o usuário envia múltiplos anexos numa mesma "carta", o Telegram entrega
um Update por anexo, todos compartilhando o mesmo `media_group_id`. Sem
buffering, cada Update viraria uma chamada separada ao Claude. Aqui agrupamos
por (chat_id, media_group_id) com debounce e disparamos um único prompt
consolidado quando o grupo fica "estável" (sem novas mensagens por DEBOUNCE seg).
"""
import os
import asyncio

from lib.claude import enviar_para_claude

# (chat_id, media_group_id) -> {
#     "items": [(path, descricao_item), ...],
#     "caption": str,            # primeira legenda não-vazia do grupo
#     "task": asyncio.Task|None, # timer de debounce em curso
#     "update": Update,          # primeiro update (usado para responder)
# }
_buffers: dict = {}

# Tempo de espera após o último Update do grupo antes de disparar.
# Telegram costuma entregar todos os anexos do álbum em < 1s; 1.5s dá folga.
DEBOUNCE_SEG = 1.5


async def adicionar_ao_grupo_ou_processar(update, file_path: str, descricao_item: str, caption_atual: str = ""):
    """
    Se o Update faz parte de um media group, agrega ao buffer e (re)agenda o
    disparo. Caso contrário, processa imediatamente como mensagem única.

    `descricao_item` é uma string curta tipo "a imagem" ou "o arquivo X.pdf",
    usada para montar o prompt final.
    """
    msg = update.message
    media_group_id = msg.media_group_id if msg else None

    if not media_group_id:
        prompt = _montar_prompt([(file_path, descricao_item)], caption_atual)
        try:
            await enviar_para_claude(update, prompt)
        finally:
            _limpar_arquivos([file_path])
        return

    chat_id = update.effective_chat.id
    chave = (chat_id, media_group_id)

    buf = _buffers.get(chave)
    if buf is None:
        buf = {
            "items": [],
            "caption": "",
            "task": None,
            "update": update,
        }
        _buffers[chave] = buf

    buf["items"].append((file_path, descricao_item))
    if caption_atual and not buf["caption"]:
        buf["caption"] = caption_atual

    # Cancela timer anterior e reagenda — só dispara quando o grupo estabilizar
    if buf["task"] and not buf["task"].done():
        buf["task"].cancel()

    buf["task"] = asyncio.create_task(_disparar_apos_debounce(chave))


async def _disparar_apos_debounce(chave):
    try:
        await asyncio.sleep(DEBOUNCE_SEG)
    except asyncio.CancelledError:
        return

    buf = _buffers.pop(chave, None)
    if not buf:
        return

    items = buf["items"]
    caption = buf["caption"]
    update = buf["update"]

    prompt = _montar_prompt(items, caption)
    try:
        await enviar_para_claude(update, prompt)
    finally:
        _limpar_arquivos([p for p, _ in items])


def _montar_prompt(items, caption: str) -> str:
    """Monta o prompt consolidado. Para 1 item, mantém formato similar ao antigo."""
    if len(items) == 1:
        path, descricao = items[0]
        if caption:
            return f"Analise {descricao} em {path} e responda: {caption}"
        return (
            f"Leia {descricao} em {path}. Se for um erro ou bug, sugira a correção. "
            "Se for código, analise. Seja direto e objetivo, sem descrever."
        )

    linhas = [f"- {descricao}: {path}" for path, descricao in items]
    contexto = "\n".join(linhas)

    if caption:
        return (
            f"O usuário enviou {len(items)} anexos juntos. Analise todos eles "
            f"como parte do mesmo contexto:\n{contexto}\n\n"
            f"Pergunta do usuário: {caption}"
        )
    return (
        f"O usuário enviou {len(items)} anexos juntos. Analise todos eles "
        f"como parte do mesmo contexto:\n{contexto}\n\n"
        "Seja direto e objetivo."
    )


def _limpar_arquivos(paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.unlink(p)
        except OSError:
            pass
