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
        globals = connection.execute(sqlalchemy.text("""
                                                     SELECT 
                                                     num_potions, 
                                                     gold, 
                                                     red_ml, 
                                                     green_ml, 
                                                     blue_ml, 
                                                     dark_ml
                                                     FROM global_inventory""")).one()

    total_ml = globals.red_ml + globals.green_ml + globals.blue_ml + globals.dark_ml

    return {"number_of_potions": globals.num_potions, "ml_in_barrels": total_ml, "gold": globals.gold}

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
