import os
import pandas as pd
from sklearn.cluster import KMeans
from sqlalchemy import create_engine, text
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
engine = create_engine(f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}", echo=True)
print("Database connection initialized successfully.")

# Logging setup
logging.basicConfig(level=logging.INFO)


def fetch_lsi_vectors():
    """Fetch LSI vectors from the database."""
    print("Fetching LSI vectors from the database...")
    try:
        with engine.connect() as connection:
            query = text("SELECT speech_id, lsi_vector FROM lsi_speeches")
            result = connection.execute(query)
            data = result.fetchall()

            if not data:
                print("No LSI vectors found in the database.")
                return [], pd.DataFrame()

            print(f"Fetched {len(data)} LSI vectors. Showing first 5 rows:")
            for row in data[:5]:  # Print sample data
                print(row)

            speech_ids = [row[0] for row in data]
            lsi_vectors = [row[1] for row in data]  # LSI vectors as arrays

            return speech_ids, pd.DataFrame(lsi_vectors)
    except Exception as e:
        print(f"Error fetching LSI vectors: {e}")
        return [], pd.DataFrame()


def store_clusters(speech_ids, clusters):
    """Store clustering results in a new table."""
    print("Storing clustering results in the database...")
    try:
        with engine.connect() as connection:
            print("Dropping existing 'clustered_speeches' table...")
            connection.execute(text("DROP TABLE IF EXISTS clustered_speeches"))
            connection.commit()  # Commit the drop

            print("Creating new 'clustered_speeches' table...")
            connection.execute(text("""
                CREATE TABLE clustered_speeches (
                    speech_id INT PRIMARY KEY,
                    cluster_id INT
                )
            """))
            connection.commit()
            print("Table 'clustered_speeches' created successfully.")

            # Insert the clustering results
            print("Inserting clustering results...")
            for speech_id, cluster_id in zip(speech_ids, clusters):
                connection.execute(text("""
                    INSERT INTO clustered_speeches (speech_id, cluster_id)
                    VALUES (:speech_id, :cluster_id)
                """), {"speech_id": speech_id, "cluster_id": cluster_id})
            connection.commit()
            print(f"Inserted {len(speech_ids)} rows into 'clustered_speeches'.")
    except Exception as e:
        print(f"Error storing clustering results: {e}")


def perform_clustering(n_clusters=10):
    """Main function to fetch LSI vectors, perform clustering, and store results."""
    print("Starting clustering process...")
    speech_ids, lsi_vectors = fetch_lsi_vectors()

    # Check if LSI vectors are empty
    if lsi_vectors.empty or not speech_ids:
        print("No LSI vectors found. Exiting clustering process.")
        return

    print("Performing K-Means clustering...")
    try:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(lsi_vectors)
        print(f"Clustering completed. Assigned {n_clusters} clusters.")

        print("Storing clustering results...")
        store_clusters(speech_ids, clusters)
        print("Clustering results stored successfully.")
    except Exception as e:
        print(f"Error during clustering: {e}")


if __name__ == "__main__":
    print("Executing clustering script...")
    perform_clustering(n_clusters=10)
    print("Clustering script execution completed.")
