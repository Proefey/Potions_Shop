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
    order_desc = "BOTTLE DELIVERERED ID: " + str(order_id) 
    with db.engine.begin() as connection:
        check = connection.execute(sqlalchemy.text("SELECT 1 FROM transactions where description = :desc LIMIT 1"), {'desc': order_desc})
        #Prevent Re-ordering
        if check.rowcount > 0:
            print("CONFLICT DETECTED, DESC: " + order_desc)
            return "OK"
        new_id = connection.execute(sqlalchemy.text("INSERT INTO transactions (description) VALUES (:desc) RETURNING id;"), {'desc': order_desc}).scalar_one()
        print("TRANSACTION RECORDED WITH ID: " + str(new_id))
        result = connection.execute(
            sqlalchemy.text("SELECT field_name, sum(quantity) FROM ledger GROUP BY field_name")
            )
        num_red_ml = 0
        num_green_ml = 0
        num_blue_ml = 0
        num_dark_ml = 0
        for row in result:
            if(row[0] == "num_red_ml"): num_red_ml = row[1]
            elif(row[0] == "num_green_ml"): num_green_ml = row[1]
            elif(row[0] == "num_blue_ml"): num_blue_ml = row[1]
            elif(row[0] == "num_dark_ml"): num_dark_ml = row[1]
            else:
                print("UNKOWN FIELD: " + str(row[0]))
        print(potions_delivered)
        print("Bottle Old ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))
        red_diff = 0
        green_diff = 0
        blue_diff = 0
        dark_diff = 0
        for p in potions_delivered:
            result = connection.execute(sqlalchemy.text("SELECT id, sku FROM potions WHERE num_red_ml = :num0 AND num_green_ml = :num1 AND num_blue_ml = :num2 AND num_dark_ml = :num3"), {'num0': p.potion_type[0], 'num1': p.potion_type[1], 'num2': p.potion_type[2], 'num3': p.potion_type[3]})
            if result is not None and result.rowcount > 0:
                potion_tuple = result.fetchone()
                potion_id = potion_tuple[0]
                new_sku = potion_tuple[1]
                print("Updating Existing POTION: " + str(new_sku) + " BY: " + str(p.quantity))
                red_diff -= p.potion_type[0] * p.quantity
                green_diff -= p.potion_type[1] * p.quantity
                blue_diff -= p.potion_type[2] * p.quantity
                dark_diff -= p.potion_type[3] * p.quantity
                connection.execute(sqlalchemy.text("INSERT INTO ledger (potion_id, quantity, transaction_id) " + 
                                        "VALUES (:potion_id, :quantity, :new_id)"), 
                        {'new_id': new_id, 'potion_id': potion_id, 'quantity': p.quantity})
            else:
                print("UNKNOWN POTION" + str(p.potion_type) + "\n")
                
        connection.execute(sqlalchemy.text("INSERT INTO ledger (field_name, quantity, transaction_id) " + 
                                        "VALUES ('num_red_ml', :red, :new_id), ('num_green_ml', :green, :new_id),"
                                        + "('num_blue_ml', :blue, :new_id), ('num_dark_ml', :dark, :new_id)"), 
                        {'new_id': new_id, 'red': red_diff, 'green': green_diff, 'blue': blue_diff, 'dark': dark_diff})
    
    print("ML USED: " + str(red_diff) + ":" + str(green_diff) + ":" + str(blue_diff) + ":" + str(dark_diff))
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
        min_potions = connection.execute(sqlalchemy.text("SELECT min_potions FROM magic")).scalar_one()
        result = connection.execute(
            sqlalchemy.text("SELECT field_name, sum(quantity) FROM ledger GROUP BY field_name")
            )
        num_red_ml = 0
        num_green_ml = 0
        num_blue_ml = 0
        num_dark_ml = 0
        for row in result:
            if(row[0] == "num_red_ml"): num_red_ml = row[1]
            elif(row[0] == "num_green_ml"): num_green_ml = row[1]
            elif(row[0] == "num_blue_ml"): num_blue_ml = row[1]
            elif(row[0] == "num_dark_ml"): num_dark_ml = row[1]
            else:
                print("UNKNOWN FIELD: " + str(row[0]))
        print("Bottle Old ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))

        result2 = connection.execute(sqlalchemy.text("SELECT id, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM potions")).fetchall()
        potion_to_inv = connection.execute(sqlalchemy.text("SELECT potion_id, sum(quantity) FROM ledger GROUP BY potion_id")).fetchall()
        potion_dict = {p[0]: p[1] for p in potion_to_inv}
        print(potion_dict)
        for id, red, green, blue, dark in result2:
            inventory = potion_dict.get(id)
            if inventory is None: inventory = 0
            if inventory < min_potions:
                potions.append(Potion_Plan(id, inventory, [red, green, blue, dark]))
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