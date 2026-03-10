from sqlalchemy import create_engine, inspect

engine = create_engine("sqlite:///C:/Users/hp/Desktop/trial/db.sqlite3")

inspector = inspect(engine)

print("Tables in DB:", inspector.get_table_names())

columns = inspector.get_columns("metrics")

print("\nColumns in metrics table:")

for column in columns:
    print(column["name"], "-", column["type"])