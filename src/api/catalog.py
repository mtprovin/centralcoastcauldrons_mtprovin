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
        inv = connection.execute(sqlalchemy.text("""
                                SELECT 
                                potions.sku,
                                COALESCE(SUM(ledger.change), 0) as quantity,
                                potions.price,
                                potions.red_ml,
                                potions.green_ml,
                                potions.blue_ml,
                                potions.dark_ml
                                FROM potions
                                LEFT JOIN ledger ON potions.inventory_id = ledger.inventory_id
                                GROUP BY potions.potion_id
                                ORDER BY quantity desc, price asc
                                LIMIT 6
                                """)).all()

    catalog = []

    for item in inv:
        if item.quantity > 0:
            catalog.append({
                    "sku": item.sku,
                    "name": item.sku,
                    "quantity": item.quantity,
                    "price": item.price,
                    "potion_type": [item.red_ml, item.green_ml, item.blue_ml, item.dark_ml]
                })

    print(f"catalog: {catalog}")
    return catalog
