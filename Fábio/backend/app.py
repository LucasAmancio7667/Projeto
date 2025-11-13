from flask import Flask, jsonify, send_from_directory, request
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import string
import click
from manage_db import setup_database
from routes.alunos_bp import alunos_bp
from routes.forum_bp import forum_bp

# CORREÇÃO AQUI: static_folder deve apontar para o nome real da sua pasta de frontend
app = Flask(__name__, static_folder='../PROJETO_FINAL', static_url_path='/')
app.register_blueprint(alunos_bp)
app.register_blueprint(forum_bp)


# ADIÇÃO: Configuração para uploads de materiais
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ADIÇÃO: Função para gerar nome de usuário baseado nas iniciais do nome


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
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    
    # Fallback se a conexão falhar após a verificação inicial
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500


# ====================================================================================================
# ROTAS PARA USERS (LOGIN E ADMINISTRAÇÃO DE USUÁRIOS GERAIS)
# ====================================================================================================
@app.route('/users', methods=['GET'])
def get_users():

    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    users = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # ATUALIZAÇÃO AQUI: Adicionámos data_criacao à consulta
            cursor.execute("SELECT id, username, full_name, role, student_id, last_login, total_logins, online_status, data_criacao FROM users")
            users = cursor.fetchall()
            for user in users:
                if user.get('last_login'):
                    user['last_login'] = user['last_login'].isoformat() # Formatar data para JSON
                # ATUALIZAÇÃO AQUI: Adicionámos a formatação para a nova data
                if user.get('data_criacao'):
                    user['data_criacao'] = user['data_criacao'].isoformat()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar usuários: {e}")
        finally:
            if connection.is_connected():
                connection.close()
    return jsonify(users)

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):

    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify({'message': 'Erro de conexão com o banco de dados'}), 500

@app.route('/users/add', methods=['POST'])
def add_user():
    user_data = request.get_json()
    username = user_data.get('username')
    password = user_data.get('password')
    full_name = user_data.get('full_name')
    role = user_data.get('role')
    student_id_raw = user_data.get('student_id')

    print(f"Dados recebidos para adicionar usuário: {user_data}")

    if not username or not password or not role:
        print("Erro: Username, Password e Role são obrigatórios.")
        return jsonify({'success': False, 'message': 'Username, Password e Role são obrigatórios!'}), 400

    allowed_roles = ['student', 'teacher']
    if role not in allowed_roles:
        print(f"Erro: Role inválida - {role}")
        return jsonify({'success': False, 'message': 'Role inválida. Opções válidas: student, teacher.'}), 400

    student_id = None
    if role == 'student':
        if student_id_raw:
            try:
                student_id = int(student_id_raw)
            except ValueError:
                print(f"Erro: student_id '{student_id_raw}' não é um número válido para o perfil de aluno.")
                return jsonify({'success': False, 'message': 'Para o perfil de Aluno, o ID de Aluno deve ser um número válido.'}), 400

    hashed_password = generate_password_hash(password)
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
            query = """
            INSERT INTO users (username, password_hash, full_name, role, student_id)
            VALUES (%s, %s, %s, %s, %s)
            """
            values = (username, hashed_password, full_name, role, student_id)
            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            return jsonify({'success': True, 'message': 'Usuário adicionado com sucesso!'}), 201
        except Error as e:
            print(f"Erro MySQL ao adicionar usuário: {e}")
            connection.rollback()
            if e.errno == 1062:
                print(f"Erro de duplicidade detectado: {e.msg}")
                return jsonify({'success': False, 'message': f'Erro: Nome de usuário "{username}" já existe.'}), 409
            return jsonify({'success': False, 'message': 'Erro interno do servidor ou usuário já existe.'}), 500
        finally:
            if connection and connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500

@app.route('/users/edit/<int:user_id>', methods=['PUT'])
def edit_user(user_id):
    user_data = request.get_json()
    
    username = user_data.get('username')

    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
                allowed_roles = ['student', 'teacher']
                if user_data.get('role') not in allowed_roles:
                    return jsonify({'success': False, 'message': 'Role inválida. Opções válidas: student, teacher.'}), 400
                set_clauses.append("role = %s")
                values.append(user_data['role'])
            if 'student_id' in user_data:
                edit_student_id_raw = user_data.get('student_id')
                edit_student_id = None
                if user_data.get('role') == 'student':
                    if edit_student_id_raw:
                        try:
                            edit_student_id = int(edit_student_id_raw)
                        except ValueError:
                            return jsonify({'success': False, 'message': 'Para o perfil de Aluno, o ID de Aluno deve ser um número válido.'}), 400
                set_clauses.append("student_id = %s")
                values.append(edit_student_id)
            if 'last_login' in user_data:
                set_clauses.append("last_login = %s")
                values.append(user_data['last_login'])
            if 'total_logins' in user_data:
                set_clauses.append("total_logins = %s")
                values.append(user_data['total_logins'])
            if 'online_status' in user_data:
                set_clauses.append("online_status = %s")
                values.append(user_data['online_status'])
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
            if e.errno == 1062:
                msg = f'Erro: Nome de usuário "{username}" já existe.' if username else 'Erro: Um registro com dados duplicados já existe.'
                return jsonify({'success': False, 'message': msg}), 409
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
        finally:
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500


@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):

    from db_utils import create_db_connection
    connection = create_db_connection()

    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados'}), 500

@app.route('/login', methods=['POST'])
def login():
    credentials = request.get_json()
    username = credentials.get('username')
    password = credentials.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Nome de usuário e senha são obrigatórios.'}), 400
    
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT id, username, password_hash, full_name, role, student_id FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            cursor.close()

            if user and check_password_hash(user['password_hash'], password):
                cursor_update = connection.cursor()
                update_query = "UPDATE users SET last_login = NOW(), total_logins = total_logins + 1, online_status = 'Online' WHERE id = %s"
                cursor_update.execute(update_query, (user['id'],))
                connection.commit()
                cursor_update.close()

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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/logout/<int:user_id>', methods=['POST'])
def logout(user_id):
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500


# ====================================================================================================
# ROTAS PARA CLASSES
# ====================================================================================================
@app.route('/classes', methods=['GET'])
def get_classes():
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify(classes)

@app.route('/classes/<int:class_id>', methods=['GET'])
def get_class_by_id(class_id):
    from db_utils import create_db_connection
    connection = create_db_connection()

    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
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
    from db_utils import create_db_connection
    connection = create_db_connection()

    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/classes/edit/<int:class_id>', methods=['PUT'])
def edit_class(class_id):
    class_data = request.get_json()
    from db_utils import create_db_connection
    connection = create_db_connection()

    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/classes/delete/<int:class_id>', methods=['DELETE'])
def delete_class(class_id):
    from db_utils import create_db_connection
    connection = create_db_connection()

    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

# ====================================================================================================
# ROTAS PARA REGISTROS DE FREQUÊNCIA (attendance_records)
# ====================================================================================================
@app.route('/attendance', methods=['GET'])
def get_attendance_records():
    from db_utils import create_db_connection
    connection = create_db_connection()

    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify(records)

@app.route('/attendance/student/<int:student_id>', methods=['GET'])
def get_attendance_by_student(student_id):

    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
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
    
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
            
            check_query = "SELECT id FROM attendance_records WHERE student_id = %s AND class_id = %s"
            cursor.execute(check_query, (student_id, class_id))
            existing_record = cursor.fetchone()

            if existing_record:
                record_id = existing_record[0]
                update_query = "UPDATE attendance_records SET attendance_status = %s WHERE id = %s"
                cursor.execute(update_query, (attendance_status, record_id))
                connection.commit()
            else:
                insert_query = "INSERT INTO attendance_records (student_id, class_id, attendance_status) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (student_id, class_id, attendance_status))
                connection.commit()
                record_id = cursor.lastrowid

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

            cursor.close()
            return jsonify({'success': True, 'message': 'Registro de frequência salvo com sucesso!', 'id': record_id}), 200
        except Error as e:
            print(f"Erro ao adicionar/atualizar registro de frequência e faltas: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/attendance/edit/<int:record_id>', methods=['PUT'])
def edit_attendance_record(record_id):
    record_data = request.get_json()
    attendance_status = record_data.get('attendance_status')

    if not attendance_status:
        return jsonify({'success': False, 'message': 'Status de Frequência é obrigatório.'}), 400
    
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
            query = "UPDATE attendance_records SET attendance_status = %s WHERE id = %s"
            values = (attendance_status, record_id)
            cursor.execute(query, values)
            connection.commit()
            
            get_student_id_query = "SELECT student_id FROM attendance_records WHERE id = %s"
            cursor.execute(get_student_id_query, (record_id,))
            result = cursor.fetchone()
            
            if result:
                student_id = result[0]
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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/attendance/delete/<int:record_id>', methods=['DELETE'])
def delete_attendance_record(record_id):
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
            
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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

# ====================================================================================================
# ROTAS PARA STATUS DOS ALUNOS (status_alunos - AQUI SERÁ A TABELA CONSOLIDADA)
# ====================================================================================================
@app.route('/status_alunos', methods=['GET'])
def get_status_alunos():
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    statuses = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
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
            if connection.is_connected():
                connection.close()
    return jsonify(statuses)

# ADIÇÃO: Rotas para Atividades dos Alunos
@app.route('/atividades_alunos', methods=['GET'])
def get_atividades_alunos():
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    activities = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
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
            if connection.is_connected():
                connection.close()
    return jsonify(activities)

@app.route('/atividades_alunos/update_aula/<int:aluno_id>', methods=['PUT'])
def update_aula_status(aluno_id):
    update_data = request.get_json()
    aula_col = update_data.get('aula_col')
    new_status = update_data.get('new_status')

    if not aula_col or not new_status or not aluno_id:
        return jsonify({'success': False, 'message': 'Dados de atualização insuficientes.'}), 400
    
    if aula_col not in [f'aula_{i}' for i in range(1, 11)]:
        return jsonify({'success': False, 'message': 'Coluna de aula inválida.'}), 400
    
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
            query_aula = f"UPDATE atividades_alunos SET {aula_col} = %s WHERE id = %s"
            cursor.execute(query_aula, (new_status, aluno_id))
            
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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

# ====================================================================================================
# ROTAS PARA MATERIAIS
# ====================================================================================================
@app.route('/materials', methods=['GET'])
def get_materials():
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
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

        from db_utils import create_db_connection
        connection = create_db_connection()
        
        # MELHORIA DE DISPONIBILIDADE
        if not connection:
            # Tenta remover o arquivo salvo se o BD estiver offline
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
                if connection.is_connected():
                    connection.close()
        return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500
    return jsonify({'success': False, 'message': 'Erro no upload do arquivo.'}), 500

@app.route('/materials/download/<path:filename>', methods=['GET'])
def download_material(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/materials/edit/<int:material_id>', methods=['PUT'])
def edit_material(material_id):
    material_data = request.get_json()
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/materials/delete/<int:material_id>', methods=['DELETE'])
def delete_material(material_id):
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT file_path FROM materials WHERE id = %s", (material_id,))
            material = cursor.fetchone()
            
            if material and material.get('file_path'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], material['file_path'])
                if os.path.exists(filepath):
                    os.remove(filepath)
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
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

# ====================================================================================================
# ROTAS PARA AVISOS
# ====================================================================================================
@app.route('/avisos', methods=['GET'])
def get_avisos():
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    avisos = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
            SELECT a.id, a.titulo, a.mensagem, a.data_criacao, u.full_name as autor
            FROM avisos a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.data_criacao DESC
            """
            cursor.execute(query)
            avisos = cursor.fetchall()
            for aviso in avisos:
                if aviso.get('data_criacao'):
                    aviso['data_criacao'] = aviso['data_criacao'].isoformat()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar avisos: {e}")
        finally:
            if connection.is_connected():
                connection.close()
    return jsonify(avisos)

@app.route('/avisos/add', methods=['POST'])
def add_aviso():
    aviso_data = request.get_json()
    titulo = aviso_data.get('titulo')
    mensagem = aviso_data.get('mensagem')
    user_id = aviso_data.get('user_id')

    if not titulo or not mensagem or not user_id:
        return jsonify({'success': False, 'message': 'Título, mensagem e ID do usuário são obrigatórios.'}), 400
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
            query = "INSERT INTO avisos (titulo, mensagem, user_id) VALUES (%s, %s, %s)"
            values = (titulo, mensagem, user_id)
            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            return jsonify({'success': True, 'message': 'Aviso adicionado com sucesso!'}), 201
        except Error as e:
            print(f"Erro ao adicionar aviso: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500

@app.route('/avisos/delete/<int:aviso_id>', methods=['DELETE'])
def delete_aviso(aviso_id):
    from db_utils import create_db_connection
    connection = create_db_connection()
    
    # MELHORIA DE DISPONIBILIDADE
    if not connection:
        return jsonify({'success': False, 'message': 'MAINTENANCE_MODE'}), 503

    if connection:
        try:
            cursor = connection.cursor()
            query = "DELETE FROM avisos WHERE id = %s"
            cursor.execute(query, (aviso_id,))
            connection.commit()
            cursor.close()
            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Aviso excluído com sucesso!'}), 200
            else:
                return jsonify({'success': False, 'message': 'Aviso não encontrado.'}), 404
        except Error as e:
            print(f"Erro ao deletar aviso: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            if connection.is_connected():
                connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500


@app.cli.command("init-db")
def init_db_command():
    """Limpa os dados existentes e cria novas tabelas."""
    setup_database()
    click.echo("Banco de dados inicializado.")

if __name__ == '__main__':
    app.run(debug=True, port=5000)