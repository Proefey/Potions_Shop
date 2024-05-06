from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

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

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    new_catalog = []
    with db.engine.begin() as connection:
        potion_info = connection.execute(sqlalchemy.text("SELECT sku, COALESCE(SUM(potion_ledger.quantity), 0) as inventory,num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, price from potions LEFT JOIN potion_ledger ON potion_ledger.potion_sku = sku GROUP BY sku")).fetchall()
        for sku, inventory, red, green, blue, dark, price in potion_info: 
            if inventory is not None and inventory > 0:
                new_catalog.append({
                    "sku": sku,
                    "name": sku,
                    "quantity": inventory,
                    "price": price,
                    "potion_type": [red, green, blue, dark],
                })

    return new_catalog

'''
        new_catalog.append({
                "sku": "BLUE_POTION_0",
                "name": "blue potion",
                "quantity": num_blue_potions,
                "price": 60,
                "potion_type": [0, 0, 100, 0],
            })
'''