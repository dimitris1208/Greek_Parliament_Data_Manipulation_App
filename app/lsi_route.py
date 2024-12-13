from flask import Blueprint, jsonify , render_template , request
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Flask Blueprint
lsi_blueprint = Blueprint("lsi", __name__)

# Database connection details
db_user = os.getenv("db_user")
db_password = os.getenv("db_password")
db_host = os.getenv("db_host")
db_port = os.getenv("db_port")
db_name = os.getenv("db_name")

engine = create_engine(f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

@lsi_blueprint.route("/lsi_vectors", methods=["GET"])
def get_lsi_vectors():
    """Render the LSI vectors page with simplified pagination."""
    try:
        # Get the current page from query parameters, default to page 1
        page = int(request.args.get("page", 1))
        vectors_per_page = 20
        offset = (page - 1) * vectors_per_page

        with engine.connect() as connection:
            # Fetch the total number of vectors
            total_count = connection.execute(text("SELECT COUNT(*) FROM lsi_speeches")).scalar()

            # Fetch the vectors for the current page
            result = connection.execute(
                text("SELECT speech_id, lsi_vector FROM lsi_speeches LIMIT :limit OFFSET :offset"),
                {"limit": vectors_per_page, "offset": offset}
            )
            vectors = [{"speech_id": row[0], "lsi_vector": row[1]} for row in result.fetchall()]

        # Calculate total pages
        total_pages = (total_count + vectors_per_page - 1) // vectors_per_page

        return render_template(
            "lsi.html",
            vectors=vectors,
            current_page=page,
            total_pages=total_pages,
        )
    except Exception as e:
        return render_template("error.html", error_message=str(e))
