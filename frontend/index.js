// Καθορισμός του Base URL του API σύμφωνα με τις προδιαγραφές
const API_BASE_URL = "http://localhost:3000/movielens/api";

// Δομή στη μνήμη για την αποθήκευση των βαθμολογιών του session
let sessionRatings = [];

document.addEventListener("DOMContentLoaded", () => {
    setupAddMovieForm();
    setupSearch();
    setupRecommendations();
});

// --- 1. Λειτουργία: Προσθήκη Νέας Ταινίας ---
function setupAddMovieForm() {
    const form = document.getElementById("add-movie-form");
    const feedback = document.getElementById("add-movie-feedback");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const title = document.getElementById("movie-title").value.trim();
        const genres = document.getElementById("movie-genres").value.trim();

        try {
            const response = await fetch(`${API_BASE_URL}/movies`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ title, genres })
            });

            const data = await response.json();

            if (data.status === "success") {
                feedback.className = "feedback success";
                feedback.textContent = `Η ταινία προστέθηκε επιτυχώς με ID: ${data.movieId}`;
                form.reset();
            } else {
                throw new Error("Αποτυχία κατά την αποθήκευση της ταινίας.");
            }
        } catch (error) {
            feedback.className = "feedback error";
            feedback.textContent = `Σφάλμα: ${error.message}`;
        }
    });
}

// --- 2. Λειτουργία: Αναζήτηση Ταινιών & Υπολογισμός Μέσης Βαθμολογίας ---
function setupSearch() {
    const searchInput = document.getElementById("search-input");
    const searchBtn = document.getElementById("search-btn");
    const resultsContainer = document.getElementById("search-results-container");

    const performSearch = async () => {
        const keyword = searchInput.value.trim();
        if (!keyword) return;

        resultsContainer.innerHTML = "<p>Αναζήτηση σε εξέλιξη...</p>";

        try {
            // Βήμα Α: Κλήση του endpoint αναζήτησης ταινιών
            const resMovies = await fetch(`${API_BASE_URL}/movies?search=${encodeURIComponent(keyword)}`);
            const dataMovies = await resMovies.json();

            if (dataMovies.status !== "success" || dataMovies.movies.length === 0) {
                resultsContainer.innerHTML = "<p class='placeholder-text'>Δεν βρέθηκαν ταινίες με αυτό το κλειδί.</p>";
                return;
            }

            // Δημιουργία δομής πίνακα
            let tableHtml = `
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Τίτλος</th>
                            <th>Μέση Βαθμολογία</th>
                            <th>Η Βαθμολογία σας</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            // Βήμα Β: Για κάθε ταινία, φέρνουμε παράλληλα τις βαθμολογίες της για υπολογισμό του μέσου όρου
            const ratingPromises = dataMovies.movies.map(movie => 
                fetch(`${API_BASE_URL}/ratings/${movie.movieId}`).then(res => res.json())
            );
            
            const allRatingsResults = await Promise.all(ratingPromises);

            dataMovies.movies.forEach((movie, index) => {
                const ratingsData = allRatingsResults[index];
                let avgDisplay = "Καμία Βαθμολογία";
                
                if (ratingsData.status === "success" && ratingsData.ratings.length > 0) {
                    const sum = ratingsData.ratings.reduce((acc, curr) => acc + curr.rating, 0);
                    avgDisplay = (sum / ratingsData.ratings.length).toFixed(2);
                }

                // Έλεγχος αν ο χρήστης την έχει ήδη βαθμολογήσει στο τρέχον session
                const existingRating = sessionRatings.find(r => r.movieId === movie.movieId);
                const currentRatingValue = existingRating ? existingRating.rating : "";

                tableHtml += `
                    <tr>
                        <td>${movie.movieId}</td>
                        <td>${movie.title}</td>
                        <td><strong>${avgDisplay}</strong></td>
                        <td>
                            <div class="rating-input-group">
                                <input type="number" id="input-rate-${movie.movieId}" min="0.5" max="5" step="0.5" value="${currentRatingValue}" placeholder="0.5-5">
                                <button class="btn btn-sm" onclick="submitSessionRating(${movie.movieId}, '${movie.title.replace(/'/g, "\\'")}')">Υποβολή</button>
                            </div>
                        </td>
                    </tr>
                `;
            });

            tableHtml += `</tbody></table>`;
            resultsContainer.innerHTML = tableHtml;

        } catch (error) {
            resultsContainer.innerHTML = `<p class='feedback error'>Σφάλμα κατά την ανάκτηση δεδομένων: ${error.message}</p>`;
        }
    };

    searchBtn.addEventListener("click", performSearch);
    searchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") performSearch();
    });
}

// --- 3. Λειτουργία: Αποθήκευση Βαθμολογίας στη Μνήμη (Session) ---
window.submitSessionRating = function(movieId, movieTitle) {
    const inputElement = document.getElementById(`input-rate-${movieId}`);
    const ratingValue = parseFloat(inputElement.value);

    if (isNaN(ratingValue) || ratingValue < 0.5 || ratingValue > 5) {
        alert("Παρακαλώ εισάγετε έγκυρη βαθμολογία μεταξύ 0.5 και 5 (με βήμα 0.5).");
        return;
    }

    // Αν υπάρχει ήδη η ταινία στο session, την ενημερώνουμε, αλλιώς την προσθέτουμε
    const existingIndex = sessionRatings.findIndex(r => r.movieId === movieId);
    if (existingIndex >= 0) {
        sessionRatings[existingIndex].rating = ratingValue;
    } else {
        sessionRatings.push({ movieId, title: movieTitle, rating: ratingValue });
    }

    updateSessionRatingsUI();
};

function updateSessionRatingsUI() {
    const container = document.getElementById("session-ratings-container");
    const recommendBtn = document.getElementById("get-recommendations-btn");

    if (sessionRatings.length === 0) {
        container.innerHTML = `<p class="placeholder-text">Δεν έχετε βαθμολογήσει κάποια ταινία ακόμα σε αυτό το session.</p>`;
        recommendBtn.disabled = true;
        return;
    }

    let html = "<table><thead><tr><th>Τίτλος</th><th>Βαθμολογία</th><th>Ενέργεια</th></tr></thead><tbody>";
    sessionRatings.forEach(item => {
        html += `
            <tr>
                <td>${item.title}</td>
                <td><strong>${item.rating}</strong></td>
                <td><button class="btn btn-sm" style="background-color: #dc2626;" onclick="removeSessionRating(${item.movieId})">Διαγραφή</button></td>
            </tr>
        `;
    });
    html += "</tbody></table>";
    
    container.innerHTML = html;
    recommendBtn.disabled = false; // Ενεργοποίηση κουμπιού συστάσεων
}

window.removeSessionRating = function(movieId) {
    sessionRatings = sessionRatings.filter(r => r.movieId !== movieId);
    updateSessionRatingsUI();
    
    // Αν υπάρχει ανοιχτό input στον πίνακα αναζήτησης, το καθαρίζουμε
    const inputElement = document.getElementById(`input-rate-${movieId}`);
    if (inputElement) inputElement.value = "";
};

// --- 4. Λειτουργία: Αίτημα και Εμφάνιση Συστάσεων ---
function setupRecommendations() {
    const recommendBtn = document.getElementById("get-recommendations-btn");
    const recSection = document.getElementById("recommendations-section");
    const recContainer = document.getElementById("recommendations-container");

    recommendBtn.addEventListener("click", async () => {
        recSection.classList.remove("hidden");
        recContainer.innerHTML = "<p>Ο αλγόριθμος Pearson επεξεργάζεται τα δεδομένα σας...</p>";

        // Μορφοποίηση του payload σύμφωνα με το μοντέλο Pydantic του backend
        const payload = {
            ratings: sessionRatings.map(item => ({
                movieId: item.movieId,
                rating: item.rating
            }))
        };

        try {
            const response = await fetch(`${API_BASE_URL}/recommendations`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.status !== "success" || data.recommendations.length === 0) {
                recContainer.innerHTML = "<p class='placeholder-text'>Δεν κατέστη δυνατή η δημιουργία προτάσεων. Δοκιμάστε να βαθμολογήσετε περισσότερες ταινίες για να βρεθούν όμοιοι χρήστες.</p>";
                return;
            }

            let tableHtml = `
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Προτεινόμενος Τίτλος</th>
                            <th>Κατηγορίες (Genres)</th>
                            <th>Προβλεπόμενη Βαθμολογία</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            data.recommendations.forEach(movie => {
                tableHtml += `
                    <tr>
                        <td>${movie.movieId}</td>
                        <td><strong>${movie.title}</strong></td>
                        <td>${movie.genres}</td>
                        <td><span style="color: #059669; font-weight: bold;">${movie.predictedRating} / 5</span></td>
                    </tr>
                `;
            });

            tableHtml += `</tbody></table>`;
            recContainer.innerHTML = tableHtml;

        } catch (error) {
            recContainer.innerHTML = `<p class='feedback error'>Σφάλμα κατά τον υπολογισμό προτάσεων: ${error.message}</p>`;
        }
    });
}