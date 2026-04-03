from fastapi import FastAPI, Path, APIRouter
from typing import Optional
import sqlite3
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Επιτρέπει σε όλα τα frontends να κάνουν αιτήματα 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter(prefix="/movielens/api")

@router.get("/ratings/{movieId}")
async def ratings(movieId: int):
    conn = sqlite3.connect('movielens.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM ratings
        WHERE movieId = ?
        ''', (movieId,))
    ratings = cursor.fetchall() 
    conn.close()
    formattedRatings = []
    for row in ratings:
        singleRating = {
            "userId": row[0],
            "rating": row[2]
        }
        formattedRatings.append(singleRating)

    return {"status": "success", "ratings": formattedRatings}
app.include_router(router)