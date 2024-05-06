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
    potion_dict = []
    with db.engine.begin() as connection:
        check = connection.execute(sqlalchemy.text("SELECT 1 FROM transactions where description = :desc LIMIT 1"), {'desc': order_desc})
        #Prevent Re-ordering
        if check.rowcount > 0:
            print("CONFLICT DETECTED, DESC: " + order_desc)
            return "OK"
        
        new_id = connection.execute(sqlalchemy.text("INSERT INTO transactions (description) VALUES (:desc) RETURNING id;"), {'desc': order_desc}).scalar_one()
        print("TRANSACTION RECORDED WITH ID: " + str(new_id))

        potion_info = connection.execute(sqlalchemy.text("SELECT sku, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml from potions")).fetchall()
        for sku, red, green, blue, dark in potion_info: 
            potion_dict.append((sku, [red, green, blue, dark]))

        general = connection.execute(sqlalchemy.text("SELECT field_name, sum(quantity) FROM general_ledger GROUP BY field_name")).fetchall()
        for entry in general:
            if(entry[0] == "num_red_ml"): num_red_ml = entry[1]
            elif(entry[0] == "num_green_ml"): num_green_ml = entry[1]
            elif(entry[0] == "num_blue_ml"): num_blue_ml = entry[1]
            elif(entry[0] == "num_dark_ml"): num_dark_ml = entry[1]
            elif(entry[0] != "gold"): print("UNKOWN FIELD: " + str(entry[0]))

    print(potions_delivered)
    print(potion_dict)
    print("Bottle Old ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))
    red_diff = 0
    green_diff = 0
    blue_diff = 0
    dark_diff = 0
    new_potions = []
    for p in potions_delivered:
        new_sku = None
        for p1 in potion_dict:
            if p.potion_type == p1[1]:
                new_sku = p1[0]
        if new_sku is None:
            print("Unknown Potion: " + str(p))
            continue
        print("Updating Existing POTION: " + str(new_sku) + " BY: " + str(p.quantity))
        red_diff -= p.potion_type[0] * p.quantity
        green_diff -= p.potion_type[1] * p.quantity
        blue_diff -= p.potion_type[2] * p.quantity
        dark_diff -= p.potion_type[3] * p.quantity
        new_potions.append([new_sku, p.quantity, new_id])
    print(new_potions)
    if(len(new_potions) < 1): return "OK"

    newstr = "INSERT INTO potion_ledger (potion_sku, quantity, transaction_id) VALUES"
    for potion in new_potions:
        newstr += " ('%s', %d, %d)," % (potion[0], potion[1], potion[2])
    newstr = newstr[:-1]
    print(newstr)

    with db.engine.begin() as connection:
        
        connection.execute(sqlalchemy.text("INSERT INTO general_ledger (field_name, quantity, transaction_id) " + 
                                            "VALUES ('num_red_ml', :red, :new_id), ('num_green_ml', :green, :new_id),"
                                            + "('num_blue_ml', :blue, :new_id), ('num_dark_ml', :dark, :new_id)"), 
                            {'new_id': new_id, 'red': red_diff, 'green': green_diff, 'blue': blue_diff, 'dark': dark_diff})
        connection.execute(sqlalchemy.text(newstr))
        
    print("ML USED: " + str(red_diff) + ":" + str(green_diff) + ":" + str(blue_diff) + ":" + str(dark_diff))
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

class Potion_Plan:
    def __init__(self, sku, inv, type):
        self.sku = sku
        self.inventory = inv
        self.potion_type = type
    def __str__(self):
        return "SKU: " + str(self.sku) + ", QUANTITY:" + str(self.inventory) + ", POTION: " + str(self.potion_type[0]) + ":" + str(self.potion_type[1]) + ":" + str(self.potion_type[2]) + ":" + str(self.potion_type[3])
    sku: str
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
    num_red_ml = 0
    num_green_ml = 0
    num_blue_ml = 0
    num_dark_ml = 0
    potion_dict = []
    with db.engine.begin() as connection:
        min_potions = connection.execute(sqlalchemy.text("SELECT min_potions FROM magic")).scalar_one()
        general = connection.execute(sqlalchemy.text("SELECT field_name, sum(quantity) FROM general_ledger GROUP BY field_name")).fetchall()
        for entry in general:
            if(entry[0] == "num_red_ml"): num_red_ml = entry[1]
            elif(entry[0] == "num_green_ml"): num_green_ml = entry[1]
            elif(entry[0] == "num_blue_ml"): num_blue_ml = entry[1]
            elif(entry[0] == "num_dark_ml"): num_dark_ml = entry[1]
            elif(entry[0] != "gold"): print("UNKNOWN FIELD: " + str(entry[0]))
        print("Bottle Old ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))

        potion_info = connection.execute(sqlalchemy.text("SELECT sku, COALESCE(SUM(potion_ledger.quantity), 0) as inventory,num_red_ml, num_green_ml, num_blue_ml, num_dark_ml from potions LEFT JOIN potion_ledger ON potion_ledger.potion_sku = sku GROUP BY sku")).fetchall()
        for sku, inventory, red, green, blue, dark in potion_info: 
            if inventory is None: inventory = 0
            if inventory < min_potions:
                potions.append(Potion_Plan(sku, inventory, [red, green, blue, dark]))
                print(potions[len(potions) - 1])
        print(potion_dict)
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