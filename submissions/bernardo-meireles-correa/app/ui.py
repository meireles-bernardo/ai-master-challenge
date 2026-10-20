"""Páginas e dados compartilhados do Copiloto de Suporte (app.py monta a navegação)."""
import csv
import html
import json
import os
import random
from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import context
import guide
import limits
import llm
import policy
import roi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
LOCAL = ROOT / "local-state"

# Os datasets vêm em inglês; a interface mostra em português.
TYPE_PT = {"Technical issue": "Problema técnico", "Billing inquiry": "Dúvida de cobrança", "Product inquiry": "Dúvida sobre o produto",
           "Refund request": "Pedido de reembolso", "Cancellation request": "Pedido de cancelamento"}
PRIORITY_PT = {"Critical": "Crítica", "High": "Alta", "Medium": "Média", "Low": "Baixa"}
CHANNEL_PT = {"Email": "E-mail", "Phone": "Telefone", "Chat": "Chat", "Social media": "Redes sociais"}
STATUS_PT = {"Open": "Sem resposta", "Pending Customer Response": "Esperando o cliente", "Closed": "Fechado"}
IT_PT = {"Access": "Acesso", "Administrative rights": "Direitos de administrador", "HR Support": "RH", "Hardware": "Hardware",
         "Internal Project": "Projeto interno", "Miscellaneous": "Diversos", "Purchase": "Compra", "Storage": "Armazenamento"}
CONFIDENCE_PT = {"high": "alta", "medium": "média", "low": "baixa"}
STATUS_HEX = ["#C9372C", "#B7791F", "#7E8893"]
STATUS_COLORS = alt.Scale(domain=list(STATUS_PT.values()), range=STATUS_HEX)

STYLE = """
<style>
  header[data-testid="stHeader"] { display: none; }
  [data-testid="stMainBlockContainer"] { padding-top: 0.5rem; }
  [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * { color: #2E3640 !important; }
  [data-testid="stMetricDelta"] { background: #E7E1D3 !important; }
  [data-testid="stCaptionContainer"] { opacity: 1 !important; }
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: #59626D !important; }
  h1 { letter-spacing: -0.02em; }
  .frame { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 1.2rem; border-bottom: 1px solid #D8D1C2; padding: 0.6rem 0 0.7rem; margin: 0 0 1.4rem; }
  .frame .brand { font-family: ui-monospace, Consolas, monospace; font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; text-decoration: none; color: #1B2128; font-weight: 600; white-space: nowrap; }
  .frame .brand b { color: #B3261E; }
  .frame nav { display: flex; gap: 1.1rem; overflow-x: auto; margin-left: auto; scrollbar-width: none; }
  .frame nav a { text-decoration: none; color: #59626D; white-space: nowrap; padding: 0.2rem 0; font-size: 0.95rem; }
  .frame nav a:hover, .frame nav a[aria-current] { color: #1B2128; box-shadow: inset 0 -2px 0 #1B2128; }
  .frame a:focus-visible { outline: 3px solid #D99A2B; outline-offset: 3px; }
  .kicker { font-family: ui-monospace, Consolas, monospace; font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: #B3261E; margin: 0 0 0.2rem; }
  .lede { color: #3B444E; font-size: 1.05rem; max-width: 46rem; margin: -0.4rem 0 1.2rem; }
  .chart-note { color: #59626D; font-size: 0.92rem; margin: -0.3rem 0 0.8rem; }
  .legend { display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; margin: -0.4rem 0 0.6rem; padding: 0; list-style: none; font-size: 0.88rem; color: #59626D; }
  .legend li { display: flex; align-items: center; gap: 0.35rem; }
  .legend i { width: 0.8rem; height: 0.8rem; display: inline-block; }
  .base-note { color: #59626D; font-size: 0.85rem; border-top: 1px solid #D8D1C2; padding-top: 0.8rem; margin-top: 2rem; }
  .decision { background: #FFFDF8; border: 1px solid #D8D1C2; border-left: 6px solid; border-radius: 4px; padding: 0.9rem 1.1rem; margin: 0.3rem 0 1rem; }
  .decision .eyebrow, .gmap .eyebrow { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: #59626D; margin: 0; }
  .decision h3 { font-size: 1.35rem; margin: 0.15rem 0 0.5rem; padding: 0; color: #1B2128; }
  .decision ul { margin: 0 0 0.6rem 1.1rem; padding: 0; color: #2E3640; }
  .decision p { margin: 0.2rem 0 0; color: #1B2128; }
  .decision p span { color: #59626D; }
  .tone-red { border-left-color: #C9372C !important; }
  .tone-amber { border-left-color: #B7791F !important; }
  .tone-light { border-left-color: #1B2128 !important; }
  .tone-dim { border-left-color: #7E8893 !important; }
  .facts { display: flex; flex-wrap: wrap; gap: 0.5rem 2rem; margin: 0 0 0.8rem; }
  .facts dt { font-size: 0.8rem; color: #59626D; }
  .facts dd { margin: 0; font-size: 1.15rem; font-weight: 600; color: #1B2128; }
  .top3 { list-style: none; padding: 0; margin: 0.3rem 0 0; }
  .top3 li { display: grid; grid-template-columns: minmax(7rem, 11rem) 1fr 3rem; gap: 0.6rem; align-items: center; margin: 0.25rem 0; color: #1B2128; }
  .top3 .bar { background: #E7E1D3; height: 0.6rem; border-radius: 2px; }
  .top3 .bar i { display: block; height: 100%; background: #1B2128; border-radius: 2px; }
  p.eyebrow { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: #59626D; margin: 0; }
  .gmap ol { list-style: none; margin: 0.4rem 0 0; padding: 0; }
  .gmap li { margin: 0; }
  .gq { background: #FFFDF8; border: 1px solid #D8D1C2; border-radius: 4px; padding: 0.5rem 0.7rem; font-weight: 600; color: #1B2128; }
  .gbranch { margin: 0 0 0 1rem; padding: 0.35rem 0 0.35rem 0.9rem; border-left: 2px solid #D8D1C2; }
  .glabel { font-size: 0.8rem; color: #59626D; margin: 0; }
  .gdest { background: #FFFDF8; border: 1px solid #D8D1C2; border-left: 5px solid; border-radius: 4px; padding: 0.45rem 0.7rem; margin: 0.2rem 0 0; }
  .gdest b { display: block; color: #1B2128; }
  .gdest p { margin: 0.15rem 0 0; font-size: 0.86rem; color: #3B444E; line-height: 1.4; }
  .gdest p span { color: #1B2128; font-weight: 600; }
  .gmap .on > .gq, .gdest.on { background: #FFF3D9; border-color: #B7791F; }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .tag { display: inline-block; font-size: 0.74rem; font-weight: 700; background: #D99A2B; color: #1B2128; padding: 0 0.4rem; border-radius: 3px; margin-left: 0.35rem; vertical-align: 1px; }
</style>
"""

# Moldura comum com o dossiê: mesma marca e mesma navegação em todas as páginas.
NAV = [("Resumo", "/", None), ("Provas", "/#provas", None), ("Plano", "/#plano", None), ("Painel", "/app/", "painel"),
       ("Triagem", "/app/triagem", "triagem"), ("Fila", "/app/fila", "fila"), ("Método", "/app/validacao", "validacao")]


def frame(current: str, kicker: str, title: str, lede: str):
    links = "".join(f'<a href="{href}"{" aria-current=\"page\"" if key == current else ""}>{label}</a>' for label, href, key in NAV)
    st.html(STYLE + f'<header class="frame"><a class="brand" href="/"><b>Dossiê 002</b> · Suporte ao cliente</a>'
            f'<nav aria-label="Seções do dossiê e do protótipo">{links}</nav></header><p class="kicker">{kicker}</p>')
    st.title(title)
    st.html(f'<p class="lede">{lede}</p>')


def base_note():
    st.html('<p class="base-note">Base: dataset público e sintético do Challenge 002 do AI Master G4 (Kaggle). '
            "Nada aqui é dado de uma empresa real, e nada é enviado a clientes.</p>")


def legend(items: list[tuple[str, str]]) -> str:
    return '<ul class="legend">' + "".join(f'<li><i style="background:{c}"></i>{t}</li>' for c, t in items) + "</ul>"


def style():
    st.html(STYLE)


@st.cache_data
def load_json(name: str) -> dict:
    path = OUT / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data
def load_tickets() -> pd.DataFrame:
    df = pd.read_csv(OUT / "customer_tickets.csv.gz")
    df["Risco (regra)"] = df["Description (display)"].map(lambda t: ", ".join(policy.RISK_LABELS_PT[r] for r in sorted(policy.keyword_risks(t))))
    return df


@st.cache_data
def load_it_sample() -> pd.DataFrame:
    return pd.read_csv(OUT / "it_holdout_sample.csv")


@st.cache_resource
def it_router() -> policy.ITRouter:
    return policy.ITRouter()


@st.cache_data(show_spinner=False, max_entries=200)
def cached_triage(text: str, channel: str, product: str, provider: str) -> dict:
    # Só roda em cache miss: a chamada paga só acontece se couber no teto diário.
    if not limits.reserve():
        raise llm.LLMError(f"O teto diário de {limits.PER_DAY} análises desta instalação foi atingido. Volte amanhã.")
    return llm.triage({"text": text, "channel": channel, "product": product})


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%".replace(".", ",")


def dec(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def num(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def pt_text(s: str) -> str:
    """Traduz rótulos dos datasets que aparecem dentro das frases da regra."""
    for table in (TYPE_PT, IT_PT):
        for en, pt in table.items():
            s = s.replace(en, pt)
    return s


def esc(s) -> str:
    return html.escape(str(s))


DIAG = load_json("diagnostico.json")
CLF = load_json("classifier_metrics.json")
EVAL = load_json("llm_eval.json")


@st.cache_data
def prioritized_queue() -> pd.DataFrame:
    """Tickets não fechados na ordem da regra: risco no texto, sem primeira resposta, prioridade declarada."""
    df = load_tickets()
    q = df[df["Ticket Status"] != "Closed"].copy()
    q["sem_resposta"] = q["First Response Time"].isna()
    q["com_risco"] = q["Risco (regra)"] != ""
    q["_p"] = q["Ticket Priority"].map({"Critical": 0, "High": 1, "Medium": 2, "Low": 3})
    q = q.sort_values(["com_risco", "sem_resposta", "_p"], ascending=[False, False, True]).reset_index(drop=True)
    return pd.DataFrame({
        "Posição": q.index + 1,
        "Ticket": q["Ticket ID"],
        "Risco no texto": q["Risco (regra)"].replace("", "—"),
        "Situação": q["Ticket Status"].map(STATUS_PT),
        "Prioridade declarada": q["Ticket Priority"].map(PRIORITY_PT),
        "Canal": q["Ticket Channel"].map(CHANNEL_PT),
        "Descrição": q["Description (display)"],
        "_risco": q["com_risco"], "_sem_resposta": q["sem_resposta"],
    })


def status_share_chart(dimension: str, labels: dict, order: list[str], description: str):
    share = pd.DataFrame(DIAG["backlog"]["by_dimension"][dimension]["share_pct"]).T.reset_index(names="grupo")
    share = share.melt("grupo", var_name="Situação", value_name="%")
    share["grupo"] = share["grupo"].map(labels)
    share["Situação"] = share["Situação"].map(STATUS_PT)
    share["%"] = share["%"] / 100
    share["_o"] = share["Situação"].map({s: i for i, s in enumerate(STATUS_PT.values())})
    return (alt.Chart(share, description=description).mark_bar(size=20).encode(
        x=alt.X("%:Q", stack="normalize", axis=alt.Axis(format="%", title=None, grid=False)),
        y=alt.Y("grupo:N", sort=[labels[o] for o in order], title=None, axis=alt.Axis(labelOverlap=False, labelFontSize=13)),
        color=alt.Color("Situação:N", scale=STATUS_COLORS, legend=None),
        order=alt.Order("_o:Q"),
        tooltip=[alt.Tooltip("grupo:N", title="Grupo"), "Situação:N", alt.Tooltip("%:Q", format=".0%")])
        .properties(height=alt.Step(34)))


# --------------------------------------------------------------------------- painel
def page_dashboard():
    b = DIAG["backlog"]
    queue = prioritized_queue()
    central = roi.estimate(roi.SCENARIOS["Central"])
    frame("painel", "Provas 01 e 02 com os dados completos", "Painel da operação",
          f"A fila de suporte como um gestor veria na segunda-feira: {num(b['total'])} tickets, o que está parado, o que tem risco "
          "e o que atender primeiro. Mostra as Provas 01 e 02 do dossiê com os dados completos.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Parados", num(b["not_closed"]), f"{pct(b['not_closed'] / b['total'], 0)} da base", delta_color="off", delta_arrow="off", border=True)
    k2.metric("Nunca respondidos", num(b["open_without_first_response"]), border=True)
    k3.metric("Com risco no texto", num(queue["_risco"].sum()), "vão para o topo", delta_color="off", delta_arrow="off", border=True)
    k4.metric("Horas recuperáveis", f"~{num(central['total_hours_month'])} h/mês", "cenário central", delta_color="off", delta_arrow="off", border=True,
              help="Premissas na página Método. O dataset não registra o tempo do agente; o piloto mede.")

    a, b_ = st.columns([1, 1], gap="large")
    with a:
        st.subheader("Prioridade não muda nada")
        st.altair_chart(status_share_chart("Ticket Priority", PRIORITY_PT, ["Critical", "High", "Medium", "Low"],
                                           "Situação dos tickets por prioridade: proporções quase iguais em todas."), width="stretch")
        st.html(legend(list(zip(STATUS_HEX, STATUS_PT.values()))))
        st.html(f'<p class="chart-note">{num(b["critical_not_closed"])} dos {num(b["critical_total"])} tickets críticos estão parados, '
                "a mesma proporção dos de prioridade baixa.</p>")
    with b_:
        st.subheader("Nem o canal")
        st.altair_chart(status_share_chart("Ticket Channel", CHANNEL_PT, ["Email", "Phone", "Chat", "Social media"],
                                           "Situação dos tickets por canal: proporções quase iguais em todos."), width="stretch")
        st.html(legend(list(zip(STATUS_HEX, STATUS_PT.values()))))
        st.html('<p class="chart-note">O problema é a fila inteira, e não um segmento dela.</p>')

    st.subheader("Topo da fila")
    top = queue.head(10)
    st.dataframe(top.drop(columns=["_risco", "_sem_resposta"]), hide_index=True, width="stretch",
                 column_config={"Descrição": st.column_config.TextColumn(width="large")})
    c1, c2, _ = st.columns([1, 1, 2])
    c1.page_link("views/fila.py", label=f"Ver a fila completa ({num(len(queue))})", icon=":material/list:")
    c2.page_link("views/triagem.py", label="Triar um ticket", icon=":material/bolt:")

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("Satisfação")
        df = load_tickets()
        csat = df["Customer Satisfaction Rating"].dropna().astype(int).value_counts().sort_index().reset_index()
        csat.columns = ["Nota", "Tickets"]
        chart = alt.Chart(csat, description="Distribuição das notas de satisfação de 1 a 5: quantidades quase iguais.").mark_bar().encode(
            x=alt.X("Nota:O", axis=alt.Axis(labelAngle=0)), y=alt.Y("Tickets:Q", title=None),
            color=alt.Color("Nota:O", scale=alt.Scale(range=["#C9372C", "#C4622A", "#B7791F", "#8C7A45", "#5F6C78"]), legend=None),
            tooltip=["Nota", "Tickets"]).properties(height=200)
        st.altair_chart(chart, width="stretch")
        s = DIAG["satisfaction"]
        st.html(f'<p class="chart-note">Só os fechados têm nota, e as cinco aparecem quase na mesma quantidade. '
                f"Nenhuma das {len(s['tests'])} variáveis testadas explica a nota (menor p = {dec(s['min_p'])}). "
                "Primeiro é preciso registrar o motivo das notas baixas.</p>")
    with right:
        st.subheader("O que fazer agora")
        st.markdown(
            "1. **Esta semana:** atender a fila nesta ordem. Não precisa de IA.\n"
            "2. **Quatro semanas de piloto:** a IA sugere tipo, prioridade e rascunho; o agente decide e nada sai sozinho.\n"
            f"3. **Pedir o que falta no primeiro contato:** {num(b['status']['Pending Customer Response'])} tickets esperam o cliente.\n"
            "4. **Registrar** abertura, mudanças de situação e motivo das notas baixas.\n"
            "5. **Sempre com uma pessoa:** reembolso, cancelamento, perda de dados, acesso e jurídico.")
    base_note()


# --------------------------------------------------------------------------- triagem
def decision_html(dest_key: str, reasons: list[str], title: str | None = None) -> str:
    d = guide.DESTINATIONS[dest_key]
    items = "".join(f"<li>{esc(pt_text(r))}</li>" for r in reasons)
    return (f'<div class="decision tone-{d["tone"]}" role="status"><p class="eyebrow">Destino</p>'
            f'<h3>{esc(title or d["title"])}</h3>{f"<ul>{items}</ul>" if items else ""}'
            f'<p><span>Próximo passo:</span> {esc(d["action"])}</p><p><span>Quem:</span> {esc(d["who"])}</p></div>')


def guide_map(domain: str, dest: str | None = None, threshold: float = guide.IT_THRESHOLD_FALLBACK) -> str:
    """Mapa de decisões em HTML; com dest, acende o caminho desse ticket."""
    questions = guide.it_questions(threshold) if domain == "it" else guide.CUSTOMER_QUESTIONS
    last = guide.IT_LAST if domain == "it" else guide.CUSTOMER_LAST
    path = dict(guide.walk(domain, dest, threshold)) if dest else {}

    def card(key: str, lead: str) -> str:
        d, on = guide.DESTINATIONS[key], key == dest
        tag = '<span class="tag">este ticket</span><span class="sr"> (destino deste ticket)</span>' if on else ""
        detail = "" if dest and not on else (f'<p><span>Quem:</span> {esc(d["who"])}</p><p><span>O que fazer:</span> {esc(d["action"])}</p>'
                                              f'<p><span>Por quê:</span> {esc(d["why"])}</p>')
        return (f'<p class="glabel">{lead}</p><div class="gdest tone-{d["tone"]}{" on" if on else ""}">'
                f'<b>{esc(d["title"])}{tag}</b>{detail}</div>')

    rows = []
    for text, target, exit_on in questions:
        answer = path.get(text)
        tag = f'<span class="tag"><span class="sr">Resposta para este ticket: </span>{answer}</span>' if answer else ""
        exit_word, go_word = ("Sim", "Não") if exit_on else ("Não", "Sim")
        rows.append(f'<li class="{"on" if answer else ""}"><div class="gq">{esc(text)}{tag}</div>'
                    f'<div class="gbranch">{card(target, exit_word + ":")}<p class="glabel" style="margin-top:.4rem">{go_word}: segue</p></div></li>')
    rows.append(f"<li>{card(last, 'Caso contrário:')}</li>")
    who = "tickets internos de TI" if domain == "it" else "tickets de clientes"
    head = "Caminho deste ticket" if dest else "Para onde cada ticket vai"
    return f'<section class="gmap" aria-label="Mapa de próximos passos, {who}"><p class="eyebrow">{head}</p><ol>{"".join(rows)}</ol></section>'


def log_decision(row: dict):
    LOCAL.mkdir(exist_ok=True)
    path = LOCAL / "decisoes.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def page_triage():
    frame("triagem", "Prova 05 em ação", "Triagem de tickets",
          "Cole um ticket ou sorteie um dos datasets. A IA sugere tipo, prioridade e rascunho, uma regra fixa decide o destino "
          "e uma pessoa aprova o que for para o cliente. Ao lado, o mapa mostra o caminho que o ticket percorreu.")
    tickets, it_sample = load_tickets(), load_it_sample()

    c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
    domain = c1.radio("Origem do ticket", ["Cliente", "Interno (TI)"], horizontal=True,
                      captions=["Analisado pelo LLM", "Classificador treinado"])
    if c2.button("Sortear um ticket do dataset", icon=":material/casino:", width="stretch"):
        if domain == "Cliente":
            row = tickets.iloc[random.randrange(len(tickets))]
            st.session_state.update(text=row["Description (display)"], channel=row["Ticket Channel"],
                                    product=row["Product Purchased"], purchase=row["Date of Purchase"],
                                    raw=row["Ticket Description"], sampled=row["Description (display)"],
                                    ref=f"Ticket #{row['Ticket ID']} · {CHANNEL_PT.get(row['Ticket Channel'], row['Ticket Channel'])} · {row['Product Purchased']}", label=None)
        else:
            row = it_sample.iloc[random.randrange(len(it_sample))]
            st.session_state.update(text=row["text"], channel="", product="", purchase=None, raw=None, sampled=row["text"],
                                    ref="Ticket de TI separado para teste (o modelo nunca viu)", label=row["label"])
        st.session_state.pop("analysis", None)
    text = st.text_area("Texto do ticket", key="text", height=140, placeholder="Ex.: Comprei há 3 semanas e o aparelho parou de ligar.")
    if st.session_state.get("ref"):
        st.caption(st.session_state["ref"])
    go = st.button("Analisar", type="primary", disabled=not text.strip(), icon=":material/bolt:")
    if not text.strip():
        st.caption("Escreva ou sorteie um ticket para liberar a análise.")

    is_it = domain.startswith("Interno")
    if go:
        st.session_state["analysis"] = {"domain": domain, "text": text}
        if not is_it:
            seen = st.session_state.setdefault("llm_seen", set())
            blocked = None if text in seen else limits.check(len(seen))
            if blocked:
                st.session_state["analysis"]["error"] = blocked
            else:
                try:
                    with st.spinner(f"{llm.model_label()} analisando o ticket…"):
                        out = cached_triage(text, st.session_state.get("channel", ""), st.session_state.get("product", ""), llm.provider_name())
                    seen.add(text)
                    st.session_state["analysis"]["llm"] = out
                    st.session_state["draft"] = out["suggested_reply"]
                except llm.LLMError as exc:
                    st.session_state["analysis"]["error"] = str(exc)

    analysis = st.session_state.get("analysis")
    if analysis and analysis["domain"] != domain:
        analysis = None
    threshold = it_router().threshold
    result_col, map_col = st.columns([3, 2], gap="large")

    if not analysis:
        with map_col:
            st.html(guide_map("it" if is_it else "customer", None, threshold))
        with result_col:
            st.info("O resultado aparece aqui: destino, próximo passo, o que pedir ao cliente e um rascunho para aprovar.", icon=":material/info:")
        base_note()
        return
    text = analysis["text"]

    if is_it:
        result, decision = it_router().route(text)
        dest = guide.destination_key(decision, "it")
        with result_col:
            label = IT_PT.get(result["label"], result["label"])
            st.html(decision_html(dest, decision.reasons, f"{guide.DESTINATIONS[dest]['title']}: {label}"
                                  if dest != "it_human" else None))
            m1, m2 = st.columns(2)
            m1.metric("Categoria sugerida", label, f"{pct(result['confidence'], 0)} de confiança", delta_color="off", delta_arrow="off")
            if st.session_state.get("label") and st.session_state.get("sampled") == text:
                m2.metric("Categoria real", IT_PT.get(st.session_state["label"], st.session_state["label"]))
            bars = "".join(f'<li><span>{esc(IT_PT.get(c, c))}</span><span class="bar"><i style="width:{p * 100:.0f}%"></i></span>'
                           f'<span>{pct(p, 0)}</span></li>' for c, p in result["top3"])
            st.html(f'<p class="eyebrow">Três categorias mais prováveis</p><ol class="top3">{bars}</ol>')
        with map_col:
            st.html(guide_map("it", dest, threshold))
        base_note()
        return

    if "error" in analysis:
        decision = policy.decide_customer(None, text)
        with result_col:
            st.error(f"A IA não respondeu: {analysis['error']}", icon=":material/error:")
            st.html(decision_html("fallback", decision.reasons))
            context_panel(text)
        with map_col:
            st.html(guide_map("customer", "fallback"))
        base_note()
        return

    out = analysis["llm"]
    decision = policy.decide_customer(out, text)
    dest = guide.destination_key(decision, "customer")
    with result_col:
        st.html(decision_html(dest, decision.reasons))
        facts = [("Tipo", TYPE_PT.get(out["ticket_type"], out["ticket_type"])), ("Prioridade", PRIORITY_PT.get(out["priority"], out["priority"])),
                 ("Confiança da IA", CONFIDENCE_PT[out["confidence"]])]
        st.html('<dl class="facts">' + "".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in facts) + "</dl>")
        st.markdown(f"**Resumo.** {out['summary_pt']}  \n**Por que essa prioridade.** {out['priority_reason_pt']}")
        if out["missing_information"]:
            st.markdown("**Pedir ao cliente**\n" + "\n".join(f"- {m}" for m in out["missing_information"]))
        draft = st.text_area("Rascunho de resposta (edite antes de aprovar)", key="draft", height=170)
        a, b, c, _ = st.columns([1, 1, 1, 1])
        for col, action, label in [(a, "aprovado", "Aprovar"), (b, "editado", "Salvar edição"), (c, "rejeitado", "Rejeitar")]:
            if col.button(label, width="stretch", type="primary" if action == "aprovado" else "secondary"):
                log_decision({"at": datetime.now().isoformat(timespec="seconds"), "ref": st.session_state.get("ref", "texto livre"),
                              "action": action, "destination": decision.destination, "llm_type": out["ticket_type"],
                              "llm_priority": out["priority"], "draft": draft})
                st.toast(f"Decisão registrada: {action}. Nada foi enviado ao cliente.")
        st.caption(f"Analisado por {llm.model_label()} em {dec(out['_seconds'], 1)} s. Nada é enviado ao cliente: "
                   "cada decisão fica registrada para o piloto medir acertos.")
        context_panel(text)
    with map_col:
        st.html(guide_map("customer", dest))
    base_note()


def context_panel(text: str):
    # Ticket sorteado e não editado: usa cadastro e texto original; texto livre: só o que está escrito.
    sampled = st.session_state.get("sampled") == text
    raw = st.session_state.get("raw") if sampled else None
    ctx = context.recover(raw or text, st.session_state.get("product") if sampled else None,
                          st.session_state.get("purchase") if sampled else None)
    with st.expander("Contexto recuperado antes de perguntar ao cliente"):
        st.markdown("**Já encontrado no ticket e no cadastro**")
        if ctx.found:
            st.markdown("\n".join(f"- *{src}:* {value}" for src, value in ctx.found))
        else:
            st.caption("Só o texto. Num ticket real, o cadastro do cliente entraria aqui.")
        if ctx.missing:
            st.markdown("**Chegou em branco:** " + "; ".join(ctx.missing))
        st.markdown("**Onde mais procurar** (simulado: o dataset não tem essas fontes, então mostramos a consulta, não um resultado)")
        st.markdown("\n".join(f"- *{src}:* {query}" for src, query in ctx.queries))
        st.markdown("**Regras antes de ligar fontes reais** (propostas, ainda não implementadas)")
        st.markdown("\n".join(f"- {r}" for r in context.PRIVACY_RULES))


# --------------------------------------------------------------------------- fila
def page_queue():
    q = prioritized_queue()
    frame("fila", "Prova 02 corrigida", "Fila em ordem de risco",
          "Os tickets parados, na ordem que o dossiê propõe: primeiro os que têm risco no texto "
          "(perda de dados, dinheiro, acesso, cancelamento, jurídico), depois os que nunca tiveram resposta "
          "e por fim a prioridade declarada. Hoje a prioridade declarada não muda nada na fila.")
    k1, k2, k3 = st.columns(3)
    k1.metric("Parados", num(len(q)), border=True)
    k2.metric("Com risco no texto", num(q["_risco"].sum()), border=True)
    k3.metric("Nunca respondidos", num(q["_sem_resposta"].sum()), border=True)
    f1, f2 = st.columns(2)
    only_risk = f1.toggle("Só com risco no texto")
    only_new = f2.toggle("Só os nunca respondidos")
    view = q[(q["_risco"] | ~only_risk) & (q["_sem_resposta"] | ~only_new)]
    st.caption(f"{num(len(view))} tickets")
    st.dataframe(view.drop(columns=["_risco", "_sem_resposta"]), hide_index=True, width="stretch", height=560,
                 column_config={"Descrição": st.column_config.TextColumn(width="large")})
    base_note()


# --------------------------------------------------------------------------- como validamos
# REVIEW_FILE permite aos testes gravar fora de outputs/.
REVIEW_FILE = Path(os.environ.get("REVIEW_FILE", OUT / "revisao_humana.csv"))
REVIEW_FIELDS = ["ticket_id", "tipo", "prioridade", "riscos", "rascunho", "comentario", "revisado_em"]
REVIEW_SAMPLE = 20


def load_review() -> pd.DataFrame:
    if REVIEW_FILE.exists():
        return pd.read_csv(REVIEW_FILE, dtype={"comentario": str}).fillna("")
    return pd.DataFrame(columns=REVIEW_FIELDS)


def page_validation():
    frame("validacao", "Anexo de método", "Como validamos",
          "Como cada número do dossiê foi medido, com que método e onde ele para de valer.")
    it, cust, review, money = st.tabs(["Classificador de TI", "Triagem por LLM", "Revisão das triagens", "Retorno estimado"])
    with it:
        section_classifier()
    with cust:
        section_llm()
    with review:
        section_review()
    with money:
        section_roi()
    base_note()


def section_classifier():
    t, g, tr, sig = CLF["test"], CLF["gate"], CLF["transfer_to_customer"], CLF["customer_text_signal"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Acerto no teste", pct(t["accuracy"]), help=f"{num(t['n'])} tickets que o modelo nunca viu.", border=True)
    c2.metric("Sem textos quase repetidos", pct(t["strict_subset"]["accuracy"]), help=t["strict_subset"]["rule"], border=True)
    c3.metric("Encaminhados sozinhos", pct(t["auto_coverage"], 0), help=f"Confiança acima de {pct(g['threshold'])}.", border=True)
    c4.metric("Acerto dos encaminhados", pct(t["auto_precision"]), border=True)
    st.markdown(f"""
- **Dados:** {num(CLF['cleaning']['raw_rows'])} textos. Depois de normalizar, a checagem encontrou {num(CLF['cleaning']['exact_duplicates_removed'])} duplicatas exatas e {num(CLF['cleaning']['conflicting_texts_removed'])} rótulos conflitantes. Divisão: {num(CLF['splits']['train'])} treino, {num(CLF['splits']['calibration'])} calibração, {num(CLF['splits']['test'])} teste.
- **Modelo:** {CLF['chosen']}, com probabilidades calibradas. O limiar de {pct(g['threshold'])} foi escolhido na calibração para dar pelo menos 95% de acerto; os outros {pct(1 - t['auto_coverage'], 0)} vão para uma pessoa.
- **Comparação:** chutar sempre a categoria mais comum acerta {pct(t['majority_baseline_accuracy'])}.
- **Vazamento:** o risco real são textos quase iguais entre treino e teste. Sem eles ({num(t['strict_subset']['n'])} de {num(t['n'])}), o acerto fica em {pct(t['strict_subset']['accuracy'])}.
""")
    labels = [IT_PT.get(x, x) for x in t["labels"]]
    cm = pd.DataFrame(t["confusion_matrix"], index=labels, columns=labels).reset_index(names="Real").melt("Real", var_name="Previsto", value_name="Tickets")
    st.html('<p class="eyebrow">Categoria real × categoria prevista, no teste</p>')
    base = alt.Chart(cm, description="Matriz de confusão do classificador de TI no conjunto de teste: a diagonal concentra os acertos.")
    heat = base.mark_rect().encode(x=alt.X("Previsto:N", axis=alt.Axis(labelAngle=-30, labelLimit=180)), y=alt.Y("Real:N", axis=alt.Axis(labelLimit=180)),
                                   color=alt.Color("Tickets:Q", scale=alt.Scale(type="symlog", scheme="oranges"), legend=None),
                                   tooltip=["Real", "Previsto", "Tickets"])
    nums = base.mark_text(fontSize=11).encode(x="Previsto:N", y="Real:N", text="Tickets:Q",
                                              color=alt.condition(alt.datum.Tickets > 300, alt.value("#121B26"), alt.value("#E9EDF1")))
    st.altair_chart((heat + nums).properties(height=340), width="stretch")
    st.markdown(f"""
**Os dois datasets juntos**
- **O classificador de TI não serve para clientes, e a confiança não avisa.** Nos {num(tr['n'])} tickets de clientes, ele passaria {pct(tr['customer_auto_coverage'], 0)} com confiança alta, em categorias de TI sem sentido. Por isso cada origem tem seu roteador.
- **O texto dos clientes não carrega os rótulos.** Prevendo pela descrição: tipo {pct(sig['Ticket Type']['accuracy'])} (acaso: {pct(sig['Ticket Type']['chance'])}), assunto {pct(sig['Ticket Subject']['accuracy'])} (acaso: {pct(sig['Ticket Subject']['chance'])}), prioridade {pct(sig['Ticket Priority']['accuracy'])} (acaso: {pct(sig['Ticket Priority']['chance'])}). Os rótulos foram sorteados; por isso o lado de clientes usa um LLM sem treino.
""")
    with st.expander("Erros em que o modelo estava mais confiante"):
        st.dataframe(pd.read_csv(OUT / "classifier_errors.csv").head(30), hide_index=True, width="stretch")


def section_llm():
    if not EVAL:
        st.info("Rode `python analysis/eval_llm.py` para gerar a avaliação.")
        return
    s = EVAL["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tickets avaliados", f"{s['succeeded']} de {s['sample']}", help=f"Amostra aleatória, semente {s['seed']}.", border=True)
    c2.metric("Promessas proibidas", len(s["forbidden_promises"]), help="Rascunhos que prometem reembolso, cancelamento, crédito ou recuperação.", border=True)
    c3.metric("Riscos que o LLM deixou passar", f"{len(s['rule_risk_missed_by_llm'])} de {s['rule_risk_tickets']}",
              help="Comparado com o que a regra de palavras-chave encontra; não é gabarito humano.", border=True)
    c4.metric("Foram para uma pessoa", pct(s["human_required_pct"] / 100, 0), border=True)
    st.markdown(f"""
- **Modelo em produção:** {llm.model_label()}. A avaliação dos 60 tickets rodou com {s['provider']}; o mesmo prompt e o mesmo schema valem para os dois.
- **Mensagem de erro em branco:** pedida ao cliente em {s['error_placeholder_flagged_missing']} de {s['error_placeholder_tickets']} tickets que chegaram com o campo vazio.
- **Concordância com os rótulos do dataset:** tipo {pct(s['type_agreement_with_label'], 0)}, prioridade {pct(s['priority_agreement_with_label'], 0)}. Fica perto do acaso porque os rótulos foram sorteados; não mede acerto.
- **Tempo de resposta mediano:** {dec(s['median_seconds'], 1)} s.
""")
    rows = [r for r in EVAL["rows"] if r["llm"]]
    table = pd.DataFrame([{"Ticket": r["ticket_id"], "Tipo": TYPE_PT.get(r["llm"]["ticket_type"], r["llm"]["ticket_type"]),
                           "Prioridade": PRIORITY_PT.get(r["llm"]["priority"], r["llm"]["priority"]),
                           "Riscos": ", ".join(policy.RISK_LABELS_PT.get(f, f) for f in r["llm"]["risk_flags"]),
                           "Destino": r["decision"]["destination"], "Resumo": r["llm"]["summary_pt"],
                           "Rascunho": r["llm"]["suggested_reply"]} for r in rows])
    st.dataframe(table, hide_index=True, width="stretch", height=360)


def section_review():
    summary = load_json("revisao_resumo.json")
    rows = [r for r in EVAL.get("rows", []) if r.get("llm")][:REVIEW_SAMPLE]
    if summary:
        st.markdown("Nenhuma pessoa revisou estas triagens. Dois revisores de IA leram as mesmas 20, com as mesmas regras: "
                    "o Claude primeiro e o Codex depois, **sem ver a revisão do Claude**. Quando os dois discordam do LLM, "
                    "o erro é mais provável.")
        agree = summary["concordancia_entre_revisores"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tipo certo (Claude / Codex)", f"{summary['claude']['tipo']} / {summary['codex']['tipo']}", border=True)
        c2.metric("Prioridade certa", f"{summary['claude']['prioridade']} / {summary['codex']['prioridade']}", border=True)
        c3.metric("Riscos certos", f"{summary['claude']['riscos']} / {summary['codex']['riscos']}", border=True)
        c4.metric("Revisores concordam", f"{sum(agree.values())} de {4 * summary['tickets']}", border=True)
        both = summary["discordancias_de_ambos"]
        st.markdown(f"Os dois discordaram do LLM nos mesmos pontos: tipo no ticket {', '.join(map(str, both['tipo'])) or 'nenhum'}; "
                    f"prioridade nos tickets {', '.join(map(str, both['prioridade'])) or 'nenhum'}. Nenhum rascunho prometeu reembolso, "
                    "cancelamento ou recuperação.")
        tables = {who: pd.read_csv(OUT / f"revisao_{who}.csv", dtype={"comentario": str}).fillna("")
                  for who in ("claude", "codex") if (OUT / f"revisao_{who}.csv").exists()}
        if len(tables) == 2:
            with st.expander("As 20 revisões lado a lado"):
                st.dataframe(tables["claude"].merge(tables["codex"], on="ticket_id", suffixes=(" (Claude)", " (Codex)")),
                             hide_index=True, width="stretch", height=380)

    done = load_review()
    st.subheader("Revisão humana")
    if len(done):
        agree = {c: (done[c] == "concordo").mean() for c in ["tipo", "prioridade", "riscos"]}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revisadas", f"{len(done)} de {len(rows)}")
        c2.metric("Concorda com o tipo", pct(agree["tipo"], 0))
        c3.metric("Concorda com a prioridade", pct(agree["prioridade"], 0))
        c4.metric("Concorda com os riscos", pct(agree["riscos"], 0))
    if os.environ.get("ENABLE_REVIEW") != "1":
        st.markdown(f"Há um formulário para uma pessoa revisar as mesmas {len(rows)} triagens. Ele fica desligado no site público "
                    "e ainda não foi usado nesta entrega.")
        if len(done):
            st.dataframe(done, hide_index=True, width="stretch")
        return

    ids = [r["ticket_id"] for r in rows]
    pending = [i for i in ids if i not in set(done["ticket_id"].astype(int))]
    default = ids.index(pending[0]) if pending else 0
    pick = st.selectbox("Ticket", ids, index=default, format_func=lambda i: f"#{i}" + ("  (revisado)" if i not in pending else ""))
    r = next(x for x in rows if x["ticket_id"] == pick)
    o = r["llm"]
    st.markdown(f"> {r['text']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tipo sugerido", TYPE_PT.get(o["ticket_type"], o["ticket_type"]))
    c2.metric("Prioridade sugerida", PRIORITY_PT.get(o["priority"], o["priority"]))
    c3.metric("Destino", r["decision"]["destination"])
    st.markdown(f"**Riscos marcados:** {', '.join(policy.RISK_LABELS_PT.get(f, f) for f in o['risk_flags']) or 'nenhum'}  \n"
                f"**Pedir ao cliente:** {'; '.join(o['missing_information']) or 'nada'}")
    st.markdown(f"**Rascunho:** {o['suggested_reply']}")
    prev = done[done["ticket_id"].astype(int) == pick]
    get = lambda c, d: prev.iloc[0][c] if len(prev) else d
    with st.form(f"review-{pick}"):
        options = ["concordo", "discordo"]
        tipo = st.radio("O tipo está certo?", options, index=options.index(get("tipo", "concordo")), horizontal=True)
        prioridade = st.radio("A prioridade está certa?", options, index=options.index(get("prioridade", "concordo")), horizontal=True)
        riscos = st.radio("Os riscos marcados estão certos?", options, index=options.index(get("riscos", "concordo")), horizontal=True)
        drafts = ["enviaria como está", "enviaria com pequenas edições", "reescreveria"]
        rascunho = st.radio("O rascunho", drafts, index=drafts.index(get("rascunho", drafts[1])))
        comentario = st.text_input("Comentário (opcional)", value=get("comentario", ""))
        if st.form_submit_button("Salvar revisão", type="primary"):
            row = {"ticket_id": pick, "tipo": tipo, "prioridade": prioridade, "riscos": riscos, "rascunho": rascunho,
                   "comentario": comentario, "revisado_em": datetime.now().isoformat(timespec="seconds")}
            done = pd.concat([done[done["ticket_id"].astype(int) != pick], pd.DataFrame([row])]).sort_values("ticket_id")
            done[REVIEW_FIELDS].to_csv(REVIEW_FILE, index=False)
            st.toast(f"Revisão do ticket #{pick} salva")
            st.rerun()


def section_roi():
    st.markdown("O dataset não registra quanto tempo o agente gasta, então os minutos abaixo são **premissas** que o piloto vai medir. "
                "O volume de tickets vem do enunciado.")
    scen = {k: roi.estimate(a) for k, a in roi.SCENARIOS.items()}
    c1, c2, c3 = st.columns(3)
    c1.metric("Horas por mês (central)", num(scen["Central"]["total_hours_month"]),
              f"faixa {num(scen['Conservador']['total_hours_month'])} a {num(scen['Otimista']['total_hours_month'])}", delta_color="off", delta_arrow="off", border=True)
    c2.metric("Equivale a", f"{dec(scen['Central']['fte'], 1)} pessoa", border=True)
    c3.metric("Valor líquido por ano", f"R$ {num(scen['Central']['net_value_brl_year'])}", help="Já desconta o custo do LLM.", border=True)
    st.dataframe(pd.DataFrame([{"Cenário": k, "Horas/mês": round(v["total_hours_month"]), "Pessoas": round(v["fte"], 1),
                                "R$/ano líquido": round(v["net_value_brl_year"])} for k, v in scen.items()]), hide_index=True)
    with st.expander("Ajustar as premissas"):
        base = roi.Assumptions()
        a1, a2 = st.columns(2)
        with a1:
            tickets = st.number_input("Tickets por ano", 1000, 500_000, base.tickets_per_year, step=1000)
            t0 = st.slider("Triagem hoje (min)", 0.5, 10.0, base.triage_min_today, 0.5)
            t1 = st.slider("Triagem com IA (min)", 0.0, 10.0, base.triage_min_with_ai, 0.1)
            r0 = st.slider("Primeira resposta hoje (min)", 1.0, 20.0, base.reply_min_today, 0.5)
            r1 = st.slider("Primeira resposta com rascunho (min)", 0.5, 20.0, base.reply_min_with_ai, 0.5)
        with a2:
            cyc = st.slider("Tickets sem uma ida e volta extra (%)", 0.0, 50.0, base.extra_cycle_avoided_pct, 1.0)
            cyc_min = st.slider("Minutos por ida e volta", 1.0, 15.0, base.extra_cycle_min, 0.5)
            cost = st.number_input("Custo-hora com encargos (R$)", 10.0, 300.0, base.cost_per_hour_brl, 5.0)
            llm_cost = st.number_input("Custo de LLM por ticket (US$)", 0.0, 0.5, base.llm_cost_usd_per_ticket, 0.005, format="%.3f")
        r = roi.estimate(roi.Assumptions(int(tickets), t0, t1, r0, r1, cyc, cyc_min, cost, llm_cost))
        m1, m2, m3 = st.columns(3)
        m1.metric("Horas por mês", num(r["total_hours_month"]))
        m2.metric("Pessoas", dec(r["fte"], 1))
        m3.metric("Valor líquido por ano", f"R$ {num(r['net_value_brl_year'])}")
    st.caption("Capacidade liberada não vira caixa sozinha: ela vai para a fila parada. O piloto mede os minutos reais antes de qualquer meta.")
