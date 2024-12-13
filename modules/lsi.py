from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from multiprocessing import Pool, cpu_count
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

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

def create_lsi_table():
    """Create the LSI table in the database."""
    try:
        logging.info("Creating LSI table...")
        with engine.connect() as connection:
            connection.execute(text("DROP TABLE IF EXISTS lsi_speeches"))
            connection.execute(text("""
                CREATE TABLE lsi_speeches (
                    speech_id INT PRIMARY KEY,
                    lsi_vector FLOAT[]
                )
            """))
            connection.commit()  # Explicitly commit the transaction
        logging.info("LSI table created successfully.")
    except Exception as e:
        logging.error(f"Error creating LSI table: {e}")
        raise

def fetch_speeches_chunk(offset, limit):
    """Fetch a chunk of processed speeches from the database."""
    try:
        with engine.connect() as connection:
            logging.debug(f"Fetching speeches: offset={offset}, limit={limit}")
            result = connection.execute(
                text("SELECT speech_id, processed_speech FROM processed_speeches ORDER BY speech_id LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset}
            )
            return pd.DataFrame(result.fetchall(), columns=["speech_id", "processed_speech"])
    except Exception as e:
        logging.error(f"Error fetching speeches: {e}")
        raise


def compute_lsi_for_chunk(speeches_chunk, n_components=10):
    """Compute LSI vectors for a chunk of speeches."""
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
        tfidf_matrix = vectorizer.fit_transform(speeches_chunk["processed_speech"])

        svd = TruncatedSVD(n_components=n_components, random_state=42)
        lsi_matrix = svd.fit_transform(tfidf_matrix)

        return [(row["speech_id"], lsi_vector.tolist()) for row, lsi_vector in zip(speeches_chunk.to_dict(orient="records"), lsi_matrix)]
    except Exception as e:
        logging.error(f"Error during LSI computation: {e}")
        raise

def store_lsi_vectors_in_parallel(data_chunk):
    """Store LSI vectors for a chunk in the database with conflict handling."""
    engine_process = create_engine(f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}", echo=False)

    try:
        with engine_process.connect() as connection:
            with connection.begin():  # Start a transaction
                for speech_id, lsi_vector in data_chunk:
                    connection.execute(
                        text("""
                            INSERT INTO lsi_speeches (speech_id, lsi_vector)
                            VALUES (:speech_id, :lsi_vector)
                            ON CONFLICT (speech_id) DO NOTHING
                        """),
                        {"speech_id": speech_id, "lsi_vector": lsi_vector}
                    )
                logging.debug(f"Stored LSI vectors for {len(data_chunk)} speeches.")
    except Exception as e:
        logging.error(f"Error storing LSI vectors: {e}")
        raise
    finally:
        engine_process.dispose()  # Clean up the engine for this process



def process_lsi_in_parallel(total_speeches, chunk_size=1000):
    """Process LSI vectors in parallel."""
    num_chunks = (total_speeches + chunk_size - 1) // chunk_size
    logging.info(f"Processing {num_chunks} chunks with {cpu_count()} workers...")

    with Pool(cpu_count()) as pool:
        for i in range(num_chunks):
            offset = i * chunk_size
            logging.info(f"Fetching chunk {i + 1}/{num_chunks}...")
            speeches_chunk = fetch_speeches_chunk(offset, chunk_size)

            logging.info("Computing LSI vectors...")
            lsi_data = compute_lsi_for_chunk(speeches_chunk)

            logging.info("Storing LSI vectors...")
            pool.apply_async(store_lsi_vectors_in_parallel, (lsi_data,))

        pool.close()
        pool.join()

def apply_lsi_parallel():
    """Main function to compute LSI using multiprocessing."""
    create_lsi_table()  # Ensure the table is created before starting multiprocessing

    try:
        logging.info("Fetching total number of speeches...")
        with engine.connect() as connection:
            total_speeches = connection.execute(
                text("SELECT COUNT(*) FROM processed_speeches")
            ).scalar()
            logging.info(f"Total speeches: {total_speeches}")
    except Exception as e:
        logging.error(f"Error fetching total number of speeches: {e}")
        raise

    process_lsi_in_parallel(total_speeches)

if __name__ == "__main__":
    apply_lsi_parallel()
