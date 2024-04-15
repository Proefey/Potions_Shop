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
    num_red_ml = 0
    num_blue_ml = 0

    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar_one()
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()
        num_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar_one()
        num_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar_one()

    for b in barrels_delivered:
        gold -= b.price * b.quantity
        num_red_ml += b.ml_per_barrel * b.potion_type[0] * b.quantity
        num_green_ml += b.ml_per_barrel * b.potion_type[1] * b.quantity
        num_blue_ml += b.ml_per_barrel * b.potion_type[2] * b.quantity

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :num"), {'num': gold})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :num"), {'num': num_green_ml})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = :num"), {'num': num_red_ml})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_ml = :num"), {'num': num_blue_ml})

    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    num_green_potions = 0
    num_red_potions = 0
    num_blue_potions = 0
    gold = 0
    
    #Get Values From Database
    with db.engine.begin() as connection:
        num_green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar_one()
        num_red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory")).scalar_one()
        num_blue_potions = connection.execute(sqlalchemy.text("SELECT num_blue_potions FROM global_inventory")).scalar_one()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar_one()

    #Determine Which Barrels To Buy
    ToBuy = [(int) (num_red_potions < 10), (int) (num_green_potions < 10), (int) (num_blue_potions < 10), 0]
    if ToBuy == [0,0,0,0]: return []

    redBarrels = []
    greenBarrels = []
    blueBarrels = []
    #Sort Catalog
    for b in wholesale_catalog:
        if b.quantity < 1: continue
        elif b.potion_type[0] > 0 and ToBuy[0] > 0: redBarrels.append(b)
        elif b.potion_type[1] > 0 and ToBuy[1] > 0: greenBarrels.append(b)
        elif b.potion_type[2] > 0 and ToBuy[2] > 0: blueBarrels.append(b)
    
    #Sort By Price
    redBarrels = sorted(redBarrels, key=lambda k: k.price)
    greenBarrels = sorted(greenBarrels, key=lambda k: k.price)
    blueBarrels = sorted(blueBarrels, key=lambda k: k.price)
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

    #Objectively Unnecessarily Complicated Barrel Logic
    if num_red_potions <= num_green_potions and num_red_potions <= num_blue_potions and ToBuy[0] == 1:
        maxsku = ""
        for x in range(1, len(redBarrels)):
            if gold >= redBarrels[x].price:
                maxsku = redBarrels[x].sku
        if len(maxsku) > 0:
            purchase.append({
                "sku": maxsku,
                "quantity": 1,
            })
    elif num_green_potions <= num_blue_potions and ToBuy[1] == 1:
        maxsku = ""
        for x in range(1, len(greenBarrels)):
            if gold >= greenBarrels[x].price:
                maxsku = greenBarrels[x].sku
        if len(maxsku) > 0:
            purchase.append({
                "sku": maxsku,
                "quantity": 1,
            })
    elif ToBuy[2] == 1:
        maxsku = ""
        for x in range(1, len(blueBarrels)):
            if gold >= blueBarrels[x].price:
                maxsku = blueBarrels[x].sku
        if len(maxsku) > 0:
            purchase.append({
                "sku": maxsku,
                "quantity": 1,
            })

    return purchase
