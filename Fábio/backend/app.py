from flask import Flask, jsonify, send_from_directory, request
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random 
import string 
import click
from manage_db import setup_database

# CORREÇÃO AQUI: static_folder deve apontar para o nome real da sua pasta de frontend
app = Flask(__name__, static_folder='../PROJETO_FINAL', static_url_path='/')

# Configurações do Banco de Dados MySQL
db_config = {
    'host': 'localhost',
    'database': 'Scratch',
    'user': 'root',
    'password': 'root' # SUA SENHA AQUI
}

# ADIÇÃO: Configuração para uploads de materiais
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def create_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Conexão com o banco de dados MySQL bem-sucedida!")
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
    return connection

# ADIÇÃO: Função para gerar nome de usuário baseado nas iniciais do nome
def generate_username(full_name, connection):
    if not full_name:
        return None

    # Pega as iniciais de cada palavra no nome completo
    parts = full_name.split()
    initials = "".join([part[0].lower() for part in parts if part])

    base_username = initials
    username = base_username
    counter = 1
    
    # Verifica se o username já existe no banco de dados
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

# ADIÇÃO: Função para gerar senha aleatória
def generate_random_password(length=7):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password

# Rota para servir a página HTML principal (index.html)
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

# Rota para servir todas as outras páginas HTML na pasta frontend
@app.route('/<path:filename>')
def serve_static_files(filename):
    return send_from_directory(app.static_folder, filename)

# ====================================================================================================
# NOVA ROTA PARA ESTATÍSTICAS DO DASHBOARD
# ====================================================================================================
@app.route('/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Contar alunos
            cursor.execute("SELECT COUNT(*) as total_alunos FROM alunos")
            total_alunos = cursor.fetchone()['total_alunos']
            
            # Contar aulas ministradas (status 'completed')
            cursor.execute("SELECT COUNT(*) as aulas_ministradas FROM classes WHERE status = 'completed'")
            aulas_ministradas = cursor.fetchone()['aulas_ministradas']
            
            # Calcular frequência média
            cursor.execute("SELECT COUNT(*) as total_presentes FROM attendance_records WHERE attendance_status = 'P'")
            total_presentes = cursor.fetchone()['total_presentes']
            
            cursor.execute("SELECT COUNT(*) as total_registros FROM attendance_records")
            total_registros = cursor.fetchone()['total_registros']
            
            frequencia_media = (total_presentes / total_registros * 100) if total_registros > 0 else 0
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'total_alunos': total_alunos,
                'aulas_ministradas': aulas_ministradas,
                'frequencia_media': round(frequencia_media)
            }), 200

        except Error as e:
            print(f"Erro ao buscar estatísticas: {e}")
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500

# ====================================================================================================
# ROTAS PARA ALUNOS (info_alunos)
# ====================================================================================================
@app.route('/alunos')
def get_alunos():
    connection = create_db_connection()
    alunos = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, turma, nome, email, telefone, data_nascimento, rg, cpf, endereco, escolaridade, escola, responsavel FROM alunos")
            alunos = cursor.fetchall()
            for aluno in alunos:
                if aluno.get('data_nascimento'):
                    aluno['data_nascimento'] = aluno['data_nascimento'].strftime('%Y-%m-%d')
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar alunos: {e}")
        finally:
            connection.close()
    return jsonify(alunos)

@app.route('/alunos/<int:aluno_id>', methods=['GET'])
def get_aluno_by_id(aluno_id):
    connection = create_db_connection()
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
            connection.close()
    return jsonify({'message': 'Erro de conexão com o banco de dados'}), 500

# MODIFICAÇÃO: Rota para adicionar um novo aluno (agora com inserções em outras tabelas)
@app.route('/alunos/add', methods=['POST'])
def add_aluno():
    if request.method == 'POST':
        aluno_data = request.get_json()

        # ADIÇÃO DE LOG: Imprime os dados recebidos para adicionar aluno
        print(f"Dados recebidos para adicionar aluno: {aluno_data}")

        if not aluno_data or not aluno_data.get('nome') or not aluno_data.get('turma'):
            print("Erro: Nome e Turma são obrigatórios.") # LOG
            return jsonify({'success': False, 'message': 'Nome e Turma são obrigatórios'}), 400

        # ADIÇÃO: Validação para a coluna 'turma'
        allowed_turmas = ['25.1 - T1', '25.1 - T2', '25.2 - T1']
        if aluno_data.get('turma') not in allowed_turmas:
            print(f"Erro: Turma inválida - {aluno_data.get('turma')}") # LOG
            return jsonify({'success': False, 'message': 'Turma inválida. Opções válidas: 25.1 - T1, 25.1 - T2, 25.2 - T1.'}), 400
        
        # ADIÇÃO: Validações para outros campos, conforme condições
        if not aluno_data.get('cpf'):
            print("Erro: CPF é obrigatório.") # LOG
            return jsonify({'success': False, 'message': 'CPF é obrigatório.'}), 400
        if not aluno_data.get('responsavel'):
            print("Erro: Responsável é obrigatório.") # LOG
            return jsonify({'success': False, 'message': 'Responsável é obrigatório.'}), 400
        # Você pode adicionar mais validações aqui para outros campos como email, telefone, rg, nome, etc.

        connection = create_db_connection()
        if connection:
            try:
                cursor = connection.cursor()

                # 1. Inserir na tabela 'alunos'
                query_alunos = """
                INSERT INTO alunos (turma, nome, email, telefone, data_nascimento, rg, cpf, endereco, escolaridade, escola, responsavel)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values_alunos = (
                    aluno_data.get('turma'),
                    aluno_data.get('nome'),
                    aluno_data.get('email'),
                    aluno_data.get('telefone'),
                    aluno_data.get('data_nascimento'),
                    aluno_data.get('rg'),
                    aluno_data.get('cpf'),
                    aluno_data.get('endereco'),
                    aluno_data.get('escolaridade'),
                    aluno_data.get('escola'),
                    aluno_data.get('responsavel')
                )
                print(f"Executando query_alunos: {query_alunos} com valores: {values_alunos}") # LOG
                cursor.execute(query_alunos, values_alunos)
                aluno_id = cursor.lastrowid # Pega o ID gerado para o novo aluno
                print(f"Aluno inserido com ID: {aluno_id}") # LOG

                # 2. Inserir na tabela 'users' (para login_alunos)
                aluno_full_name = aluno_data.get('nome')
                generated_username = generate_username(aluno_full_name, connection)
                generated_password = generate_random_password()
                hashed_password = generate_password_hash(generated_password)

                query_users = """
                INSERT INTO users (username, password_hash, full_name, role, student_id)
                VALUES (%s, %s, %s, %s, %s)
                """
                values_users = (generated_username, hashed_password, aluno_full_name, 'student', aluno_id)
                print(f"Executando query_users: {query_users} com valores: {values_users}") # LOG
                cursor.execute(query_users, values_users)
                print(f"Usuário de login inserido: {generated_username}") # LOG

                # 3. Inserir na tabela 'status_alunos'
                query_status = """
                INSERT INTO status_alunos (id, faltas, situacao)
                VALUES (%s, %s, %s)
                """
                values_status = (aluno_id, 0, 'Ativo')
                print(f"Executando query_status: {query_status} com valores: {values_status}") # LOG
                cursor.execute(query_status, values_status)
                print("Status do aluno inserido.") # LOG

                # 4. Inserir na tabela 'atividades_alunos'
                query_atividades = """
                INSERT INTO atividades_alunos (id, aula_1, aula_2, aula_3, aula_4, aula_5, aula_6, aula_7, aula_8, aula_9, aula_10, total_enviadas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values_atividades = (aluno_id, 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 0)
                print(f"Executando query_atividades: {query_atividades} com valores: {values_atividades}") # LOG
                cursor.execute(query_atividades, values_atividades)
                print("Atividades do aluno inseridas.") # LOG

                connection.commit()
                cursor.close()

                # Retorna o nome de usuário e senha gerados para que o frontend possa exibir
                return jsonify({
                    'success': True,
                    'message': 'Aluno e credenciais de login adicionados com sucesso!',
                    'generated_username': generated_username,
                    'generated_password': generated_password
                }), 201

            except Error as e:
                print(f"Erro MySQL ao adicionar aluno e dados relacionados: {e}") # LOG DETALHADO DO ERRO
                connection.rollback()
                # Verificar se o erro é de chave duplicada (por exemplo, email, CPF, RG, telefone)
                if e.errno == 1062: # MySQL error code for Duplicate entry
                    # ADIÇÃO DE LOG: Qual campo pode estar duplicado
                    print(f"Erro de duplicidade detectado: {e.msg}")
                    return jsonify({'success': False, 'message': f'Erro: Um registro com dados duplicados (email, CPF, RG ou telefone) já existe. Detalhes: {e.msg}'}), 409
                return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
            finally:
                if connection and connection.is_connected():
                    connection.close()
                    print("Conexão com o banco de dados fechada.") # LOG
        print("Erro: Conexão com o banco de dados não estabelecida.") # LOG
        return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500

@app.route('/alunos/delete/<int:aluno_id>', methods=['DELETE'])
def delete_aluno(aluno_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # Devido ao ON DELETE CASCADE nas chaves estrangeiras, a exclusão em 'alunos'
            # automaticamente excluirá registros em 'users', 'status_alunos' e 'atividades_alunos'.
            query = "DELETE FROM alunos WHERE id = %s"
            cursor.execute(query, (aluno_id,))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Aluno e dados relacionados excluídos com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Aluno não encontrado ou já excluído.'}), 404
        except Error as e:
            print(f"Erro ao deletar aluno: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500

@app.route('/alunos/edit/<int:aluno_id>', methods=['PUT'])
def edit_aluno(aluno_id):
    if request.method == 'PUT':
        aluno_data = request.get_json()

        if not aluno_data or not aluno_data.get('nome') or not aluno_id:
            return jsonify({'success': False, 'message': 'ID do aluno e Nome são obrigatórios'}), 400

        # ADIÇÃO: Validação para a coluna 'turma' se estiver sendo atualizada
        if 'turma' in aluno_data:
            allowed_turmas = ['25.1 - T1', '25.1 - T2', '25.2 - T1']
            if aluno_data['turma'] not in allowed_turmas:
                return jsonify({'success': False, 'message': 'Turma inválida. Opções válidas: 25.1 - T1, 25.1 - T2, 25.2 - T1.'}), 400
        # ADIÇÃO: Adicione validações para outros campos que podem ser únicos ou ter regras de formato

        connection = create_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                set_clauses = []
                values = []
                
                # Campos da tabela 'alunos' que podem ser atualizados
                updatable_fields = [
                    'turma', 'nome', 'email', 'telefone', 'data_nascimento',
                    'rg', 'cpf', 'endereco', 'escolaridade', 'escola', 'responsavel'
                ]

                for field in updatable_fields:
                    if field in aluno_data:
                        set_clauses.append(f"{field} = %s")
                        values.append(aluno_data[field])

                if not set_clauses:
                    return jsonify({'success': False, 'message': 'Nenhum dado para atualizar para o aluno.'}), 400

                query = f"UPDATE alunos SET {', '.join(set_clauses)} WHERE id = %s"
                values.append(aluno_id)
                
                cursor.execute(query, tuple(values))
                connection.commit()
                cursor.close()

                if cursor.rowcount > 0:
                    # Se o nome do aluno foi atualizado, também atualizar em 'users'
                    if 'nome' in aluno_data:
                        # Recuperar o username do aluno para atualizar o full_name em users
                        cursor_users_update = connection.cursor()
                        update_user_name_query = "UPDATE users SET full_name = %s WHERE student_id = %s"
                        cursor_users_update.execute(update_user_name_query, (aluno_data['nome'], aluno_id))
                        connection.commit() # Commit para a atualização do user
                        cursor_users_update.close()

                    return jsonify({'success': True, 'message': 'Aluno atualizado com sucesso!'}), 200
                else:
                    return jsonify({'success': False, 'message': 'Aluno não encontrado para atualização.'}), 404
            except Error as e:
                print(f"Erro ao atualizar aluno: {e}")
                connection.rollback()
                if e.errno == 1062: # MySQL error code for Duplicate entry
                    return jsonify({'success': False, 'message': f'Erro: Um registro com dados duplicados (email, CPF, RG ou telefone) já existe. Detalhes: {e.msg}'}), 409
                return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
            finally:
                connection.close()
        return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500

# ====================================================================================================
# ROTAS PARA USERS (LOGIN E ADMINISTRAÇÃO DE USUÁRIOS GERAIS)
# ====================================================================================================
@app.route('/users', methods=['GET'])
def get_users():
    connection = create_db_connection()
    users = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, username, full_name, role, student_id, last_login, total_logins, online_status FROM users")
            users = cursor.fetchall()
            for user in users:
                if user.get('last_login'):
                    user['last_login'] = user['last_login'].isoformat() # Formatar data para JSON
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar usuários: {e}")
        finally:
            connection.close()
    return jsonify(users)

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    connection = create_db_connection()
    user = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, username, full_name, role, student_id, last_login, total_logins, online_status FROM users WHERE id = %s"
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            cursor.close()
            if user:
                if user.get('last_login'):
                    user['last_login'] = user['last_login'].isoformat()
                return jsonify(user), 200
            else:
                return jsonify({'message': 'Usuário não encontrado!'}), 404
        except Error as e:
            print(f"Erro ao buscar usuário por ID: {e}")
            return jsonify({'message': 'Erro interno do servidor'}), 500
        finally:
            connection.close()
    return jsonify({'message': 'Erro de conexão com o banco de dados'}), 500

@app.route('/users/add', methods=['POST'])
def add_user():
    user_data = request.get_json()
    username = user_data.get('username')
    password = user_data.get('password')
    full_name = user_data.get('full_name')
    role = user_data.get('role')
    student_id_raw = user_data.get('student_id') # Pega o valor bruto do frontend

    # ADIÇÃO DE LOG: Imprime os dados recebidos para adicionar usuário
    print(f"Dados recebidos para adicionar usuário: {user_data}")

    if not username or not password or not role:
        print("Erro: Username, Password e Role são obrigatórios.") # LOG
        return jsonify({'success': False, 'message': 'Username, Password e Role são obrigatórios!'}), 400

    # ADIÇÃO: Validação de role (apenas student ou teacher)
    allowed_roles = ['student', 'teacher']
    if role not in allowed_roles:
        print(f"Erro: Role inválida - {role}") # LOG
        return jsonify({'success': False, 'message': 'Role inválida. Opções válidas: student, teacher.'}), 400

    # CORREÇÃO: Trata student_id para garantir que seja None ou um inteiro
    student_id = None # Inicializa como None
    if role == 'student':
        if student_id_raw: # Se o valor não for vazio
            try:
                student_id = int(student_id_raw)
            except ValueError:
                print(f"Erro: student_id '{student_id_raw}' não é um número válido para o perfil de aluno.")
                return jsonify({'success': False, 'message': 'Para o perfil de Aluno, o ID de Aluno deve ser um número válido.'}), 400
        # Se student_id_raw for vazio ('' ou None), student_id permanece None, o que é correto.
    # Se o role for 'teacher', student_id permanece None, o que também é correto.

    hashed_password = generate_password_hash(password)

    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = """
            INSERT INTO users (username, password_hash, full_name, role, student_id)
            VALUES (%s, %s, %s, %s, %s)
            """
            values = (username, hashed_password, full_name, role, student_id)
            print(f"Executando query_users: {query} com valores: {values}") # LOG
            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            print("Usuário adicionado com sucesso.") # LOG
            return jsonify({'success': True, 'message': 'Usuário adicionado com sucesso!'}), 201
        except Error as e:
            print(f"Erro MySQL ao adicionar usuário: {e}") # LOG DETALHADO DO ERRO
            connection.rollback()
            if e.errno == 1062: # MySQL error code for Duplicate entry
                # ADIÇÃO DE LOG: Qual campo pode estar duplicado
                print(f"Erro de duplicidade detectado: {e.msg}")
                return jsonify({'success': False, 'message': f'Erro: Nome de usuário "{username}" já existe.'}), 409
            return jsonify({'success': False, 'message': 'Erro interno do servidor ou usuário já existe.'}), 500
        finally:
            if connection and connection.is_connected():
                connection.close()
                print("Conexão com o banco de dados fechada.") # LOG
        print("Erro: Conexão com o banco de dados não estabelecida.") # LOG
        return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500

@app.route('/users/edit/<int:user_id>', methods=['PUT'])
def edit_user(user_id):
    user_data = request.get_json()
    
    # CORREÇÃO: Inicializa username aqui para garantir que esteja sempre definido
    username = user_data.get('username')
    
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            set_clauses = []
            values = []
            
            if 'username' in user_data:
                set_clauses.append("username = %s")
                values.append(user_data['username'])
            if 'full_name' in user_data:
                set_clauses.append("full_name = %s")
                values.append(user_data['full_name'])
            if 'role' in user_data:
                # ADIÇÃO: Validação de role ao editar
                allowed_roles = ['student', 'teacher']
                if user_data.get('role') not in allowed_roles:
                    return jsonify({'success': False, 'message': 'Role inválida. Opções válidas: student, teacher.'}), 400
                set_clauses.append("role = %s")
                values.append(user_data['role'])
            if 'student_id' in user_data:
                # CORREÇÃO: Trata student_id para garantir que seja None ou um inteiro na edição
                edit_student_id_raw = user_data.get('student_id')
                edit_student_id = None
                if user_data.get('role') == 'student': # Apenas tenta converter se o perfil for aluno
                    if edit_student_id_raw:
                        try:
                            edit_student_id = int(edit_student_id_raw)
                        except ValueError:
                            print(f"Erro: student_id '{edit_student_id_raw}' não é um número válido na edição.")
                            return jsonify({'success': False, 'message': 'Para o perfil de Aluno, o ID de Aluno deve ser um número válido.'}), 400
                set_clauses.append("student_id = %s")
                values.append(edit_student_id) # Usa o valor tratado
            if 'last_login' in user_data:
                set_clauses.append("last_login = %s")
                values.append(user_data['last_login'])
            if 'total_logins' in user_data:
                set_clauses.append("total_logins = %s")
                values.append(user_data['total_logins'])
            if 'online_status' in user_data:
                set_clauses.append("online_status = %s")
                values.append(user_data['online_status'])
            # Se a senha for alterada, hash novamente
            if 'password' in user_data and user_data['password']:
                set_clauses.append("password_hash = %s")
                values.append(generate_password_hash(user_data['password']))

            if not set_clauses:
                return jsonify({'success': False, 'message': 'Nenhum dado para atualizar.'}), 400

            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s"
            values.append(user_id)
            
            cursor.execute(query, tuple(values))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Usuário atualizado com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Usuário não encontrado para atualização.'}), 404
        except Error as e:
            print(f"Erro ao atualizar usuário: {e}")
            connection.rollback()
            if e.errno == 1062: # MySQL error code for Duplicate entry
                # CORREÇÃO: Verifica se username está definido antes de usá-lo na mensagem
                msg = f'Erro: Nome de usuário "{username}" já existe.' if username else 'Erro: Um registro com dados duplicados já existe.'
                return jsonify({'success': False, 'message': msg}), 409
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500


@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "DELETE FROM users WHERE id = %s"
            cursor.execute(query, (user_id,))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Usuário excluído com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 404
        except Error as e:
            print(f"Erro ao deletar usuário: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500

# ADIÇÃO: Rota para login de usuário
@app.route('/login', methods=['POST'])
def login():
    credentials = request.get_json()
    username = credentials.get('username')
    password = credentials.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Nome de usuário e senha são obrigatórios.'}), 400

    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, username, password_hash, full_name, role, student_id FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            cursor.close()

            if user and check_password_hash(user['password_hash'], password):
                # Atualiza last_login e total_logins
                cursor_update = connection.cursor()
                update_query = "UPDATE users SET last_login = NOW(), total_logins = total_logins + 1, online_status = 'Online' WHERE id = %s"
                cursor_update.execute(update_query, (user['id'],))
                connection.commit()
                cursor_update.close()

                # Retorna dados do usuário (exceto a senha hasheada)
                return jsonify({
                    'success': True,
                    'message': 'Login bem-sucedido!',
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'full_name': user['full_name'],
                        'role': user['role'],
                        'student_id': user['student_id']
                    }
                }), 200
            else:
                return jsonify({'success': False, 'message': 'Nome de usuário ou senha incorretos.'}), 401
        except Error as e:
            print(f"Erro no login: {e}")
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

# ADIÇÃO: Rota para logout de usuário (opcional, para atualizar status online)
@app.route('/logout/<int:user_id>', methods=['POST'])
def logout(user_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "UPDATE users SET online_status = 'Offline' WHERE id = %s"
            cursor.execute(query, (user_id,))
            connection.commit()
            cursor.close()
            return jsonify({'success': True, 'message': 'Logout bem-sucedido!'}), 200
        except Error as e:
            print(f"Erro no logout: {e}")
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500


# ====================================================================================================
# ROTAS PARA CLASSES
# ====================================================================================================
@app.route('/classes', methods=['GET'])
def get_classes():
    connection = create_db_connection()
    classes = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, title, date, status, description FROM classes ORDER BY date ASC")
            classes = cursor.fetchall()
            for cls in classes:
                if cls.get('date'):
                    cls['date'] = cls['date'].isoformat()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar classes: {e}")
        finally:
            connection.close()
    return jsonify(classes)

# ADIÇÃO: Rota para buscar uma única aula por ID
@app.route('/classes/<int:class_id>', methods=['GET'])
def get_class_by_id(class_id):
    connection = create_db_connection()
    class_item = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, title, date, status, description FROM classes WHERE id = %s"
            cursor.execute(query, (class_id,))
            class_item = cursor.fetchone()
            cursor.close()
            if class_item:
                if class_item.get('date'):
                    class_item['date'] = class_item['date'].isoformat()
                return jsonify(class_item), 200
            else:
                return jsonify({'message': 'Aula não encontrada!'}), 404
        except Error as e:
            print(f"Erro ao buscar aula por ID: {e}")
            return jsonify({'message': 'Erro interno do servidor'}), 500
        finally:
            connection.close()
    return jsonify({'message': 'Erro de conexão com o banco de dados'}), 500


@app.route('/classes/add', methods=['POST'])
def add_class():
    class_data = request.get_json()
    title = class_data.get('title')
    date = class_data.get('date')
    status = class_data.get('status', 'future')
    description = class_data.get('description')

    if not title or not date:
        return jsonify({'success': False, 'message': 'Título e Data são obrigatórios.'}), 400

    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "INSERT INTO classes (title, date, status, description) VALUES (%s, %s, %s, %s)"
            values = (title, date, status, description)
            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            return jsonify({'success': True, 'message': 'Aula adicionada com sucesso!'}), 201
        except Error as e:
            print(f"Erro ao adicionar aula: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/classes/edit/<int:class_id>', methods=['PUT'])
def edit_class(class_id):
    class_data = request.get_json()
    
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            set_clauses = []
            values = []

            if 'title' in class_data:
                set_clauses.append("title = %s")
                values.append(class_data['title'])
            if 'date' in class_data:
                set_clauses.append("date = %s")
                values.append(class_data['date'])
            if 'status' in class_data:
                set_clauses.append("status = %s")
                values.append(class_data['status'])
            if 'description' in class_data:
                set_clauses.append("description = %s")
                values.append(class_data['description'])
            
            if not set_clauses:
                return jsonify({'success': False, 'message': 'Nenhum dado para atualizar.'}), 400

            query = f"UPDATE classes SET {', '.join(set_clauses)} WHERE id = %s"
            values.append(class_id)
            
            cursor.execute(query, tuple(values))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Aula atualizada com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Aula não encontrada.'}), 404
        except Error as e:
            print(f"Erro ao atualizar aula: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/classes/delete/<int:class_id>', methods=['DELETE'])
def delete_class(class_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "DELETE FROM classes WHERE id = %s"
            cursor.execute(query, (class_id,))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Aula excluída com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Aula não encontrada.'}), 404
        except Error as e:
            print(f"Erro ao deletar aula: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

# ====================================================================================================
# ROTAS PARA REGISTROS DE FREQUÊNCIA (attendance_records)
# ====================================================================================================
@app.route('/attendance', methods=['GET'])
def get_attendance_records():
    connection = create_db_connection()
    records = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
            SELECT ar.id, ar.student_id, a.nome as student_name, ar.class_id, c.title as class_title, ar.attendance_status, ar.recorded_at
            FROM attendance_records ar
            JOIN alunos a ON ar.student_id = a.id
            JOIN classes c ON ar.class_id = c.id
            ORDER BY ar.recorded_at DESC
            """
            cursor.execute(query)
            records = cursor.fetchall()
            for rec in records:
                if rec.get('recorded_at'):
                    rec['recorded_at'] = rec['recorded_at'].isoformat()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar registros de frequência: {e}")
        finally:
            connection.close()
    return jsonify(records)

@app.route('/attendance/student/<int:student_id>', methods=['GET'])
def get_attendance_by_student(student_id):
    connection = create_db_connection()
    records = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
            SELECT ar.id, ar.student_id, ar.class_id, c.title as class_title, c.date as class_date, ar.attendance_status, ar.recorded_at
            FROM attendance_records ar
            JOIN classes c ON ar.class_id = c.id
            WHERE ar.student_id = %s
            ORDER BY c.date ASC
            """
            cursor.execute(query, (student_id,))
            records = cursor.fetchall()
            for rec in records:
                if rec.get('recorded_at'):
                    rec['recorded_at'] = rec['recorded_at'].isoformat()
                if rec.get('class_date'):
                    rec['class_date'] = rec['class_date'].isoformat()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar frequência do aluno: {e}")
        finally:
            connection.close()
    return jsonify(records)


@app.route('/attendance/add', methods=['POST'])
def add_attendance_record():
    record_data = request.get_json()
    student_id = record_data.get('student_id')
    class_id = record_data.get('class_id')
    attendance_status = record_data.get('attendance_status')

    if not student_id or not class_id or not attendance_status:
        return jsonify({'success': False, 'message': 'Student ID, Class ID e Status de Frequência são obrigatórios.'}), 400

    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Tenta encontrar um registro existente para este student_id e class_id
            check_query = "SELECT id FROM attendance_records WHERE student_id = %s AND class_id = %s"
            cursor.execute(check_query, (student_id, class_id))
            existing_record = cursor.fetchone()

            if existing_record:
                # Se o registro existe, atualiza
                record_id = existing_record[0]
                update_query = "UPDATE attendance_records SET attendance_status = %s WHERE id = %s"
                cursor.execute(update_query, (attendance_status, record_id))
                connection.commit()
                print(f"Presença do aluno {student_id} na aula {class_id} atualizada para {attendance_status}.")
            else:
                # Se o registro não existe, insere
                insert_query = "INSERT INTO attendance_records (student_id, class_id, attendance_status) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (student_id, class_id, attendance_status))
                connection.commit()
                new_record_id = cursor.lastrowid
                print(f"Nova presença adicionada para o aluno {student_id} na aula {class_id} com status {attendance_status}.")
                record_id = new_record_id # Usa o novo ID para o retorno

            # Após inserir ou atualizar a presença, recalcule as faltas do aluno
            # Contar todas as faltas (F e Fj) para este aluno
            count_absences_query = """
                SELECT COUNT(*) FROM attendance_records
                WHERE student_id = %s AND attendance_status IN ('F', 'Fj')
            """
            cursor.execute(count_absences_query, (student_id,))
            total_absences = cursor.fetchone()[0]

            # Atualizar a tabela status_alunos
            update_status_query = """
                INSERT INTO status_alunos (id, faltas, situacao)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE faltas = VALUES(faltas), situacao = VALUES(situacao)
            """
            # A situação pode ser 'Ativo' ou 'Desistente'. Por enquanto, vamos manter 'Ativo'
            # Você pode adicionar lógica para mudar a situação com base no número de faltas, se desejar.
            cursor.execute(update_status_query, (student_id, total_absences, 'Ativo'))
            connection.commit()
            print(f"Status do aluno {student_id} atualizado: Faltas = {total_absences}.")

            cursor.close()
            return jsonify({'success': True, 'message': 'Registro de frequência salvo com sucesso!', 'id': record_id}), 200
        except Error as e:
            print(f"Erro ao adicionar/atualizar registro de frequência e faltas: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/attendance/edit/<int:record_id>', methods=['PUT'])
def edit_attendance_record(record_id):
    record_data = request.get_json()
    attendance_status = record_data.get('attendance_status')

    if not attendance_status:
        return jsonify({'success': False, 'message': 'Status de Frequência é obrigatório.'}), 400
    
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "UPDATE attendance_records SET attendance_status = %s WHERE id = %s"
            values = (attendance_status, record_id)
            cursor.execute(query, values)
            connection.commit()
            
            # ADIÇÃO: Recalcular e atualizar faltas em status_alunos após edição
            # Primeiro, obtenha o student_id do registro de presença
            get_student_id_query = "SELECT student_id FROM attendance_records WHERE id = %s"
            cursor.execute(get_student_id_query, (record_id,))
            result = cursor.fetchone()
            
            if result:
                student_id = result[0]
                # Contar todas as faltas (F e Fj) para este aluno
                count_absences_query = """
                    SELECT COUNT(*) FROM attendance_records
                    WHERE student_id = %s AND attendance_status IN ('F', 'Fj')
                """
                cursor.execute(count_absences_query, (student_id,))
                total_absences = cursor.fetchone()[0]

                # Atualizar a tabela status_alunos (usando ON DUPLICATE KEY UPDATE para garantir que insere ou atualiza)
                update_status_query = """
                    INSERT INTO status_alunos (id, faltas, situacao)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE faltas = VALUES(faltas), situacao = VALUES(situacao)
                """
                cursor.execute(update_status_query, (student_id, total_absences, 'Ativo'))
                connection.commit()
                print(f"Status do aluno {student_id} atualizado (edição): Faltas = {total_absences}.")

            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Registro de frequência atualizado com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Registro de frequência não encontrado.'}), 404
        except Error as e:
            print(f"Erro ao atualizar registro de frequência: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/attendance/delete/<int:record_id>', methods=['DELETE'])
def delete_attendance_record(record_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # ADIÇÃO: Obter student_id antes de deletar para recalcular faltas
            get_student_id_query = "SELECT student_id FROM attendance_records WHERE id = %s"
            cursor.execute(get_student_id_query, (record_id,))
            result = cursor.fetchone()
            student_id = None
            if result:
                student_id = result[0]

            query = "DELETE FROM attendance_records WHERE id = %s"
            cursor.execute(query, (record_id,))
            connection.commit()
            
            if cursor.rowcount > 0:
                # ADIÇÃO: Recalcular e atualizar faltas em status_alunos após exclusão
                if student_id:
                    count_absences_query = """
                        SELECT COUNT(*) FROM attendance_records
                        WHERE student_id = %s AND attendance_status IN ('F', 'Fj')
                    """
                    cursor.execute(count_absences_query, (student_id,))
                    total_absences = cursor.fetchone()[0]

                    update_status_query = """
                        INSERT INTO status_alunos (id, faltas, situacao)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE faltas = VALUES(faltas), situacao = VALUES(situacao)
                    """
                    cursor.execute(update_status_query, (student_id, total_absences, 'Ativo'))
                    connection.commit()
                    print(f"Status do aluno {student_id} atualizado (exclusão): Faltas = {total_absences}.")

                cursor.close()
                return jsonify({'success': True, 'message': 'Registro de frequência excluído com sucesso!'}), 200
            else:
                cursor.close()
                return jsonify({'success': False, 'message': 'Registro de frequência não encontrado.'}), 404
        except Error as e:
            print(f"Erro ao deletar registro de frequência: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

# ====================================================================================================
# ROTAS PARA STATUS DOS ALUNOS (status_alunos - AQUI SERÁ A TABELA CONSOLIDADA)
# ====================================================================================================
@app.route('/status_alunos', methods=['GET'])
def get_status_alunos():
    connection = create_db_connection()
    statuses = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Juntar com 'alunos' para obter o nome
            query = """
            SELECT sa.id, a.nome as student_name, sa.faltas, sa.situacao
            FROM status_alunos sa
            JOIN alunos a ON sa.id = a.id
            ORDER BY a.nome ASC
            """
            cursor.execute(query)
            statuses = cursor.fetchall()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar status dos alunos: {e}")
            return jsonify({'message': 'Erro interno do servidor'}), 500
        finally:
            connection.close()
    return jsonify(statuses)

# ADIÇÃO: Rotas para Atividades dos Alunos
@app.route('/atividades_alunos', methods=['GET'])
def get_atividades_alunos():
    connection = create_db_connection()
    activities = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Juntar com 'alunos' para obter o nome
            query = """
            SELECT aa.*, a.nome as student_name
            FROM atividades_alunos aa
            JOIN alunos a ON aa.id = a.id
            ORDER BY a.nome ASC
            """
            cursor.execute(query)
            activities = cursor.fetchall()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar atividades dos alunos: {e}")
            return jsonify({'message': 'Erro interno do servidor'}), 500
        finally:
            connection.close()
    return jsonify(activities)

# ADIÇÃO: Rota para atualizar o status de uma aula individualmente
@app.route('/atividades_alunos/update_aula/<int:aluno_id>', methods=['PUT'])
def update_aula_status(aluno_id):
    update_data = request.get_json()
    aula_col = update_data.get('aula_col') # Ex: 'aula_1', 'aula_2'
    new_status = update_data.get('new_status') # Ex: 'Enviada', 'Verificada'

    if not aula_col or not new_status or not aluno_id:
        return jsonify({'success': False, 'message': 'Dados de atualização insuficientes.'}), 400
    
    # Validar que a coluna é uma das aulas válidas
    if aula_col not in [f'aula_{i}' for i in range(1, 11)]:
        return jsonify({'success': False, 'message': 'Coluna de aula inválida.'}), 400

    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # Atualiza a coluna da aula específica
            query_aula = f"UPDATE atividades_alunos SET {aula_col} = %s WHERE id = %s"
            cursor.execute(query_aula, (new_status, aluno_id))
            
            # Recalcular total_enviadas:
            # Busca todos os status de aula para o aluno e soma os que são 'Enviada' ou 'Verificada'
            sum_query_parts = [f"CASE WHEN aula_{i} IN ('Enviada', 'Verificada') THEN 1 ELSE 0 END" for i in range(1, 11)]
            sum_query = f"SELECT ({' + '.join(sum_query_parts)}) FROM atividades_alunos WHERE id = %s"
            cursor.execute(sum_query, (aluno_id,))
            calculated_total = cursor.fetchone()[0]
            
            update_total_query = "UPDATE atividades_alunos SET total_enviadas = %s WHERE id = %s"
            cursor.execute(update_total_query, (calculated_total, aluno_id))

            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': f'Status da {aula_col} e total atualizados com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Aluno ou aula não encontrada para atualização.'}), 404
        except Error as e:
            print(f"Erro ao atualizar status da aula: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

# ====================================================================================================
# ROTAS PARA MATERIAIS
# ====================================================================================================
@app.route('/materials', methods=['GET'])
def get_materials():
    connection = create_db_connection()
    materials = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name, file_type, file_size, upload_date, description, file_path FROM materials ORDER BY upload_date DESC")
            materials = cursor.fetchall()
            for mat in materials:
                if mat.get('upload_date'):
                    mat['upload_date'] = mat['upload_date'].isoformat()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar materiais: {e}")
        finally:
            connection.close()
    return jsonify(materials)

@app.route('/materials/upload', methods=['POST'])
def upload_material():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado.'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado.'}), 400
    
    name = request.form.get('name', file.filename)
    description = request.form.get('description', '')

    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        connection = create_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                query = """
                INSERT INTO materials (name, file_type, file_size, description, file_path)
                VALUES (%s, %s, %s, %s, %s)
                """
                values = (name, file.content_type, file.content_length, description, filename)
                cursor.execute(query, values)
                connection.commit()
                material_id = cursor.lastrowid
                cursor.close()
                return jsonify({'success': True, 'message': 'Material enviado e registrado com sucesso!', 'id': material_id}), 201
            except Error as e:
                print(f"Erro ao registrar material no DB: {e}")
                connection.rollback()
                return jsonify({'success': False, 'message': 'Erro interno do servidor ao registrar material.'}), 500
            finally:
                connection.close()
        return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500
    return jsonify({'success': False, 'message': 'Erro no upload do arquivo.'}), 500

@app.route('/materials/download/<path:filename>', methods=['GET'])
def download_material(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/materials/edit/<int:material_id>', methods=['PUT'])
def edit_material(material_id):
    material_data = request.get_json()
    
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            set_clauses = []
            values = []

            if 'name' in material_data:
                set_clauses.append("name = %s")
                values.append(material_data['name'])
            if 'description' in material_data:
                set_clauses.append("description = %s")
                values.append(material_data['description'])
            
            if not set_clauses:
                return jsonify({'success': False, 'message': 'Nenhum dado para atualizar.'}), 400

            query = f"UPDATE materials SET {', '.join(set_clauses)} WHERE id = %s"
            values.append(material_id)
            
            cursor.execute(query, tuple(values))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Material atualizado com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Material não encontrado.'}), 404
        except Error as e:
            print(f"Erro ao atualizar material: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/materials/delete/<int:material_id>', methods=['DELETE'])
def delete_material(material_id):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT file_path FROM materials WHERE id = %s", (material_id,))
            material = cursor.fetchone()
            
            if material and material.get('file_path'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], material['file_path'])
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"Arquivo {filepath} excluído do servidor.")
                else:
                    print(f"Arquivo {filepath} não encontrado no servidor, mas continuará a exclusão do DB.")

            query = "DELETE FROM materials WHERE id = %s"
            cursor.execute(query, (material_id,))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Material excluído com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Material não encontrado.'}), 404
        except Error as e:
            print(f"Erro ao deletar material: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.cli.command("init-db")
def init_db_command():
    """Limpa os dados existentes e cria novas tabelas."""
    setup_database()
    click.echo("Banco de dados inicializado.")

if __name__ == '__main__':
    app.run(debug=True, port=5000)

