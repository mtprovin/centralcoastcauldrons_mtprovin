from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from sqlalchemy.exc import IntegrityError
from src import database as db
import math
import copy

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
                red_ml += b.ml_per_barrel * b.quantity
            elif b.potion_type == [0,1,0,0]:
                green_ml += b.ml_per_barrel * b.quantity
            elif b.potion_type == [0,0,1,0]:
                blue_ml += b.ml_per_barrel * b.quantity
            elif b.potion_type == [0,0,0,1]:
                dark_ml += b.ml_per_barrel * b.quantity
            else:
                raise Exception("invalid potion type")
                
        print(f"gold_paid: {gold_paid} red_ml: {red_ml} green_ml: {green_ml} blue_ml: {blue_ml} dark_ml: {dark_ml}")

        transaction = connection.execute(sqlalchemy.text(
            """
                INSERT INTO transactions
                (description)
                VALUES
                ('deliver barrels')
                RETURNING transaction_id
            """)).one().transaction_id

        connection.execute(sqlalchemy.text(
            """
                INSERT INTO ledger
                (transaction_id, inventory_id, change)
                VALUES
                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'red_ml'), :red_ml),
                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'green_ml'), :green_ml),
                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'blue_ml'), :blue_ml),
                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'dark_ml'), :dark_ml),
                (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'gold'), :gold)
            """),
            [{"transaction_id": transaction,
              "red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml, "gold": -gold_paid}])

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print("get_wholesale_purchase_plan ----------")
    print("catalog: ", wholesale_catalog)

    # sort by cheapest barrels
    barrels_sorted = sorted(wholesale_catalog, key=lambda barrel: barrel.price)

    # group into RGBD
    barrels_grouped = [[] for i in range(4)] 
    for b in barrels_sorted:
        barrels_grouped[b.potion_type.index(1)].append(b)

    with db.engine.begin() as connection:
        # get current gold and ml
        inv = connection.execute(sqlalchemy.text(
                                """
                                SELECT COALESCE(SUM(change),0) AS total, inventory.name AS name
                                FROM ledger
                                RIGHT JOIN inventory ON inventory.inventory_id = ledger.inventory_id
                                WHERE inventory.name in ('gold', 'red_ml', 'green_ml', 'blue_ml', 'dark_ml', 'capacity_ml')
                                GROUP BY inventory.inventory_id
                                """)).all()
        totals = {row.name: row.total for row in inv}

        gold = totals['gold'] + 100
        ml = [totals['red_ml'], totals['green_ml'], totals['blue_ml'], totals['dark_ml']]

    print("gold: ", gold)

    gold = gold * 0.4

    dark_found = False
    for b in barrels_sorted:
        if 'DARK' in b.sku:
            dark_found = True

    print("capacity: ", (totals['capacity_ml']+1)*10000)
    print("ml: ", sum(ml))
    if not dark_found or sum(ml) > (totals['capacity_ml']+1)*10000*.2:
        return []

    # initial pass, evenly distribute barrel colors, add cheapest barrel 1 at a time for each color
    done_buying = [False, False, False, False]
    c_sorted = sorted(range(4), key=lambda c: ml[c])
    i = 0
    budget = [0,0,0,0]
    gold_remaining = gold
    barrels_grouped_temp = copy.deepcopy(barrels_grouped)
    while False in done_buying:
        c = c_sorted[i]
        if len(barrels_grouped_temp[c]) <= 0:
            done_buying[c] = True
        if not done_buying[c]:
            cheapest_barrel = barrels_grouped_temp[c][0]
            
            # allow 40% of budget to be dark otherwise we'll buy almost all dark
            if c == 3 and (budget[c]+cheapest_barrel.price) / (gold+1) > .4:
                done_buying[c] = True
            # if we have enough gold to buy 1 of the cheapest, add it to our budget for that color
            elif gold_remaining > cheapest_barrel.price:
                budget[c] += cheapest_barrel.price
                gold_remaining -= cheapest_barrel.price
                cheapest_barrel.quantity -= 1
                if cheapest_barrel.quantity <= 0:
                    barrels_grouped_temp[c].pop(0)
            else:
                done_buying[c] = True
        i = (i+1) % 4

    print("budget: ", budget)

    # optimization, replace cheap purchases with equivalent expensive purchases
    plan_dict = {barrel.sku: 0 for barrel in barrels_sorted}
    ml_bought = 0
    b_max = [len(barrels_grouped[c]) - 1 for c in range(4)] # most expensive barrel
    done_buying = [False, False, False, False]
    while False in done_buying:
        c = c_sorted[i]

        if b_max[c] >= 0:
            b = b_max[c]
            barrel = barrels_grouped[c][b]

            # buy as much as possible
            if (ml_bought + sum(ml) + barrel.ml_per_barrel <= (totals['capacity_ml']+1) * 10000 and 
                    barrel.price <= gold_remaining + budget[c]):
                ml_bought += barrel.ml_per_barrel
                budget[c] -= barrel.price
                if budget[c] < 0:
                    gold_remaining += budget[c]
                    budget[c] = 0
                barrel.quantity -= 1
                if barrel.quantity <= 0:
                    barrels_grouped[c].pop(b)
                    b_max[c] -= 1
                plan_dict[barrel.sku] += 1
            else:
                b_max[c] -= 1

        elif not done_buying[c]:
            gold_remaining += budget[c] # free budget
            for j in range(4):
                if b_max[j] >= 0:
                    b_max[j] = len(barrels_grouped[j]) - 1
            done_buying[c] = True
        
        i = (i+1)%4

    plan = []
    for barrel in barrels_sorted:
        if plan_dict[barrel.sku] > 0:
            plan.append({
                "sku": barrel.sku,
                "quantity": plan_dict[barrel.sku]
            })

    return plan
