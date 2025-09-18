import mysql.connector
from mysql.connector import Error
import os

# As mesmas configurações do seu app.py
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root' # SUA SENHA AQUI
}

# Nome do seu banco de dados
DB_NAME = 'scratch'

def create_server_connection():
    """Cria uma conexão com o servidor MySQL."""
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        print("Conexão com o servidor MySQL bem-sucedida!")
    except Error as e:
        print(f"Erro ao conectar ao servidor MySQL: {e}")
    return connection

def create_database(connection):
    """Cria o banco de dados se ele não existir."""
    cursor = connection.cursor()
    try:
        cursor.execute(f"CREATE DATABASE {DB_NAME} DEFAULT CHARACTER SET 'utf8'")
        print(f"Banco de dados '{DB_NAME}' criado com sucesso!")
    except Error as e:
        print(f"Não foi possível criar o banco de dados '{DB_NAME}': {e}")
    finally:
        cursor.close()

def execute_sql_from_file(connection, filepath):
    """Executa um script SQL a partir de um arquivo."""
    cursor = connection.cursor()
    try:
        print(f"Tentando abrir o arquivo SQL em: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as sql_file:
            sql_commands = sql_file.read().split(';')
            for command in sql_commands:
                if command.strip():
                    cursor.execute(command)
            connection.commit()
        print("Script SQL executado com sucesso!")
    except Error as e:
        print(f"Erro ao executar o script SQL: {e}")
        connection.rollback()
    finally:
        cursor.close()

def setup_database():
    """Função principal para configurar o banco de dados."""
    server_conn = create_server_connection()
    if not server_conn:
        return

    cursor = server_conn.cursor()

    try:
        cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
        print(f"Banco de dados '{DB_NAME}' removido (se existia).")
    except Error as e:
        print(f"Erro ao remover o banco de dados: {e}")
        cursor.close()
        server_conn.close()
        return
    
    create_database(server_conn)
    cursor.close()
    server_conn.close()

    try:
        db_conn_config = db_config.copy()
        db_conn_config['database'] = DB_NAME
        db_connection = mysql.connector.connect(**db_conn_config)
        print(f"Conexão com o banco de dados '{DB_NAME}' estabelecida.")
    except Error as e:
        print(f"Erro ao conectar ao banco de dados '{DB_NAME}': {e}")
        return

    # --- CORREÇÃO APLICADA AQUI ---
    # Agora, o script procura o arquivo na mesma pasta em que ele está.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_script_path = os.path.join(script_dir, 'banco-de-dados.txt')
    
    execute_sql_from_file(db_connection, sql_script_path)

    db_connection.close()
    print("Configuração do banco de dados concluída.")

if __name__ == '__main__':
    print("Iniciando a configuração do banco de dados...")
    setup_database()