import pandas as pd
from sqlalchemy import create_engine
import yaml
import psycopg2



def load_config(file_path="config.yaml"):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

config = load_config()
db_config = config["database"]

# Charge credentials
SUPABASE_URL = db_config["url"]
DB_USER = db_config["user"]
DB_PASSWORD = db_config["password"]
DB_NAME = db_config["name"]
DB_PORT = db_config["port"]
TABLE_NAME = db_config["table"]

# Create conection to DB supabase
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{SUPABASE_URL}:{DB_PORT}/{DB_NAME}")

# Cargar el archivo CSV
csv_file = "weather_data.csv"
df = pd.read_csv(csv_file)

# Read the CSV into a DataFrame, only take first 11000 rows
df = pd.read_csv(csv_file, nrows=11000)


# Create connection with psycopg2 to execute SQL
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=SUPABASE_URL,
    port=DB_PORT
)
cursor = conn.cursor()

# Generate table structure
columns = []
for col, dtype in zip(df.columns, df.dtypes):
    if "int" in str(dtype):
        sql_type = "INTEGER"
    elif "float" in str(dtype):
        sql_type = "FLOAT"
    elif "bool" in str(dtype):
        sql_type = "BOOLEAN"
    else:
        sql_type = "TEXT"
    columns.append(f'"{col}" {sql_type}')

# Create table in PostgreSQL if it does not exist
create_table_query = f'''
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
   id SERIAL PRIMARY KEY,
    {", ".join(columns)}
);
'''
cursor.execute(create_table_query)
conn.commit()

# Close cursor and connection
cursor.close()
conn.close()

# Upload data to Supabase
df.to_sql(TABLE_NAME, engine, if_exists="append", index=False)

print(f"Table '{TABLE_NAME}' created and data successfully inserted into Supabase.")


#READ DB

# Read data from Supabase
df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", engine)
# Display the first 5 rows
print(df)
