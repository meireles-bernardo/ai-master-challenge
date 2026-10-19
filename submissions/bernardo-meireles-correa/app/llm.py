"""Camada de LLM com provedores intercambiáveis.

LLM_PROVIDER escolhe o backend:
  codex      -> `codex exec` com a assinatura ChatGPT local (desenvolvimento)
  openai     -> OpenAI Responses API (OPENAI_API_KEY, LLM_MODEL)
  anthropic  -> Anthropic Messages API (ANTHROPIC_API_KEY, LLM_MODEL)
  off        -> sem LLM; o app segue com classificador e regras
O LLM só redige e extrai. Quem decide se um humano é obrigatório é policy.py.
"""
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

CUSTOMER_TYPES = ["Technical issue", "Billing inquiry", "Product inquiry", "Refund request", "Cancellation request"]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["ticket_type", "summary_pt", "priority", "priority_reason_pt", "risk_flags",
                 "missing_information", "suggested_reply", "confidence"],
    "properties": {
        "ticket_type": {"type": "string", "enum": CUSTOMER_TYPES},
        "summary_pt": {"type": "string", "description": "Resumo de uma frase, em português, do que o cliente precisa."},
        "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
        "priority_reason_pt": {"type": "string"},
        "risk_flags": {"type": "array", "items": {"type": "string", "enum": [
            "refund_or_money", "cancellation_or_churn", "data_loss", "security_or_account_access",
            "legal_or_compliance", "angry_or_escalation", "safety"]}},
        "missing_information": {"type": "array", "items": {"type": "string"},
                                "description": "Dados que o agente precisa pedir antes de resolver (em português)."},
        "suggested_reply": {"type": "string", "description": "Rascunho de resposta ao cliente, no idioma do ticket."},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
}

INSTRUCTIONS = """You are the triage assistant of a customer support team. Read ONE ticket and fill the JSON schema.
Rules:
- Only use facts present in the ticket. Never invent order numbers, policies, refunds, deadlines or fixes that were not stated.
- If the text contains unfilled template placeholders like {error_message}, treat that information as missing.
- The suggested reply is a DRAFT a human agent will review. It must acknowledge the problem, ask for the missing
  information, and never promise refunds, cancellations, credits or data recovery.
- Priority: Critical = service down, data loss or security; High = blocked user or money involved; Medium = degraded;
  Low = question or how-to.
- Write summary_pt, priority_reason_pt and missing_information in Brazilian Portuguese.
Return only the JSON object."""


class LLMError(RuntimeError):
    pass


def provider_name() -> str:
    return os.environ.get("LLM_PROVIDER", "codex" if shutil.which("codex") else "off").lower()


def model_label() -> str:
    """Nome legível do modelo em uso, para a interface."""
    provider = provider_name()
    if provider == "anthropic":
        model = os.environ.get("LLM_MODEL", "claude-haiku-5-5")
        return {"claude-haiku-5-5": "Claude Haiku 5.5"}.get(model, model)
    if provider == "codex":
        return os.environ.get("LLM_CODEX_MODEL", "gpt-6-sol") + " (Codex)"
    return os.environ.get("LLM_MODEL", provider)


def _prompt(ticket: dict) -> str:
    meta = {k: ticket.get(k) for k in ("channel", "product") if ticket.get(k)}
    return f"{INSTRUCTIONS}\n\nTicket metadata: {json.dumps(meta, ensure_ascii=False)}\nTicket text:\n<<<\n{ticket['text']}\n>>>"


def _codex(ticket: dict) -> dict:
    exe = shutil.which("codex")
    if not exe:
        raise LLMError("Codex CLI não encontrado no PATH.")
    with tempfile.TemporaryDirectory() as tmp:
        schema_path, out_path = Path(tmp, "schema.json"), Path(tmp, "out.json")
        schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
        cmd = [exe, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", tmp,
               "--output-schema", str(schema_path), "-o", str(out_path)]
        # Modelo escolhido pelo candidato para os testes com a assinatura ChatGPT.
        cmd += ["-m", os.environ.get("LLM_CODEX_MODEL", "gpt-6-sol")]
        if os.environ.get("LLM_CODEX_EFFORT"):
            cmd += ["-c", f'model_reasoning_effort="{os.environ["LLM_CODEX_EFFORT"]}"']
        cmd.append("-")
        proc = subprocess.run(cmd, input=_prompt(ticket), capture_output=True, text=True, encoding="utf-8",
                              timeout=int(os.environ.get("LLM_TIMEOUT", "180")))
        if proc.returncode != 0 or not out_path.exists():
            raise LLMError(f"codex exec falhou ({proc.returncode}): {proc.stderr.strip()[-400:]}")
        return json.loads(out_path.read_text(encoding="utf-8"))


def _post(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=int(os.environ.get("LLM_TIMEOUT", "60"))) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise LLMError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:400]}") from exc


def _openai(ticket: dict) -> dict:
    key, model = os.environ.get("OPENAI_API_KEY"), os.environ.get("LLM_MODEL")
    if not key or not model:
        raise LLMError("Defina OPENAI_API_KEY e LLM_MODEL.")
    data = _post("https://api.openai.com/v1/responses", {"authorization": f"Bearer {key}"}, {
        "model": model, "input": _prompt(ticket),
        "text": {"format": {"type": "json_schema", "name": "triage", "schema": SCHEMA, "strict": True}},
    })
    text = next(c["text"] for item in data["output"] if item.get("type") == "message" for c in item["content"] if c.get("type") == "output_text")
    result = json.loads(text)
    usage = data.get("usage", {})
    result["_usage"] = {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")}
    return result


def _anthropic(ticket: dict) -> dict:
    import anthropic  # só necessário neste provedor

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError("Defina ANTHROPIC_API_KEY.")
    client = anthropic.Anthropic(timeout=float(os.environ.get("LLM_TIMEOUT", "60")))
    try:
        # Structured outputs garantem JSON válido no schema; esforço baixo basta para triagem.
        response = client.messages.create(
            model=os.environ.get("LLM_MODEL", "claude-haiku-5-5"),
            max_tokens=4000,
            output_config={"effort": os.environ.get("LLM_EFFORT", "low"), "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": _prompt(ticket)}],
        )
    except anthropic.RateLimitError as exc:
        raise LLMError("Limite de requisições da Anthropic atingido; tente de novo em instantes.") from exc
    except anthropic.APIStatusError as exc:
        raise LLMError(f"Anthropic respondeu {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError("Sem conexão com a API da Anthropic.") from exc
    if response.stop_reason == "refusal":
        raise LLMError("O modelo recusou analisar este texto. Encaminhe para triagem humana.")
    if response.stop_reason == "max_tokens":
        raise LLMError("Resposta cortada pelo limite de tokens.")
    result = json.loads(next(b.text for b in response.content if b.type == "text"))
    result["_usage"] = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    return result


PROVIDERS = {"codex": _codex, "openai": _openai, "anthropic": _anthropic}


def triage(ticket: dict) -> dict:
    """ticket = {"text": ..., "channel": ..., "product": ...}. Retorna o JSON do schema + metadados."""
    name = provider_name()
    if name == "off":
        raise LLMError("LLM desligado (LLM_PROVIDER=off).")
    if name not in PROVIDERS:
        raise LLMError(f"Provedor desconhecido: {name}")
    start = time.time()
    result = PROVIDERS[name](ticket)
    result["_provider"], result["_seconds"] = name, round(time.time() - start, 1)
    return result
