from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
#import math

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(
                    sqlalchemy.text("SELECT field_name, sum(quantity) FROM ledger GROUP BY field_name")
                    )
        num_red_ml = 0
        num_green_ml = 0
        num_blue_ml = 0
        num_dark_ml = 0
        gold = 0
        for row in result:
            if(row[0] == "num_red_ml"): num_red_ml = row[1]
            elif(row[0] == "num_green_ml"): num_green_ml = row[1]
            elif(row[0] == "num_blue_ml"): num_blue_ml = row[1]
            elif(row[0] == "num_dark_ml"): num_dark_ml = row[1]
            elif(row[0] == "gold"): gold = row[1]
            else:
                print("UNKOWN FIELD: " + str(row[0]))
        potion_count = 0
        potion_count = connection.execute(
                    sqlalchemy.text("SELECT sum(quantity) FROM ledger WHERE potion_id IS NOT NULL")
                ).scalar_one()
    total_barrel = num_red_ml + num_green_ml + num_blue_ml + num_dark_ml

    return {"number_of_potions": potion_count, "ml_in_barrels": total_barrel, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
