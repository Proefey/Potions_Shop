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
        result2 = connection.execute(sqlalchemy.text("SELECT id, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, sku, price FROM potions")).fetchall()
        potion_to_inv = connection.execute(sqlalchemy.text("SELECT potion_id, sum(quantity) FROM ledger GROUP BY potion_id")).fetchall()
        potion_dict = {p[0]: p[1] for p in potion_to_inv}
        print(potion_dict)
        for id, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, sku, price in result2:
            inventory = potion_dict.get(id)
            if inventory is not None and inventory > 0:
                new_catalog.append({
                    "sku": sku,
                    "name": sku,
                    "quantity": inventory,
                    "price": price,
                    "potion_type": [num_red_ml, num_green_ml, num_blue_ml, num_dark_ml],
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