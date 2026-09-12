"""
explore_circuit.py - PASO 0 (solo exploracion) del proyecto "startle-induced climbing".

Objetivo: averiguar si en el conectoma MaleCNS v1.0 existe un circuito PEQUENO e
IDENTIFICABLE para la geotaxis negativa (la mosca, tras un golpe, trepa hacia arriba).
NO simula nada, NO baja tablas de conectividad: solo metadatos de neuronas.

Mapa mental del circuito, en 3 eslabones (misma logica que un pipeline web:
input -> controller -> output):

  1. SENSORES (mecanosensoriales): la mosca "siente" el golpe y donde esta el suelo.
     Cerdas (bristles) = tacto; sensilla campaniforme = fuerza/carga en la pata;
     organo cordotonal = estiramiento/vibracion; Johnston's organ (wind_gravity) =
     antena, detecta gravedad y viento. Estos son la ENTRADA del reflejo.
  2. NEURONAS DESCENDENTES (DN): ~1300 neuronas que bajan del cerebro al VNC. Son el
     cuello de botella del sistema: TODA orden motora pasa por aqui. Son el "comando".
  3. MOTONEURONAS DE PATA (VNC): la salida final que contrae musculos de las 6 patas.

Por que importa: si el eslabon 2 son pares bilaterales de 2 neuronas, el circuito es
simulable; si fueran miles, no.
"""

import os
import sys

# En esta maquina Norton intercepta HTTPS y rompe la verificacion de certificados.
# truststore hace que Python use el almacen de certificados de Windows (donde SI esta
# el CA de Norton) en vez del bundle de certifi. Inofensivo en otras maquinas.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import pandas as pd
from dotenv import load_dotenv
from neuprint import Client

load_dotenv()                                  # lee el .env que esta junto a este script
TOKEN = os.environ.get("NEUPRINT_TOKEN")       # nunca hardcodeado: sale del entorno
if not TOKEN:
    sys.exit("Falta NEUPRINT_TOKEN. Copia .env.example a .env y pon tu token.")

SERVER, DATASET = "neuprint.janelia.org", "male-cns:v1.0"
client = Client(SERVER, dataset=DATASET, token=TOKEN)

# Primero imprimimos los datasets disponibles para confirmar el nombre EXACTO del
# dataset (neuPrint versiona: "male-cns:v0.9" y "male-cns:v1.0" son bases distintas).
print(f"Datasets disponibles en {SERVER}:")
for name in sorted(client.fetch_datasets()):
    print(f"   {'->' if name == DATASET else '  '} {name}")
print(f"\nUsando: {DATASET}\n")

# Cypher = el SQL de Neo4j. En neuPrint cada neurona es un nodo con etiqueta :Neuron
# (:Neuron = reconstruida y revisada por humanos; hay millones de fragmentos que NO
# tienen esa etiqueta y quedan fuera a proposito). Agrupamos por n.type = "tipo celular":
# el nombre de la clase de neurona, no de la neurona individual. Un tipo suele tener 2
# copias, una por hemisferio. Contar TIPOS, no neuronas, es lo que dice si un circuito
# es tratable. Solo pedimos metadatos (nombre, clase, neurotransmisor, nro de sinapsis);
# ninguna tabla de conexiones.
QUERY = """
MATCH (n:Neuron) WHERE {predicate}
RETURN coalesce(n.type, '(sin tipo asignado)') AS tipo,
       count(*)                                AS neuronas,
       collect(DISTINCT n.class)[0..2]         AS clase,
       collect(DISTINCT n.subclass)[0..3]      AS subclase,
       collect(DISTINCT n.somaNeuromere)[0..3] AS neuromero,
       collect(DISTINCT n.consensusNt)[0..2]   AS neurotransmisor,
       sum(n.pre) AS sinapsis_salida, sum(n.post) AS sinapsis_entrada
ORDER BY neuronas ASC, tipo ASC
"""

# Cada categoria = (titulo, que estoy preguntando en cristiano, filtro Cypher).
CATEGORIES = [
    ("A. Entrada mecanosensorial (el golpe)",
     "Neuronas que detectan contacto, carga en la pata, vibracion y gravedad. "
     "Filtro: class empieza por 'mechanosensory' y subclass es uno de los organos "
     "clasicos del reflejo de enderezamiento.",
     "n.class STARTS WITH 'mechanosensory' AND n.subclass IN "
     "['campaniform sensilla','chordotonal organ','hair plate','wind_gravity',"
     "'leg bristle','mechanosensory bristle','leg']"),

    ("B. Neuronas descendentes (la orden)",
     "Todas las DN: cerebro -> VNC. Son el 'comando' que decide caminar/trepar. "
     "Filtro: superclass empieza por 'descending'.",
     "n.superclass STARTS WITH 'descending'"),

    ("C. Motoneuronas de pata en el VNC (la salida)",
     "Motoneuronas del VNC cuyo subclass es fl/ml/hl = pata delantera/media/trasera. "
     "Son el ultimo eslabon: disparan y el musculo se contrae.",
     "n.superclass = 'vnc_motor' AND n.subclass IN ['fl','ml','hl']"),

    ("D. Atajo: DN nombradas en la literatura de escape/caminata",
     "Lista corta y explicita de DN ya caracterizadas: DNp01 es la Giant Fiber "
     "(escape/salto tras un susto), DNa01/DNa02 dirigen giros al caminar, MDN hace "
     "caminar hacia atras, DNp09 congela. Sirve para anclar el modelo en algo conocido.",
     "n.type IN ['DNp01','DNa01','DNa02','DNa10','DNb02','DNg13','DNg100',"
     "'MDN','DNp07','DNp09','DNp10']"),
]


def as_markdown(df: pd.DataFrame) -> str:
    """DataFrame -> tabla markdown (evita depender de 'tabulate')."""
    clean = df.map(lambda v: ", ".join(map(str, v)) if isinstance(v, list) else str(v))
    head = "| " + " | ".join(clean.columns) + " |\n|" + "---|" * len(clean.columns) + "\n"
    return head + "".join("| " + " | ".join(r) + " |\n" for r in clean.values)


report = [f"# Candidatos de circuito - geotaxis negativa\n",
          f"Dataset: `{DATASET}` ({SERVER}) | solo metadatos, sin conectividad.\n"]

for title, explanation, predicate in CATEGORIES:
    df = client.fetch_custom(QUERY.format(predicate=predicate))
    print(f"===== {title} =====")
    print(f"{len(df)} tipos celulares, {df['neuronas'].sum()} neuronas en total")
    print(df.head(12).to_string(index=False), "\n")   # consola: solo una muestra
    report += [f"\n## {title}\n", f"_{explanation}_\n",
               f"\n**{len(df)} tipos celulares / {df['neuronas'].sum()} neuronas.** "
               f"Ordenado de menos a mas neuronas (arriba = mas tratable).\n\n",
               as_markdown(df)]                       # el .md: la tabla completa

with open("circuit_candidates.md", "w", encoding="utf-8") as fh:
    fh.write("".join(report))
print("Escrito circuit_candidates.md")
