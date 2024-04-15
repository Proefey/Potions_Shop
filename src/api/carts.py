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

temp_carts = {}

@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    new_cart_id = len(temp_carts) + 1
    temp_carts[new_cart_id] = [0, 0, 0]
    return {"cart_id": new_cart_id}


class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    if item_sku == "RED_POTION_0":
        temp_carts[cart_id][0] += cart_item.quantity
    elif item_sku == "GREEN_POTION_0":
        temp_carts[cart_id][1] += cart_item.quantity
    elif item_sku == "BLUE_POTION_0":
        temp_carts[cart_id][2] += cart_item.quantity
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(cart_checkout.payment)
    #Subtract Potions, Add Gold
    num_green_potions = 0
    num_red_potions = 0
    num_blue_potions = 0
    gold = 0
    total = temp_carts[cart_id][0] + temp_carts[cart_id][1] + temp_carts[cart_id][2]
    gold_diff = 40 * temp_carts[cart_id][0] + 50 * temp_carts[cart_id][1] + 60 * temp_carts[cart_id][2]
    with db.engine.begin() as connection:
        num_green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar_one()
        num_red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory")).scalar_one()
        num_blue_potions = connection.execute(sqlalchemy.text("SELECT num_blue_potions FROM global_inventory")).scalar_one()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar_one()
        num_red_potions -= temp_carts[cart_id][0]
        num_green_potions -= temp_carts[cart_id][1]
        num_blue_potions -= temp_carts[cart_id][2]
        gold += gold_diff
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = :num"), {'num': num_green_potions})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_potions = :num"), {'num': num_red_potions})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_potions = :num"), {'num': num_blue_potions})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :num"), {'num': gold})
    del temp_carts[cart_id]

    return {"total_potions_bought": total, "total_gold_paid": gold_diff}
