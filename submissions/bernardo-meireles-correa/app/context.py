"""Recuperar o que falta num ticket antes de perguntar de novo ao cliente.

Separa o que é sinal real, extraído do próprio ticket, do que depende de uma
integração que não existe no dataset. Para as fontes simuladas, mostramos a
consulta que seria feita, nunca um resultado inventado.

Regras de uso (LGPD): somente leitura, só conversas ligadas ao ticket ou ao
cliente, mínimo necessário, cada consulta registrada, nada enviado sem uma pessoa.
"""
import re
from dataclasses import dataclass, field
from datetime import date

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}(?:\.[a-z]{2,})?", re.I)
LOG_LINE = re.compile(r"\[\d{2}:\d{2}:\d{2}(?:\.\d+)?\][^\n\[]{0,80}")
# Data de referência: os timestamps do dataset estão entre 31/05 e 02/06/2023.
REFERENCE_DATE = date(2023, 6, 1)
WARRANTY_MONTHS = 12

PRIVACY_RULES = [
    "Somente leitura: a IA consulta, não altera nem envia nada.",
    "Só conversas e registros ligados a este ticket ou a este cliente.",
    "Coleta o mínimo necessário para resolver o pedido.",
    "Cada consulta fica registrada com quem pediu e por quê.",
    "Base legal LGPD: execução do contrato de suporte; o cliente é informado.",
    "Nada vai ao cliente sem aprovação de uma pessoa.",
]


@dataclass
class Context:
    found: list[tuple[str, str]] = field(default_factory=list)      # (fonte, achado) reais
    missing: list[str] = field(default_factory=list)                 # o que o texto deixou em branco
    queries: list[tuple[str, str]] = field(default_factory=list)     # (fonte simulada, consulta)


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def recover(text: str, product: str | None = None, purchase_date: str | None = None) -> Context:
    ctx = Context()
    contacts = sorted(set(m.rstrip(".") for m in EMAIL.findall(text)))
    if contacts:
        ctx.found.append(("Contato citado no texto", ", ".join(contacts)))
    for line in LOG_LINE.findall(text)[:2]:
        ctx.found.append(("Trecho de log no texto", line.strip()))
    if product:
        ctx.found.append(("Cadastro: produto", product))
    if purchase_date:
        bought = date.fromisoformat(str(purchase_date)[:10])
        age = months_between(bought, REFERENCE_DATE)
        status = "fora" if age > WARRANTY_MONTHS else "dentro"
        ctx.found.append(("Cadastro: compra", f"{bought.strftime('%d/%m/%Y')}, há {age} meses ({status} da garantia de {WARRANTY_MONTHS} meses)"))

    if "{error_message}" in text:
        ctx.missing.append("mensagem de erro (o campo chegou em branco)")
    if "{product_purchased}" in text:
        ctx.missing.append("produto (o campo chegou em branco)")

    subject = product or "o produto citado"
    ctx.queries = [
        ("Caixa de e-mail do suporte", f"Respostas já enviadas por outro agente e anexos do cliente sobre {subject} nos últimos 30 dias."),
        ("CRM", "Plano contratado, contatos alternativos autorizados e tickets anteriores do mesmo cliente."),
        ("Telemetria do produto", "Erros registrados pelo dispositivo nas últimas 72 horas, para recuperar a mensagem de erro."),
    ]
    return ctx
