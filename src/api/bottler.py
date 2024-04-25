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

potion_lookup = {}

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print("post_deliver_bottles ----------")
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        potions_made = 0
        red_ml_used = 0
        green_ml_used = 0
        blue_ml_used = 0
        dark_ml_used = 0
        for potionType in potions_delivered:
            global potion_lookup
            # pretty hacky way to not have to lookup potion id by type
            hash = potionType.potion_type[0] + potionType.potion_type[1]*101 + potionType.potion_type[2]*(101**2) + potionType.potion_type[3]*(101**3)
            id = potion_lookup[hash]

            red_ml_used += potionType.potion_type[0] * potionType.quantity
            green_ml_used += potionType.potion_type[1] * potionType.quantity
            blue_ml_used += potionType.potion_type[2] * potionType.quantity
            dark_ml_used += potionType.potion_type[3] * potionType.quantity
            potions_made += potionType.quantity
            
            connection.execute(sqlalchemy.text("""
                                               UPDATE potions SET 
                                               quantity = quantity + :quantity
                                               WHERE potion_id = :potion_id
                                               """),
                                               [{"quantity": potionType.quantity, "potion_id": id}])
        connection.execute(sqlalchemy.text("""
                                            UPDATE global_inventory SET 
                                            red_ml = red_ml - :red_ml,
                                            green_ml = green_ml - :green_ml,
                                            blue_ml = blue_ml - :blue_ml,
                                            dark_ml = dark_ml - :dark_ml,
                                            num_potions = num_potions + :potions_made
                                            """), 
                                            [{"red_ml": red_ml_used,
                                              "green_ml": green_ml_used,
                                              "blue_ml": blue_ml_used,
                                              "dark_ml": dark_ml_used,
                                              "potions_made": potions_made}])
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
        inv = connection.execute(sqlalchemy.text("""
                                                 SELECT 
                                                 red_ml,
                                                 green_ml,
                                                 blue_ml,
                                                 dark_ml
                                                 FROM global_inventory
                                                 """)).one()
        p_types = connection.execute(sqlalchemy.text("""
                                                 SELECT 
                                                 potion_id,
                                                 quantity,
                                                 red_ml,
                                                 green_ml,
                                                 blue_ml,
                                                 dark_ml
                                                 FROM potions
                                                 """)).all()

        # sort by fewest potions
        p_types_sorted = sorted(p_types, key=lambda potion: potion.quantity)

        plan_dict = {p_type.potion_id: 0 for p_type in p_types_sorted}

        red_ml = inv.red_ml
        green_ml = inv.green_ml
        blue_ml = inv.blue_ml
        dark_ml = inv.dark_ml

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
        
        plan = []
        for p_type in p_types_sorted:
            if plan_dict[p_type.potion_id] > 0:
                plan.append({
                    "potion_type": [p_type.red_ml, p_type.green_ml, p_type.blue_ml, p_type.dark_ml],
                    "quantity": round(plan_dict[p_type.potion_id] * 0.775),
                })

            global potion_lookup
            if p_type.potion_id not in potion_lookup.values():
                # pretty hacky way to not have to lookup potion id by type
                hash = p_type.red_ml + p_type.green_ml*101 + p_type.blue_ml*(101**2) + p_type.dark_ml*(101**3)
                potion_lookup[hash] = p_type.potion_id
        
    print("plan: ", plan)
    return plan

if __name__ == "__main__":
    print(get_bottle_plan())
