from flask import Blueprint, jsonify, request
from mysql.connector import Error
from db_utils import create_db_connection

forum_bp = Blueprint('forum_bp', __name__)

# Rota para buscar todos os posts de uma aula específica
@forum_bp.route('/forum/posts/<int:class_id>', methods=['GET'])
def get_forum_posts(class_id):
    connection = create_db_connection()
    posts = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Juntar com a tabela 'users' para obter o nome de quem postou
            query = """
            SELECT fp.id, fp.mensagem, fp.data_postagem, u.full_name as autor
            FROM forum_posts fp
            JOIN users u ON fp.user_id = u.id
            WHERE fp.class_id = %s
            ORDER BY fp.data_postagem ASC
            """
            cursor.execute(query, (class_id,))
            posts = cursor.fetchall()
            # Formatar a data para ser compatível com JSON
            for post in posts:
                if post.get('data_postagem'):
                    post['data_postagem'] = post['data_postagem'].isoformat()
            cursor.close()
        except Error as e:
            print(f"Erro ao buscar posts do fórum: {e}")
        finally:
            connection.close()
    return jsonify(posts)

# Rota para adicionar um novo post a uma aula
@forum_bp.route('/forum/posts/add', methods=['POST'])
def add_forum_post():
    post_data = request.get_json()
    class_id = post_data.get('class_id')
    user_id = post_data.get('user_id')
    mensagem = post_data.get('mensagem')

    if not all([class_id, user_id, mensagem]):
        return jsonify({'success': False, 'message': 'ID da aula, ID do usuário e mensagem são obrigatórios.'}), 400

    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "INSERT INTO forum_posts (class_id, user_id, mensagem) VALUES (%s, %s, %s)"
            values = (class_id, user_id, mensagem)
            cursor.execute(query, values)
            connection.commit()
            cursor.close()
            return jsonify({'success': True, 'message': 'Mensagem publicada com sucesso!'}), 201
        except Error as e:
            print(f"Erro ao adicionar post no fórum: {e}")
            connection.rollback()
            return jsonify({'success': False, 'message': 'Erro interno do servidor.'}), 500
        finally:
            connection.close()
    return jsonify({'success': False, 'message': 'Erro de conexão com o banco de dados.'}), 500