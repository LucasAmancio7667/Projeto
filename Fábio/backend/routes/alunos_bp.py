from flask import Blueprint, jsonify, request
from mysql.connector import Error
# IMPORTAÇÃO ALTERADA: Importa os templates methods
from db_utils import execute_db_query, execute_db_transaction
from factories import get_user_factory

alunos_bp = Blueprint('alunos_bp', __name__)

def _get_alunos_logic(connection, cursor, page, limit, search, offset):
    # ATUALIZAÇÃO: Adicionar LEFT JOIN para a tabela status_alunos
    count_query = "SELECT COUNT(*) as count FROM alunos"
    query = """
    SELECT a.id, a.turma, a.nome, a.email, a.telefone, a.data_nascimento, a.rg, a.cpf, a.endereco, a.escolaridade, a.escola, a.responsavel,
    sm.status_matricula 
    FROM alunos a
    LEFT JOIN status_alunos sm ON a.id = sm.id
    """
    
    where_clause = ""
    params = []

    if search:
        where_clause = " WHERE nome LIKE %s OR email LIKE %s OR cpf LIKE %s OR rg LIKE %s OR telefone LIKE %s"
        like_term = f"%{search}%"
        params = [like_term, like_term, like_term, like_term, like_term]

    count_query += where_clause
    query += where_clause
    
    cursor.execute(count_query, params)
    total_alunos = cursor.fetchone()['count']

    query += " ORDER BY nome LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cursor.execute(query, tuple(params))

    alunos = cursor.fetchall()
    for aluno in alunos:
        if aluno.get('data_nascimento'):
            aluno['data_nascimento'] = aluno['data_nascimento'].strftime('%Y-%m-%d')
            
    return {
        'total': total_alunos,
        'alunos': alunos
    }, 200
    
@alunos_bp.route('/alunos')
def get_alunos():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search', "", type=str)
    offset = (page - 1) * limit

    # CHAMA O TEMPLATE METHOD DE LEITURA
    return execute_db_query(_get_alunos_logic, page=page, limit=limit, search=search, offset=offset, error_message='Erro ao buscar alunos')


def _get_aluno_by_id_logic(connection, cursor, aluno_id):
    query = "SELECT id, turma, nome, email, telefone, data_nascimento, rg, cpf, endereco, escolaridade, escola, responsavel FROM alunos WHERE id = %s"
    cursor.execute(query, (aluno_id,))
    aluno = cursor.fetchone()
    
    if aluno:
        if aluno.get('data_nascimento'):
            aluno['data_nascimento'] = aluno['data_nascimento'].strftime('%Y-%m-%d')
        return aluno, 200
    else:
        return {'message': 'Aluno não encontrado!'}, 404
    
@alunos_bp.route('/alunos/<int:aluno_id>', methods=['GET'])
def get_aluno_by_id(aluno_id):
    # CHAMA O TEMPLATE METHOD DE LEITURA
    return execute_db_query(_get_aluno_by_id_logic, aluno_id=aluno_id, error_message='Erro ao buscar aluno por ID')


def _add_aluno_logic(connection, cursor, aluno_data):
    if not aluno_data or not aluno_data.get('nome') or not aluno_data.get('turma'):
        raise ValueError('Nome e Turma são obrigatórios')

    # 1. Inserir na tabela 'alunos'
    query_alunos = """
    INSERT INTO alunos (turma, nome, email, telefone, data_nascimento, rg, cpf, endereco, escolaridade, escola, responsavel)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values_alunos = (
        aluno_data.get('turma'), aluno_data.get('nome'), aluno_data.get('email'),
        aluno_data.get('telefone'), aluno_data.get('data_nascimento'),
        aluno_data.get('rg'), aluno_data.get('cpf'), aluno_data.get('endereco'),
        aluno_data.get('escolaridade'), aluno_data.get('escola'),
        aluno_data.get('responsavel')
    )
    cursor.execute(query_alunos, values_alunos)
    aluno_id = cursor.lastrowid

    # 2. Usar a fábrica para criar o objeto do usuário
    student_factory = get_user_factory("student")
    aluno_data['aluno_id'] = aluno_id # Adiciona o ID para a fábrica usar
    # O generate_username dentro do create_user fará um SELECT na conexão atual
    user_to_create = student_factory.create_user(aluno_data, connection) 

    # 3. Inserir o usuário criado pela fábrica
    query_users = """
    INSERT INTO users (username, password_hash, full_name, role, student_id)
    VALUES (%s, %s, %s, %s, %s)
    """
    values_users = (
        user_to_create['username'], user_to_create['password_hash'],
        user_to_create['full_name'], user_to_create['role'],
        user_to_create['student_id']
    )
    cursor.execute(query_users, values_users)

    # 4. Inserir em status_alunos
    query_status = "INSERT INTO status_alunos (id, faltas, situacao) VALUES (%s, %s, %s)"
    cursor.execute(query_status, (aluno_id, 0, 'Ativo'))
    
    # 5. Inserir em atividades_alunos
    query_atividades = "INSERT INTO atividades_alunos (id) VALUES (%s)"
    cursor.execute(query_atividades, (aluno_id,))
    
    return {
        'success': True,
        'message': 'Aluno e credenciais de login adicionados com sucesso!',
        'generated_username': user_to_create['username'],
        'generated_password': user_to_create['generated_password'] 
    }, 201, None # Retorna os dados, status e nenhuma info extra de erro

@alunos_bp.route('/alunos/add', methods=['POST'])
def add_aluno():
    aluno_data = request.get_json()
    # CHAMA O TEMPLATE METHOD DE ESCRITA
    return execute_db_transaction(_add_aluno_logic, aluno_data=aluno_data, rollback_message='Erro interno do servidor')


def _delete_aluno_logic(connection, cursor, aluno_id):
    # A FOREIGN KEY com ON DELETE CASCADE na tabela 'alunos' é quem vai limpar 'users', 'status_alunos', etc.
    query = "DELETE FROM alunos WHERE id = %s"
    cursor.execute(query, (aluno_id,))
    
    if cursor.rowcount > 0:
        return {'success': True, 'message': 'Aluno e dados relacionados excluídos com sucesso!'}, 200, None
    else:
        return {'success': False, 'message': 'Aluno não encontrado ou já excluído.'}, 404, None
    
@alunos_bp.route('/alunos/delete/<int:aluno_id>', methods=['DELETE'])
def delete_aluno(aluno_id):
    # CHAMA O TEMPLATE METHOD DE ESCRITA
    return execute_db_transaction(_delete_aluno_logic, aluno_id=aluno_id, rollback_message='Erro interno do servidor')


def _edit_aluno_logic(connection, cursor, aluno_id, aluno_data):
    if not aluno_data or not aluno_id:
        raise ValueError('ID do aluno e dados de edição são obrigatórios')
        
    set_clauses_alunos = []
    values_alunos = []
    
    updatable_fields_alunos = [
        'turma', 'nome', 'email', 'telefone', 'data_nascimento',
        'rg', 'cpf', 'endereco', 'escolaridade', 'escola', 'responsavel'
    ]

    for field in updatable_fields_alunos:
        if field in aluno_data:
            set_clauses_alunos.append(f"{field} = %s")
            values_alunos.append(aluno_data[field])

    if set_clauses_alunos:
        query_alunos = f"UPDATE alunos SET {', '.join(set_clauses_alunos)} WHERE id = %s"
        values_alunos.append(aluno_id)
        cursor.execute(query_alunos, tuple(values_alunos))

    if 'status_matricula' in aluno_data:
        update_status_query = """
            INSERT INTO status_alunos (id, status_matricula) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE status_matricula = VALUES(status_matricula)
        """
        cursor.execute(update_status_query, (aluno_id, aluno_data['status_matricula']))

    if 'nome' in aluno_data:
        update_user_name_query = "UPDATE users SET full_name = %s WHERE student_id = %s"
        cursor.execute(update_user_name_query, (aluno_data['nome'], aluno_id))
    
    # Verifica se o aluno existe
    cursor.execute("SELECT id FROM alunos WHERE id = %s", (aluno_id,))
    if cursor.fetchone():
        return {'success': True, 'message': 'Aluno atualizado com sucesso!'}, 200, None
    else:
        return {'success': False, 'message': 'Aluno não encontrado para atualização.'}, 404, None

@alunos_bp.route('/alunos/edit/<int:aluno_id>', methods=['PUT'])
def edit_aluno(aluno_id):
    aluno_data = request.get_json()
    # CHAMA O TEMPLATE METHOD DE ESCRITA
    return execute_db_transaction(_edit_aluno_logic, aluno_id=aluno_id, aluno_data=aluno_data, rollback_message='Erro interno do servidor')