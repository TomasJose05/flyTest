# flyTest

Experimentos con el conectoma de *Drosophila* usando la API de [neuPrint](https://neuprint.janelia.org).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Copia `.env.example` a `.env` y pon tu token de neuPrint:

```bash
cp .env.example .env
```

`.env` esta en `.gitignore` y nunca se sube al repo.
