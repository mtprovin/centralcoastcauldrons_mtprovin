from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    print("get_inventory ----------")
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text(
                                """
                                SELECT SUM(change) AS total, inventory.name AS name
                                FROM ledger
                                JOIN inventory ON inventory.inventory_id = ledger.inventory_id
                                WHERE inventory.name in ('gold', 'red_ml', 'green_ml', 'blue_ml', 'dark_ml')
                                GROUP BY inventory.inventory_id
                                """)).all()
        num_potions = connection.execute(sqlalchemy.text(
                                """
                                SELECT SUM(change) AS num_potions
                                FROM ledger
                                JOIN potions ON potions.inventory_id = ledger.inventory_id
                                """)).one().num_potions
        totals = {row.name: row.total for row in inv}

    total_ml = totals['red_ml'] + totals['green_ml'] + totals['blue_ml'] + totals['dark_ml']

    return {"number_of_potions": num_potions, "ml_in_barrels": total_ml, "gold": totals['gold'] + 100}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
