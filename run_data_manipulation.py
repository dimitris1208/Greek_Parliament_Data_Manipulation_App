# Import the necessary functions from the modules
from modules.cluster_speeches import perform_clustering
from modules.import_csv_to_db import import_csv_to_postgresql
from modules.create_final_speeches import create_final_speeches_table
from modules.clear_null_values import delete_null_member_name_rows
from modules.preprocess import  create_processed_speeches_table,preprocess_and_store_speeches
from modules.create_tf_idf import process_corpus_and_insert
from modules.create_indexes import create_indexes
from modules.create_member_similarity import process_member_similarity
from modules.lsi import apply_lsi_parallel

def run_data_pipeline():
    """
    Run the data manipulation pipeline sequentially.
    """
    try:

        print("Starting the data manipulation pipeline...")
        # Step 1: Import CSV to Database
        print("\nStep 1: Importing CSV into the database...")
        import_csv_to_postgresql()
        print("Step 1 completed\n")

        # Step 2: Create `final_speeches` table
        print("Step 2: Creating the `final_speeches` table...")
        create_final_speeches_table()
        print("Step 2 completed\n")

        # Step 3: Clear rows with NULL `member_name`
        print("Step 3: Cleaning `final_speeches` table by removing rows with NULL `member_name`...")
        delete_null_member_name_rows()
        print("Step 3 completed\n")
        
        print("Step 4: Preprocessing , TF-IDF calculation  process...")
        create_processed_speeches_table()
        preprocess_and_store_speeches()

        print("Step 4 completed\n ")
        print("Step 5: Create Indexes using GIN postgres' indexing")
        create_indexes()
        print("Step 5: Completed \n")

        print("Step 6 : Creating member_similarity table")
        process_member_similarity()
        print("Step 6: Completed\n")

        print("Step 7 : Creating lsi vectors  table")
        apply_lsi_parallel()
        print("Step 7: Completed \n")

        print("Step 8 : Creating clusters  table")
        perform_clustering()

        print("Data manipulation pipeline completed successfully.")




    except Exception as e:
        print(f"An error occurred during the pipeline: {e}")

if __name__ == "__main__":
    run_data_pipeline()
