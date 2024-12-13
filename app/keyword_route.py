from flask import Blueprint, render_template, request
from sqlalchemy import create_engine, text
from datetime import datetime
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

keywords_blueprint = Blueprint('keywords', __name__)

@keywords_blueprint.route('/keywords', methods=['GET', 'POST'])
def keywords():
    try:
        # Retrieve all unique members and political parties
        members_query = text("SELECT DISTINCT member_name FROM final_speeches")
        parties_query = text("SELECT DISTINCT political_party FROM final_speeches")

        with engine.connect() as connection:
            members = connection.execute(members_query).fetchall()
            parties = connection.execute(parties_query).fetchall()

        # Process the request for a selected member or party
        if request.method == 'POST':
            selected_member = request.form.get('member')
            selected_party = request.form.get('party')

            results_with_tfidf = []

            if selected_member:
                # Fetch top 3 keywords for the selected member and how they change over time
                member_keywords_query = text("""
                    SELECT tfidf_values.term, tfidf_values.tfidf_value, final_speeches.sitting_date
                    FROM tfidf_values
                    JOIN final_speeches ON final_speeches.id = tfidf_values.speech_id
                    WHERE final_speeches.member_name = :member_name
                    AND tfidf_values.tfidf_value > 0.2
                    ORDER BY tfidf_values.tfidf_value DESC
                    LIMIT 3
                """)
                with engine.connect() as connection:
                    result = connection.execute(member_keywords_query, {'member_name': selected_member}).fetchall()
                    for term, tfidf_value, sitting_date in result:
                        # Format the sitting_date to 'YYYY-MM-DD'
                        formatted_date = sitting_date.strftime('%Y-%m-%d') if sitting_date else None
                        results_with_tfidf.append({
                            'term': term,
                            'tfidf_value': tfidf_value,
                            'sitting_date': formatted_date
                        })

            elif selected_party:
                # Fetch top 3 keywords for the selected political party and how they change over time
                party_keywords_query = text("""
                    SELECT tfidf_values.term, tfidf_values.tfidf_value, final_speeches.sitting_date
                    FROM tfidf_values
                    JOIN final_speeches ON final_speeches.id = tfidf_values.speech_id
                    WHERE final_speeches.political_party = :political_party
                    AND tfidf_values.tfidf_value > 0.2
                    ORDER BY tfidf_values.tfidf_value DESC
                    LIMIT 3
                """)
                with engine.connect() as connection:
                    result = connection.execute(party_keywords_query, {'political_party': selected_party}).fetchall()
                    for term, tfidf_value, sitting_date in result:
                        # Format the sitting_date to 'YYYY-MM-DD'
                        formatted_date = sitting_date.strftime('%Y-%m-%d') if sitting_date else None
                        results_with_tfidf.append({
                            'term': term,
                            'tfidf_value': tfidf_value,
                            'sitting_date': formatted_date
                        })

            return render_template('keywords.html', results=results_with_tfidf, members=members, parties=parties)

        return render_template('keywords.html', members=members, parties=parties, results=None)

    except Exception as e:
        print(f"Error occurred during keyword calculation: {e}")
        return render_template('error.html', error_message="An error occurred while calculating keywords.")
