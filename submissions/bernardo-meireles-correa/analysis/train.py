"""Classificador de tickets IT (Dataset 2) e teste de transferência para o Dataset 1.

1. Normaliza textos, remove duplicatas exatas e grupos com rótulos conflitantes.
2. Divide em treino (70%), calibração (10%) e teste (20%), estratificado; o teste só é lido no fim.
3. Escolhe a representação pela macro-F1 na calibração e o limiar de confiança que garante
   precisão >= 95% na calibração. Esse limiar decide o que vai sozinho para a fila e o que vai para um humano.
4. Mede no teste, inclusive no subconjunto sem quase-duplicatas do treino.
5. Aplica o modelo aos tickets de clientes para medir quanto ele se abstém fora do domínio.
Uso: python analysis/train.py [--source-dir data/raw]
"""
import argparse
import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from common import DEFAULT_SOURCE, MODELS, OUTPUTS, SEED, load_customer, load_it

TARGET_PRECISION = 0.95


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower()))


def candidates() -> dict:
    # Vocabulário limitado para o modelo caber no repositório (~5 MB); uma versão com
    # n-gramas de caracteres foi testada e não superou a de palavras na calibração.
    word = lambda: TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=100_000)
    svc = lambda c: CalibratedClassifierCV(LinearSVC(C=c), cv=3, method="sigmoid", ensemble=False)
    return {f"TF-IDF (palavras e bigramas) + SVM linear, C={c}": Pipeline([("tfidf", word()), ("clf", svc(c))]) for c in (0.25, 1.0)}


def choose_threshold(proba: np.ndarray, y: np.ndarray, classes: np.ndarray) -> dict:
    conf, pred = proba.max(axis=1), classes[proba.argmax(axis=1)]
    best = {"threshold": 1.0, "coverage": 0.0, "precision": None}
    for t in np.arange(0.30, 0.996, 0.005):
        mask = conf >= t
        if mask.sum() < 200:
            break
        precision = float((pred[mask] == y[mask]).mean())
        if precision >= TARGET_PRECISION:
            best = {"threshold": round(float(t), 3), "coverage": float(mask.mean()), "precision": precision}
            break
    return best


def evaluate(model, X, y, threshold) -> dict:
    proba = model.predict_proba(X)
    classes = model.classes_
    pred, conf = classes[proba.argmax(axis=1)], proba.max(axis=1)
    auto = conf >= threshold
    return {
        "n": len(y),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "auto_coverage": float(auto.mean()),
        "auto_precision": float((pred[auto] == y[auto]).mean()) if auto.any() else None,
        "human_queue_accuracy": float((pred[~auto] == y[~auto]).mean()) if (~auto).any() else None,
        "per_class": classification_report(y, pred, output_dict=True, zero_division=0),
        "labels": classes.tolist(),
        "confusion_matrix": confusion_matrix(y, pred, labels=classes).tolist(),
    }, pred, conf


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    args = ap.parse_args()
    OUTPUTS.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)

    it, it_meta = load_it(args.source_dir)
    it["normalized"] = it["Document"].map(normalize)
    labels_per_text = it.groupby("normalized")["Topic_group"].nunique()
    conflicting = set(labels_per_text[labels_per_text > 1].index)
    clean = it[~it["normalized"].isin(conflicting) & (it["normalized"].str.len() > 0)].drop_duplicates("normalized")
    cleaning = {
        "raw_rows": len(it),
        "conflicting_texts_removed": len(conflicting),
        "rows_in_conflicting_groups": int(it["normalized"].isin(conflicting).sum()),
        "exact_duplicates_removed": int(len(it) - it["normalized"].isin(conflicting).sum() - len(clean)),
        "clean_rows": len(clean),
    }

    X, y = clean["Document"].astype(str).to_numpy(), clean["Topic_group"].to_numpy()
    X_rest, X_test, y_rest, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=SEED)
    X_train, X_cal, y_train, y_cal = train_test_split(X_rest, y_rest, test_size=0.125, stratify=y_rest, random_state=SEED)

    selection = {}
    fitted = {}
    for name, model in candidates().items():
        model.fit(X_train, y_train)
        selection[name] = float(f1_score(y_cal, model.predict(X_cal), average="macro"))
        fitted[name] = model
        print(f"{name}: macro-F1 calibração = {selection[name]:.3f}", flush=True)
    chosen = max(selection, key=selection.get)
    model = fitted[chosen]
    gate = choose_threshold(model.predict_proba(X_cal), y_cal, model.classes_)

    test, pred, conf = evaluate(model, X_test, y_test, gate["threshold"])

    # Quase-duplicatas: similaridade de cosseno do teste com o treino no espaço de palavras.
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit(X_train)
    A, B = vec.transform(X_test), vec.transform(X_train)
    max_sim = np.concatenate([(A[i:i + 2000] @ B.T).max(axis=1).toarray().ravel() for i in range(0, A.shape[0], 2000)])
    strict = max_sim < 0.8
    test["strict_subset"] = {
        "rule": "teste sem nenhum texto de treino com cosseno >= 0,8",
        "n": int(strict.sum()),
        "accuracy": float((pred[strict] == y_test[strict]).mean()),
        "macro_f1": float(f1_score(y_test[strict], pred[strict], average="macro")),
    }

    # Linha de base com LLM ausente: classe majoritária, para dar escala à acurácia.
    majority = pd.Series(y_train).mode()[0]
    test["majority_baseline_accuracy"] = float((y_test == majority).mean())

    errors = pd.DataFrame({"text": X_test, "label": y_test, "prediction": pred, "confidence": conf})
    errors = errors[errors.label != errors.prediction].sort_values("confidence", ascending=False)

    # Transferência: o modelo de IT recebendo tickets de clientes (outro domínio).
    customer, _ = load_customer(args.source_dir)
    cust_text = [d.replace("{product_purchased}", p) for d, p in zip(customer["Ticket Description"], customer["Product Purchased"])]
    cust_proba = model.predict_proba(cust_text)
    cust_conf = cust_proba.max(axis=1)
    transfer = {
        "n": len(cust_text),
        "it_test_auto_coverage": test["auto_coverage"],
        "customer_auto_coverage": float((cust_conf >= gate["threshold"]).mean()),
        "customer_median_confidence": float(np.median(cust_conf)),
        "it_test_median_confidence": float(np.median(conf)),
        "customer_predicted_distribution": pd.Series(model.classes_[cust_proba.argmax(axis=1)]).value_counts().to_dict(),
    }

    # O texto dos clientes carrega sinal sobre o tipo/assunto? (5-fold, regressão logística)
    signal = {}
    for target in ["Ticket Type", "Ticket Subject", "Ticket Priority"]:
        pipe = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)), ("clf", LogisticRegression(max_iter=2000))])
        acc = cross_val_score(pipe, cust_text, customer[target], cv=5, scoring="accuracy")
        signal[target] = {"accuracy": float(acc.mean()), "chance": float(customer[target].value_counts(normalize=True).max()), "classes": int(customer[target].nunique())}

    joblib.dump({"model": model, "threshold": gate["threshold"], "name": chosen}, MODELS / "it_classifier.joblib", compress=3)
    metrics = {
        "source": it_meta, "cleaning": cleaning,
        "splits": {"train": len(X_train), "calibration": len(X_cal), "test": len(X_test)},
        "selection_macro_f1_calibration": selection, "chosen": chosen,
        "gate": {**gate, "target_precision": TARGET_PRECISION},
        "test": test, "transfer_to_customer": transfer, "customer_text_signal": signal,
    }
    (OUTPUTS / "classifier_metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    errors.head(300).to_csv(OUTPUTS / "classifier_errors.csv", index=False)
    sample = pd.DataFrame({"text": X_test, "label": y_test}).sample(400, random_state=SEED)
    sample.to_csv(OUTPUTS / "it_holdout_sample.csv", index=False)

    print(json.dumps({"chosen": chosen, "gate": gate, "accuracy": test["accuracy"], "macro_f1": test["macro_f1"],
                      "auto": [test["auto_coverage"], test["auto_precision"]], "strict": test["strict_subset"],
                      "transfer": {k: transfer[k] for k in ["customer_auto_coverage", "customer_median_confidence", "it_test_median_confidence"]},
                      "signal": signal}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
