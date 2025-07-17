import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

create_userfinancials_sql = '''
CREATE TABLE IF NOT EXISTS "UserFinancials" (
    session_id UUID PRIMARY KEY,
    gross_salary NUMERIC(15, 2),
    basic_salary NUMERIC(15, 2),
    hra_received NUMERIC(15, 2),
    rent_paid NUMERIC(15, 2),
    deduction_80c NUMERIC(15, 2),
    deduction_80d NUMERIC(15, 2),
    standard_deduction NUMERIC(15, 2),
    professional_tax NUMERIC(15, 2),
    tds NUMERIC(15, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
'''

create_taxcomparison_sql = '''
CREATE TABLE IF NOT EXISTS "TaxComparison" (
    session_id UUID PRIMARY KEY,
    tax_old_regime NUMERIC(15, 2),
    tax_new_regime NUMERIC(15, 2),
    best_regime VARCHAR(10),
    selected_regime VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
'''

def main():
    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        print("Connection successful!")
        cursor = connection.cursor()
        cursor.execute(create_userfinancials_sql)
        cursor.execute(create_taxcomparison_sql)
        connection.commit()
        print("Tables created or already exist.")
        cursor.close()
        connection.close()
        print("Connection closed.")
    except Exception as e:
        print(f"Failed to connect or create tables: {e}")

if __name__ == '__main__':
    main() 