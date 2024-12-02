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
engine = create_engine(f'postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}', echo=True)

create_table_query = """
CREATE TABLE public.final_speeches AS
SELECT
    ROW_NUMBER() OVER () AS id, -- Generate a unique ID for each grouped row
    member_name,
    sitting_date,
    parliamentary_period,
    parliamentary_session,
    parliamentary_sitting,
    political_party,
    government,
    member_region,
    roles,
    member_gender,
    STRING_AGG(speech, ' ') AS merged_speech -- Combine speeches into a single row
FROM
    speeches
GROUP BY
    member_name,
    sitting_date,
    parliamentary_period,
    parliamentary_session,
    parliamentary_sitting,
    political_party,
    government,
    member_region,
    roles,
    member_gender
ORDER BY
    sitting_date, parliamentary_period, parliamentary_session, parliamentary_sitting;
"""

def create_final_speeches_table():
    """
    Execute the SQL command to create the `final_speeches` table with progress messages.
    """
    try:
        print("Connecting to the database...")
        with engine.connect() as connection:
            print("Connection established.")

            # Start a transaction
            with connection.begin():
                print("Checking if `final_speeches` table exists...")
                connection.execute(text("DROP TABLE IF EXISTS public.final_speeches;"))
                print("Old `final_speeches` table dropped (if it existed).")

                print("Creating the `final_speeches` table...")
                connection.execute(text(create_table_query))
                print("Table `final_speeches` created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")


def verify_table_contents():
    """
    Verify the contents of the `final_speeches` table.
    """
    try:
        print("Fetching data from `final_speeches`...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM public.final_speeches LIMIT 10;"))
            rows = result.fetchall()
            if rows:
                print("Sample rows from `final_speeches`:")
                for row in rows:
                    print(row)
            else:
                print("`final_speeches` table is empty.")
    except Exception as e:
        print(f"An error occurred while verifying the table: {e}")


if __name__ == "__main__":
    print("Starting the process to create the `final_speeches` table...")
    create_final_speeches_table()
    verify_table_contents()
    print("Process completed.")
