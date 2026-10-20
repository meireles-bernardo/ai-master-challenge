# Dados de origem

O app roda com o que já está em `outputs/` e `models/`. Os ZIPs só são necessários para reproduzir a análise.

Baixe do Kaggle (licença CC0) e salve nesta pasta, em `data/raw/`, sem descompactar:

| Arquivo | Fonte | SHA-256 |
|---|---|---|
| `customer-support-ticket-dataset.zip` | https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset | `99e848c33601eb8863d00f1b8304faa7d1336243b985c2e3ceabe35806149df8` |
| `it-service-ticket-classification-dataset.zip` | https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset | `1e6c2508dba84f737ef30f589c2e4f7b2b27a4bbec753e6b5c84183a5f91ed4f` |

Depois rode, da raiz: `python analysis/diagnose.py`, `python analysis/train.py` e (com um LLM configurado) `python analysis/eval_llm.py`.

`outputs/customer_tickets.csv.gz` é o Dataset 1 sem nome e e-mail dos clientes.
