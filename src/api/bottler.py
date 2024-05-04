from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import math

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print("post_deliver_bottles ----------")
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        red_ml_used = 0
        green_ml_used = 0
        blue_ml_used = 0
        dark_ml_used = 0
        transaction = connection.execute(sqlalchemy.text(
                """
                    INSERT INTO transactions
                    (description)
                    VALUES
                    ('deliver bottles')
                    RETURNING transaction_id
                """)).one().transaction_id
        
        for potionType in potions_delivered:
            red_ml_used += potionType.potion_type[0] * potionType.quantity
            green_ml_used += potionType.potion_type[1] * potionType.quantity
            blue_ml_used += potionType.potion_type[2] * potionType.quantity
            dark_ml_used += potionType.potion_type[3] * potionType.quantity
            
            connection.execute(sqlalchemy.text(
                                """
                                    INSERT INTO ledger
                                    (transaction_id, inventory_id, change)
                                    VALUES
                                    (:transaction_id, 
                                    (SELECT inventory_id FROM potions WHERE red_ml = :red_ml AND green_ml = :green_ml AND blue_ml = :blue_ml AND dark_ml = :dark_ml LIMIT 1), 
                                    :potion_quantity)
                                """),
                                [{"transaction_id": transaction, "potion_quantity": potionType.quantity,
                                  "red_ml": potionType.potion_type[0], "green_ml": potionType.potion_type[1], 
                                  "blue_ml": potionType.potion_type[2], "dark_ml": potionType.potion_type[3]}])

        connection.execute(sqlalchemy.text(
                            """
                                INSERT INTO ledger
                                (transaction_id, inventory_id, change)
                                VALUES
                                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'red_ml'), :red_ml),
                                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'green_ml'), :green_ml),
                                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'blue_ml'), :blue_ml),
                                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'dark_ml'), :dark_ml)
                            """),
                            [{"transaction_id": transaction,
                              "red_ml": -red_ml_used, "green_ml": -green_ml_used, "blue_ml": -blue_ml_used, "dark_ml": -dark_ml_used}])
        
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    print("get_bottle_plan ----------")

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text(
                                """
                                SELECT COALESCE(SUM(change),0) AS total, inventory.name AS name
                                FROM ledger
                                RIGHT JOIN inventory ON inventory.inventory_id = ledger.inventory_id
                                WHERE inventory.name in ('red_ml', 'green_ml', 'blue_ml', 'dark_ml', 'capacity_potions')
                                GROUP BY inventory.inventory_id
                                """)).all()

        totals = {row.name: row.total for row in inv}

        num_potions = connection.execute(sqlalchemy.text(
                                """
                                SELECT COALESCE(SUM(change),0) AS num_potions
                                FROM ledger
                                RIGHT JOIN potions ON potions.inventory_id = ledger.inventory_id
                                """)).one().num_potions

        p_types = connection.execute(sqlalchemy.text("""
                                SELECT 
                                potions.potion_id,
                                COALESCE(SUM(ledger.change), 0) as quantity,
                                potions.red_ml,
                                potions.green_ml,
                                potions.blue_ml,
                                potions.dark_ml
                                FROM potions
                                LEFT JOIN ledger ON potions.inventory_id = ledger.inventory_id
                                WHERE discontinued = FALSE
                                GROUP BY potions.potion_id
                                """)).all()

        # sort by fewest potions
        p_types_sorted = sorted(p_types, key=lambda potion: potion.quantity)

        plan_dict = {p_type.potion_id: 0 for p_type in p_types_sorted}

        red_ml = totals['red_ml']
        green_ml = totals['green_ml']
        blue_ml = totals['blue_ml']
        dark_ml = totals['dark_ml']

        p = 0
        while p < len(p_types_sorted):
            p_type = p_types_sorted[p]
            if (red_ml >= p_type.red_ml and green_ml >= p_type.green_ml and
                blue_ml >= p_type.blue_ml and dark_ml >= p_type.dark_ml):
                plan_dict[p_type.potion_id] += 1

                red_ml -= p_type.red_ml
                green_ml -= p_type.green_ml
                blue_ml -= p_type.blue_ml
                dark_ml -= p_type.dark_ml

                p_types_sorted = sorted(p_types, key=lambda potion: potion.quantity + plan_dict[potion.potion_id])
                p = 0
            else:
                p += 1
        
        potions_bought = 0

        plan = []
        for p_type in p_types_sorted:
            if plan_dict[p_type.potion_id] > 0 and num_potions + potions_bought < (totals['capacity_potions']+1) * 50:
                quantity = min(plan_dict[p_type.potion_id], ((totals['capacity_potions']+1) * 50) - (num_potions + potions_bought))
                potions_bought += quantity
                plan.append({
                    "potion_type": [p_type.red_ml, p_type.green_ml, p_type.blue_ml, p_type.dark_ml],
                    "quantity": quantity
                })
        
    print("plan: ", plan)
    return plan

if __name__ == "__main__":
    print(get_bottle_plan())
