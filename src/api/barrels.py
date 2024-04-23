from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from sqlalchemy.exc import IntegrityError
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

    # get current gold
    with db.engine.begin() as connection:
        #try:
        #    connection.execute(
        #        sqlalchemy.text("blah"),
        #        [{"order_id": order_id}]
        #    )
        #except IntegrityError as e:
        #    return "OK"
        
        gold_paid = 0
        green_ml = 0
        red_ml = 0
        blue_ml = 0
        dark_ml = 0
            
        for b in barrels_delivered:
            gold_paid += b.price * b.quantity
            if b.potion_type == [1,0,0,0]:
                green_ml += b.ml_per_barrel * b.quantity
            elif b.potion_type == [0,1,0,0]:
                red_ml += b.ml_per_barrel * b.quantity
            elif b.potion_type == [0,0,1,0]:
                blue_ml += b.ml_per_barrel * b.quantity
            elif b.potion_type == [0,0,0,1]:
                dark_ml += b.ml_per_barrel * b.quantity
            else:
                raise Exception("invalid potion type")
                
        print(f"gold_paid: {gold_paid} red_ml: {red_ml} green_ml: {green_ml} blue_ml: {blue_ml} dark_ml: {dark_ml}")

        connection.execute(sqlalchemy.text(
            """
                UPDATE global_inventory SET
                red_ml = red_ml + :red_ml,
                green_ml = green_ml + :green_ml, 
                blue_ml = blue_ml + :blue_ml,
                dark_ml = dark_ml + :dark_ml,
                gold = gold - :gold
            """),
            [{"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml, "gold": gold_paid}])

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
        inv = connection.execute(sqlalchemy.text(
                                """
                                SELECT gold
                                FROM global_inventory
                                """)).one()
        gold = inv.gold

    # construct plan
    plan = []
    i = 0
    while i < len(barrels_sorted) and gold > barrels_sorted[i].price:
        plan.append({
            "sku": barrels_sorted[i].sku,
            "quantity": 1
        })
        gold -= barrels_sorted[i].price

        i += 1
    print("plan: ", plan)

    return plan

