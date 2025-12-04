import mysql.connector
from mysql.connector import Error
import time
from flask import jsonify # Novo import para retorno unificado

# Configurações do Banco de Dados MySQL
db_config = {
    'host': 'localhost',
    'database': 'scratch',
    'user': 'root',
    'password': 'root' # SUA SENHA AQUI - Certifique-se de usar sua senha real aqui
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
            # print(f"Erro ao conectar ao MySQL (Tentativa {i+1}/{attempts}): {e}")
            if i < attempts - 1:
                time.sleep(wait_time) # Espera antes de tentar de novo
            else:
                # print("Todas as tentativas de conexão com o banco de dados falharam.")
                return None
    return None

# ====================================================================================================
# PADRÃO TEMPLATE METHOD: CENTRALIZAÇÃO DO BOILERPLATE DE TRANSAÇÃO
# ====================================================================================================

"""def execute_db_transaction(op_function, *args, rollback_message='Erro interno do servidor.', **kwargs):#L39-L123
  
    connection = create_db_connection()

    # Template Step 1 (Hook): Checa a disponibilidade
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    try:
        cursor = connection.cursor()
        
        # Template Step 2 (Método Primitivo): A lógica de negócio (Hook)
        # op_function deve retornar (response_data, status_code, extra_info)
        response_data, status_code, extra_info = op_function(connection, cursor, *args, **kwargs)
        
        # Template Step 3 (Fixo): Commit em caso de sucesso
        connection.commit()
        
        # Prepara a resposta (assume que response_data é um dicionário)
        if 'success' not in response_data:
             response_data['success'] = True
             
        # Adiciona mensagens de erro específicas do MySQL se for um rollback
        if extra_info and extra_info.get('error_code') == 1062:
             response_data['success'] = False
             response_data['message'] = extra_info.get('error_message')
             status_code = 409
             
        return jsonify(response_data), status_code
        
    except Error as e:
        # Template Step 4 (Fixo): Rollback em caso de falha (Garante a consistência)
        connection.rollback()
        
        # Tratamento de Erros Comuns
        if e.errno == 1062: # Erro de Duplicidade (Unique Constraint)
            return jsonify({'success': False, 'message': f'Erro: Um registro com dados duplicados já existe. Detalhes: {e.msg}'}), 409
            
        # print(f"Erro no Template Method: {e}")
        return jsonify({'success': False, 'message': rollback_message}), 500
        
    except ValueError as ve:
        # Trata erros de validação da lógica de negócio (Hook)
        return jsonify({'success': False, 'message': str(ve)}), 400
        
    finally:
        # Template Step 5 (Fixo): Fechar a conexão
        if connection.is_connected():
            connection.close()

def execute_db_query(query_function, *args, error_message='Erro interno do servidor', **kwargs):
   
    connection = create_db_connection()
    
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    try:
        # Usa dictionary=True para facilitar o retorno JSON
        cursor = connection.cursor(dictionary=True)
        
        # O 'Hook' ou 'Método Primitivo' a ser implementado por cada rota
        # query_function deve retornar (response_data, status_code)
        response_data, status_code = query_function(connection, cursor, *args, **kwargs)"""
        
        return jsonify(response_data), status_code
        
    except Error as e:
        # print(f"Erro no Template Query: {e}")
        return jsonify({'success': False, 'message': error_message}), 500
        
    finally:
        if connection and connection.is_connected():
            # A checagem de cursor.close() deve ser feita se o cursor foi criado
            try:
                cursor.close()
            except:
                pass
            connection.close()
