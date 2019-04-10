from schedulit import Termin, login
from getpass import getpass

try:
    from .schedulit_credentials import username, password
except ModuleNotFoundError:
    username = input("Username: ")
    password = getpass("Password: ")

t = Termin("RV", 'sc15ba4a2c4b907a', "2", "08:00", "08:45",
           "Baze podataka 1 (P)")
login(username, password)
