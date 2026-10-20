"""Revisão das 20 primeiras triagens do LLM por dois revisores de IA independentes.

O candidato não revisou as triagens. A revisão é feita pelo Claude (outputs/revisao_claude.csv,
escrita à mão) e por uma segunda opinião do Codex, que recebe as mesmas triagens e regras
sem ver a revisão do Claude. O script grava a revisão do Codex e mede a concordância.
Uso: python analysis/review_triages.py   (precisa do Codex CLI com login)
"""
import csv
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from common import OUTPUTS

N = 20
CHOICES = {"tipo": ["concordo", "discordo"], "prioridade": ["concordo", "discordo"], "riscos": ["concordo", "discordo"],
           "rascunho": ["enviaria como está", "enviaria com pequenas edições", "reescreveria"]}
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["reviews"], "properties": {"reviews": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["ticket_id", *CHOICES, "comentario"],
    "properties": {"ticket_id": {"type": "integer"}, **{k: {"type": "string", "enum": v} for k, v in CHOICES.items()},
                   "comentario": {"type": "string"}}}}}}

RULES = """Você revisa a triagem que um LLM fez de tickets de suporte. Julgue cada triagem pelo texto do ticket, não por rótulos externos.
Tipos possíveis: Technical issue, Billing inquiry, Product inquiry, Refund request, Cancellation request.
Regra de prioridade que o LLM devia seguir: Critical = serviço fora do ar, perda de dados ou segurança; High = usuário bloqueado ou dinheiro envolvido;
Medium = funcionamento degradado; Low = dúvida ou como fazer.
Riscos possíveis: refund_or_money, cancellation_or_churn, data_loss, security_or_account_access, legal_or_compliance, angry_or_escalation, safety.
O rascunho é revisado por um agente antes de ir ao cliente e nunca pode prometer reembolso, cancelamento, crédito ou recuperação.
Os textos vêm de um dataset sintético e têm trechos incoerentes; a IA deve tratar isso como ruído e pedir o que falta.
Para cada ticket, diga se concorda com tipo, prioridade e riscos, avalie o rascunho e explique discordâncias em português, em uma frase.
Seja crítico: concordar com tudo sem motivo é uma revisão ruim."""


def triages() -> list[dict]:
    rows = [r for r in json.loads((OUTPUTS / "llm_eval_v1_codex.json").read_text(encoding="utf-8"))["rows"] if r.get("llm")][:N]
    return [{"ticket_id": r["ticket_id"], "texto": r["text"], "tipo": r["llm"]["ticket_type"], "prioridade": r["llm"]["priority"],
             "riscos": r["llm"]["risk_flags"], "pedir_ao_cliente": r["llm"]["missing_information"], "rascunho": r["llm"]["suggested_reply"]} for r in rows]


def ask_codex(items: list[dict]) -> list[dict]:
    exe = shutil.which("codex")
    with tempfile.TemporaryDirectory() as tmp:
        schema, out = Path(tmp, "schema.json"), Path(tmp, "out.json")
        schema.write_text(json.dumps(SCHEMA), encoding="utf-8")
        prompt = RULES + "\n\nTriagens (JSON):\n" + json.dumps(items, ensure_ascii=False, indent=1)
        proc = subprocess.run([exe, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", tmp, "-m", "gpt-6-sol",
                               "--output-schema", str(schema), "-o", str(out), "-"],
                              input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=900)
        if proc.returncode != 0 or not out.exists():
            raise SystemExit(f"codex exec falhou: {proc.stderr[-500:]}")
        return json.loads(out.read_text(encoding="utf-8"))["reviews"]


def read_csv(path: Path) -> dict[int, dict]:
    with path.open(encoding="utf-8") as f:
        return {int(r["ticket_id"]): r for r in csv.DictReader(f)}


def main() -> None:
    items = triages()
    codex = ask_codex(items)
    fields = ["ticket_id", *CHOICES, "comentario"]
    with (OUTPUTS / "revisao_codex.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in sorted(codex, key=lambda r: r["ticket_id"]):
            w.writerow({k: r[k] for k in fields})
    claude, cdx = read_csv(OUTPUTS / "revisao_claude.csv"), read_csv(OUTPUTS / "revisao_codex.csv")
    ids = [t["ticket_id"] for t in items]
    summary = {"tickets": len(ids), "revisores": ["Claude (Opus 5.5)", "Codex (gpt-6-sol), sem ver a revisão do Claude"],
               "nota": "Revisão por IA; o candidato não revisou as triagens."}
    for name, rev in (("claude", claude), ("codex", cdx)):
        summary[name] = {k: sum(rev[i][k] == "concordo" for i in ids) for k in ("tipo", "prioridade", "riscos")}
        summary[name]["rascunho"] = {c: sum(rev[i]["rascunho"] == c for i in ids) for c in CHOICES["rascunho"]}
    summary["concordancia_entre_revisores"] = {k: sum(claude[i][k] == cdx[i][k] for i in ids) for k in CHOICES}
    summary["discordancias_de_ambos"] = {k: [i for i in ids if claude[i][k] == "discordo" and cdx[i][k] == "discordo"] for k in ("tipo", "prioridade", "riscos")}
    (OUTPUTS / "revisao_resumo.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
