import pandas as pd
from sqlalchemy import create_engine
import psycopg
import os
from python-dotenv import load_dotenv

load_dotenv()

# Database connection details
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_host = os.getenv('db_host')
db_port = os.getenv('db_port')
db_name = os.getenv('db_name')
table_name = 'speeches'  # Table name in your PostgreSQL database

# Path to the CSV file
csv_file_path = "../data/Greek_Parliament_Proceedings_1989_2020.csv"

# Batch size for processing chunks
chunk_size = 10000

# Create the database engine
engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')


def preprocess_chunk(chunk):
    """
    Preprocess each chunk of the CSV: clean and format data.
    """
    # Convert sitting_date from DD/MM/YYYY to YYYY-MM-DD
    chunk['sitting_date'] = pd.to_datetime(chunk['sitting_date'], format='%d/%m/%Y', errors='coerce')

    # Fill NaN with None (SQL NULL)
    chunk = chunk.where(pd.notnull(chunk), None)

    return chunk


def import_csv_to_postgresql():
    """
    Import a large CSV file into the PostgreSQL database in chunks.
    """
    try:
        # Process the CSV in chunks
        for chunk in pd.read_csv(csv_file_path, chunksize=chunk_size, encoding='utf-8'):
            # Preprocess the chunk
            chunk = preprocess_chunk(chunk)

            # Write the chunk to the database
            chunk.to_sql(table_name, con=engine, if_exists='append', index=False)

            print(f"Imported a chunk of size {len(chunk)}")

        print("CSV file imported successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    import_csv_to_postgresql()
