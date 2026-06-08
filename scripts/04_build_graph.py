import pandas as pd
import networkx as nx

df = pd.read_excel("results/cosing_match_result.xlsx")

G = nx.Graph()

for _, row in df.iterrows():

    ingredient = row["matched_inci"]
    function = row["function"]
    cas = row["cas_no"]

    if function:
        G.add_edge(ingredient, function, relation="has_function")

    if cas:
        G.add_edge(ingredient, cas, relation="has_cas")

print("Nodes:", G.number_of_nodes())
print("Edges:", G.number_of_edges())