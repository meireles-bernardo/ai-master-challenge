"""Páginas e dados compartilhados do Copiloto de Suporte (app.py monta a navegação)."""
import csv
import json
import random
from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import llm
import policy
import roi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
LOCAL = ROOT / "local-state"

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
    return llm.triage({"text": text, "channel": channel, "product": product})


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%".replace(".", ",")


def dec(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def num(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


DIAG = load_json("diagnostico.json")
CLF = load_json("classifier_metrics.json")
EVAL = load_json("llm_eval.json")


# --------------------------------------------------------------------------- páginas
def page_director():
    b, r, s, q = DIAG["backlog"], DIAG["resolution_time"], DIAG["satisfaction"], DIAG["text_quality"]
    central = roi.estimate(roi.SCENARIOS["Central"])
    st.title("O que os dados dizem ao Diretor de Operações")
    st.caption(f"Base: {num(b['total'])} tickets do Customer Support Ticket Dataset e {num(CLF['source']['rows'])} tickets do IT Service Ticket Dataset.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("1 · Onde perdemos tempo", f"{pct(b['not_closed'] / b['total'], 0)} parado",
                  help="Tickets que não estão fechados.")
        st.markdown(f"**{num(b['open_without_first_response'])}** tickets nunca receberam primeira resposta e "
                    f"**{num(b['status']['Pending Customer Response'])}** esperam o cliente. "
                    "Canal, prioridade e tipo **não** mudam isso: a fila trava igual em todos.")
    with c2:
        st.metric("2 · O que explica a satisfação", f"0 de {len(s['tests'])}",
                  help="Menor p-valor entre todas as variáveis testadas.")
        st.markdown(f"CSAT médio **{str(s['mean']).replace('.', ',')}** com notas 1–5 em proporções iguais. "
                    f"Nenhuma das {len(s['tests'])} variáveis testadas (canal, prioridade, tipo, assunto, produto, gênero, idade, tempo) tem associação (menor p = {dec(s['min_p'])}). "
                    "Não existe alavanca de CSAT nesses dados; o primeiro passo é medir.")
    with c3:
        st.metric("3 · Quanto dá para recuperar", f"~{num(central['total_hours_month'])} h/mês",
                  help="Cenário central; premissas editáveis na página ROI.")
        st.markdown(f"≈ **{str(round(central['fte'], 1)).replace('.', ',')} pessoa** em capacidade "
                    f"(faixa {num(roi.estimate(roi.SCENARIOS['Conservador'])['total_hours_month'])}–"
                    f"{num(roi.estimate(roi.SCENARIOS['Otimista'])['total_hours_month'])} h/mês) com triagem, rascunho e coleta de dados por IA, "
                    "sempre com revisão humana.")

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("A prioridade não está priorizando")
        share = pd.DataFrame(b["by_dimension"]["Ticket Priority"]["share_pct"]).T.reset_index(names="Prioridade")
        share = share.melt("Prioridade", var_name="Status", value_name="%")
        chart = alt.Chart(share).mark_bar().encode(
            x=alt.X("%:Q", stack="normalize", axis=alt.Axis(format="%"), title=None),
            y=alt.Y("Prioridade:N", sort=["Critical", "High", "Medium", "Low"], title=None),
            color=alt.Color("Status:N", scale=alt.Scale(domain=["Closed", "Open", "Pending Customer Response"], range=["#4c9a6a", "#d9534f", "#f0ad4e"])),
            tooltip=["Prioridade", "Status", "%"])
        st.altair_chart(chart.properties(height=220), width="stretch")
        st.markdown(f"Um ticket **Critical** tem a mesma chance de estar parado que um **Low**: "
                    f"{num(b['critical_not_closed'])} de {num(b['critical_total'])} críticos não estão fechados "
                    f"(V de Cramér {dec(b['by_dimension']['Ticket Priority']['cramers_v'])}, quase zero). "
                    "A fila é atendida por ordem de chegada, não por risco.")
    with right:
        st.subheader("As \"piores combinações\" são ruído")
        worst = pd.DataFrame(r["worst_combinations"])
        worst["Combinação"] = worst[["Ticket Channel", "Ticket Priority", "Ticket Type"]].agg(" · ".join, axis=1)
        st.dataframe(worst[["Combinação", "median", "count"]].rename(columns={"median": "Mediana (h)", "count": "Tickets"}),
                     hide_index=True, width="stretch")
        st.markdown(f"Entre as {r['combinations_n']} combinações canal × prioridade × tipo, as diferenças não passam no teste "
                    f"(Kruskal-Wallis p = {dec(r['combinations_kruskal_p'])}). Cada combinação tem de {r['combination_sizes'][0]} a "
                    f"{r['combination_sizes'][1]} tickets, e uma pior combinação desse tamanho surge por acaso em "
                    f"{pct(r['worst_median_permutation_p'], 0)} dos embaralhamentos. Ranquear isso levaria a investir no lugar errado.")

    st.subheader("O que fazer na segunda-feira")
    st.markdown(f"""
1. **Atacar a fila por risco, não por ordem de chegada.** A página *Fila priorizada* reordena os {num(b['not_closed'])} tickets abertos com regras de risco e coloca os sem primeira resposta no topo.
2. **Triagem e primeira resposta com IA, revisadas por humano.** A IA lê o ticket, sugere tipo e prioridade, marca riscos, lista o que falta e rascunha a resposta. O agente aprova ou edita (página *Triagem ao vivo*).
3. **Pedir o dado faltante já no primeiro contato.** {pct(b['status']['Pending Customer Response'] / b['total'], 0)} dos tickets esperam o cliente; {num(q['placeholder_error_message'])} descrições chegam com a mensagem de erro em branco.
4. **Instrumentar antes de prometer CSAT.** Registrar abertura, eventos e motivo de nota baixa; hoje os timestamps cobrem só {str(r['timestamp_window_hours']).replace('.', ',')} h e {pct(r['inverted_pct'] / 100, 0)} dos fechados têm resolução antes da primeira resposta.
5. **Não automatizar:** reembolso, cancelamento, perda de dados, acesso/segurança e casos jurídicos vão sempre para um humano, mesmo que o modelo esteja confiante.
""")

    with st.expander("Por que confiar (e onde não confiar) nesses dados"):
        st.markdown(f"""
- **{pct(q['placeholder_product_pct'] / 100, 0)}** das descrições têm o marcador `{{product_purchased}}` não preenchido, e os textos de resolução são frases sem sentido ("{q['resolution_examples'][0]}"). O Dataset 1 é sintético.
- O texto dos clientes não prevê o tipo, o assunto nem a prioridade rotulados (acurácia igual ao acaso; ver *Evidências*). Os rótulos foram sorteados, então **não dá para treinar um classificador de clientes com eles**. Por isso o lado de clientes usa um LLM sem treino (zero-shot), e o classificador treinado fica no lado de TI.
- Conclusões sobre *processo* (fila, prioridade ignorada, falta de instrumentação) valem para o desenho da operação. Já números absolutos de tempo e CSAT não devem ser lidos como desempenho real.
""")


def decision_card(decision: policy.Decision):
    box = st.warning if decision.human_required else st.success
    box(f"**Destino:** {decision.destination}  \n" + "  \n".join(f"• {r}" for r in decision.reasons))


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
    st.title("Triagem ao vivo")
    provider = llm.provider_name()
    st.caption(f"Provedor de LLM: **{provider}**. Qualquer texto funciona; os botões sorteiam tickets reais dos datasets.")
    domain = st.radio("Origem do ticket", ["Cliente (produto)", "Interno (TI)"], horizontal=True)
    tickets, it_sample = load_tickets(), load_it_sample()

    if st.button("🎲 Sortear ticket real"):
        if domain.startswith("Cliente"):
            row = tickets.iloc[random.randrange(len(tickets))]
            st.session_state.update(text=row["Description (display)"], channel=row["Ticket Channel"],
                                    product=row["Product Purchased"], ref=f"Ticket #{row['Ticket ID']}", label=None)
        else:
            row = it_sample.iloc[random.randrange(len(it_sample))]
            st.session_state.update(text=row["text"], channel="", product="", ref="Holdout IT (não visto no treino)", label=row["label"])
        st.session_state.pop("analysis", None)
    text = st.text_area("Texto do ticket", key="text", height=150)
    if st.session_state.get("ref"):
        st.caption(st.session_state["ref"])

    if st.button("Analisar", type="primary", disabled=not text.strip()):
        st.session_state["analysis"] = {"domain": domain, "text": text}
        if domain.startswith("Cliente"):
            try:
                with st.spinner("LLM analisando…"):
                    out = cached_triage(text, st.session_state.get("channel", ""), st.session_state.get("product", ""), provider)
                st.session_state["analysis"]["llm"] = out
                st.session_state["draft"] = out["suggested_reply"]
            except llm.LLMError as exc:
                st.session_state["analysis"]["error"] = str(exc)
    analysis = st.session_state.get("analysis")
    if not analysis or analysis["domain"] != domain:
        return
    text = analysis["text"]

    if domain.startswith("Interno"):
        result, decision = it_router().route(text)
        c1, c2 = st.columns([1, 2])
        c1.metric("Categoria", result["label"], f"{pct(result['confidence'], 0)} de confiança")
        if st.session_state.get("label"):
            c1.caption(f"Rótulo original: **{st.session_state['label']}**")
        c2.bar_chart(pd.DataFrame(result["top3"], columns=["Categoria", "Probabilidade"]).set_index("Categoria"), horizontal=True, height=160)
        decision_card(decision)
        return

    if "error" in analysis:
        st.error(f"LLM indisponível: {analysis['error']}")
        decision_card(policy.decide_customer(None, text))
        return
    out = analysis["llm"]
    decision = policy.decide_customer(out, text)
    c1, c2, c3 = st.columns(3)
    c1.metric("Tipo sugerido", out["ticket_type"])
    c2.metric("Prioridade sugerida", out["priority"])
    c3.metric("Confiança", {"high": "alta", "medium": "média", "low": "baixa"}[out["confidence"]])
    st.markdown(f"**Resumo:** {out['summary_pt']}  \n**Por que essa prioridade:** {out['priority_reason_pt']}")
    if out["missing_information"]:
        st.markdown("**Pedir ao cliente:**\n" + "\n".join(f"- {m}" for m in out["missing_information"]))
    decision_card(decision)
    draft = st.text_area("Rascunho de resposta (edite antes de aprovar)", key="draft", height=140)
    a, b, c = st.columns(3)
    for col, action in [(a, "aprovado"), (b, "editado"), (c, "rejeitado")]:
        if col.button(action.capitalize()):
            log_decision({"at": datetime.now().isoformat(timespec="seconds"), "ref": st.session_state.get("ref", "texto livre"),
                          "action": action, "destination": decision.destination, "llm_type": out["ticket_type"],
                          "llm_priority": out["priority"], "draft": draft})
            st.toast(f"Decisão registrada: {action}")
    st.caption(f"Resposta em {out['_seconds']} s via {out['_provider']}. Nada é enviado ao cliente; a decisão fica em local-state/decisoes.csv.")


def page_queue():
    st.title("Fila priorizada")
    df = load_tickets()
    open_ = df[df["Ticket Status"] != "Closed"].copy()
    open_["Sem 1ª resposta"] = open_["First Response Time"].isna()
    open_["Com risco"] = open_["Risco (regra)"] != ""
    rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    open_ = open_.sort_values(["Com risco", "Sem 1ª resposta", "Ticket Priority"],
                              key=lambda s: s.map(rank) if s.name == "Ticket Priority" else ~s)
    c1, c2, c3 = st.columns(3)
    c1.metric("Tickets parados", num(len(open_)))
    c2.metric("Com risco detectado no texto", num(open_["Com risco"].sum()))
    c3.metric("Sem primeira resposta", num(open_["Sem 1ª resposta"].sum()))
    st.markdown("Ordem: **risco no texto** (perda de dados, dinheiro, acesso, cancelamento, jurídico) → **sem primeira resposta** → prioridade declarada. "
                "Hoje a prioridade declarada não muda nada no fluxo; com a regra, os casos que pedem julgamento humano aparecem primeiro.")
    only_risk = st.toggle("Mostrar só tickets com risco")
    view = open_[open_["Com risco"]] if only_risk else open_
    st.dataframe(view[["Ticket ID", "Risco (regra)", "Sem 1ª resposta", "Ticket Priority", "Ticket Channel", "Ticket Subject", "Description (display)"]]
                 .rename(columns={"Description (display)": "Descrição"}), hide_index=True, width="stretch", height=480)


def page_evidence():
    st.title("Evidências")
    t, g, tr, sig = CLF["test"], CLF["gate"], CLF["transfer_to_customer"], CLF["customer_text_signal"]
    st.subheader("Classificador de TI (Dataset 2)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Acurácia no teste", pct(t["accuracy"]), help=f"{num(t['n'])} tickets nunca vistos no treino.")
    c2.metric("Sem quase-duplicatas", pct(t["strict_subset"]["accuracy"]), help=t["strict_subset"]["rule"])
    c3.metric("Roteados sozinhos", pct(t["auto_coverage"], 0), help=f"Confiança ≥ {g['threshold']:.0%}.")
    c4.metric("Precisão dos roteados", pct(t["auto_precision"]))
    st.markdown(f"""
- Limpeza: {num(CLF['cleaning']['raw_rows'])} textos, {num(CLF['cleaning']['exact_duplicates_removed'])} duplicatas exatas e {num(CLF['cleaning']['conflicting_texts_removed'])} rótulos conflitantes após normalização. O risco real de vazamento são quase-duplicatas, que o teste estrito exclui ({num(t['strict_subset']['n'])} de {num(t['n'])} textos). Divisão: {num(CLF['splits']['train'])} treino, {num(CLF['splits']['calibration'])} calibração, {num(CLF['splits']['test'])} teste.
- Modelo: {CLF['chosen']}, com probabilidades calibradas. O limiar de {g['threshold']:.0%} foi escolhido na calibração para dar ≥95% de precisão. No teste: {pct(t['auto_precision'])} de precisão em {pct(t['auto_coverage'], 0)} dos tickets; os outros {pct(1 - t['auto_coverage'], 0)} vão para triagem humana.
- Linha de base (classe majoritária): {pct(t['majority_baseline_accuracy'])}.
""")
    cm = pd.DataFrame(t["confusion_matrix"], index=t["labels"], columns=t["labels"]).reset_index(names="Real").melt("Real", var_name="Previsto", value_name="n")
    st.altair_chart(alt.Chart(cm).mark_rect().encode(x="Previsto:N", y="Real:N", color=alt.Color("n:Q", scale=alt.Scale(type="log")), tooltip=["Real", "Previsto", "n"]).properties(height=320), width="stretch")
    with st.expander("Erros mais confiantes do modelo"):
        st.dataframe(pd.read_csv(OUT / "classifier_errors.csv").head(30), hide_index=True, width="stretch")

    st.subheader("Cruzamento dos dois datasets")
    st.markdown(f"""
- **O classificador de TI não serve para clientes, e a confiança não avisa.** Aplicado aos {num(tr['n'])} tickets de clientes, ele passaria {pct(tr['customer_auto_coverage'], 0)} deles com confiança acima do limiar, em categorias de TI que não fazem sentido. A confiança não detecta texto de outro domínio. **Decisão:** um roteador por domínio, escolhido pela origem do ticket.
- **O texto dos clientes não carrega os rótulos.** Prever a partir da descrição: tipo {pct(sig['Ticket Type']['accuracy'])} (acaso {pct(sig['Ticket Type']['chance'])}), assunto {pct(sig['Ticket Subject']['accuracy'])} (acaso {pct(sig['Ticket Subject']['chance'])}), prioridade {pct(sig['Ticket Priority']['accuracy'])} (acaso {pct(sig['Ticket Priority']['chance'])}). **Decisão:** no lado de clientes, LLM sem treino (zero-shot), avaliado por verificações objetivas e não por esses rótulos.
""")

    st.subheader("Triagem por LLM (Dataset 1)")
    if not EVAL:
        st.info("Rode `python analysis/eval_llm.py` para gerar a avaliação.")
        return
    s = EVAL["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tickets avaliados", f"{s['succeeded']}/{s['sample']}", help=f"Amostra aleatória, semente {s['seed']}.")
    c2.metric("Promessas proibidas", len(s["forbidden_promises"]), help="Rascunhos que prometem reembolso, cancelamento, crédito ou recuperação.")
    c3.metric("Risco perdido pelo LLM", len(s["rule_risk_missed_by_llm"]), help="Casos pegos pela regra de segurança, que cobre o LLM.")
    c4.metric("Exigiram humano", pct(s["human_required_pct"] / 100, 0))
    st.markdown(f"""
- Mensagem de erro em branco detectada e pedida ao cliente: **{s['error_placeholder_flagged_missing']} de {s['error_placeholder_tickets']}** tickets com `{{error_message}}`.
- Concordância com os rótulos originais: tipo {pct(s['type_agreement_with_label'], 0)}, prioridade {pct(s['priority_agreement_with_label'], 0)}. Os valores ficam perto do acaso, como esperado para rótulos sorteados; não é uma medida de acerto.
- Latência mediana: {str(s['median_seconds']).replace('.', ',')} s via {s['provider']}.
""")
    rows = [r for r in EVAL["rows"] if r["llm"]]
    table = pd.DataFrame([{"Ticket": r["ticket_id"], "Tipo LLM": r["llm"]["ticket_type"], "Prioridade LLM": r["llm"]["priority"],
                           "Riscos": ", ".join(r["llm"]["risk_flags"]), "Destino": r["decision"]["destination"],
                           "Resumo": r["llm"]["summary_pt"], "Rascunho": r["llm"]["suggested_reply"]} for r in rows])
    st.dataframe(table, hide_index=True, width="stretch", height=360)


def page_roi():
    st.title("ROI: horas recuperáveis")
    st.markdown("O dataset não registra o esforço do agente, por isso os minutos abaixo são **premissas**, que o piloto em sombra vai medir. "
                "Ajuste e veja o efeito. O volume vem do enunciado.")
    base = roi.Assumptions()
    c1, c2 = st.columns(2)
    with c1:
        tickets = st.number_input("Tickets por ano", 1000, 500_000, base.tickets_per_year, step=1000)
        t0 = st.slider("Triagem hoje (min)", 0.5, 10.0, base.triage_min_today, 0.5)
        t1 = st.slider("Triagem com IA (min)", 0.0, 10.0, base.triage_min_with_ai, 0.1)
        r0 = st.slider("1ª resposta hoje (min)", 1.0, 20.0, base.reply_min_today, 0.5)
        r1 = st.slider("1ª resposta com rascunho (min)", 0.5, 20.0, base.reply_min_with_ai, 0.5)
    with c2:
        cyc = st.slider("Tickets sem ida e volta extra (%)", 0.0, 50.0, base.extra_cycle_avoided_pct, 1.0)
        cyc_min = st.slider("Minutos por ida e volta", 1.0, 15.0, base.extra_cycle_min, 0.5)
        cost = st.number_input("Custo-hora carregado (R$)", 10.0, 300.0, base.cost_per_hour_brl, 5.0)
        llm_cost = st.number_input("Custo de LLM por ticket (US$)", 0.0, 0.5, base.llm_cost_usd_per_ticket, 0.005, format="%.3f")
    r = roi.estimate(roi.Assumptions(int(tickets), t0, t1, r0, r1, cyc, cyc_min, cost, llm_cost))
    m1, m2, m3 = st.columns(3)
    m1.metric("Horas por mês", num(r["total_hours_month"]))
    m2.metric("Equivalente em pessoas", str(round(r["fte"], 1)).replace(".", ","))
    m3.metric("Valor líquido por ano", f"R$ {num(r['net_value_brl_year'])}", help=f"Já desconta R$ {num(r['llm_cost_brl_year'])} de LLM.")
    st.bar_chart(pd.Series(r["hours_per_year"], name="horas/ano") / 12, horizontal=True)
    st.subheader("Cenários")
    st.dataframe(pd.DataFrame([{"Cenário": k, "h/mês": round(v["total_hours_month"]), "Pessoas": round(v["fte"], 1), "R$/ano líquido": round(v["net_value_brl_year"])}
                               for k, v in ((k, roi.estimate(a)) for k, a in roi.SCENARIOS.items())]), hide_index=True)
    st.caption("Capacidade liberada não vira caixa automaticamente: ela vai para a fila parada. O piloto em sombra (IA sugere, humano decide, nada é enviado) mede os minutos reais antes de qualquer meta.")


