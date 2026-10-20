"""Estimativa de horas recuperáveis. Todas as premissas são explícitas e editáveis no app.

O dataset não registra esforço do agente; por isso as entradas de minutos são premissas a medir
no piloto em sombra. O volume (30 mil/ano) vem do enunciado do desafio.
"""
from dataclasses import asdict, dataclass

HOURS_PER_FTE_MONTH = 168


@dataclass
class Assumptions:
    tickets_per_year: int = 30_000
    triage_min_today: float = 2.0       # ler, classificar, priorizar e encaminhar
    triage_min_with_ai: float = 0.5     # conferir a sugestão
    reply_min_today: float = 6.0        # escrever a primeira resposta
    reply_min_with_ai: float = 3.0      # revisar e editar o rascunho
    extra_cycle_avoided_pct: float = 15.0  # % de tickets que deixam de ter uma ida e volta por falta de dado
    extra_cycle_min: float = 4.0        # minutos do agente por ida e volta
    cost_per_hour_brl: float = 45.0     # custo-hora carregado do agente
    llm_cost_usd_per_ticket: float = 0.01
    brl_per_usd: float = 5.4


SCENARIOS = {
    "Conservador": Assumptions(triage_min_with_ai=1.0, reply_min_with_ai=4.5, extra_cycle_avoided_pct=5.0),
    "Central": Assumptions(),
    "Otimista": Assumptions(triage_min_with_ai=0.3, reply_min_with_ai=2.0, extra_cycle_avoided_pct=25.0),
}


def estimate(a: Assumptions) -> dict:
    minutes_per_ticket = {
        "Triagem e roteamento": a.triage_min_today - a.triage_min_with_ai,
        "Rascunho da 1ª resposta": a.reply_min_today - a.reply_min_with_ai,
        "Idas e voltas evitadas": a.extra_cycle_avoided_pct / 100 * a.extra_cycle_min,
    }
    hours_year = {k: v * a.tickets_per_year / 60 for k, v in minutes_per_ticket.items()}
    total_hours = sum(hours_year.values())
    llm_cost = a.tickets_per_year * a.llm_cost_usd_per_ticket * a.brl_per_usd
    gross = total_hours * a.cost_per_hour_brl
    return {
        "assumptions": asdict(a),
        "minutes_per_ticket": minutes_per_ticket,
        "hours_per_year": hours_year,
        "total_hours_year": total_hours,
        "total_hours_month": total_hours / 12,
        "fte": total_hours / 12 / HOURS_PER_FTE_MONTH,
        "gross_value_brl_year": gross,
        "llm_cost_brl_year": llm_cost,
        "net_value_brl_year": gross - llm_cost,
    }


if __name__ == "__main__":
    for name, a in SCENARIOS.items():
        r = estimate(a)
        print(f"{name:12s} {r['total_hours_month']:6.0f} h/mês  {r['fte']:.1f} FTE  R$ {r['net_value_brl_year']:,.0f}/ano líquido")
