from flask import Blueprint, jsonify, request
from mysql.connector import Error
from db_utils import create_db_connection
from factories import get_user_factory

alunos_bp = Blueprint('alunos_bp', __name__)

@alunos_bp.route('/alunos')
def get_alunos():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search', "", type=str)
    offset = (page - 1) * limit

    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    alunos = []
    total_alunos = 0
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
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
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar alunos: {e}")
        finally:
            if connection.is_connected():
                connection.close()
            
    return jsonify({
        'total': total_alunos,
        'alunos': alunos
    })

@alunos_bp.route('/alunos/<int:aluno_id>', methods=['GET'])

def get_aluno_by_id(aluno_id):
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    aluno = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, turma, nome, email, telefone, data_nascimento, rg, cpf, endereco, escolaridade, escola, responsavel FROM alunos WHERE id = %s"
            cursor.execute(query, (aluno_id,))
            aluno = cursor.fetchone()
            cursor.close()
            if aluno:
                if aluno.get('data_nascimento'):
                    aluno['data_nascimento'] = aluno['data_nascimento'].strftime('%Y-%m-%d')
                return jsonify(aluno), 200
            else:
                return jsonify({'message': 'Aluno não encontrado!'}), 404
        except Error as e:
            print(f"Erro ao buscar aluno por ID: {e}")
            return jsonify({'message': 'Erro interno do servidor'}), 500
        finally:
            if connection.is_connected():
                connection.close()
    return jsonify({'message': 'Erro de conexão com o banco de dados'}), 500

@alunos_bp.route('/alunos/add', methods=['POST'])
def add_aluno():

    aluno_data = request.get_json()

    if not aluno_data or not aluno_data.get('nome') or not aluno_data.get('turma'):
        return jsonify({'success': False, 'message': 'Nome e Turma são obrigatórios'}), 400

    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()

            # 1. Inserir na tabela 'alunos' (isso continua igual)
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

            # --- AQUI A MÁGICA DA FÁBRICA ACONTECE ---
            # 2. Usar a fábrica para criar o objeto do usuário
            student_factory = get_user_factory("student")
            aluno_data['aluno_id'] = aluno_id # Adiciona o ID para a fábrica usar
            user_to_create = student_factory.create_user(aluno_data, connection)
            # -------------------------------------------

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

            # O resto da lógica (inserir em status_alunos, atividades_alunos) continua igual
            query_status = "INSERT INTO status_alunos (id, faltas, situacao) VALUES (%s, %s, %s)"
            cursor.execute(query_status, (aluno_id, 0, 'Ativo'))
            
            # ... (código para inserir em atividades_alunos) ...

            connection.commit()
            cursor.close()

            return jsonify({
                'success': True,
                'message': 'Aluno e credenciais de login adicionados com sucesso!',
                'generated_username': user_to_create['username'],
                'generated_password': user_to_create['generated_password'] 
            }), 201

        except Error as e:
            connection.rollback()
            if e.errno == 1062:
                return jsonify({'success': False, 'message': f'Erro: Um registro com dados duplicados já existe. Detalhes: {e.msg}'}), 409
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
        finally:
            if connection and connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500


@alunos_bp.route('/alunos/delete/<int:aluno_id>', methods=['DELETE'])
def delete_aluno(aluno_id):
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
            query = "DELETE FROM alunos WHERE id = %s"
            cursor.execute(query, (aluno_id,))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Aluno e dados relacionados excluídos com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Aluno não encontrado ou já excluído.'}), 404
        except Error as e:
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
        finally:
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@alunos_bp.route('/alunos/edit/<int:aluno_id>', methods=['PUT'])
def edit_aluno(aluno_id):
    aluno_data = request.get_json()

    if not aluno_data or not aluno_data.get('nome') or not aluno_id:
        return jsonify({'success': False, 'message': 'ID do aluno e Nome são obrigatórios'}), 400

    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
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
            
            connection.commit()
            
            cursor.execute("SELECT id FROM alunos WHERE id = %s", (aluno_id,))
            if cursor.fetchone():
                cursor.close()
                return jsonify({'success': True, 'message': 'Aluno atualizado com sucesso!'}), 200
            else:
                cursor.close()
                return jsonify({'success': False, 'message': 'Aluno não encontrado para atualização.'}), 404

        except Error as e:
            connection.rollback()
            if e.errno == 1062:
                return jsonify({'success': False, 'message': f'Erro: Dados duplicados. Detalhes: {e.msg}'}), 409
            return jsonify({'success': False, 'message': f'Erro interno do servidor: {e}'}), 500
        finally:
            if connection and connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500