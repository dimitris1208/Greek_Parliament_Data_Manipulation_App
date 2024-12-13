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
    Search for speeches based on a query (multiple terms), return those containing all terms,
    or if no such speech, return the best matching speeches based on TF-IDF score > 0.2.
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
        speeches_with_all_terms = {}

        # Use full-text search for matching terms in the term_vector column
        for term in terms:
            sql_query = text("""
                SELECT speech_id, tfidf_value 
                FROM tfidf_values 
                WHERE term = :term AND tfidf_value > 0.2  -- Filter by tfidf_value > 0.2
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
                    speech_scores[speech_id].append(tfidf_value)
                else:
                    speech_scores[speech_id] = [tfidf_value]

                # Check if this speech contains all terms and store it separately
                if speech_id not in speeches_with_all_terms:
                    speeches_with_all_terms[speech_id] = set()
                speeches_with_all_terms[speech_id].add(term)

        # Identify speeches that contain all terms
        complete_match_speeches = {
            speech_id: data for speech_id, data in speeches_with_all_terms.items()
            if len(data) == len(terms)  # All terms must be present in the speech
        }

        # If no speeches contain all terms, return the best matching speeches based on TF-IDF scores
        results_with_tfidf = []
        if complete_match_speeches:
            # Only include speeches that contain all the query terms
            for speech_id in complete_match_speeches:
                # Calculate the aggregated TF-IDF score (average of all terms for the speech)
                aggregated_score = sum(speech_scores[speech_id]) / len(speech_scores[speech_id])

                # Fetch the corresponding speech details from final_speeches table
                sql_speeches_query = text("""
                    SELECT id, merged_speech, member_name, sitting_date, political_party, roles
                    FROM final_speeches 
                    WHERE id = :speech_id
                """)

                with engine.connect() as connection:
                    speech_result = connection.execute(sql_speeches_query, {'speech_id': speech_id}).fetchone()

                if speech_result:
                    # Format the sitting_date to show only the date part (YYYY-MM-DD)
                    formatted_sitting_date = speech_result[3].strftime('%Y-%m-%d') if speech_result[3] else None

                    results_with_tfidf.append({
                        'speech': {
                            'id': speech_result[0],
                            'merged_speech': speech_result[1],
                            'member_name': speech_result[2],
                            'sitting_date': formatted_sitting_date,  # Use formatted date here
                            'political_party': speech_result[4],
                            'roles': speech_result[5]
                        },
                        'tfidf_value': aggregated_score  # Display the aggregated TF-IDF score
                    })


        else:
            # If no speech has all the terms, return the top speeches based on individual term matches
            for speech_id, scores in speech_scores.items():
                # Calculate the average score for each speech
                avg_score = sum(scores) / len(scores)

                # Only include speeches with an aggregated score > 0.2
                if avg_score > 0.2:
                    sql_speeches_query = text("""
                        SELECT id, merged_speech, member_name, sitting_date, political_party, roles
                        FROM final_speeches 
                        WHERE id = :speech_id
                    """)

                    with engine.connect() as connection:
                        speech_result = connection.execute(sql_speeches_query, {'speech_id': speech_id}).fetchone()

                    if speech_result:
                        results_with_tfidf.append({
                            'speech': {
                                'id': speech_result[0],
                                'merged_speech': speech_result[1],
                                'member_name': speech_result[2],
                                'sitting_date': speech_result[3],
                                'political_party': speech_result[4],
                                'roles': speech_result[5]
                            },
                            'tfidf_value': avg_score  # Display the aggregated TF-IDF score
                        })

        # Order the results by TF-IDF value in descending order
        results_with_tfidf = sorted(results_with_tfidf, key=lambda x: x['tfidf_value'], reverse=True)

        return results_with_tfidf

    except Exception as e:
        print(f"Error occurred during search: {e}")
        return []












