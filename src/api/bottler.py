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
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            ml = [row.num_red_ml, row.num_green_ml, row.num_blue_ml]
            num_potions = [row.num_red_potions, row.num_green_potions, row.num_blue_potions]

        p_names = ["num_red_potions", "num_green_potions", "num_blue_potions"]
        ml_names = ["num_red_ml", "num_green_ml", "num_blue_ml"]
        for potionType in potions_delivered:
            for i in range(3):
                p_type = [0,0,0,0]
                p_type[i] = 100
                if potionType.potion_type == p_type:
                    num_potions[i] += potionType.quantity
                    ml[i] -= 100*potionType.quantity
                    
                    # update ml and potions
                    print(f"UPDATE global_inventory SET {p_names[i]} = {num_potions[i]}")
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET {p_names[i]} = {num_potions[i]}"))
                    print(f"UPDATE global_inventory SET {ml_names[i]} = {ml[i]}")
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET {ml_names[i]} = {ml[i]}"))


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

    plan = []

    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            quant = [math.floor(row.num_red_ml/100), math.floor(row.num_green_ml/100), math.floor(row.num_blue_ml/100)]

        for i in range(3):
            if quant[i] > 0:
                p_type = [0,0,0,0]
                p_type[i] += 100
                plan.append({
                    "potion_type": p_type,
                    "quantity": quant[i],
                })
        
    print("plan: ", plan)
    return plan

if __name__ == "__main__":
    print(get_bottle_plan())