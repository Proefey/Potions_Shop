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
    print(search_page)
    
    ORDER_STR = " ORDER BY " + sort_col + " " + sort_order + ", cart_items.id DESC"
    NAME_FILTER = ""
    ITEM_FILTER = ""
    if(len(customer_name) > 0): NAME_FILTER = " AND carts.customer = \'" + customer_name + "\'"
    if(len(potion_sku) > 0): ITEM_FILTER = " WHERE potion_sku = \'" + potion_sku + "\'"
    offset = 0
    previous_str = ""
    next_str = ""
    if search_page.isnumeric():
        offset = int(search_page)
        if offset > 4:
            previous_str = str(offset - 5)
    with db.engine.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT cart_items.id, potion_sku as item_sku, quantity as line_item_total, carts.customer as customer_name, transactions.created_at as timestamp from cart_items"
                                              +" JOIN carts ON carts.id = cart_items.cart_id" + NAME_FILTER
                                              +" JOIN transactions on transactions.cart_id = cart_items.cart_id"
                                              + ITEM_FILTER
                                              + ORDER_STR
                                              +" OFFSET :offset")
                                              ,{'offset': offset})
        total_rows = result.rowcount
        print(total_rows)
        if total_rows > 5:
            next_str = str(offset + 5)
        json = []
        count = 0
        for row in result:
            if count > 4: break
            json.append(
                {
                    "line_item_id": row.id,
                    "item_sku": row.item_sku,
                    "customer_name": row.customer_name,
                    "line_item_total": row.line_item_total,
                    "timestamp": row.timestamp,
                }
            )
            count += 1

    return {
        "previous": previous_str,
        "next": next_str,
        "results": json
    }
'''
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
'''

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
        sku, inventory = connection.execute(sqlalchemy.text("SELECT potion_sku, COALESCE(SUM(quantity), 0) as inventory from potion_ledger where potion_sku = :item_sku GROUP BY potion_sku"), {'item_sku': item_sku}).fetchone()
        print("FOUND POTION SKU: " + str(sku) + ", INVENTORY: " + str(inventory))
        if inventory < cart_item.quantity or inventory < 1 or cart_item.quantity < 1:
            print("INVALID NUMBER OF POTIONS ADDED TO CART: " + str(cart_item.quantity) + ", IN INVENTORY: " + str(inventory))
            return "OK"
        connection.execute(sqlalchemy.text("INSERT INTO cart_items (cart_id, quantity, potion_sku) SELECT :cart_id, :quantity, :item_sku"), {'cart_id': cart_id, 'quantity': cart_item.quantity, 'item_sku': item_sku})
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
        result = connection.execute(sqlalchemy.text("SELECT quantity, potion_sku FROM cart_items WHERE cart_id = :id"), {'id': cart_id}).fetchall()
        new_id = connection.execute(sqlalchemy.text("INSERT INTO transactions (description, cart_id) VALUES (:desc, :cart_id) RETURNING id;"), {'desc': order_desc, 'cart_id': cart_id}).scalar_one()
        print("TRANSACTION RECORDED WITH ID: " + str(new_id))
        for quantity, potion_sku in result:
            total += quantity
            price = connection.execute(sqlalchemy.text("SELECT price FROM potions WHERE sku = :sku"), {'sku': potion_sku}).scalar_one()
            print("CHECKOUT ITEM: " + str(potion_sku) + ", QUANTITY:" + str(quantity))
            gold_diff += price * quantity
            connection.execute(sqlalchemy.text("INSERT INTO potion_ledger (potion_sku, quantity, transaction_id) " + 
                                        "VALUES (:potion_sku, :quantity, :new_id)"), 
                        {'new_id': new_id, 'potion_sku': potion_sku, 'quantity': quantity * -1})
            #connection.execute(sqlalchemy.text("DELETE FROM cart_items WHERE cart_id = :id"), {'id': cart_id})
            #connection.execute(sqlalchemy.text("DELETE FROM carts WHERE id = :id"), {'id': cart_id})

        connection.execute(sqlalchemy.text("INSERT INTO general_ledger (field_name, quantity, transaction_id) " + 
                                        "VALUES (:field_name, :quantity, :new_id)"), 
                        {'new_id': new_id, 'field_name': "gold", 'quantity': gold_diff})

    return {"total_potions_bought": total, "total_gold_paid": gold_diff}
