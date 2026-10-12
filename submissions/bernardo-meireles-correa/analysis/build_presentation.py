"""Gera presentation/data.js com os números reais usados pela apresentação.

Um .js (e não .json) para a página abrir direto do arquivo, sem servidor.
Uso: python analysis/build_presentation.py
"""
import json
import re
import sys

import pandas as pd

from common import OUTPUTS, ROOT

sys.path.insert(0, str(ROOT / "app"))
import context  # noqa: E402
import policy  # noqa: E402
import roi  # noqa: E402

HOOK_TICKET_ID = 609  # aberto, Critical, perda de dados, nunca respondido
DATA_LOSS = r"data loss|lost|deleted"
STATUS = {"Open": "o", "Pending Customer Response": "p", "Closed": "c"}
PRIORITY = {"Critical": "C", "High": "H", "Medium": "M", "Low": "L"}


def main() -> None:
    tickets = pd.read_csv(OUTPUTS / "customer_tickets.csv.gz")
    diag = json.loads((OUTPUTS / "diagnostico.json").read_text(encoding="utf-8"))
    clf = json.loads((OUTPUTS / "classifier_metrics.json").read_text(encoding="utf-8"))
    llm = json.loads((OUTPUTS / "llm_eval.json").read_text(encoding="utf-8"))
    position = {int(t): i for i, t in enumerate(tickets["Ticket ID"])}
    sample = [{"i": position[r["ticket_id"]], "stage": r["decision"]["stage"]} for r in llm["rows"] if r.get("decision")]
    hook = tickets[tickets["Ticket ID"] == HOOK_TICKET_ID].iloc[0]
    sentences = re.split(r"(?<=[.?!])\s+", hook["Description (display)"].strip())
    same = tickets[(tickets["Ticket Status"] == "Open") & (tickets["Ticket Priority"] == "Critical")
                   & tickets["Description (display)"].str.contains(DATA_LOSS, case=False)]
    ctx = [context.recover(t) for t in tickets["Ticket Description"]]
    scenarios = {name: round(roi.estimate(a)["total_hours_month"]) for name, a in roi.SCENARIOS.items()}
    data = {
        "status": "".join(tickets["Ticket Status"].map(STATUS)),
        "priority": "".join(tickets["Ticket Priority"].map(PRIORITY)),
        "csat": "".join(tickets["Customer Satisfaction Rating"].fillna(0).astype(int).astype(str)),
        "risk": "".join("1" if policy.keyword_risks(t) else "0" for t in tickets["Description (display)"]),
        "csatMinP": diag["satisfaction"]["min_p"],
        "classifier": {"accuracy": clf["test"]["accuracy"], "n": clf["test"]["n"], "auto": clf["test"]["auto_coverage"],
                       "autoPrecision": clf["test"]["auto_precision"]},
        "llm": {"sample": llm["summary"]["sample"], "promises": len(llm["summary"]["forbidden_promises"]),
                "missed": len(llm["summary"]["rule_risk_missed_by_llm"]),
                "placeholder": [llm["summary"]["error_placeholder_flagged_missing"], llm["summary"]["error_placeholder_tickets"]],
                "rows": sample},
        "roi": {"hours": scenarios, "fteHours": roi.HOURS_PER_FTE_MONTH},
        "hook": {"index": position[HOOK_TICKET_ID], "id": HOOK_TICKET_ID, "quote": " ".join(sentences[:2]),
                 "product": hook["Product Purchased"], "channel": hook["Ticket Channel"], "same": len(same)},
        "found": "".join("1" if c.found else "0" for c in ctx),
        "blank": "".join("1" if any("erro" in m for m in c.missing) else "0" for c in ctx),
    }
    out = ROOT / "presentation" / "data.js"
    out.parent.mkdir(exist_ok=True)
    out.write_text("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"{out} ({out.stat().st_size // 1024} KB)", scenarios)


if __name__ == "__main__":
    main()
