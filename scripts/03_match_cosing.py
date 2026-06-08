import pandas as pd
from rapidfuzz import process, fuzz

ingredients = pd.read_csv("data/ingredients_clean.csv")
cosing = pd.read_csv("data/ingredients_dataset.csv")

cosing_list = cosing["inci_name"].tolist()

results = []

for inci in ingredients["inci_name"]:

    match = process.extractOne(
        inci,
        cosing_list,
        scorer=fuzz.token_sort_ratio
    )

    best_match = match[0]
    score = match[1]

    data = cosing[cosing["inci_name"] == best_match].iloc[0]

    results.append({
        "input_inci": inci,
        "matched_inci": best_match,
        "substance": data["substance"],
        "cas_no": data["cas_no"],
        "function": data["function"],
        "score": score
    })

result_df = pd.DataFrame(results)

result_df.to_excel("results/cosing_match_result.xlsx", index=False)

print("Matching complete")