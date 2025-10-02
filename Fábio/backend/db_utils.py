import mysql.connector
from mysql.connector import Error

# Configurações do Banco de Dados MySQL
db_config = {
    'host': 'localhost',
    'database': 'Scratch',
    'user': 'root',
    'password': 'root' # SUA SENHA AQUI
}

def create_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
    return connection