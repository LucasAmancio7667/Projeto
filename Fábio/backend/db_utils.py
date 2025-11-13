import mysql.connector
from mysql.connector import Error
import time

# Configurações do Banco de Dados MySQL
db_config = {
    'host': 'localhost',
    'database': 'Scratch',
    'user': 'root',
    'password': 'root' # SUA SENHA AQUI
}

def create_db_connection():
    """Cria e retorna uma conexão com o banco de dados, com retries."""
    connection = None
    attempts = 3
    wait_time = 1 # segundos

    for i in range(attempts):
        try:
            connection = mysql.connector.connect(**db_config)
            if connection.is_connected():
                # Sucesso!
                return connection
        except Error as e:
            print(f"Erro ao conectar ao MySQL (Tentativa {i+1}/{attempts}): {e}")
            if i < attempts - 1:
                time.sleep(wait_time) # Espera antes de tentar de novo
            else:
                # Se todas as tentativas falharem, retorna None
                print("Todas as tentativas de conexão com o banco de dados falharam.")
                return None
    return None