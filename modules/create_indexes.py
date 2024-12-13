import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
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

def create_indexes():
    """Create indexes on the tfidf_values table."""
    session = Session()
    try:
        logging.info("Creating index on the 'term' column of tfidf_values table...")

        # Add the term_vector column if it doesn't exist
        session.execute(
            text("""
                ALTER TABLE tfidf_values ADD COLUMN IF NOT EXISTS term_vector tsvector;

                -- Update the term_vector column with the proper tsvector
                UPDATE tfidf_values SET term_vector = to_tsvector('greek', term);

                -- Create an index on the term_vector column using GIN
                CREATE INDEX IF NOT EXISTS idx_tfidf_values_term_vector ON tfidf_values USING gin (term_vector);
            """)
        )
        session.commit()
        logging.info("Index on 'term' column created successfully.")

    except Exception as e:
        session.rollback()
        logging.error(f"An error occurred while creating indexes: {e}")
    finally:
        session.close()



if __name__ == "__main__":
    logging.info("Starting index creation process...")
    create_indexes()
    logging.info("Index creation process completed.")
