from sqlalchemy import create_engine, text
import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection details
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_host = os.getenv('db_host')
db_port = os.getenv('db_port')
db_name = os.getenv('db_name')

# Create the database engine
engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}', echo=True)

def delete_null_member_name_rows():
    """
    Delete rows with NULL values in the 'member_name' column.
    """
    delete_query = """
    DELETE FROM final_speeches
    WHERE member_name IS NULL;
    """
    try:
        print("Connecting to the database...")
        with engine.connect() as connection:
            print("Connection established.")

            # Start a transaction
            with connection.begin():
                print("Deleting rows where 'member_name' is NULL...")
                result = connection.execute(text(delete_query))
                print(f"Deleted {result.rowcount} rows from the `final_speeches` table.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    print("Starting the process to clean the `final_speeches` table...")
    delete_null_member_name_rows()
    print("Process completed.")
