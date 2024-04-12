from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api.carts import customer_carts, next_cart_id


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    print("reset ----------")
    with db.engine.begin() as connection:
        item_names = ["num_red_potions", "num_green_potions", "num_blue_potions",
                      "num_red_ml", "num_green_ml", "num_blue_ml"]
        for item in item_names:
            connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET {item} = 0"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = 100"))
    
    global customer_carts
    global next_cart_id
    next_cart_id = 0
    customer_carts.clear()

    return "OK"

