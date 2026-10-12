"""Regras determinísticas: o que a IA pode fazer sozinha e onde um humano é obrigatório.

O LLM e o classificador sugerem; estas regras decidem o destino. Elas não dependem do LLM
acertar: uma rede de segurança por palavras-chave marca risco mesmo se o modelo esquecer.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]

RISK_PATTERNS = {
    "refund_or_money": r"\b(refund|chargeback|charged? twice|overcharg|money back|reembols|cobran)",
    "cancellation_or_churn": r"\b(cancel|unsubscribe|terminate|close my account|cancelar)",
    "data_loss": r"\b(data loss|lost (all )?(my )?(data|files)|deleted|corrupt)",
    "security_or_account_access": r"\b(hack|password|unauthori[sz]ed|breach|locked out|2fa|phishing|account access)",
    "legal_or_compliance": r"\b(lawyer|legal|lawsuit|gdpr|lgpd|procon|regulator)",
    "angry_or_escalation": r"\b(unacceptable|furious|worst|escalat|manager|supervisor)",
}

RISK_LABELS_PT = {
    "refund_or_money": "dinheiro/reembolso",
    "cancellation_or_churn": "cancelamento/churn",
    "data_loss": "perda de dados",
    "security_or_account_access": "segurança/acesso à conta",
    "legal_or_compliance": "jurídico/regulatório",
    "angry_or_escalation": "cliente irritado/escalonamento",
    "safety": "segurança física",
}

# Categorias IT em que rotear é seguro, mas executar exige aprovação do dono do sistema.
IT_APPROVAL_REQUIRED = {"Access", "Administrative rights", "Purchase"}


def keyword_risks(text: str) -> set[str]:
    low = text.lower()
    return {flag for flag, pattern in RISK_PATTERNS.items() if re.search(pattern, low)}


@dataclass
class Decision:
    destination: str
    human_required: bool
    reasons: list[str] = field(default_factory=list)
    stage: str = ""


def decide_customer(llm: dict | None, text: str) -> Decision:
    rules = keyword_risks(text)
    if llm is None:
        reasons = ["LLM indisponível: triagem manual completa."]
        if rules:
            reasons.append("Risco detectado por regra: " + ", ".join(RISK_LABELS_PT[r] for r in sorted(rules)))
        return Decision("Fila de triagem humana", True, reasons, "fallback")
    flags = set(llm.get("risk_flags", [])) | rules
    reasons = []
    if flags:
        reasons.append("Risco: " + ", ".join(RISK_LABELS_PT.get(f, f) for f in sorted(flags)))
    if llm.get("ticket_type") in {"Refund request", "Cancellation request"}:
        reasons.append(f"Tipo {llm['ticket_type']} envolve decisão comercial.")
    if llm.get("confidence") == "low":
        reasons.append("Confiança do modelo: baixa.")
    if rules - set(llm.get("risk_flags", [])):
        reasons.append("A regra de segurança encontrou risco que o LLM não marcou.")
    if reasons:
        return Decision("Agente sênior revisa antes de responder", True, reasons, "julgamento humano")
    if llm.get("missing_information") or llm.get("confidence") != "high":
        why = ["Rascunho pronto; faltam dados para resolver."] if llm.get("missing_information") else []
        if llm.get("confidence") != "high":
            why.append("Confiança média: o agente confere tipo e prioridade.")
        return Decision("Agente revisa o rascunho e pede os dados faltantes", True, why, "assistido")
    return Decision("Elegível a resposta automática (fase 2)", False,
                    ["Pergunta informativa, sem risco e com confiança alta. No piloto, ainda passa por revisão."], "automatizável")


class ITRouter:
    def __init__(self, path: Path = ROOT / "models" / "it_classifier.joblib"):
        bundle = joblib.load(path)
        self.model, self.threshold, self.name = bundle["model"], bundle["threshold"], bundle["name"]

    def route(self, text: str) -> tuple[dict, Decision]:
        proba = self.model.predict_proba([text])[0]
        ranked = sorted(zip(self.model.classes_, proba), key=lambda x: -x[1])
        label, conf = ranked[0]
        result = {"label": label, "confidence": float(conf), "top3": [(c, float(p)) for c, p in ranked[:3]]}
        rules = keyword_risks(text)
        if conf < self.threshold:
            return result, Decision("Fila de triagem humana", True,
                                    [f"Confiança {conf:.0%} abaixo do limiar {self.threshold:.0%} (calibrado para 95% de precisão)."], "julgamento humano")
        reasons = [f"Roteado automaticamente para {label} ({conf:.0%})."]
        human = False
        if label in IT_APPROVAL_REQUIRED:
            reasons.append("Executar a mudança exige aprovação do dono do sistema.")
            human = True
        if rules:
            reasons.append("Risco detectado por regra: " + ", ".join(RISK_LABELS_PT[r] for r in sorted(rules)))
            human = True
        return result, Decision(f"Fila {label}", human, reasons, "automatizável" if not human else "assistido")
