"""Leitura das fontes e caminhos compartilhados pelos scripts de análise."""
import hashlib
import io
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
MODELS = ROOT / "models"
DEFAULT_SOURCE = ROOT / "data" / "raw"

CUSTOMER_ZIP = "customer-support-ticket-dataset.zip"
IT_ZIP = "it-service-ticket-classification-dataset.zip"
SEED = 42


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_zip_csv(source: Path, name: str) -> tuple[pd.DataFrame, dict]:
    path = source / name
    if not path.exists():
        raise SystemExit(f"Fonte não encontrada: {path}. Baixe os ZIPs do Kaggle para {source} (ver data/README.md).")
    with zipfile.ZipFile(path) as z:
        member = next(n for n in z.namelist() if n.endswith(".csv"))
        df = pd.read_csv(io.BytesIO(z.read(member)))
    return df, {"zip": name, "member": member, "sha256": sha256(path), "rows": len(df)}


def load_customer(source: Path) -> tuple[pd.DataFrame, dict]:
    df, meta = read_zip_csv(source, CUSTOMER_ZIP)
    df["First Response Time"] = pd.to_datetime(df["First Response Time"])
    df["Time to Resolution"] = pd.to_datetime(df["Time to Resolution"])
    return df, meta


def load_it(source: Path) -> tuple[pd.DataFrame, dict]:
    return read_zip_csv(source, IT_ZIP)
