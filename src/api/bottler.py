from fastapi import APIRouter, Depends
#from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    num_green_potion = 0
    num_green_ml = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in result:
            num_green_ml = row[3]
            num_green_potion = row[2]

    for p in potions_delivered:
        if p.potion_type == [0, 100, 0, 0]:
            num_green_potion += p.quantity
            num_green_ml -= p.quantity * 100

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = :num"), {'num': num_green_potion})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :num"), {'num': num_green_ml})
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.
    num_green_ml = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
        for row in result:
            num_green_ml = row[3]
    num_green_potion_add = int(num_green_ml / 100)
    if num_green_potion_add < 1:
        return []
    return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": num_green_potion_add,
            }
        ]

if __name__ == "__main__":
    print(get_bottle_plan())