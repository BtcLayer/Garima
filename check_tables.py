from sqlalchemy import create_engine, inspect

# Use same DB file
engine = create_engine("sqlite:///C:/Users/hp/Desktop/trial/db.sqlite3")

inspector = inspect(engine)
print("Tables in DB:", inspector.get_table_names())