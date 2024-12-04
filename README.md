# Greek Parliament Speeches: Information Retrieval Project

This project processes and analyzes speeches from the Greek Parliament, focusing on transforming raw data into a PostgreSQL database and providing data management functionality through Python scripts.

---

## Prerequisites

### Software Requirements
- **Python**: Version 3.10 - 3.12 ([Download Python](https://www.python.org/downloads/))
- **PostgreSQL**: Version 14 or higher, including pgAdmin ([Download PostgreSQL](https://www.postgresql.org/download/))
- **Microsoft C++ Build Tools**: Required for some Python dependencies ([Download Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/))


---

## Project Setup

### Environment Variables

Create a `.env` file in the root directory with the following format:

- `DB_USER=your_database_username`
- `DB_PASSWORD=your_database_password`
- `DB_HOST=localhost`
- `DB_PORT=5432`
- `DB_NAME=greek_parliament`


## Directory Structure



---



### Greek Stemmer Library Modification

For the GreekStemmer library to work properly with the correct encoding, modify the __init__.py file of the library as follows:

```python

class GreekStemmer:
    def load_settings(self):
        custom_rules = ""
        with open(os.path.join(
                  os.path.dirname(__file__), 'stemmer.yml'), 'r', encoding='utf-8') as f:
            custom_rules = yaml.load(f.read(), Loader=yaml.FullLoader)
        return custom_rules
        
```

This ensures that the stemmer.yml file is loaded with the correct encoding.



---

## Usage

### 1. Set Up the Virtual Environment




### 2. Import the CSV Data
Run the script to import the CSV data into your PostgreSQL database:
  `python modules/import_csv_to_db.py`


### 3. Create the Final Speeches Table
After importing the data, create the `final_speeches` table:
 `python modules/create_final_speeches.py`


### 4. Clean Up Data
Remove rows with NULL values in the `member_name` column:
 `python modules/clear_null_values.py`

---

## Notes

- Ensure PostgreSQL is running before executing the scripts.
- Place the `Greek_Parliament_Proceedings_1989_2020.csv` file in the `data` folder.
- The `.env` file is critical for securely passing database credentials.

---




