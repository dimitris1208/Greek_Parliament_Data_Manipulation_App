from flask import Blueprint, render_template, request
from sqlalchemy import create_engine, text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from math import ceil
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection details
db_user = os.getenv("db_user")
db_password = os.getenv("db_password")
db_host = os.getenv("db_host")
db_port = os.getenv("db_port")
db_name = os.getenv("db_name")

# Create the database engine
engine = create_engine(f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

cluster_blueprint = Blueprint('clusters', __name__)

ITEMS_PER_PAGE = 10  # Number of speeches per page


@cluster_blueprint.route('/clusters', methods=['GET'])
def clusters():
    """Main route to display clusters and speeches."""
    try:
        # Fetch all unique cluster IDs
        with engine.connect() as connection:
            cluster_ids = connection.execute(text("""
                SELECT DISTINCT cluster_id FROM clustered_speeches ORDER BY cluster_id
            """)).fetchall()
            cluster_ids = [row[0] for row in cluster_ids]

        # Get query parameters
        cluster_id = request.args.get('cluster_id', cluster_ids[0] if cluster_ids else 0, type=int)
        page = request.args.get('page', 1, type=int)
        offset = (page - 1) * ITEMS_PER_PAGE

        # Fetch speeches for the selected cluster
        with engine.connect() as connection:
            speeches = connection.execute(text("""
                SELECT f.id, f.member_name, f.sitting_date, f.political_party, f.merged_speech
                FROM clustered_speeches c
                JOIN final_speeches f ON c.speech_id = f.id
                WHERE c.cluster_id = :cluster_id
                ORDER BY f.id
                LIMIT :limit OFFSET :offset
            """), {"cluster_id": cluster_id, "limit": ITEMS_PER_PAGE, "offset": offset}).fetchall()

            # Count total speeches in the cluster for pagination
            total_count = connection.execute(text("""
                SELECT COUNT(*) FROM clustered_speeches
                WHERE cluster_id = :cluster_id
            """), {"cluster_id": cluster_id}).scalar()

        # Calculate total pages
        total_pages = ceil(total_count / ITEMS_PER_PAGE)

        return render_template(
            'clusters.html',
            cluster_ids=cluster_ids,
            selected_cluster=cluster_id,
            speeches=speeches,
            current_page=page,
            total_pages=total_pages
        )
    except Exception as e:
        return f"An error occurred: {e}"


@cluster_blueprint.route('/clusters/similar/<int:speech_id>/<int:cluster_id>', methods=['GET'])
def recommend_similar_speeches(speech_id, cluster_id):
    """Render the recommendations page immediately without performing calculations."""
    return render_template('recommendations.html', speech_id=speech_id, cluster_id=cluster_id)



@cluster_blueprint.route('/clusters/similar_json/<int:speech_id>/<int:cluster_id>', methods=['GET'])
def recommend_similar_speeches_json(speech_id, cluster_id):
    """Return top 5 similar speeches as JSON, excluding the speech itself."""
    try:
        # Fetch all speeches for the cluster
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT f.id, f.merged_speech
                FROM clustered_speeches c
                JOIN final_speeches f ON c.speech_id = f.id
                WHERE c.cluster_id = :cluster_id
            """), {"cluster_id": cluster_id})
            speeches = pd.DataFrame(result.fetchall(), columns=["id", "merged_speech"])

        # Find the selected speech
        target_speech = speeches.loc[speeches["id"] == speech_id, "merged_speech"].values[0]

        # Compute cosine similarity
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([target_speech] + speeches["merged_speech"].tolist())
        cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

        # Add similarity scores to speeches and filter out the target speech
        speeches["similarity"] = cosine_similarities
        filtered_speeches = speeches[speeches["id"] != speech_id]

        # Get top 5 similar speeches
        top_speeches = filtered_speeches.sort_values(by="similarity", ascending=False).head(5)

        # Return JSON response
        return {
            "recommendations": top_speeches[["id", "similarity"]].to_dict(orient="records")
        }
    except Exception as e:
        return {"error": str(e)}


