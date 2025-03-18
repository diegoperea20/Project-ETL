import pandas as pd
from sqlalchemy import create_engine
import yaml
import psycopg2

def load_config(file_path="config.yaml"):
    """
    Load database configuration from a YAML file.
    """
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

def get_db_engine():
    """
    Create and return a SQLAlchemy engine for database connection.
    """
    config = load_config()
    db_config = config["database"]
    return create_engine(f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['url']}:{db_config['port']}/{db_config['name']}")

def extract(csv_file="weather_data.csv", nrows=11000):
    """
    Extract data from a CSV file and insert it into a PostgreSQL database.
    """
    engine = get_db_engine()
    df = pd.read_csv(csv_file, nrows=nrows)
    
    config = load_config()
    db_config = config["database"]
    
    conn = psycopg2.connect(
        dbname=db_config["name"],
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["url"],
        port=db_config["port"]
    )
    cursor = conn.cursor()
    
    columns = [f'"{col}" {"INTEGER" if "int" in str(dtype) else "FLOAT" if "float" in str(dtype) else "BOOLEAN" if "bool" in str(dtype) else "TEXT"}' for col, dtype in zip(df.columns, df.dtypes)]
    create_table_query = f'''
    CREATE TABLE IF NOT EXISTS {db_config["table"]} (
       id SERIAL PRIMARY KEY,
        {", ".join(columns)}
    );'''
    cursor.execute(create_table_query)
    conn.commit()
    cursor.close()
    conn.close()
    
    df.to_sql(db_config["table"], engine, if_exists="append", index=False)
    print(f"Table '{db_config['table']}' created and data successfully inserted into Supabase.")
    return df

def transform():
    """
    Transform data by extracting date components, normalizing temperature and wind speed,
    and calculating the average temperature per location.
    """
    engine = get_db_engine()
    config = load_config()
    db_config = config["database"]
    
    df = pd.read_sql(f"SELECT * FROM {db_config['table']}", engine)
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    df["Year"], df["Month"], df["Day"], df["Hour"], df["Minute"] = df["Date_Time"].dt.year, df["Date_Time"].dt.month, df["Date_Time"].dt.day, df["Date_Time"].dt.hour, df["Date_Time"].dt.minute
    df["Location"] = df["Location"].str.upper()
    df["Temperature_F"] = (df["Temperature_C"] * 9/5) + 32
    df["Wind_Speed_mph"] = df["Wind_Speed_kmh"] * 0.621371
    avg_temp_df = df.groupby("Location")["Temperature_C"].mean().reset_index().rename(columns={"Temperature_C": "Avg_Temperature_C"})
    df_merged = df.merge(avg_temp_df, on="Location", how="left")
    return df_merged

def merge(df_merged):
    """
    Merge transformed data back into the database and display the last 5 rows.
    """
    engine = get_db_engine()
    config = load_config()
    db_config = config["database"]
    
    df_merged.to_sql(db_config["table"], engine, if_exists="replace", index=False)
    df = pd.read_sql(f"SELECT * FROM {db_config['table']}", engine)
    print(df.tail(5))

if __name__ == "__main__":
    df_extracted = extract()
    df_transformed = transform()
    merge(df_transformed)
