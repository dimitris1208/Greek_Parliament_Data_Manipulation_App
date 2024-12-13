import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import spacy
import pandas as pd
import logging
import unicodedata
import re
import pickle
from multiprocessing import Pool
from greek_stemmer import GreekStemmer  # type: ignore # Ensure this is correctly imported
from tqdm import tqdm

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

# Load the Greek language model from SpaCy
try:
    nlp = spacy.load("el_core_news_sm")
except OSError:
    raise Exception("Greek language model not found. Please run python -m spacy download el_core_news_sm.")

# Load stopwords from SpaCy
stopwords = nlp.Defaults.stop_words

# Initialize Greek stemmer
greek_stemmer = GreekStemmer()  # Assuming GreekStemmer has been correctly initialized

CHUNK_SIZE = 100  # Process 100 speeches at a time
BATCH_SIZE = 100  # Batch size for inserts into the database

# Logging setup
logging.basicConfig(level=logging.INFO)


def remove_accents(text):
    """Remove accents from Greek words."""
    if not text:
        return ''
    normalized_text = unicodedata.normalize('NFD', text)
    accent_removed_text = ''.join(
        char for char in normalized_text if unicodedata.category(char) != 'Mn'
    )
    return unicodedata.normalize('NFC', accent_removed_text)


def preprocess_documents_chunk(texts, nlp, greek_stopwords, UNWANTED_PATTERN, TAB_PATTERN, stemmer, batch_size=250,
                               n_process=1):
    """
    Generator that preprocesses texts in chunks to manage memory usage.
    """
    for doc in nlp.pipe(texts, batch_size=batch_size, n_process=n_process, disable=["parser", "ner"]):
        tokens = []
        for token in doc:
            # Remove unwanted patterns
            cleaned_token = UNWANTED_PATTERN.sub('', token.text)
            cleaned_token = TAB_PATTERN.sub('', cleaned_token)

            # Uppercase the word and remove accents before passing to stemmer
            cleaned_token = cleaned_token.upper()  # Uppercase
            cleaned_token = remove_accents(cleaned_token)  # Remove accents

            # Skip if token is empty, a stopword, or a single character
            if (not cleaned_token) or (cleaned_token.lower() in greek_stopwords) or (len(cleaned_token) == 1):
                continue

            # Apply stemming based on POS tag
            pos = token.pos_
            try:
                if pos == "NOUN":
                    stemmed = stemmer.stem(cleaned_token)  # Stemming method
                elif pos == "VERB":
                    stemmed = stemmer.stem(cleaned_token)  # Stemming method
                elif pos in {"ADJ", "ADV"}:
                    stemmed = stemmer.stem(cleaned_token)  # Stemming method
                elif pos == "PROPN":
                    stemmed = stemmer.stem(cleaned_token)  # Stemming method
                else:
                    stemmed = stemmer.stem(cleaned_token)  # Stemming method

                if stemmed:
                    tokens.append(stemmed)
            except Exception as e:
                print(f"Error stemming word '{cleaned_token}': {e}")
                continue

        preprocessed_text = ' '.join(tokens)
        yield preprocessed_text


def create_processed_speeches_table():
    """Create the processed_speeches table if it doesn't exist."""
    session = Session()
    try:
        logging.info("Creating processed_speeches table...")
        session.execute(
            text("""
                CREATE TABLE IF NOT EXISTS processed_speeches (
                    speech_id INT PRIMARY KEY,
                    processed_speech TEXT NOT NULL
                );
            """)
        )
        session.commit()
        logging.info("processed_speeches table is ready.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error creating processed_speeches table: {e}")
    finally:
        session.close()


def save_processed_speeches(speeches_data):
    """Insert preprocessed speeches into the database in batches."""
    session = Session()
    try:
        logging.info("Inserting preprocessed speeches into the database...")

        # Insert the preprocessed speeches in batches
        for i in range(0, len(speeches_data), BATCH_SIZE):
            batch = speeches_data[i:i + BATCH_SIZE]
            session.execute(
                text("""
                    INSERT INTO processed_speeches (speech_id, processed_speech)
                    VALUES (:speech_id, :processed_speech)
                    ON CONFLICT (speech_id) DO UPDATE
                    SET processed_speech = EXCLUDED.processed_speech;
                """),
                [{"speech_id": row[0], "processed_speech": row[1]} for row in batch]
            )

        session.commit()
        logging.info(f"Inserted {len(speeches_data)} rows into the processed_speeches table.")
    except Exception as e:
        session.rollback()
        logging.error(f"An error occurred: {e}")
    finally:
        session.close()


def preprocess_and_store_speeches():
    """Preprocess speeches and store them into the processed_speeches table."""
    session = Session()
    try:
        logging.info("Fetching speeches from final_speeches table...")
        result = session.execute(text("SELECT id, merged_speech FROM final_speeches ")).fetchall()

        # Process the data in chunks
        chunks = [result[i:i + CHUNK_SIZE] for i in range(0, len(result), CHUNK_SIZE)]
        logging.info(f"Split speeches into {len(chunks)} chunks.")

        processed_speeches_data = []
        with Pool(3) as pool:  # Process in parallel with 3 processes
            logging.info(f"Processing chunks using 3 CPU cores...")
            results = pool.map(process_chunk, chunks)

        # Flatten results into a list of processed speeches
        for sublist in results:
            for row in sublist:
                processed_speeches_data.append((row[0], row[1]))  # Append speech_id and processed_speech

        # Save the processed speeches to the database
        save_processed_speeches(processed_speeches_data)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        session.close()


def process_chunk(chunk):
    """Process a chunk of speeches (for multiprocessing)."""
    logging.info(f"Processing chunk with {len(chunk)} speeches...")
    speeches = [row[1] for row in chunk]  # Extract speeches
    speech_ids = [row[0] for row in chunk]  # Extract speech_ids

    # Preprocess the speeches with the required arguments
    UNWANTED_PATTERN = re.compile(r'[0-9@#$%^&*()\-\_=+\[\]{};:\'",.<>/?\\|`~!]')
    TAB_PATTERN = re.compile(r'\t+')

    # Process each chunk with the correct arguments
    preprocessed_speeches = [
        preprocessed_speech
        for preprocessed_speech in preprocess_documents_chunk(
            texts=speeches,
            nlp=nlp,
            greek_stopwords=stopwords,
            UNWANTED_PATTERN=UNWANTED_PATTERN,
            TAB_PATTERN=TAB_PATTERN,
            stemmer=greek_stemmer
        )
    ]

    return [(speech_id, preprocessed_speech) for speech_id, preprocessed_speech in
            zip(speech_ids, preprocessed_speeches)]


if __name__ == "__main__":
    logging.info("Starting the preprocessing of speeches...")

    # Step 1: Create processed_speeches table (ensure it's ready)
    create_processed_speeches_table()

    # Step 2: Preprocess and store speeches (skip TF-IDF calculation)
    preprocess_and_store_speeches()

    logging.info("Preprocessing completed successfully.")
