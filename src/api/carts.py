from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db
from src.prices import prices

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

next_cart_id = 1
customer_carts = {}

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print("post_visits ----------")
    print(customers)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    print("create_cart ----------")
    print("new_cart: ", new_cart)
    global next_cart_id
    global customer_carts
    cart = {}
    id = next_cart_id
    customer_carts[next_cart_id] = cart

    next_cart_id += 1

    return {"cart_id": id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    print("set_item_quantity ----------")
    print(f"cart_id: {cart_id}, item_sku: {item_sku}, cart_item: {cart_item}")
    if item_sku not in prices.keys():
        print("Error: SKU doesn't exist")

    global customer_carts
    cart = customer_carts[cart_id]
    
    cart[item_sku] = cart_item.quantity

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print("checkout ----------")
    print(f"cart_id: {cart_id}, cart_checkout: {cart_checkout}")
    global customer_carts
    cart = customer_carts[cart_id]

    potions_bought = [0,0,0]
    total_cost = 0
    for sku, quant in cart.items():
        if "RED" in sku:
            potions_bought[0] += quant
        elif "GREEN" in sku:
            potions_bought[1] += quant
        elif "BLUE" in sku:
            potions_bought[2] += quant
        total_cost += prices[sku]*quant


    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in inv:
            num_potions = [row.num_red_potions, row.num_green_potions, row.num_blue_potions]
            gold = row.gold
        
        for i in range(3):
            if num_potions[i] < potions_bought[i]:
                return {}   # invalid order
        
        p_names = ["num_red_potions", "num_green_potions", "num_blue_potions"]
        for i in range(3):
            num_potions[i] -= potions_bought[i]
            print(f"UPDATE global_inventory SET {p_names[i]} = {num_potions[i]}")
            connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET {p_names[i]} = {num_potions[i]}"))

        gold += total_cost
        print(f"UPDATE global_inventory SET gold = {gold}")
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold}"))

    print(f"total_potions_bought: {sum(potions_bought)}, total_gold_paid: {total_cost}")
    return {"total_potions_bought": sum(potions_bought), "total_gold_paid": total_cost}