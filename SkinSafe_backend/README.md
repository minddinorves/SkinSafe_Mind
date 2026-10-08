# SkinSafe Backend — Phase 8 Starter

## 1. Setup
Create a virtual environment and install:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the PostgreSQL connection values.

## 2. Run

```bash
uvicorn app.main:app --reload
```

Open `/docs` to test the FastAPI endpoints.

## 3. Endpoints
- `GET /health`
- `GET /ingredients/{ingredient_id}?skin_type_id=2`
- `GET /ingredients/by-name/NIACINAMIDE`
- `POST /analysis`

Example request:

```json
{
  "ingredient_ids": [11094, 6605, 11242],
  "skin_type_id": 2
}
```

## 4. Important
This starter reads the existing PostgreSQL schema and applies the Recommendation Engine rules defined in the SkinSafe project.

It does not yet connect OCR or LINE webhook code.
Do not claim an endpoint has been tested against the live database until it is actually run in the user's environment.
