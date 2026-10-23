from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from ..SkinSafe_backend.app.repository import find_ingredient, get_ingredient_detail
from ..SkinSafe_backend.app.recommendation import classify_ingredient, summarize_product

app = FastAPI(title="SkinSafe Backend", version="0.1.0")

class AnalyzeRequest(BaseModel):
    ingredient_ids: list[int] = Field(min_length=1)
    skin_type_id: int = Field(ge=1, le=5)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ingredients/{ingredient_id}")
def ingredient(ingredient_id: int, skin_type_id: int | None = None):
    detail = get_ingredient_detail(ingredient_id, skin_type_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return detail

@app.get("/ingredients/by-name/{name}")
def ingredient_by_name(name: str):
    result = find_ingredient(name)
    if not result:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return result

@app.post("/analysis")
def analysis(request: AnalyzeRequest):
    results = []
    for ingredient_id in request.ingredient_ids:
        detail = get_ingredient_detail(ingredient_id, request.skin_type_id)
        if detail:
            results.append(classify_ingredient(detail))

    if not results:
        raise HTTPException(status_code=404, detail="No ingredients found")

    return {
        "skin_type_id": request.skin_type_id,
        "summary": summarize_product(results),
        "ingredients": results,
    }
