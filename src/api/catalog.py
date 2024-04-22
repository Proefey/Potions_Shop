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
        result2 = connection.execute(sqlalchemy.text("SELECT id, inventory, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, sku, price FROM potions")).fetchall()
        for row in result2:
            if row[1] > 0:
                new_catalog.append({
                    "sku": row[6],
                    "name": row[6],
                    "quantity": row[1],
                    "price": row[7],
                    "potion_type": [row[2], row[3], row[4], row[5]],
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