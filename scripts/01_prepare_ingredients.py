import pandas as pd

# โหลด dataset
df = pd.read_excel("data/cosmetic_ingredients_600.xlsx")

# normalize
df["inci_name"] = df["inci_name"].str.lower().str.strip()

# ลบซ้ำ
df = df.drop_duplicates(subset="inci_name")

print("Total ingredients:", len(df))

# save
df.to_csv("data/ingredients_clean.csv", index=False)

print("ingredients_clean.csv created")