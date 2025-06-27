# app.py
from flask import Flask, render_template, request, jsonify
import logging
from recommender import get_recommendations, setup_recommendation_system

app = Flask(__name__)

# Load data and build the recommendation model
movies, cosine_sim = setup_recommendation_system()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Handle movie recommendation requests.
    Expects a JSON request with a 'movie' field.
    """
    data = request.get_json()
    if not data or 'movie' not in data:
        return jsonify({'error': 'No movie title provided.'}), 400

    movie_title = data['movie']
    recommendations = get_recommendations(movie_title, movies, cosine_sim)

    if recommendations is None:
        return jsonify({'error': 'Movie not found. Please try another title.'}), 404

    return jsonify({'recommendations': recommendations})

if __name__ == "__main__":
    app.run(debug=True)