from fastapi import APIRouter, Depends
#from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE potions SET inventory = 0"))
        connection.execute(sqlalchemy.text("TRUNCATE cart_items, carts, ledger, transactions"))
        connection.execute(sqlalchemy.text("INSERT INTO ledger (field_name, quantity) " + 
                                        "VALUES (:field_name, :quantity)"), 
                        {'field_name': "gold", 'quantity': 100})
    return "OK"

