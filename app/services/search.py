import os
import spacy
import re
import unicodedata
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from greek_stemmer import GreekStemmer  # Ensure this is correctly imported
from sqlalchemy.dialects.postgresql import ARRAY

# Load environment variables
load_dotenv()

# Fetch database credentials from .env
db_user = os.getenv("db_user")
db_password = os.getenv("db_password")
db_host = os.getenv("db_host")
db_port = os.getenv("db_port")
db_name = os.getenv("db_name")

# Create the database engine
engine = create_engine(f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}", echo=False)

# Load the Greek language model from spaCy
nlp = spacy.load("el_core_news_sm")

# Load stopwords from spaCy
stopwords = nlp.Defaults.stop_words

# Initialize Greek stemmer
greek_stemmer = GreekStemmer()  # Assuming GreekStemmer has been correctly initialized


def remove_accents(text):
    """Remove accents from Greek words."""
    if not text:
        return ''
    normalized_text = unicodedata.normalize('NFD', text)
    accent_removed_text = ''.join(
        char for char in normalized_text if unicodedata.category(char) != 'Mn'
    )
    return unicodedata.normalize('NFC', accent_removed_text)


def preprocess_query(query, nlp, greek_stopwords, stemmer):
    """
    Preprocess the search query by:
    1. Removing unwanted patterns (special characters and punctuation)
    2. Converting to lowercase
    3. Removing accents
    4. Tokenizing
    5. Removing stopwords
    6. Stemming
    """
    # Remove unwanted characters and punctuation (similar to the chunk preprocessing)
    UNWANTED_PATTERN = re.compile(r'[0-9@#$%^&*()\-\_=+\[\]{};:\'",.<>/?\\|`~!]')  # Define unwanted pattern
    TAB_PATTERN = re.compile(r'\t+')  # Define tab pattern

    # Step 1: Uppercase the query
    query = query.upper()

    # Step 2: Remove unwanted patterns and tabs from the query
    query = UNWANTED_PATTERN.sub('', query)
    query = TAB_PATTERN.sub('', query)

    # Step 3: Remove accents
    query = remove_accents(query)

    # Step 4: Tokenize the query using spaCy
    doc = nlp(query)

    # Step 5: Process tokens by removing stopwords and applying stemming
    processed_query = []

    for token in doc:
        # Skip if token is empty, a stopword, or a single character
        cleaned_token = token.text
        if cleaned_token in greek_stopwords or len(cleaned_token) <= 1:
            continue

        # Apply stemming
        stemmed_token = stemmer.stem(cleaned_token)

        # Add the processed (stemmed) token
        if stemmed_token:
            stemmed_token_final= stemmed_token.lower()
            processed_query.append(stemmed_token_final)

    # Step 6: Return the final preprocessed query
    return " ".join(processed_query)





def search_speeches(query):
    """
    Search for speeches based on a query (multiple terms).
    """
    try:
        # Preprocess the query before performing the search
        processed_query = preprocess_query(query, nlp, stopwords, greek_stemmer)
        print(f"Processed query: {processed_query}")  # Debugging log for the processed query

        # Split the query into individual terms for multi-term search
        terms = processed_query.split()  # Processed query will have individual terms
        if not terms:
            print("No terms found in query after preprocessing.")  # Debug log if no valid terms
            return []

        # Create a dictionary to hold speech IDs and their aggregated TF-IDF scores
        speech_scores = {}

        # Use full-text search for matching terms in the term_vector column
        for term in terms:
            sql_query = text("""
                SELECT speech_id, tfidf_value 
                FROM tfidf_values 
                WHERE term = :term
            """)

            # Execute the query with the current term
            with engine.connect() as connection:
                result = connection.execute(sql_query, {'term': term}).fetchall()

            print(f"Result for term '{term}': {result}")  # Debug log for query result

            # Aggregate the TF-IDF values for each speech
            for row in result:
                speech_id = row[0]  # Get the speech ID
                tfidf_value = row[1]  # Get the TF-IDF value

                # If speech_id already in the dictionary, add the TF-IDF value, otherwise, initialize it
                if speech_id in speech_scores:
                    speech_scores[speech_id] += tfidf_value
                else:
                    speech_scores[speech_id] = tfidf_value

        # If no speeches were found
        if not speech_scores:
            print("No matching terms found.")  # Debug log if no speeches matched
            return []

        # Get the speech IDs that we have aggregated TF-IDF scores for
        speech_ids = list(speech_scores.keys())

        # Now retrieve the speeches themselves along with their aggregated scores
        sql_speeches_query = text("""
            SELECT id, merged_speech, member_name, sitting_date, political_party, roles
            FROM final_speeches 
            WHERE id = ANY(:speech_ids)
        """)

        # Pass the speech_ids to the query
        with engine.connect() as connection:
            speeches_result = connection.execute(sql_speeches_query, {'speech_ids': speech_ids}).fetchall()


        # Format the results with the aggregated TF-IDF score
        results_with_tfidf = []
        for speech in speeches_result:
            speech_id = speech[0]  # Access by index
            merged_speech = speech[1]  # Access by index
            member_name = speech[2]  # Access by index
            sitting_date = speech[3]  # Access by index
            political_party = speech[4]  # Access by index
            roles = speech[5]  # Access by index

            # Get the aggregated TF-IDF score for this speech
            total_tfidf = speech_scores.get(speech_id, 0)  # Default to 0 if no score is found

            results_with_tfidf.append({
                'speech': {
                    'id': speech_id,
                    'merged_speech': merged_speech,
                    'member_name': member_name,
                    'sitting_date': sitting_date,
                    'political_party': political_party,
                    'roles': roles
                },
                'tfidf_value': total_tfidf  # Display the aggregated TF-IDF score
            })

        # Order the results by TF-IDF value in descending order
        results_with_tfidf = sorted(results_with_tfidf, key=lambda x: x['tfidf_value'], reverse=True)


        return results_with_tfidf

    except Exception as e:
        print(f"Error occurred during search: {e}")
        return []









