import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd

# Load environment variables
load_dotenv()

# Database connection details
db_user = os.getenv("db_user")
db_password = os.getenv("db_password")
db_host = os.getenv("db_host")
db_port = os.getenv("db_port")
db_name = os.getenv("db_name")

# Create the database engine
engine = create_engine(f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}", echo=True)
Session = sessionmaker(bind=engine)

# Load the Greek language model from spaCy
try:
    nlp = spacy.load("el_core_news_sm")
except OSError:
    raise Exception("Greek language model not found. Please run `python -m spacy download el_core_news_sm`.")

# Load stopwords from spaCy
stopwords = nlp.Defaults.stop_words

CHUNK_SIZE = 100  # Number of rows to process per chunk


def preprocess_and_lemmatize(text):
    """
    Preprocess text: lowercase, remove stopwords, and lemmatize.
    """
    doc = nlp(text.lower())  # Convert to lowercase and process text
    lemmatized_tokens = [
        token.lemma_ for token in doc
        if token.text.lower() not in stopwords and token.is_alpha  # Exclude stopwords and non-alphabetic tokens
    ]
    return ' '.join(lemmatized_tokens)


def save_preprocessed_data(preprocessed_table):
    """
    Save preprocessed data into a new table in smaller chunks.
    """
    try:
        session = Session()

        # Fetch total number of rows to calculate progress
        total_rows = session.execute(text("SELECT COUNT(*) FROM final_speeches")).scalar()
        print(f"Total rows to process: {total_rows}")

        # Create a new table for the preprocessed data
        session.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {preprocessed_table} (
                id INT PRIMARY KEY,
                preprocessed_speech TEXT NOT NULL
            )
        """))
        session.commit()

        offset = 0
        while offset < total_rows:
            # Fetch a chunk of rows
            result = session.execute(
                text("SELECT id, merged_speech FROM final_speeches ORDER BY id LIMIT :limit OFFSET :offset"),
                {"limit": CHUNK_SIZE, "offset": offset}
            ).fetchall()

            print(f"Processing rows {offset + 1} to {offset + len(result)}...")

            preprocessed_data = []
            for row in result:
                speech_id, merged_speech = row  # Unpack tuple
                preprocessed_text = preprocess_and_lemmatize(merged_speech)
                preprocessed_data.append((speech_id, preprocessed_text))

            # Insert the preprocessed data into the new table
            session.execute(
                text(f"INSERT INTO {preprocessed_table} (id, preprocessed_speech) VALUES (:id, :speech)"),
                [{"id": speech_id, "speech": speech} for speech_id, speech in preprocessed_data]
            )
            session.commit()

            offset += CHUNK_SIZE
            print(f"Completed rows {offset}/{total_rows}.")

        print(f"Data saved to table `{preprocessed_table}` successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()


def calculate_tfidf(preprocessed_table, tfidf_table):
    """
    Calculate TF-IDF for preprocessed speeches and save to a new table.
    """
    try:
        session = Session()

        # Fetch preprocessed data
        result = session.execute(text(f"SELECT id, preprocessed_speech FROM {preprocessed_table}")).fetchall()

        # Prepare data for TF-IDF calculation
        ids = [row[0] for row in result if row[1]]  # Only include rows with non-empty text
        documents = [row[1] for row in result if row[1]]

        if not documents:
            print("No documents available for TF-IDF calculation.")
            return

        # Calculate TF-IDF
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(documents)
        terms = vectorizer.get_feature_names_out()

        print("TF-IDF calculation complete.")

        # Create the TF-IDF table
        session.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {tfidf_table} (
                speech_id INT NOT NULL,
                term TEXT NOT NULL,
                tfidf_value FLOAT NOT NULL
            )
        """))
        session.commit()

        # Insert TF-IDF values into the table
        for i, speech_id in enumerate(ids):
            tfidf_values = tfidf_matrix[i].toarray()[0]
            data = [
                {"speech_id": speech_id, "term": term, "tfidf_value": value}
                for term, value in zip(terms, tfidf_values)
                if value > 0  # Only store non-zero TF-IDF values
            ]
            if data:  # Ensure there is data to insert
                session.execute(
                    text(f"INSERT INTO {tfidf_table} (speech_id, term, tfidf_value) VALUES (:speech_id, :term, :tfidf_value)"),
                    data
                )
                session.commit()
                print(f"Inserted TF-IDF values for speech_id {speech_id}.")
            else:
                print(f"No TF-IDF values to insert for speech_id {speech_id}.")

        print(f"TF-IDF data saved to table `{tfidf_table}` successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()




if __name__ == "__main__":
    print("Starting the preprocessing and TF-IDF calculation process...")
    save_preprocessed_data("final_speeches_preprocessed")
    calculate_tfidf("final_speeches_preprocessed", "final_speeches_tfidf")
    print("Process completed.")
