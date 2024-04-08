from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

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
    #Add ML, SUB Gold
    gold = 0
    num_green_ml = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in result:
            gold = row[4]
            num_green_ml = row[3]
    gold_diff = 0
    green_ml_diff = 0
    for b in barrels_delivered:
        if(b.potion_type[1] > 0):
            gold_diff += b.price * b.quantity
            green_ml_diff += b.ml_per_barrel * b.potion_type[1] * b.quantity

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :num"), {'num': gold - gold_diff})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :num"), {'num': num_green_ml + green_ml_diff})
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    num_green_potion = 0
    purchase_barrel = 0
    gold = 0
    purchase_sku = ""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in result:
            num_green_potion = row[2]
            gold = row[4]
    for b in wholesale_catalog:
        if b.potion_type[1] > 0 and b.quantity > 0:
            if gold >= b.price and num_green_potion < 10:
                purchase_barrel = 1
                purchase_sku = b.sku
    if purchase_barrel == 0:
        return []
    print(wholesale_catalog)

    return [
        {
            "sku": purchase_sku,
            "quantity": purchase_barrel,
        }
    ]

