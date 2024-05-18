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
        # may have duplicates
        inv = connection.execute(sqlalchemy.text("""
                WITH hourly_visitors AS (
                    SELECT 
                        carts.class AS class, ABS(AVG(Extract(hour from created_at)) - Extract(hour from now())) AS hour
                    FROM transactions
                    JOIN carts ON carts.transaction_id = transactions.transaction_id
                    GROUP BY class
                ),
                hourly_potions AS(
                    SELECT 
                        potion_id, sku, 
                        CASE 
                            WHEN hour > 12 THEN 24 - hour 
                            ELSE hour 
                        END AS hour
                    FROM hourly_visitors
                    JOIN potions ON potions.for_class LIKE '%' || hourly_visitors.class || '%'
                ),
                quantity_potions AS (
                    SELECT 
                        sku, price, red_ml, green_ml, blue_ml, dark_ml, potion_id,
                        COALESCE(SUM(ledger.change), 0) as quantity
                    FROM potions
                    LEFT JOIN ledger ON potions.inventory_id = ledger.inventory_id
                    GROUP BY potions.potion_id
                )
                SELECT quantity_potions.*
                FROM quantity_potions
                JOIN hourly_potions ON hourly_potions.potion_id = quantity_potions.potion_id
                WHERE quantity > 10
                ORDER BY hour, quantity desc, price asc
                """)).all()

    catalog = []

    skus = []
    i = 0
    while len(catalog) < 6 and i < len(inv):
        if inv[i].sku not in skus:
            catalog.append({
                        "sku": inv[i].sku,
                        "name": inv[i].sku,
                        "quantity": inv[i].quantity,
                        "price": inv[i].price,
                        "potion_type": [inv[i].red_ml, inv[i].green_ml, inv[i].blue_ml, inv[i].dark_ml]
                    })
            skus.append(inv[i].sku)
        i += 1

    print(f"catalog: {catalog}")
    return catalog
