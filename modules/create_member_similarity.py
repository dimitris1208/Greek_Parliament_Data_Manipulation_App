import os
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Database connection details
db_user = os.getenv("db_user")
db_password = os.getenv("db_password")
db_host = os.getenv("db_host")
db_port = os.getenv("db_port")
db_name = os.getenv("db_name")

# Create the database engine
engine = create_engine(f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}", echo=False)
Session = sessionmaker(bind=engine)

# Logging setup
logging.basicConfig(level=logging.INFO)


def create_similarity_tables():
    """Create the member_similarity_scores table if it doesn't exist."""
    session = Session()
    try:
        print("Creating member_similarity_scores table...")
        logging.info("Creating member_similarity_scores table...")

        session.execute(
            text("""
                CREATE TABLE IF NOT EXISTS member_similarity_scores (
                    member_1 TEXT,
                    member_2 TEXT,
                    similarity_score FLOAT,
                    PRIMARY KEY (member_1, member_2)
                );
            """)
        )
        session.commit()
        print("member_similarity_scores table is ready.")
        logging.info("member_similarity_scores table is ready.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error creating tables: {e}")
        print(f"Error creating tables: {e}")
    finally:
        session.close()


def get_member_speeches(session, member_name):
    """Retrieve all speeches for a given member from the database."""
    print(f"Fetching speeches for member: {member_name}...")
    # Adjust the SQL query to join with the 'final_speeches' table to get 'member_name'
    sql_query = text("""
        SELECT ps.processed_speech
        FROM processed_speeches ps
        JOIN final_speeches fs ON ps.speech_id = fs.id
        WHERE fs.member_name = :member_name
    """)

    result = session.execute(sql_query, {"member_name": member_name}).fetchall()
    speeches = [row[0] for row in result]
    print(f"Retrieved {len(speeches)} speeches for {member_name}.")
    return speeches


def insert_similarity_scores(session, member_1, member_2, similarity_score):
    """Insert similarity scores for a member pair into the member_similarity_scores table."""
    print(f"Inserting similarity score for {member_1} and {member_2}...")
    session.execute(
        text("""
            INSERT INTO member_similarity_scores (member_1, member_2, similarity_score)
            VALUES (:member_1, :member_2, :similarity_score)
            ON CONFLICT (member_1, member_2) DO UPDATE
            SET similarity_score = EXCLUDED.similarity_score;
        """),
        {"member_1": member_1, "member_2": member_2, "similarity_score": similarity_score}
    )
    session.commit()
    print(f"Inserted similarity score: {similarity_score}")


def calculate_similarity_and_store(session, members):
    """Calculate pairwise similarities between members and store the results."""
    print("Calculating pairwise member similarities...")

    # Create a TfidfVectorizer object
    vectorizer = TfidfVectorizer(stop_words="english")

    # Prepare list to store all speeches for vectorization
    all_speeches = {}
    for member in members:
        all_speeches[member] = get_member_speeches(session, member)

    # Fit the vectorizer on all speeches of all members
    print("Fitting the TfidfVectorizer on all speeches...")
    all_speeches_list = [speech for speeches in all_speeches.values() for speech in speeches]
    tfidf_matrix = vectorizer.fit_transform(all_speeches_list)

    # Now, we will calculate pairwise similarities
    print("Calculating cosine similarities between members...")
    for i, member_1 in enumerate(members):
        print(f"Processing member {i + 1}/{len(members)}: {member_1}")

        # Get the TF-IDF vectors for member_1
        member_1_speeches = all_speeches[member_1]
        member_1_vectors = vectorizer.transform(member_1_speeches)

        for j, member_2 in enumerate(members):
            if i < j:  # Only calculate similarity once for each pair
                print(f"Comparing {member_1} with {member_2}...")

                # Get the TF-IDF vectors for member_2
                member_2_speeches = all_speeches[member_2]
                member_2_vectors = vectorizer.transform(member_2_speeches)

                # Calculate cosine similarity between member_1 and member_2's speeches
                similarity_score = cosine_similarity(member_1_vectors, member_2_vectors).mean()
                print(f"Cosine similarity between {member_1} and {member_2}: {similarity_score}")
                insert_similarity_scores(session, member_1, member_2, similarity_score)


def process_member_similarity():
    """Main process to calculate member similarities."""
    session = Session()
    try:
        print("Fetching members from the database...")
        logging.info("Fetching members from the database...")

        # Retrieve all unique members
        members_query = text("SELECT DISTINCT member_name FROM final_speeches")

        with engine.connect() as connection:
            members = connection.execute(members_query).fetchall()
            members = [member[0] for member in members]  # Extract member names

        print(f"Found {len(members)} members in the database.")
        logging.info(f"Found {len(members)} members in the database.")

        # Step 1: Create tables if they don't exist
        create_similarity_tables()

        # Step 2: Calculate pairwise similarities and store the results
        calculate_similarity_and_store(session, members)

        print("Similarity calculation and insertion completed successfully.")
        logging.info("Similarity calculation and insertion completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    print("Starting member similarity process...")
    logging.info("Starting member similarity process...")
    process_member_similarity()
    print("Member similarity process completed.")
    logging.info("Member similarity process completed.")
