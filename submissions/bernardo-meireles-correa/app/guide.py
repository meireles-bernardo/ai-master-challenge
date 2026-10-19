"""Guia de próximos passos: para onde cada ticket vai depois da triagem, o que fazer e por quê.

Espelha as regras de policy.py (não decide nada). O app usa para desenhar o mapa e acender o
caminho do ticket analisado; analysis/build_presentation.py leva o mesmo conteúdo para a apresentação.
"""
import policy

IT_THRESHOLD_FALLBACK = 0.745

# Cada pergunta leva a um destino (sim) ou à próxima pergunta (não).
CUSTOMER_QUESTIONS = [
    ("A IA respondeu?", "fallback", False),
    ("Tem risco no texto, é reembolso ou cancelamento, ou a confiança é baixa?", "senior", True),
    ("Falta informação ou a confiança é média?", "assisted", True),
]
CUSTOMER_LAST = "auto"

DESTINATIONS = {
    "senior": {
        "title": "Agente sênior revisa antes de responder",
        "who": "Agente sênior",
        "action": "Decide a parte comercial ou técnica e edita o rascunho. Nada sai sem a aprovação dele.",
        "why": "Erro aqui custa dinheiro, dados ou o cliente. A IA não promete reembolso nem recuperação.",
        "tone": "red",
    },
    "assisted": {
        "title": "Agente revisa o rascunho e pede o que falta",
        "who": "Agente de primeiro nível",
        "action": "Confere tipo e prioridade e envia o rascunho já pedindo os dados que faltam.",
        "why": "Um terço da fila espera o cliente. Pedir tudo no primeiro contato evita uma ida e volta.",
        "tone": "amber",
    },
    "auto": {
        "title": "Resposta automática (depois do piloto)",
        "who": "No piloto, um agente aprova com um clique",
        "action": "Pergunta simples, sem risco e com tudo o que precisa: o rascunho pode sair sozinho na fase 2.",
        "why": "Só se automatiza o que o piloto provar seguro. Nos 60 tickets testados, nenhum caiu aqui.",
        "tone": "light",
    },
    "fallback": {
        "title": "Triagem manual completa",
        "who": "Agente",
        "action": "Faz a triagem sem IA. A regra de palavras-chave continua marcando os riscos.",
        "why": "Se a IA cair ou o teto diário acabar, a fila não para.",
        "tone": "dim",
    },
    "it_auto": {
        "title": "Fila da equipe, direto",
        "who": "Equipe da categoria",
        "action": "O ticket entra na fila certa sem passar por ninguém.",
        "why": "Acima do limiar, 95% dos encaminhamentos automáticos acertaram no teste.",
        "tone": "light",
    },
    "it_approval": {
        "title": "Fila da equipe, com aprovação",
        "who": "Dono do sistema aprova, equipe executa",
        "action": "O encaminhamento é automático, mas executar o pedido exige aprovação.",
        "why": "Acesso, direitos de administrador e compras concedem permissão ou gastam dinheiro. Risco no texto também pede uma pessoa.",
        "tone": "amber",
    },
    "it_human": {
        "title": "Uma pessoa classifica",
        "who": "Triagem de TI",
        "action": "Lê o ticket e escolhe a categoria.",
        "why": "Abaixo do limiar o acerto cai. Cerca de 1 em cada 4 tickets vem para cá.",
        "tone": "dim",
    },
}

APPROVAL_PT = {"Access": "Acesso", "Administrative rights": "Direitos de administrador", "Purchase": "Compra"}


def it_questions(threshold: float = IT_THRESHOLD_FALLBACK) -> list[tuple[str, str, bool]]:
    pct = f"{threshold * 100:.1f}".replace(".", ",")
    cats = ", ".join(APPROVAL_PT[c] for c in sorted(policy.IT_APPROVAL_REQUIRED))
    return [
        (f"A confiança do classificador passa de {pct}%?", "it_human", False),
        (f"A categoria é {cats}, ou há risco no texto?", "it_approval", True),
    ]


IT_LAST = "it_auto"


def destination_key(decision: policy.Decision, domain: str) -> str:
    """Traduz a decisão de policy.py para o destino do mapa."""
    if domain == "it":
        if decision.stage == "julgamento humano":
            return "it_human"
        return "it_approval" if decision.human_required else "it_auto"
    return {"fallback": "fallback", "julgamento humano": "senior", "assistido": "assisted"}.get(decision.stage, "auto")


def walk(domain: str, dest: str, threshold: float = IT_THRESHOLD_FALLBACK) -> list[tuple[str, str]]:
    """Respostas a cada pergunta até chegar em dest: [(pergunta, 'sim'|'não'), ...]."""
    questions = it_questions(threshold) if domain == "it" else CUSTOMER_QUESTIONS
    out = []
    for text, target, exit_on in questions:
        if target == dest:
            out.append((text, "sim" if exit_on else "não"))
            return out
        out.append((text, "não" if exit_on else "sim"))
    return out
