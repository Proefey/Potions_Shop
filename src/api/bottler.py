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
    print(potions_delivered)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory")).fetchone()
        num_red_ml = result[0]
        num_green_ml = result[1]
        num_blue_ml = result[2]
        num_dark_ml = result[3]

        print("Bottle Old ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))
        for p in potions_delivered:
            result = connection.execute(sqlalchemy.text("SELECT id, sku FROM potions WHERE num_red_ml = :num0 AND num_green_ml = :num1 AND num_blue_ml = :num2 AND num_dark_ml = :num3"), {'num0': p.potion_type[0], 'num1': p.potion_type[1], 'num2': p.potion_type[2], 'num3': p.potion_type[3]})
            if result is not None and result.rowcount > 0:
                potion_tuple = result.fetchone()
                new_id = potion_tuple[0]
                new_sku = potion_tuple[1]
                print("Updating Existing POTION: " + str(new_sku) + " BY: " + str(p.quantity))
                num_red_ml -= p.potion_type[0] * p.quantity
                num_green_ml -= p.potion_type[1] * p.quantity
                num_blue_ml -= p.potion_type[2] * p.quantity
                num_dark_ml -= p.potion_type[3] * p.quantity
                connection.execute(sqlalchemy.text("UPDATE potions SET inventory = inventory + :num WHERE id = :id"), {'num': p.quantity, 'id': new_id})
            else:
                print("UNKNOWN POTION" + str(p.potion_type) + "\n")
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = :num0, num_green_ml = :num1, num_blue_ml = :num2, num_dark_ml = :num3"), {'num0': num_red_ml, 'num1': num_green_ml, 'num2': num_blue_ml, 'num3': num_dark_ml})
    
    print("Bottle New ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

class Potion_Plan:
    def __init__(self, id, inv, type):
        self.id = id
        self.inventory = inv
        self.potion_type = type
    def __str__(self):
        return "ID: " + str(self.id) + ", QUANTITY:" + str(self.inventory) + "POTION: " + str(self.potion_type[0]) + ":" + str(self.potion_type[1]) + ":" + str(self.potion_type[2]) + ":" + str(self.potion_type[3])
    id: int
    inventory: int
    potion_type: list[int]

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.
    potions = []
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory")).fetchone()
        num_red_ml = result[0]
        num_green_ml = result[1]
        num_blue_ml = result[2]
        num_dark_ml = result[3]
        min_potions = connection.execute(sqlalchemy.text("SELECT min_potions FROM magic")).scalar_one()
        result2 = connection.execute(sqlalchemy.text("SELECT id, inventory, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM potions")).fetchall()
        for row in result2:
            if row[1] < min_potions:
                potions.append(Potion_Plan(row[0], row[1], [row[2], row[3], row[4], row[5]]))
                print(potions[len(potions) - 1])
    print("Bottle Plan Old ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))
    bottles = []
    if len(potions) < 1:
        return bottles
    i = 0
    count = 0
    while i < len(potions):
        #Check if potion can be created
        if potions[i].potion_type[0] <= num_red_ml and potions[i].potion_type[1] <= num_green_ml and potions[i].potion_type[2] <= num_blue_ml and potions[i].potion_type[3] <= num_dark_ml and potions[i].inventory < min_potions:
            num_red_ml -= potions[i].potion_type[0]
            num_green_ml -= potions[i].potion_type[1]
            num_blue_ml -= potions[i].potion_type[2]
            num_dark_ml -= potions[i].potion_type[3]
            potions[i].inventory += 1
            count += 1
        else:
            if count > 0:
                bottles.append({
                    "potion_type": potions[i].potion_type,
                    "quantity": count,
                })
            i += 1
            count = 0

    print("Bottle Plan New ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))
    return bottles

'''
        bottles.append({
            "potion_type": [0, 0, 100, 0],
            "quantity": num_blue_potion_add,
        })
'''

if __name__ == "__main__":
    print(get_bottle_plan())