"""Avalia a triagem do LLM numa amostra aleatória de tickets reais do Dataset 1.

Não há gabarito confiável (os rótulos de tipo/prioridade não têm relação com o texto, ver
classifier_metrics.json), então medimos o que dá para verificar automaticamente:
- risco que a regra de palavras-chave encontra e o LLM deixa passar;
- placeholder {error_message} tratado como informação faltante;
- rascunhos que prometem reembolso, cancelamento, crédito ou recuperação (proibido);
- concordância com os rótulos originais, só para documentar que eles são aleatórios.
Uso: LLM_PROVIDER=codex python analysis/eval_llm.py [--n 60] [--workers 3]
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import llm  # noqa: E402
import policy  # noqa: E402
from common import OUTPUTS, SEED  # noqa: E402

PROMISE = re.compile(r"(we (will|have|'ll|'ve) (refund|issue(d)? (a|your) refund|cancel|credit|restore|recover))|"
                     r"(refund (has been|will be) (processed|issued))|(your (subscription|account|order) (has been|will be) cancel)", re.I)


def run_one(row: dict) -> dict:
    ticket = {"text": row["Description (display)"], "channel": row["Ticket Channel"], "product": row["Product Purchased"]}
    try:
        out = llm.triage(ticket)
        error = None
    except Exception as exc:  # registra a falha em vez de descartar o ticket
        out, error = None, str(exc)[:300]
    return {"ticket_id": int(row["Ticket ID"]), "text": ticket["text"], "label_type": row["Ticket Type"],
            "label_priority": row["Ticket Priority"], "had_error_placeholder": "{error_message}" in ticket["text"],
            "rule_risks": sorted(policy.keyword_risks(ticket["text"])), "llm": out, "error": error}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--rescore", action="store_true", help="Recalcula decisões e resumo a partir de llm_eval.json, sem chamar o LLM.")
    args = ap.parse_args()
    if args.rescore:
        previous = json.loads((OUTPUTS / "llm_eval.json").read_text(encoding="utf-8"))
        rows, args.n = previous["rows"], previous["summary"]["sample"]
        provider = previous["summary"]["provider"]
    else:
        tickets = pd.read_csv(OUTPUTS / "customer_tickets.csv.gz").sample(args.n, random_state=SEED)
        with ThreadPoolExecutor(args.workers) as pool:
            rows = list(pool.map(run_one, tickets.to_dict("records")))
        provider = llm.provider_name()

    ok = [r for r in rows if r["llm"]]
    for r in ok:
        d = policy.decide_customer(r["llm"], r["text"])
        r["decision"] = {"destination": d.destination, "human_required": d.human_required, "stage": d.stage}
    missed = [r["ticket_id"] for r in ok if set(r["rule_risks"]) - set(r["llm"]["risk_flags"])]
    placeholder = [r for r in ok if r["had_error_placeholder"]]
    placeholder_ok = [r for r in placeholder if any("erro" in m.lower() for m in r["llm"]["missing_information"])]
    promises = [r["ticket_id"] for r in ok if PROMISE.search(r["llm"]["suggested_reply"])]
    summary = {
        "provider": provider, "sample": args.n, "seed": SEED, "succeeded": len(ok),
        "failed": len(rows) - len(ok),
        "median_seconds": float(pd.Series([r["llm"]["_seconds"] for r in ok]).median()) if ok else None,
        "rule_risk_tickets": sum(bool(r["rule_risks"]) for r in ok),
        "rule_risk_missed_by_llm": missed,
        "llm_only_risk_tickets": sum(bool(set(r["llm"]["risk_flags"]) - set(r["rule_risks"])) for r in ok),
        "error_placeholder_tickets": len(placeholder),
        "error_placeholder_flagged_missing": len(placeholder_ok),
        "forbidden_promises": promises,
        "type_agreement_with_label": sum(r["llm"]["ticket_type"] == r["label_type"] for r in ok) / max(len(ok), 1),
        "priority_agreement_with_label": sum(r["llm"]["priority"] == r["label_priority"] for r in ok) / max(len(ok), 1),
        "stages": pd.Series([r["decision"]["stage"] for r in ok]).value_counts().to_dict(),
        "human_required_pct": sum(r["decision"]["human_required"] for r in ok) / max(len(ok), 1) * 100,
    }
    (OUTPUTS / "llm_eval.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
