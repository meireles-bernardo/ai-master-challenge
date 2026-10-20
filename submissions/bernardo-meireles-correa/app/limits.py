"""Tetos de uso do LLM para o site público.

Três camadas: limite por sessão do navegador, teto diário da instalação
(contador em disco) e o teto de gasto configurado no painel do provedor.
Respostas repetidas saem do cache e não contam. O teto diário é reservado antes
da chamada; a trava vale para o processo único do Streamlit.
"""
import json
import os
import threading
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("STATE_DIR", ROOT / "local-state"))
PER_SESSION = int(os.environ.get("LLM_MAX_CALLS_PER_SESSION", "8"))
PER_DAY = int(os.environ.get("LLM_MAX_CALLS_PER_DAY", "300"))
_lock = threading.Lock()


def _path() -> Path:
    return STATE / "llm_usage.json"


def used_today() -> int:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    return int(data.get(date.today().isoformat(), 0))


def check(session_calls: int) -> str | None:
    """Retorna o motivo do bloqueio, ou None se a chamada pode seguir."""
    if session_calls >= PER_SESSION:
        return f"Limite de {PER_SESSION} análises por visita atingido. Recarregue mais tarde ou rode o app localmente."
    if used_today() >= PER_DAY:
        return f"O teto diário de {PER_DAY} análises desta instalação foi atingido. Volte amanhã."
    return None


def reserve() -> bool:
    """Reserva uma chamada no teto diário antes de chamar o provedor (verificação e soma juntas, sob trava)."""
    with _lock:
        STATE.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        try:
            data = json.loads(_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        used = int(data.get(today, 0))
        if used >= PER_DAY:
            return False
        _path().write_text(json.dumps({today: used + 1}), encoding="utf-8")  # guarda só o dia corrente
        return True
