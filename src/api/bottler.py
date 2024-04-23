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
            hash = potionType.potion_type[0] + potionType.potion_type[1]*100 + potionType.potion_type[2]*(100**2) + potionType.potion_type[3]*(100**3)
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

        plan = []
        red_ml = inv.red_ml
        green_ml = inv.green_ml
        blue_ml = inv.blue_ml
        dark_ml = inv.dark_ml
        for p_type in p_types_sorted:
            if (red_ml >= p_type.red_ml and green_ml >= p_type.green_ml and
                blue_ml >= p_type.blue_ml and dark_ml >= p_type.dark_ml and
                100 not in p_type): # TODO: can get rid of this after testing potion mixes
                p_mix = [p_type.red_ml, p_type.green_ml, p_type.blue_ml, p_type.dark_ml]
                plan.append({
                    "potion_type": p_mix,
                    "quantity": 1,
                })
                # pretty hacky way to not have to lookup potion id by type
                hash = p_type.red_ml + p_type.green_ml*100 + p_type.blue_ml*(100**2) + p_type.dark_ml*(100**3)
                global potion_lookup
                potion_lookup[hash] = p_type.potion_id
                red_ml -= p_type.red_ml
                green_ml -= p_type.green_ml
                blue_ml -= p_type.blue_ml
                dark_ml -= p_type.dark_ml
        
    print("plan: ", plan)
    return plan

if __name__ == "__main__":
    print(get_bottle_plan())