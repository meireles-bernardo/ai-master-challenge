"""Teste de fumaça do app inteiro, sem navegador (Streamlit AppTest).

Uso: python tests/test_app.py           (com LLM_PROVIDER=off pula a chamada ao LLM)
"""
import os
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app" / "app.py")


def fresh() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    return at


def main() -> None:
    at = fresh()
    assert at.title[0].value == "Painel da operação", at.title[0].value
    for page in ["fila", "validacao"]:
        at.switch_page(f"views/{page}.py").run()
        assert not at.exception, (page, at.exception)
        print(f"ok  {page}: {at.title[0].value}")

    if os.environ.get("ENABLE_REVIEW") == "1":
        at.switch_page("views/validacao.py").run()
        next(b for b in at.button if b.label == "Salvar revisão").click().run()  # salva a revisão do primeiro ticket com os valores padrão
        assert not at.exception, at.exception
        assert Path(os.environ["REVIEW_FILE"]).exists(), "revisão não foi salva"
        print("ok  revisão humana salva em", os.environ["REVIEW_FILE"])

    at.switch_page("views/triagem.py").run()
    at.radio[0].set_value("Interno (TI)").run()
    at.button[0].click().run()
    assert at.text_area[0].value, "sorteio não preencheu o texto"
    at.button[1].click().run()
    assert not at.exception, at.exception
    label = next(m for m in at.metric if m.label == "Categoria sugerida")
    assert any("este ticket" in h.proto.body for h in at.get("html")), "mapa sem o caminho do ticket"
    print(f"ok  triagem TI: {label.value} ({label.delta}), caminho aceso no mapa")

    at.radio[0].set_value("Cliente").run()
    at.button[0].click().run()
    at.button[1].click().run()
    assert not at.exception, at.exception
    panel = next(e for e in at.expander if e.label.startswith("Contexto recuperado"))
    assert any("Cadastro: compra" in m.value for m in panel.markdown), "painel sem dados do cadastro"
    print("ok  contexto recuperado:", [m.value.splitlines()[0][:60] for m in panel.markdown][:2])
    if os.environ.get("LLM_PROVIDER", "").lower() == "off":
        print("--  triagem de cliente com LLM pulada (LLM_PROVIDER=off)")
        return
    if at.error:
        sys.exit(f"LLM falhou: {at.error[0].value}")
    bodies = [h.proto.body for h in at.get("html")]
    assert any('class="decision' in b for b in bodies) and any("este ticket" in b for b in bodies), "sem destino ou caminho no mapa"
    print("ok  triagem cliente com destino e caminho no mapa")
    print("    rascunho:", at.text_area[1].value[:140])
    next(b for b in at.button if b.label == "Aprovar").click().run()
    assert not at.exception, at.exception
    assert (ROOT / "local-state" / "decisoes.csv").exists()
    print("ok  decisão registrada em local-state/decisoes.csv")


if __name__ == "__main__":
    main()
