import os
import dotenv
from sqlalchemy import create_engine, MetaData, Table

def database_connection_url():
    dotenv.load_dotenv()

    print(os.environ.get("POSTGRES_URI"))
    return os.environ.get("POSTGRES_URI")

engine = create_engine(database_connection_url(), pool_pre_ping=True)

metadata_obj = MetaData()

carts = Table("carts", metadata_obj, autoload_with=engine)
cart_items = Table("cart_items", metadata_obj, autoload_with=engine)
potions = Table("potions", metadata_obj, autoload_with=engine)
transactions = Table("transactions", metadata_obj, autoload_with=engine)