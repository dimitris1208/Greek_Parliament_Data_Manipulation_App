# Greek Parliament Speeches: Information Retrieval Project

This project processes and analyzes speeches from the Greek Parliament, focusing on transforming raw data into a PostgreSQL database and providing data management functionality through Python scripts.

---

## Prerequisites

### Software Requirements
- **Python**: Version 3.10 or higher ([Download Python](https://www.python.org/downloads/))
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




