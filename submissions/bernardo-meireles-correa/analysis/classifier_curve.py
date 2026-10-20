"""Por que o classificador de TI não chega a 99%: curva acerto x cobertura e ruído dos rótulos.

Usa a mesma limpeza, o mesmo split e o modelo salvo por train.py. O limiar de cada meta é escolhido
na calibração e medido no teste. O ruído é estimado pelos textos do teste quase idênticos (cosseno
>= 0,9) a um texto do treino: quando o rótulo difere, nem um modelo perfeito acertaria os dois.
Uso: python analysis/classifier_curve.py [--source-dir data/raw]
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

from common import DEFAULT_SOURCE, MODELS, OUTPUTS, SEED, load_it
from train import normalize

TARGETS = (0.95, 0.97, 0.98, 0.99)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    args = ap.parse_args()

    it, _ = load_it(args.source_dir)
    it["normalized"] = it["Document"].map(normalize)
    per_text = it.groupby("normalized")["Topic_group"].nunique()
    clean = it[~it["normalized"].isin(set(per_text[per_text > 1].index)) & (it["normalized"].str.len() > 0)].drop_duplicates("normalized")
    X, y = clean["Document"].astype(str).to_numpy(), clean["Topic_group"].to_numpy()
    X_rest, X_test, y_rest, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=SEED)
    X_train, X_cal, y_train, y_cal = train_test_split(X_rest, y_rest, test_size=0.125, stratify=y_rest, random_state=SEED)

    model = joblib.load(MODELS / "it_classifier.joblib")["model"]

    def scored(Xs):
        proba = model.predict_proba(Xs)
        return model.classes_[proba.argmax(1)], proba.max(1)

    pred_cal, conf_cal = scored(X_cal)
    pred_test, conf_test = scored(X_test)
    curve = []
    for target in TARGETS:
        t = next((t for t in np.arange(0.30, 0.996, 0.005)  # mesma grade e mínimo do train.py
                  if (conf_cal >= t).sum() >= 200 and (pred_cal[conf_cal >= t] == y_cal[conf_cal >= t]).mean() >= target), None)
        if t is None:
            continue
        auto = conf_test >= t
        curve.append({"target": target, "threshold": round(float(t), 4), "test_coverage": float(auto.mean()),
                      "test_precision": float((pred_test[auto] == y_test[auto]).mean())})

    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit(X_train)
    A, B = vec.transform(X_test), vec.transform(X_train)
    best_sim, best_label = np.zeros(len(X_test)), np.empty(len(X_test), dtype=object)
    for i in range(0, len(X_test), 2000):
        S = (A[i:i + 2000] @ B.T).toarray()
        j = S.argmax(1)
        best_sim[i:i + 2000], best_label[i:i + 2000] = S[np.arange(len(j)), j], y_train[j]
    near = best_sim >= 0.9
    noise = {"near_duplicates": int(near.sum()), "other_label_share": float((best_label[near] != y_test[near]).mean()),
             "model_accuracy_on_near_duplicates": float((pred_test[near] == y_test[near]).mean())}

    out = {"test_accuracy": float((pred_test == y_test).mean()), "curve": curve, "label_noise": noise}
    (OUTPUTS / "classifier_curve.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
