from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
import sqlalchemy.sql.functions as func
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

    metadata_obj = sqlalchemy.MetaData()

    carts = sqlalchemy.Table("carts", metadata_obj, autoload_with=db.engine)
    cart_items = sqlalchemy.Table("cart_items", metadata_obj, autoload_with=db.engine)
    potions = sqlalchemy.Table("potions", metadata_obj, autoload_with=db.engine)
    transactions = sqlalchemy.Table("transactions", metadata_obj, autoload_with=db.engine)

    offset = 0
    if search_page != "":
        offset = int(search_page)

    response = {"previous": "", "next": "", "results": []}
    with db.engine.begin() as connection:
        query = (sqlalchemy.select(carts.c.name.label(search_sort_options.customer_name), 
                                   func.concat(cart_items.c.quantity, ' ', potions.c.sku).label(search_sort_options.item_sku), 
                                   (cart_items.c.base_price * cart_items.c.quantity).label(search_sort_options.line_item_total), 
                                   transactions.c.created_at.label(search_sort_options.timestamp)).
                    join(cart_items, cart_items.c.cart_id == carts.c.cart_id).
                    join(potions, potions.c.potion_id == cart_items.c.potion_id, isouter=True).
                    join(transactions, transactions.c.transaction_id == carts.c.transaction_id, isouter=True).
                    where(transactions.c.created_at != None).
                    where(potions.c.sku.ilike("%"+potion_sku+"%")).
                    where(carts.c.name.ilike("%"+customer_name+"%")).
                    order_by(sqlalchemy.text(sort_col + " " + sort_order)).
                    offset(offset))
        result = connection.execute(query)

        if result.rowcount > 5:
            response["next"] = str(offset + 5)
        if offset > 0:
            response["previous"] = str(offset - 5)

        result = result.fetchmany(5)

    for i, item in enumerate(result):
        response["results"].append(
            {
                "line_item_id": i+1+offset,
                "item_sku": item.item_sku,
                "customer_name": item.customer_name,
                "line_item_total": item.line_item_total,
                "timestamp": item.timestamp
            }
        )

    return response


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
        connection.execute(sqlalchemy.text(
                """
                INSERT INTO cart_items
                (cart_id, potion_id, quantity)
                VALUES
                (:cart_id, (SELECT potion_id FROM potions WHERE sku = :item_sku LIMIT 1), :quantity)
                """),
                [{"cart_id": cart_id, "item_sku": item_sku, "quantity": cart_item.quantity}])
        
        connection.execute(sqlalchemy.text(
                """
                    UPDATE cart_items SET
                    base_price = (SELECT price FROM potions WHERE potions.sku = :item_sku LIMIT 1)
                    WHERE cart_items.cart_id = :cart_id AND cart_items.potion_id = (SELECT potion_id FROM potions WHERE sku = :item_sku LIMIT 1)
                """),
                [{"cart_id": cart_id, "item_sku": item_sku}])

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
                                                            potions.inventory_id,
                                                            cart_items.base_price AS price
                                            
                                                            FROM cart_items
                                                            LEFT JOIN potions ON cart_items.potion_id = potions.potion_id
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

        connection.execute(sqlalchemy.text(
                """
                    UPDATE carts SET
                    transaction_id = :transaction
                    WHERE carts.cart_id = :cart_id
                """),
                [{"transaction": transaction, "cart_id": cart_id}])

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
                                [{"transaction_id": transaction, "inventory_id": item.inventory_id, "potion_quantity": -item.quantity_bought}])
            
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