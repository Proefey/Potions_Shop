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
    num_green_potions = 0
    num_red_potions = 0
    num_blue_potions = 0
    num_green_ml = 0
    num_red_ml = 0
    num_blue_ml = 0
    with db.engine.begin() as connection:
        num_green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar_one()
        num_red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory")).scalar_one()
        num_blue_potions = connection.execute(sqlalchemy.text("SELECT num_blue_potions FROM global_inventory")).scalar_one()
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()
        num_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar_one()
        num_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar_one()

    for p in potions_delivered:
        if p.potion_type == [0, 100, 0, 0]:
            num_green_potions += p.quantity
            num_green_ml -= p.quantity * 100
        if p.potion_type == [100, 0, 0, 0]:
            num_red_potions += p.quantity
            num_red_ml -= p.quantity * 100
        if p.potion_type == [0, 0, 100, 0]:
            num_blue_potions += p.quantity
            num_blue_ml -= p.quantity * 100

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = :num"), {'num': num_green_potions})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_potions = :num"), {'num': num_red_potions})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_potions = :num"), {'num': num_blue_potions})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :num"), {'num': num_green_ml})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = :num"), {'num': num_red_ml})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_ml = :num"), {'num': num_blue_ml})
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
    num_red_ml = 0
    num_blue_ml = 0
    with db.engine.begin() as connection:
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()
        num_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar_one()
        num_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar_one()
    num_green_potion_add = int(num_green_ml / 100)
    num_red_potion_add = int(num_red_ml / 100)
    num_blue_potion_add = int(num_blue_ml / 100)
    bottles = []
    if num_green_potion_add > 0:
        bottles.append({
            "potion_type": [0, 100, 0, 0],
            "quantity": num_green_potion_add,
        })
    if num_red_potion_add > 0:
        bottles.append({
            "potion_type": [100, 0, 0, 0],
            "quantity": num_red_potion_add,
        })
    if num_blue_potion_add > 0:
        bottles.append({
            "potion_type": [0, 0, 100, 0],
            "quantity": num_blue_potion_add,
        })
    return bottles

if __name__ == "__main__":
    print(get_bottle_plan())