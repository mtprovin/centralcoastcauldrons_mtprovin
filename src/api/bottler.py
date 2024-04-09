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
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            green_ml = row.num_green_ml
            num_green_potions = row.num_green_potions

        for potionType in potions_delivered:
            if potionType.potion_type == [0, 100, 0, 0]:
                # update ml and potions
                connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_potions = {num_green_potions+potionType.quantity}"))

                connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = {green_ml-100*potionType.quantity}"))


    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    plan = []

    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            ml = row.num_green_ml

        quant = math.floor(ml / 100)

        if quant > 0:
            plan.append({
                "potion_type": [0, 100, 0, 0],
                "quantity": quant,
            })
        

    return plan

if __name__ == "__main__":
    print(get_bottle_plan())