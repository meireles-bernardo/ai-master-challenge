"""Diagnóstico operacional do Dataset 1 (Customer Support Tickets).

Responde às três perguntas do diretor com testes estatísticos, não só médias:
onde o fluxo trava, o que explica a satisfação e quanto tempo está parado.
Uso: python analysis/diagnose.py [--source-dir data/raw]
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, chisquare, kruskal, spearmanr

from common import DEFAULT_SOURCE, OUTPUTS, load_customer

DIMENSIONS = ["Ticket Channel", "Ticket Priority", "Ticket Type"]


def cramers_v(table: pd.DataFrame) -> float:
    chi2 = chi2_contingency(table)[0]
    n = table.to_numpy().sum()
    return float(np.sqrt(chi2 / (n * (min(table.shape) - 1))))


def backlog(df: pd.DataFrame) -> dict:
    status = df["Ticket Status"].value_counts().to_dict()
    by_dim = {}
    for col in DIMENSIONS:
        table = pd.crosstab(df[col], df["Ticket Status"])
        share = (table.div(table.sum(axis=1), axis=0) * 100).round(1)
        by_dim[col] = {
            "share_pct": share.to_dict(orient="index"),
            "chi2_p": float(chi2_contingency(table)[1]),
            "cramers_v": cramers_v(table),
        }
    critical = df[df["Ticket Priority"] == "Critical"]
    return {
        "total": len(df),
        "status": status,
        "not_closed": int((df["Ticket Status"] != "Closed").sum()),
        "open_without_first_response": int(df["First Response Time"].isna().sum()),
        "critical_not_closed": int((critical["Ticket Status"] != "Closed").sum()),
        "critical_total": len(critical),
        "by_dimension": by_dim,
    }


def resolution_time(df: pd.DataFrame) -> dict:
    closed = df[df["Ticket Status"] == "Closed"].copy()
    closed["hours"] = (closed["Time to Resolution"] - closed["First Response Time"]).dt.total_seconds() / 3600
    valid = closed[closed["hours"] >= 0]
    window = pd.concat([df["First Response Time"], df["Time to Resolution"]]).dropna()
    by_dim = {}
    for col in DIMENSIONS:
        groups = [g["hours"].to_numpy() for _, g in valid.groupby(col)]
        by_dim[col] = {
            "median_hours": valid.groupby(col)["hours"].median().round(2).to_dict(),
            "kruskal_p": float(kruskal(*groups).pvalue),
        }
    combo = valid.groupby(DIMENSIONS)["hours"].agg(["median", "count"]).reset_index()
    combo_p = float(kruskal(*[g["hours"].to_numpy() for _, g in valid.groupby(DIMENSIONS)]).pvalue)
    combo = combo.sort_values("median", ascending=False)
    # Teste de permutação: quão "ruim" seria a pior combinação se os rótulos fossem embaralhados?
    rng = np.random.default_rng(42)
    keys = valid[DIMENSIONS].astype(str).agg("|".join, axis=1).to_numpy()
    hours = valid["hours"].to_numpy()
    observed_worst = combo["median"].iloc[0]
    null_worst = []
    for _ in range(500):
        shuffled = pd.Series(rng.permutation(hours)).groupby(keys).median()
        null_worst.append(shuffled.max())
    return {
        "closed": len(closed),
        "valid_pairs": len(valid),
        "inverted_pairs": int((closed["hours"] < 0).sum()),
        "inverted_pct": round(float((closed["hours"] < 0).mean() * 100), 1),
        "median_hours": round(float(valid["hours"].median()), 2),
        "timestamp_window": [str(window.min()), str(window.max())],
        "timestamp_window_hours": round((window.max() - window.min()).total_seconds() / 3600, 1),
        "by_dimension": by_dim,
        "combinations_n": len(combo),
        "combinations_kruskal_p": combo_p,
        "worst_combinations": combo.head(5).round(2).to_dict(orient="records"),
        "best_combinations": combo.tail(5).round(2).to_dict(orient="records"),
        "worst_median_permutation_p": float(np.mean(np.array(null_worst) >= observed_worst)),
        "combination_sizes": [int(combo["count"].min()), int(combo["count"].max())],
    }


def satisfaction(df: pd.DataFrame) -> dict:
    closed = df[df["Ticket Status"] == "Closed"].copy()
    rating = closed["Customer Satisfaction Rating"]
    tests = []
    for col in DIMENSIONS + ["Ticket Subject", "Product Purchased", "Customer Gender"]:
        table = pd.crosstab(closed[col], rating)
        tests.append({"variable": col, "test": "qui-quadrado", "p": float(chi2_contingency(table)[1]), "effect": cramers_v(table), "effect_name": "V de Cramér"})
    closed["hours"] = (closed["Time to Resolution"] - closed["First Response Time"]).dt.total_seconds() / 3600
    valid = closed[closed["hours"] >= 0]
    for name, x, y in [
        ("Idade do cliente", closed["Customer Age"], rating),
        ("Horas entre 1ª resposta e resolução (pares válidos)", valid["hours"], valid["Customer Satisfaction Rating"]),
    ]:
        rho, p = spearmanr(x, y)
        tests.append({"variable": name, "test": "Spearman", "p": float(p), "effect": float(rho), "effect_name": "ρ"})
    return {
        "rated": len(closed),
        "mean": round(float(rating.mean()), 2),
        "distribution": {str(int(k)): int(v) for k, v in rating.value_counts().sort_index().items()},
        "uniform_chisquare_p": float(chisquare(rating.value_counts().sort_index().to_numpy()).pvalue),
        "low_ratings": int((rating <= 2).sum()),
        "tests": tests,
        "min_p": min(t["p"] for t in tests),
    }


def text_quality(df: pd.DataFrame) -> dict:
    desc = df["Ticket Description"].astype(str)
    res = df["Resolution"].dropna().astype(str)
    return {
        "placeholder_product_pct": round(float(desc.str.contains("{product_purchased}", regex=False).mean() * 100), 1),
        "placeholder_error_message": int(desc.str.contains("{error_message}", regex=False).sum()),
        "resolution_filled": len(res),
        "resolution_word_range": [int(res.str.split().str.len().min()), int(res.str.split().str.len().max())],
        "resolution_examples": res.sample(3, random_state=1).tolist(),
    }


def slim_tickets(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela sem nome/e-mail para o protótipo; o resto é a fonte original (CC0)."""
    keep = ["Ticket ID", "Product Purchased", "Date of Purchase", "Ticket Type", "Ticket Subject", "Ticket Description",
            "Ticket Status", "Ticket Priority", "Ticket Channel", "First Response Time",
            "Time to Resolution", "Customer Satisfaction Rating"]
    out = df[keep].copy()
    # Substitui o placeholder pelo produto para leitura; o original segue disponível na fonte.
    out["Description (display)"] = [re.sub(r"\{product_purchased\}", p, d) for d, p in zip(out["Ticket Description"], out["Product Purchased"])]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    args = ap.parse_args()
    OUTPUTS.mkdir(exist_ok=True)
    df, meta = load_customer(args.source_dir)
    result = {
        "source": meta,
        "backlog": backlog(df),
        "resolution_time": resolution_time(df),
        "satisfaction": satisfaction(df),
        "text_quality": text_quality(df),
    }
    (OUTPUTS / "diagnostico.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    slim_tickets(df).to_csv(OUTPUTS / "customer_tickets.csv.gz", index=False)
    b, r, s = result["backlog"], result["resolution_time"], result["satisfaction"]
    print(f"Não fechados: {b['not_closed']}/{b['total']} | sem 1ª resposta: {b['open_without_first_response']}")
    print(f"Tempo: mediana {r['median_hours']} h em {r['valid_pairs']} pares válidos; combinações p={r['combinations_kruskal_p']:.3f}; pior combinação vs acaso p={r['worst_median_permutation_p']:.3f}")
    print(f"CSAT: média {s['mean']}, distribuição {s['distribution']}, menor p entre variáveis={s['min_p']:.3f}")


if __name__ == "__main__":
    main()
