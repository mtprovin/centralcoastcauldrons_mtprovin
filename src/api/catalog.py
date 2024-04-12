from fastapi import APIRouter
import sqlalchemy
from src import database as db
from src.prices import prices

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    print("get_catalog ----------")

    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            num_potions = [row.num_red_potions, row.num_green_potions, row.num_blue_potions]

    catalog = []

    p_skus = ["RED_POTION_0", "GREEN_POTION_0", "BLUE_POTION_0"]
    p_names = ["red potion", "green potion", "blue potion"]
    p_types = [[100,0,0,0], [0,100,0,0], [0,0,100,0]]
    for i in range(3):
        if num_potions[i] > 0:
            catalog.append({
                    "sku": p_skus[i],
                    "name": p_names[i],
                    "quantity": num_potions[i],
                    "price": prices[p_skus[i]],
                    "potion_type": p_types[i],
                })

    print(f"catalog: {catalog}")
    return catalog
