import pandas as pd
import requests
import time

ingredients = pd.read_csv("data/ingredients_clean.csv")

results = []

for inci in ingredients["inci_name"]:

    print("Processing:", inci)

    results.append({
        "inci_name": inci,
        "substance": "",
        "cas_no": "",
        "function": ""
    })

    time.sleep(0.5)

df = pd.DataFrame(results)

df.to_csv("data/cosing_clean.csv", index=False)

print("cosing_clean.csv created")