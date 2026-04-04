from fastapi import FastAPI, Path, APIRouter
from typing import Optional
import sqlite3
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

class MovieInput(BaseModel):
    title: str
    genres: str

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Επιτρέπει σε όλα τα frontends να κάνουν αιτήματα 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter(prefix="/movielens/api")

@router.get("/movies")
async def search_title(search:str):
    conn = sqlite3.connect('movielens.db')
    cursor = conn.cursor()
    searchTerm = f"%{search}%"
    cursor.execute('select * from movies where title like ?', (searchTerm,))
    titles = cursor.fetchall()
    conn.close()
    formattedTitle = []
    for row in titles:
        singleTitles = {
            "movieId": row[0],
            "title": row[1]
        }
        formattedTitle.append(singleTitles)
    return {"status": "success", "movies": formattedTitle}

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

@router.post("/movies")
async def addMovies(movie: MovieInput):
    conn = sqlite3.connect('movielens.db')
    cursor = conn.cursor()
    cursor.execute('insert into movies (title, genres) values (?, ?)', (movie.title, movie.genres))
    conn.commit()
    newId = cursor.lastrowid
    conn.close()
    return {"status": "success", "movieId": newId}

app.include_router(router)