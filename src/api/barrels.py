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
    order_desc = "BARREL DELIVERERED ID: " + str(order_id) 
    with db.engine.begin() as connection:
        check = connection.execute(sqlalchemy.text("SELECT 1 FROM transactions where description = :desc LIMIT 1"), {'desc': order_desc})
        if check.rowcount > 0:
            print("CONFLICT DETECTED, DESC: " + order_desc)
            return "OK"
        general = connection.execute(sqlalchemy.text("SELECT field_name, sum(quantity) FROM general_ledger GROUP BY field_name")).fetchall()
        for entry in general:
            if(entry[0] == "num_red_ml"): num_red_ml = entry[1]
            elif(entry[0] == "num_green_ml"): num_green_ml = entry[1]
            elif(entry[0] == "num_blue_ml"): num_blue_ml = entry[1]
            elif(entry[0] == "num_dark_ml"): num_dark_ml = entry[1]
            elif(entry[0] == "gold"): gold = entry[1]
            else: print("UNKOWN FIELD: " + str(entry[0]))

    print(barrels_delivered)
    print("Barrel Old ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))
    print("Old Gold: " + str(gold))
    red_diff = 0
    green_diff = 0
    blue_diff = 0
    dark_diff = 0
    gold_diff = 0
    for b in barrels_delivered:
        if b.potion_type == [1, 0, 0, 0]:
            gold_diff -= b.price * b.quantity
            red_diff += b.ml_per_barrel * b.quantity
        elif b.potion_type == [0, 1, 0, 0]:
            gold_diff -= b.price * b.quantity
            green_diff += b.ml_per_barrel * b.quantity
        elif b.potion_type == [0, 0, 1, 0]:
            gold_diff -= b.price * b.quantity
            blue_diff += b.ml_per_barrel * b.quantity
        elif b.potion_type == [0, 0, 0, 1]:
            gold_diff -= b.price * b.quantity
            dark_diff += b.ml_per_barrel * b.quantity
        else:
            print("INVALID BARREL TYPE")
            print(b.potion_type)
            return "OK"

    with db.engine.begin() as connection:
        #Add Transaction
        new_id = connection.execute(sqlalchemy.text("INSERT INTO transactions (description) VALUES (:desc) RETURNING id;"), {'desc': order_desc}).scalar_one()
        print("TRANSACTION RECORDED WITH ID: " + str(new_id))
        connection.execute(sqlalchemy.text("INSERT INTO general_ledger (field_name, quantity, transaction_id) " + 
                                           "VALUES ('gold', :g, :new_id), ('num_red_ml', :red, :new_id), ('num_green_ml', :green, :new_id),"
                                           + "('num_blue_ml', :blue, :new_id), ('num_dark_ml', :dark, :new_id)"), 
                           {'new_id': new_id, 'g': gold_diff, 'red': red_diff, 'green': green_diff, 'blue': blue_diff, 'dark': dark_diff})
    print("ML ADDED: " + str(red_diff) + ":" + str(green_diff) + ":" + str(blue_diff) + ":" + str(dark_diff))
    print("GOLD SPENT" + str(gold_diff))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    print(wholesale_catalog)
    print("\n")
    #Get Values From Database
    with db.engine.begin() as connection:
        min_threshold = connection.execute(sqlalchemy.text("SELECT min_threshold FROM magic")).scalar_one()
        general = connection.execute(sqlalchemy.text("SELECT field_name, sum(quantity) FROM general_ledger GROUP BY field_name")).fetchall()
        for entry in general:
            if(entry[0] == "num_red_ml"): num_red_ml = entry[1]
            elif(entry[0] == "num_green_ml"): num_green_ml = entry[1]
            elif(entry[0] == "num_blue_ml"): num_blue_ml = entry[1]
            elif(entry[0] == "num_dark_ml"): num_dark_ml = entry[1]
            elif(entry[0] == "gold"): gold = entry[1]
            else: print("UNKOWN FIELD: " + str(entry[0]))
    print("Gold:" + str(gold))
    print("Barrel Old ML: " + str(num_red_ml) + ":" + str(num_green_ml) + ":" + str(num_blue_ml) + ":" + str(num_dark_ml))
    #Determine Which Barrels To Buy
    ToBuy = [(int) (num_red_ml < min_threshold), 
             (int) (num_green_ml < min_threshold), 
             (int) (num_blue_ml < min_threshold), 
             (int) (num_dark_ml < min_threshold)]

    if ToBuy == [0,0,0,0]: return []

    redBarrels = []
    greenBarrels = []
    blueBarrels = []
    darkBarrels = []
    
    #Sort Catalog By Barrel Color. Filter out any barrels that are too expensive or not in stock. Only care for colors that need it
    for b in wholesale_catalog:
        if b.quantity < 1: continue
        elif b.potion_type == [1,0,0,0] and b.price <= gold and b.quantity > 0 and ToBuy[0] > 0: redBarrels.append(b)
        elif b.potion_type == [0,1,0,0] and b.price <= gold and b.quantity > 0 and ToBuy[1] > 0: greenBarrels.append(b)
        elif b.potion_type == [0,0,1,0] and b.price <= gold and b.quantity > 0 and ToBuy[2] > 0: blueBarrels.append(b)
        elif b.potion_type == [0,0,0,1] and b.price <= gold and b.quantity > 0 and ToBuy[3] > 0: darkBarrels.append(b)
    
    #Sort By Cheapest
    redBarrels = sorted(redBarrels, key=lambda k: k.price)
    greenBarrels = sorted(greenBarrels, key=lambda k: k.price)
    blueBarrels = sorted(blueBarrels, key=lambda k: k.price)
    darkBarrels = sorted(darkBarrels, key=lambda k: k.price)
    purchase = []

    #Buy one of the cheapest barrel necessary for each potion that needs it. 
    if ToBuy[0] == 1 and len(redBarrels) > 0 and gold >= redBarrels[0].price: 
        purchase.append({
            "sku": redBarrels[0].sku,
            "quantity": 1,
        })
        gold -= redBarrels[0].price
    if ToBuy[1] == 1 and len(greenBarrels) > 0 and gold >= greenBarrels[0].price: 
        purchase.append({
            "sku": greenBarrels[0].sku,
            "quantity": 1,
        })
        gold -= greenBarrels[0].price
    if ToBuy[2] == 1 and len(blueBarrels) > 0 and gold >= blueBarrels[0].price: 
        purchase.append({
            "sku": blueBarrels[0].sku,
            "quantity": 1,
        })
        gold -= blueBarrels[0].price
    if ToBuy[3] == 1 and len(darkBarrels) > 0 and gold >= darkBarrels[0].price: 
        purchase.append({
            "sku": darkBarrels[0].sku,
            "quantity": 1,
        })
        gold -= darkBarrels[0].price

    #Buy an extra barrel for the lowest ml if possible
    if num_red_ml <= num_green_ml and num_red_ml <= num_blue_ml and num_red_ml <= num_dark_ml and ToBuy[0] == 1:
        maxsku = ""
        for x in range(1, len(redBarrels)):
            if gold >= redBarrels[x].price:
                maxsku = redBarrels[x].sku
        if len(maxsku) > 0:
            purchase.append({
                "sku": maxsku,
                "quantity": 1,
            })
    elif num_green_ml <= num_blue_ml and num_green_ml <= num_dark_ml and ToBuy[1] == 1:
        maxsku = ""
        for x in range(1, len(greenBarrels)):
            if gold >= greenBarrels[x].price:
                maxsku = greenBarrels[x].sku
        if len(maxsku) > 0:
            purchase.append({
                "sku": maxsku,
                "quantity": 1,
            })
    elif num_blue_ml <= num_dark_ml and ToBuy[2] == 1:
        maxsku = ""
        for x in range(1, len(blueBarrels)):
            if gold >= blueBarrels[x].price:
                maxsku = blueBarrels[x].sku
        if len(maxsku) > 0:
            purchase.append({
                "sku": maxsku,
                "quantity": 1,
            })
    elif ToBuy[3] == 1:
        maxsku = ""
        for x in range(1, len(darkBarrels)):
            if gold >= darkBarrels[x].price:
                maxsku = darkBarrels[x].sku
        if len(maxsku) > 0:
            purchase.append({
                "sku": maxsku,
                "quantity": 1,
            })

    print("PURCHASED BARRELS: \n")
    print(purchase)
    return purchase
