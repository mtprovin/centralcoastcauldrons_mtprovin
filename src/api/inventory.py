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
                                SELECT COALESCE(SUM(change),0) AS total, inventory.name AS name
                                FROM ledger
                                RIGHT JOIN inventory ON inventory.inventory_id = ledger.inventory_id
                                WHERE inventory.name in ('gold', 'red_ml', 'green_ml', 'blue_ml', 'dark_ml')
                                GROUP BY inventory.inventory_id
                                """)).all()
        num_potions = connection.execute(sqlalchemy.text(
                                """
                                SELECT COALESCE(SUM(change),0) AS num_potions
                                FROM ledger
                                RIGHT JOIN potions ON potions.inventory_id = ledger.inventory_id
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
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text(
                                """
                                SELECT COALESCE(SUM(change),0) AS total, inventory.name AS name
                                FROM ledger
                                RIGHT JOIN inventory ON inventory.inventory_id = ledger.inventory_id
                                WHERE inventory.name in ('gold', 'capacity_ml', 'capacity_potions')
                                GROUP BY inventory.inventory_id
                                """)).all()
        num_potions = connection.execute(sqlalchemy.text(
                                """
                                SELECT COALESCE(SUM(change),0) AS num_potions
                                FROM ledger
                                RIGHT JOIN potions ON potions.inventory_id = ledger.inventory_id
                                """)).one().num_potions
        totals = {row.name: row.total for row in inv}

        gold = totals['gold'] + 100

    gold_available = round(gold*.9)

    # buys potion capacity until percent in use is less than threshold
    # buys 1 ml capacity for every 2 potion capacity

    plan = {"potion_capacity": 0, "ml_capacity": 0}

    done_buying = [False, False]
    # start buying ml capacity if it's less than double potion capacity
    c = 0 if totals['capacity_ml']*2+1 <= totals['capacity_potions'] else 1
    while False in done_buying and gold_available >= 1000:
        # buy a ml capacity if it's less than double potion capacity
        if c == 0 and (totals['capacity_ml']+plan["ml_capacity"])*2+1 <= (totals['capacity_potions']+plan["potion_capacity"]):
            gold_available -= 1000
            plan["ml_capacity"] += 1
            done_buying[c] = False
        elif c == 1 and num_potions / ((totals['capacity_potions']+plan["potion_capacity"]+1)*50) > 0.6:
            gold_available -= 1000
            plan["potion_capacity"] += 1
            done_buying[c] = False
        else:
            done_buying[c] = True
        c = (c+1)%2

    return plan

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

    if capacity_purchase.ml_capacity > 0 or capacity_purchase.potion_capacity > 0:
        with db.engine.begin() as connection:
            transaction = connection.execute(sqlalchemy.text(
                    """
                        INSERT INTO transactions
                        (description)
                        VALUES
                        ('deliver capacity')
                        RETURNING transaction_id
                    """)).one().transaction_id
            
            connection.execute(sqlalchemy.text(
                    """
                        INSERT INTO ledger
                        (transaction_id, inventory_id, change)
                        VALUES
                        (:transaction_id, 
                        (SELECT inventory_id FROM inventory WHERE name = 'capacity_ml' LIMIT 1), 
                        :ml_quantity),
                        (:transaction_id, 
                        (SELECT inventory_id FROM inventory WHERE name = 'capacity_potions' LIMIT 1), 
                        :potion_quantity),
                        (:transaction_id, 
                        (SELECT inventory_id FROM inventory WHERE name = 'gold' LIMIT 1), 
                        :gold)
                    """),
                    [{"transaction_id": transaction, "ml_quantity": capacity_purchase.ml_capacity, "potion_quantity": capacity_purchase.potion_capacity, 
                      "gold": -(capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000}])

    return "OK"
