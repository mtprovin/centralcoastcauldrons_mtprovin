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
    
    with db.engine.begin() as connection:
        id = connection.execute(sqlalchemy.text("""
                                            INSERT INTO carts 
                                            (name, class, level)
                                            VALUES 
                                            (:name, :class, :level)
                                            RETURNING cart_id
                                            """),
                                            [{"name": new_cart.customer_name, "class": new_cart.character_class, "level": new_cart.level}]).one().cart_id
        #id = connection.execute(sqlalchemy.text("""
        #                                        INSERT INTO carts
        #                                        OUTPUT cart_id
        #                                        """)).one().id

    return {"cart_id": id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    print("set_item_quantity ----------")
    print(f"cart_id: {cart_id}, item_sku: {item_sku}, cart_item: {cart_item}")

    with db.engine.begin() as connection:
        potion_id = connection.execute(sqlalchemy.text("""
                                                        SELECT potion_id
                                                        FROM potions
                                                        WHERE sku = :item_sku
                                                        """),
                                                        [{"item_sku": item_sku}]).one().potion_id
        connection.execute(sqlalchemy.text("""
                                            INSERT INTO cart_items
                                            (cart_id, potion_id, quantity)
                                            VALUES
                                            (:cart_id, :potion_id, :quantity)
                                            """),
                                            [{"cart_id": cart_id, "potion_id": potion_id, "quantity": cart_item.quantity}])

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print("checkout ----------")
    print(f"cart_id: {cart_id}, cart_checkout: {cart_checkout}")

    with db.engine.begin() as connection:
        potions_bought = connection.execute(sqlalchemy.text("""
                                                            SELECT 
                                                            cart_items.quantity AS quantity_bought,
                                                            potions.potion_id,
                                                            potions.inventory_id,
                                                            potions.price, 
                                                            potions.sku
                                            
                                                            FROM cart_items
                                                            JOIN potions ON cart_items.potion_id = potions.potion_id
                                                            WHERE cart_items.cart_id = :cart_id
                                                            """),
                                                            [{"cart_id": cart_id}]).all()


        transaction = connection.execute(sqlalchemy.text(
                """
                    INSERT INTO transactions
                    (description)
                    VALUES
                    ('cart checkout')
                    RETURNING transaction_id
                """)).one().transaction_id


        cost = 0
        quantity_bought = 0
        for item in potions_bought:
            cost += item.price * item.quantity_bought
            quantity_bought += item.quantity_bought
            connection.execute(sqlalchemy.text(
                                """
                                    INSERT INTO ledger
                                    (transaction_id, inventory_id, change)
                                    VALUES
                                    (:transaction_id, :inventory_id, :potion_quantity)
                                """),
                                [{"transaction_id": transaction, "inventory_id": item.inventory_id, "potion_quantity": item.quantity_bought}])
            
        connection.execute(sqlalchemy.text(
                                """
                                    INSERT INTO ledger
                                    (transaction_id, inventory_id, change)
                                    VALUES
                                    (:transaction_id, (SELECT inventory_id FROM inventory WHERE name = 'gold'), :gold)
                                """),
                                [{"transaction_id": transaction, "gold": cost}])  

    # TODO: cleanup carts

    print(f"total_potions_bought: {quantity_bought}, total_gold_paid: {cost}")
    return {"total_potions_bought": quantity_bought, "total_gold_paid": cost}