# flyTest

Conectoma real de *Drosophila* (**MaleCNS v1.0**, via [neuPrint](https://neuprint.janelia.org))
para, mas adelante, mover una mosca simulada.

Comportamiento objetivo: **geotaxis negativa** — tras un golpe, la mosca trepa hacia arriba.

## Estado

| Paso | Que es | Estado |
|---|---|---|
| 0 | `explore_circuit.py` — buscar si existe un circuito pequeno e identificable | hecho -> [`circuit_candidates.md`](circuit_candidates.md) |
| 1 | Conectividad del circuito elegido | pendiente |
| 2 | Simulacion de neuronas spiking | pendiente |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copia `.env.example` a `.env` y pon tu token de neuPrint (Account -> Auth Token en la web).
`.env` esta en `.gitignore`: el token nunca se sube.

```bash
python explore_circuit.py
```

Imprime los datasets disponibles, resume los candidatos por consola y regenera
`circuit_candidates.md`.

### Nota Windows/Norton

Norton intercepta HTTPS en esta maquina, asi que `pip` y `requests` fallan con
`CERTIFICATE_VERIFY_FAILED`. El script llama a `truststore.inject_into_ssl()` para usar el
almacen de certificados de Windows. Si `pip install` falla, exporta el almacen a un PEM y
usa `PIP_CERT=<ruta al pem>`.
