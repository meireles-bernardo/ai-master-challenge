"""Gera presentation/data.js com os números reais usados pela apresentação.

Um .js (e não .json) para a página abrir direto do arquivo, sem servidor.
Uso: python analysis/build_presentation.py
"""
import json
import sys

import pandas as pd

from common import OUTPUTS, ROOT

sys.path.insert(0, str(ROOT / "app"))
import policy  # noqa: E402
import roi  # noqa: E402

STATUS = {"Open": "o", "Pending Customer Response": "p", "Closed": "c"}
PRIORITY = {"Critical": "C", "High": "H", "Medium": "M", "Low": "L"}


def main() -> None:
    tickets = pd.read_csv(OUTPUTS / "customer_tickets.csv.gz")
    diag = json.loads((OUTPUTS / "diagnostico.json").read_text(encoding="utf-8"))
    clf = json.loads((OUTPUTS / "classifier_metrics.json").read_text(encoding="utf-8"))
    llm = json.loads((OUTPUTS / "llm_eval.json").read_text(encoding="utf-8"))
    position = {int(t): i for i, t in enumerate(tickets["Ticket ID"])}
    sample = [{"i": position[r["ticket_id"]], "stage": r["decision"]["stage"]} for r in llm["rows"] if r.get("decision")]
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
    }
    out = ROOT / "presentation" / "data.js"
    out.parent.mkdir(exist_ok=True)
    out.write_text("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"{out} ({out.stat().st_size // 1024} KB)", scenarios)


if __name__ == "__main__":
    main()
