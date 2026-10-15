"""Verificações da entrega: links, números citados, dados da apresentação, segredos e sintaxe.

Uso: python tests/check_delivery.py   (sai com código 1 se algo falhar)
"""
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
failures = []


def check(ok: bool, msg: str):
    print(("ok  " if ok else "ERRO ") + msg)
    if not ok:
        failures.append(msg)


def tracked(pattern: str) -> list[Path]:
    files = subprocess.run(["git", "ls-files", pattern], cwd=ROOT, capture_output=True, text=True).stdout.split()
    return [ROOT / f for f in files] or list(ROOT.rglob(pattern))


# 1. Links relativos nos Markdown versionados
for md in tracked("*.md"):
    text = md.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"(https?:|mailto:|#)", target):
            continue
        path = (md.parent / target.split("#")[0]).resolve()
        check(path.exists(), f"link em {md.relative_to(ROOT)} -> {target}")

# 2. Números do README batem com os resultados
diag = json.loads((OUT / "diagnostico.json").read_text(encoding="utf-8"))
clf = json.loads((OUT / "classifier_metrics.json").read_text(encoding="utf-8"))
llm = json.loads((OUT / "llm_eval.json").read_text(encoding="utf-8"))["summary"]
rev = json.loads((OUT / "revisao_resumo.json").read_text(encoding="utf-8"))
readme = (ROOT / "README.md").read_text(encoding="utf-8")
br = lambda x, d=1: f"{x * 100:.{d}f}".replace(".", ",") + "%"
fmt = lambda n: f"{n:,}".replace(",", ".")
expected = {
    "total de tickets": fmt(diag["backlog"]["total"]),
    "não fechados": fmt(diag["backlog"]["not_closed"]),
    "sem primeira resposta": fmt(diag["backlog"]["open_without_first_response"]),
    "críticos parados": fmt(diag["backlog"]["critical_not_closed"]),
    "acurácia do classificador": br(clf["test"]["accuracy"]),
    "acurácia sem quase-duplicatas": br(clf["test"]["strict_subset"]["accuracy"]),
    "precisão dos roteados": br(clf["test"]["auto_precision"]),
    "tickets avaliados pelo LLM": f"{llm['succeeded']}/{llm['sample']}",
    "transferência para clientes": br(clf["transfer_to_customer"]["customer_auto_coverage"], 0),
}
for name, value in expected.items():
    check(value in readme, f"README cita {name} = {value}")
check(llm["forbidden_promises"] == [] and "0 promessas proibidas" in readme, "README: 0 promessas proibidas confere com llm_eval.json")
check(rev["discordancias_de_ambos"]["prioridade"] == [4716, 2128], "revisão: os dois revisores discordam da prioridade de 4716 e 2128")

# 3. presentation/data.js reflete os resultados atuais
before = (ROOT / "presentation" / "data.js").read_text(encoding="utf-8")
subprocess.run([sys.executable, str(ROOT / "analysis" / "build_presentation.py")], cwd=ROOT / "analysis", check=True, capture_output=True)
check((ROOT / "presentation" / "data.js").read_text(encoding="utf-8") == before, "presentation/data.js atualizado em relação a outputs/")

# 4. Nenhum segredo versionado
secret = re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}|ANTHROPIC_API_KEY=sk-|AKIA[0-9A-Z]{16}")
# Os dois arquivos que contêm o próprio padrão de busca ficam de fora.
SKIP = {ROOT / ".github" / "workflows" / "ci.yml", Path(__file__).resolve()}
leaks = [str(f.relative_to(ROOT)) for f in tracked("*") if f.is_file() and f.resolve() not in SKIP and f.suffix not in {".joblib", ".gz", ".png"}
         and secret.search(f.read_text(encoding="utf-8", errors="ignore"))]
check(not leaks, f"nenhum segredo versionado {leaks or ''}")
check(not (ROOT / ".env").exists() or ".env" in (ROOT / ".gitignore").read_text(encoding="utf-8"), ".env fora do Git")

# 5. Todo o Python compila
for py in tracked("*.py"):
    try:
        py_compile.compile(str(py), doraise=True)
    except py_compile.PyCompileError as exc:
        check(False, f"sintaxe {py.relative_to(ROOT)}: {exc.msg}")
check(True, f"{len(tracked('*.py'))} arquivos Python compilam")

print(f"\n{len(failures)} falha(s)")
sys.exit(1 if failures else 0)
