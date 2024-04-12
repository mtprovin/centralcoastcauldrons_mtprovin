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
    print("post_deliver_barrels ----------")
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    # get cost of transaction and added ml
    cost = 0
    added_ml = [0,0,0]
    for barrel in barrels_delivered:
        cost += barrel.price*barrel.quantity
        for i in range(3):
            if barrel.potion_type[i] > 0:
                added_ml[i] += barrel.ml_per_barrel*barrel.quantity

    # get current gold
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            gold = row.gold
            ml = [row.num_red_ml, row.num_green_ml, row.num_blue_ml]
        
        if gold < cost:
            print("Error: Invalid cost")
            return "FAIL"

        # subtract cost
        gold = gold - cost
        print(f"UPDATE global_inventory SET gold = {gold}")
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold}"))
        
        # add ml
        # red
        ml[0] = ml[0] + added_ml[0]
        print(f"UPDATE global_inventory SET num_red_ml = {ml[0]}")
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_ml = {ml[0]}"))
        # green
        ml[1] = ml[1] + added_ml[1]
        print(f"UPDATE global_inventory SET num_green_ml = {ml[1]}")
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = {ml[1]}"))
        # blue
        ml[2] = ml[2] + added_ml[2]
        print(f"UPDATE global_inventory SET num_blue_ml = {ml[2]}")
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_blue_ml = {ml[2]}"))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print("get_wholesale_purchase_plan ----------")
    print("catalog: ", wholesale_catalog)

    # buy all we can of the cheapest
    
    # sort by cheapest barrels
    barrels_sorted = sorted(wholesale_catalog, key=lambda barrel: barrel.price)

    # get current gold
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            num_potions = row.num_green_potions + row.num_red_potions + row.num_blue_potions
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
            gold -= barrel.price
        elif barrel.sku == "SMALL_RED_BARREL" and num_potions < 10 and gold >= barrel.price:
            plan.append({
                "sku": barrel.sku,
                "quantity": 1
            })
            gold -= barrel.price
        elif barrel.sku == "SMALL_BLUE_BARREL" and num_potions < 10 and gold >= barrel.price:
            plan.append({
                "sku": barrel.sku,
                "quantity": 1
            })
            gold -= barrel.price
        
        i += 1
    print("plan: ", plan)

    return plan

