# recommender.py
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def setup_recommendation_system():
    """
    Set up the recommendation system by loading and preprocessing the dataset.
    """
    # Load all necessary CSV files
    movies = pd.read_csv("data/movies.csv")
    links = pd.read_csv("data/links.csv")
    ratings = pd.read_csv("data/ratings.csv")

    # Calculate average ratings with minimum vote requirement
    rating_counts = ratings.groupby('movieId')['rating'].count()
    avg_ratings = ratings.groupby('movieId')['rating'].agg(['mean', 'count']).reset_index()
    avg_ratings.columns = ['movieId', 'avg_rating', 'rating_count']

    # Calculate weighted rating using IMDB's weighted rating formula
    # Weighted Rating (WR) = (v/(v+m) × R) + (m/(v+m) × C)
    # v = number of votes for the movie
    # m = minimum votes required (let's set this to 100)
    # R = average rating for the movie
    # C = mean rating across all movies
    m = 100  # minimum votes required
    C = ratings['rating'].mean()  # mean rating across all movies

    avg_ratings['weighted_rating'] = (
        (avg_ratings['rating_count'] / (avg_ratings['rating_count'] + m) * avg_ratings['avg_rating']) +
        (m / (avg_ratings['rating_count'] + m) * C)
    )

    # Merge all data with movies
    movies = movies.merge(links, on='movieId', how='left')
    movies = movies.merge(avg_ratings, on='movieId', how='left')

    # Create normalized titles for better matching
    movies['normalized_title'] = movies['title'].str.lower().str.strip()

    # Fill missing ratings with a default value
    movies['avg_rating'] = movies['avg_rating'].fillna(3.0)
    movies['weighted_rating'] = movies['weighted_rating'].fillna(3.0)
    movies['rating_count'] = movies['rating_count'].fillna(0)

    # Create Google search links
    movies['link'] = movies['title'].apply(
        lambda x: f"https://www.google.com/search?q={x.replace(' ', '+')}"
    )

    # Combine title and genres for TF-IDF
    movies['metadata'] = movies['title'] + " " + movies['genres'].fillna("")

    # Calculate TF-IDF matrix
    tfidf = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf.fit_transform(movies['metadata'])

    # Compute cosine similarity
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    return movies, cosine_sim

def get_recommendations(title, movies_df, cosine_sim_matrix):
    """
    Get movie recommendations based on title similarity and weighted ratings.
    Includes more flexible title matching.
    """
    # Normalize the input title - remove special characters and extra spaces
    title = title.lower().strip()
    title = ''.join(e for e in title if e.isalnum() or e.isspace())
    
    # Normalize the movie titles in the dataset similarly
    movies_df['search_title'] = movies_df['title'].apply(lambda x: ''.join(e for e in x.lower() if e.isalnum() or e.isspace()))
    
    # Find movies that contain the input title using flexible matching
    matching_movies = movies_df[
        (movies_df['search_title'].str.contains(title, case=False, na=False)) |  # Exact substring match
        (movies_df['search_title'].apply(lambda x: title.replace(' ', '') in x.replace(' ', '')))  # Match without spaces
    ]
    
    if matching_movies.empty:
        return None

    # Get the index of the best matching movie
    idx = matching_movies.index[0]

    # Rest of the function remains the same...
    sim_scores = list(enumerate(cosine_sim_matrix[idx]))
    
    combined_scores = []
    min_ratings_threshold = 5
    
    for i, sim_score in sim_scores:
        movie = movies_df.iloc[i]
        rating_count = movie['rating_count']
        
        if rating_count < min_ratings_threshold:
            continue
            
        normalized_sim = sim_score * 5
        rating_weight = min(rating_count / 100.0, 1.0)
        sim_weight = 1.0 - (rating_weight * 0.4)
        
        combined_score = (sim_weight * normalized_sim) + (rating_weight * 0.4 * movie['weighted_rating'])
        
        if movie['avg_rating'] >= 4.0:
            combined_score *= 1.1
            
        combined_scores.append({
            'index': i,
            'combined_score': combined_score,
            'similarity': sim_score,
            'rating': movie['avg_rating'],
            'rating_count': rating_count
        })

    combined_scores.sort(key=lambda x: x['combined_score'], reverse=True)

    similar_movies = []
    for score in combined_scores[1:13]:
        movie = movies_df.iloc[score['index']]
        similar_movies.append({
            'movie': movie['title'],
            'link': movie['link'],
            'rating': round(float(movie['avg_rating']), 1),
            'rating_count': int(score['rating_count']),
            'similarity': round(score['similarity'] * 100)
        })

    return similar_movies