
import string
import random
from werkzeug.security import generate_password_hash
from mysql.connector import Error

def generate_username(full_name, connection):
    if not full_name:
        return None
    parts = full_name.split()
    initials = "".join([part[0].lower() for part in parts if part])
    base_username = initials
    username = base_username
    counter = 1
    cursor = connection.cursor()
    while True:
        query = "SELECT COUNT(*) FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        count = cursor.fetchone()[0]
        if count == 0:
            break
        username = f"{base_username}{counter}"
        counter += 1
    cursor.close()
    return username

def generate_random_password(length=7):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password