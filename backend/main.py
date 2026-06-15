from fastapi import FastAPI, APIRouter
from typing import List
import sqlite3
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import math

class MovieInput(BaseModel):
    title: str
    genres: str

# --- Data Models για το Input ---
class UserRating(BaseModel):
    movieId: int
    rating: float

class RecommendationRequest(BaseModel):
    ratings: List[UserRating]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Επιτρέπει σε όλα τα frontends να κάνουν αιτήματα 
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter(prefix="/movielens/api")

@router.get("/movies")
async def search_title(search:str):
    conn = sqlite3.connect('movielens.db')
    cursor = conn.cursor()
    searchTerm = f"%{search}%"
    cursor.execute('select * from movies where title like ? limit 20', (searchTerm,))
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

@router.post("/recommendations")
async def get_recommendations(req: RecommendationRequest):
    # 0. Προετοιμασία δεδομένων του τρέχοντος χρήστη (u)
    user_u_ratings = {r.movieId: r.rating for r in req.ratings}
    print(f"\n--- ΝΕΟ REQUEST ΣΥΣΤΑΣΕΩΝ ---")
    print(f"[DEBUG 1] Βαθμολογίες session: {user_u_ratings}")
    if not user_u_ratings:
        return {"status": "success", "recommendations": []}

    avg_u = sum(user_u_ratings.values()) / len(user_u_ratings)
    movie_ids_u = tuple(user_u_ratings.keys())
    
    conn = sqlite3.connect('movielens.db')
    cursor = conn.cursor()

    # 1. Εύρεση χρηστών (v) με κοινές ταινίες 
    # Φέρνουμε όλες τις βαθμολογίες για τις ταινίες που έχει δει ο χρήστης u
    placeholders = ','.join('?' for _ in movie_ids_u)
    cursor.execute(f'''
        SELECT userId, movieId, rating 
        FROM ratings 
        WHERE movieId IN ({placeholders})
    ''', movie_ids_u)
    
    overlapping_ratings = cursor.fetchall()
    print(f"[DEBUG 2] Βρέθηκαν {len(overlapping_ratings)} εγγραφές από άλλους χρήστες για αυτές τις ταινίες")
    # Ομαδοποίηση βαθμολογιών ανά χρήστη v
    users_v_data = {}
    for uid, mid, rating in overlapping_ratings:
        if uid not in users_v_data:
            users_v_data[uid] = {}
        users_v_data[uid][mid] = rating

    # 2. Υπολογισμός Pearson Correlation sim(u,v) 
    similarities = []
    
    # Θα χρειαστούμε τις μέσες βαθμολογίες όλων των χρηστών για τον τύπο της πρόβλεψης
    cursor.execute('SELECT userId, AVG(rating) FROM ratings GROUP BY userId')
    avg_ratings_all = {row[0]: row[1] for row in cursor.fetchall()}

    for user_v, v_ratings in users_v_data.items():
        corated_items = set(user_u_ratings.keys()).intersection(set(v_ratings.keys()))
        
        # Πρέπει να έχουν τουλάχιστον 2 κοινές ταινίες για να έχει νόημα η συσχέτιση
        if len(corated_items) < 2:
            continue
            
        avg_v = avg_ratings_all.get(user_v, 0)
        
        num = 0.0
        den_u = 0.0
        den_v = 0.0
        
        for mid in corated_items:
            diff_u = user_u_ratings[mid] - avg_u
            diff_v = v_ratings[mid] - avg_v
            
            num += diff_u * diff_v
            den_u += diff_u ** 2
            den_v += diff_v ** 2
            
        if den_u == 0 or den_v == 0:
            continue
            
        sim_uv = num / (math.sqrt(den_u) * math.sqrt(den_v))
        
        # Κρατάμε μόνο θετικές συσχετίσεις για καλύτερες προτάσεις
        if sim_uv > 0:
            similarities.append((user_v, sim_uv))

    # 3. Επιλογή top-K (π.χ. K=50) 
    similarities.sort(key=lambda x: x[1], reverse=True)
    print(f"[DEBUG 3] Γείτονες που πέρασαν τα φίλτρα (κοινές ταινίες >= 2 ΚΑΙ sim > 0): {len(similarities)}")
    top_k_users = similarities[:50]
    top_k_dict = dict(top_k_users)

    if not top_k_dict:
        conn.close()
        return {"status": "success", "recommendations": []}

    # 4. Πρόβλεψη βαθμολογίας για υποψήφιες ταινίες 
    top_k_ids = tuple(top_k_dict.keys())
    placeholders_k = ','.join('?' for _ in top_k_ids)
    
    # Φέρνουμε όλες τις ταινίες που έχουν δει οι top-K χρήστες
    cursor.execute(f'''
        SELECT userId, movieId, rating 
        FROM ratings 
        WHERE userId IN ({placeholders_k})
    ''', top_k_ids)
    
    candidate_ratings = cursor.fetchall()
    print(f"[DEBUG 4] Βρέθηκαν {len(candidate_ratings)} υποψήφιες βαθμολογίες ταινιών από τους γείτονες")
    # Ομαδοποίηση ανά υποψήφια ταινία i
    predictions = []
    movies_i = {}
    for uid, mid, rating in candidate_ratings:
        if mid not in user_u_ratings: # Μόνο ταινίες που ΔΕΝ έχει δει ο u 
            if mid not in movies_i:
                movies_i[mid] = []
            movies_i[mid].append((uid, rating))

    for mid, ratings_list in movies_i.items():
        num = 0.0
        den = 0.0
        
        for uid, rating in ratings_list:
            sim_uv = top_k_dict[uid]
            avg_v = avg_ratings_all.get(uid, 0)
            
            num += sim_uv * (rating - avg_v)
            den += abs(sim_uv)
            
        if den > 0:
            predicted_rating = avg_u + (num / den)
            # Clamping μεταξύ 0.5 και 5.0
            predicted_rating = max(0.5, min(5.0, predicted_rating))
            predictions.append((mid, predicted_rating))
            

    # 5. Επιλογή top-N (π.χ. N=10) 
    predictions.sort(key=lambda x: x[1], reverse=True)
    top_n_movies = predictions[:10]

    # Εμπλουτισμός με τίτλους και genres 
    recommendations_output = []
    for mid, pred_rating in top_n_movies:
        cursor.execute('SELECT title, genres FROM movies WHERE movieId = ?', (mid,))
        movie_info = cursor.fetchone()
        if movie_info:
            recommendations_output.append({
                "movieId": mid,
                "title": movie_info[0],
                "genres": movie_info[1],
                "predictedRating": round(pred_rating, 2) 
            })

    conn.close()
    return {"status": "success", "recommendations": recommendations_output}

app.include_router(router)