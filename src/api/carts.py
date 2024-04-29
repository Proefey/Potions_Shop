from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

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
    print(customers)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("INSERT INTO carts (customer) VALUES (:name) RETURNING id;"), {'name': new_cart.customer_name})
        new_id = result.scalar_one()
        print("CUSTOMER CART CREATED: " + str(new_id))
    return {"cart_id": new_id}


class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT id FROM carts WHERE id = :cart LIMIT 1"), {'cart': cart_id})
        if result.rowcount < 1:
            print("CART_ID NOT FOUND: " + str(cart_id))
            return "OK"
        result2 = connection.execute(sqlalchemy.text("SELECT inventory FROM potions WHERE sku = :sku LIMIT 1"), {'sku': item_sku})
        if result2.rowcount < 1:
            print("ITEM_SKU NOT FOUND: " + str(item_sku))
            return "OK"
        inventory = result2.fetchone()[0]
        if inventory < cart_item.quantity:
            print("INVALID NUMBER OF POTIONS ADDED TO CART: " + str(cart_item.quantity) + ", IN INVENTORY: " + str(inventory))
            return "OK"
        connection.execute(sqlalchemy.text("INSERT INTO cart_items (cart_id, quantity, potion_id) SELECT :cart_id, :quantity, potions.id FROM potions WHERE potions.sku = :item_sku"), {'cart_id': cart_id, 'quantity': cart_item.quantity, 'item_sku': item_sku})
        print("ADDED " + str(cart_item.quantity) + " OF " + str(item_sku) + " TO " + str(cart_id))
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(cart_checkout.payment)
    #Subtract Potions, Add Gold
    total = 0
    gold_diff = 0
    print("CHECKOUT CART: " + str(cart_id))
    order_desc = "CART CHECKOUT DELIVERERED ID: " + str(cart_id)
    with db.engine.begin() as connection:
        check = connection.execute(sqlalchemy.text("SELECT 1 FROM transactions where description = :desc LIMIT 1"), {'desc': order_desc})
        #Prevent Re-ordering
        if check.rowcount > 0:
            print("CONFLICT DETECTED, DESC: " + order_desc)
            return "OK"
        result = connection.execute(sqlalchemy.text("SELECT quantity, potion_id FROM cart_items WHERE cart_id = :id"), {'id': cart_id}).fetchall()
        new_id = connection.execute(sqlalchemy.text("INSERT INTO transactions (description) VALUES (:desc) RETURNING id;"), {'desc': order_desc}).scalar_one()
        print("TRANSACTION RECORDED WITH ID: " + str(new_id))
        for quantity, potion_id in result:
            total += quantity
            sku, price = connection.execute(sqlalchemy.text("SELECT sku, price FROM potions WHERE id = :id"), {'id': potion_id}).fetchone()
            print("CHECKOUT ITEM: " + str(sku) + ", QUANTITY:" + str(quantity))
            gold_diff += price * quantity
            connection.execute(sqlalchemy.text("INSERT INTO ledger (potion_id, quantity, transaction_id) " + 
                                        "VALUES (:potion_id, :quantity, :new_id)"), 
                        {'new_id': new_id, 'potion_id': potion_id, 'quantity': quantity * -1})
            connection.execute(sqlalchemy.text("DELETE FROM cart_items WHERE cart_id = :id"), {'id': cart_id})
            #connection.execute(sqlalchemy.text("DELETE FROM carts WHERE id = :id"), {'id': cart_id})

        connection.execute(sqlalchemy.text("INSERT INTO ledger (field_name, quantity, transaction_id) " + 
                                        "VALUES (:field_name, :quantity, :new_id)"), 
                        {'new_id': new_id, 'field_name': "gold", 'quantity': gold_diff})

    return {"total_potions_bought": total, "total_gold_paid": gold_diff}
