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

    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            num_potions = row.num_green_potions

    catalog = []

    if num_potions > 0:
        catalog.append({
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": num_potions,
                "price": prices["GREEN_POTION_0"],
                "potion_type": [0, 100, 0, 0],
            })

    return catalog
