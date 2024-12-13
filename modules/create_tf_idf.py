import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
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

def create_tfidf_table():
    """Create the tfidf_values table if it doesn't exist."""
    session = Session()
    try:
        logging.info("Creating tfidf_values table...")

        session.execute(
            text("""
                CREATE TABLE IF NOT EXISTS tfidf_values (
                    speech_id INT,
                    term TEXT,
                    tfidf_value FLOAT,
                    PRIMARY KEY (speech_id, term)
                );
            """)
        )
        session.commit()
        logging.info("tfidf_values table is ready.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error creating tfidf_values table: {e}")
    finally:
        session.close()

def insert_tfidf_values_to_db(speeches, vectorizer, speech_ids, session):
    """Insert TF-IDF values for the corpus into the database, ensuring correct speech_id mapping."""
    # Create the sparse matrix using TfidfVectorizer (using sparse format)
    tfidf_matrix = vectorizer.fit_transform(speeches)  # This is a sparse matrix
    terms = vectorizer.get_feature_names_out()

    # Collect TF-IDF values in a list for batch insertion
    tfidf_values = []
    for doc_idx, doc in enumerate(tfidf_matrix):
        for term_idx, value in enumerate(doc.toarray()[0]):  # Convert sparse to dense for iteration
            if value > 0:  # Only insert non-zero values
                tfidf_values.append((speech_ids[doc_idx], terms[term_idx], value))

    try:
        for i in range(0, len(tfidf_values), 100):  # Batch insert to avoid memory overload
            batch = tfidf_values[i:i + 100]
            session.execute(
                text("""
                    INSERT INTO tfidf_values (speech_id, term, tfidf_value)
                    VALUES (:speech_id, :term, :tfidf_value)
                    ON CONFLICT (speech_id, term) DO UPDATE
                    SET tfidf_value = EXCLUDED.tfidf_value;
                """),
                [{"speech_id": row[0], "term": row[1], "tfidf_value": row[2]} for row in batch]
            )
        session.commit()
        logging.info(f"Inserted {len(tfidf_values)} rows into the tfidf_values table.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error inserting TF-IDF values: {e}")

def process_corpus_and_insert():
    """Fetch corpus from the processed_speeches table, calculate TF-IDF and insert into the table."""
    session = Session()
    try:
        logging.info("Fetching processed speeches from processed_speeches table...")
        result = session.execute(text("SELECT speech_id, processed_speech FROM processed_speeches")).fetchall()

        # Extract speeches and speech_ids
        speeches = [row[1] for row in result]
        speech_ids = [row[0] for row in result]

        # Initialize TfidfVectorizer (using stopwords)
        vectorizer = TfidfVectorizer(stop_words="english")  # You can customize the stopwords

        # Create the tfidf_values table if it doesn't exist
        create_tfidf_table()

        # Insert the TF-IDF values into the database
        insert_tfidf_values_to_db(speeches, vectorizer, speech_ids, session)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    logging.info("Starting TF-IDF insertion...")
    process_corpus_and_insert()
    logging.info("TF-IDF values inserted successfully.")
