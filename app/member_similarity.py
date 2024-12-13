from flask import Blueprint, render_template, request
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Fetch database credentials from .env
db_user = os.getenv("db_user")
db_password = os.getenv("db_password")
db_host = os.getenv("db_host")
db_port = os.getenv("db_port")
db_name = os.getenv("db_name")

# Create the database engine
engine = create_engine(f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}", echo=False)

# Define the blueprint
member_similarity_blueprint = Blueprint('member_similarity', __name__)

@member_similarity_blueprint.route('/member_similarity', methods=['GET', 'POST'])
def member_similarity():
    try:
        # Step 1: Fetch all members from the database
        members_query = text("SELECT DISTINCT member_1 FROM member_similarity_scores")

        with engine.connect() as connection:
            members = connection.execute(members_query).fetchall()
            members = [member[0] for member in members]  # Extract member names

        # Step 2: Handle the form submission (selected member and k)
        if request.method == 'POST':
            selected_member = request.form.get('member')
            k = int(request.form.get('k'))

            # Step 3: Query to get the top-k similar members for the selected member
            similarity_query = text("""
                SELECT member_2, similarity_score
                FROM member_similarity_scores
                WHERE member_1 = :member_name
                ORDER BY similarity_score DESC
                LIMIT :k
            """)

            with engine.connect() as connection:
                similar_members = connection.execute(similarity_query, {'member_name': selected_member, 'k': k}).fetchall()

            # Step 4: Prepare the results to be displayed
            results = [{"member": member, "similarity_score": score} for member, score in similar_members]

            # Return the results to the frontend
            return render_template('member_similarity.html', results=results, members=members, selected_member=selected_member, k=k)

        return render_template('member_similarity.html', members=members, results=None)

    except Exception as e:
        print(f"Error occurred: {e}")
        return render_template('error.html', error_message="An error occurred while fetching member similarities.")
