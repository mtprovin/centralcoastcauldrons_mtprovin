from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import math

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    # get cost of transaction and added ml
    cost = 0
    added_ml = 0
    for barrel in barrels_delivered:
        cost += barrel.price*barrel.quantity
        added_ml += barrel.ml_per_barrel*barrel.quantity

    # get current gold
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            gold = row.gold
            ml = row.num_green_ml
        
        # subtract cost
        gold = gold - cost
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold}"))
        
        # add ml
        ml = ml + added_ml
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = {ml}"))

    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    # buy all we can of the cheapest
    
    # sort by cheapest barrels
    barrels_sorted = sorted(wholesale_catalog, key=lambda barrel: barrel.price)

    # get current gold
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            num_potions = row.num_green_potions
            gold = row.gold

    # construct plan
    plan = []
    i = 0
    while i < len(barrels_sorted) and gold > 0:
        barrel = barrels_sorted[i]
        #quantPurchase = min(math.floor(gold / barrel.price), barrel.quantity)
        #if (quantPurchase > 0):
        #    plan.append({
        #        "sku": barrel.sku,
        #        "quantity": quantPurchase
        #    })
        #gold = gold - quantPurchase*barrel.price

        if barrel.sku == "SMALL_GREEN_BARREL" and num_potions < 10 and gold >= barrel.price:
            plan.append({
                "sku": barrel.sku,
                "quantity": 1
            })
            break
        
        i += 1

    return plan

