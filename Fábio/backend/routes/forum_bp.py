from flask import Blueprint, jsonify, request
from mysql.connector import Error
# IMPORTAÇÃO ALTERADA: Importa os templates methods
from db_utils import execute_db_query, execute_db_transaction

forum_bp = Blueprint('forum_bp', __name__)

def _get_forum_posts_logic(connection, cursor, class_id):
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
            
    return posts, 200

# Rota para buscar todos os posts de uma aula específica
@forum_bp.route('/forum/posts/<int:class_id>', methods=['GET'])
def get_forum_posts(class_id):
    # CHAMA O TEMPLATE METHOD DE LEITURA
    return execute_db_query(_get_forum_posts_logic, class_id=class_id, error_message='Erro ao buscar posts do fórum')


def _add_forum_post_logic(connection, cursor, post_data):
    class_id = post_data.get('class_id')
    user_id = post_data.get('user_id')
    mensagem = post_data.get('mensagem')

    if not all([class_id, user_id, mensagem]):
        raise ValueError('ID da aula, ID do usuário e mensagem são obrigatórios.')

    query = "INSERT INTO forum_posts (class_id, user_id, mensagem) VALUES (%s, %s, %s)"
    values = (class_id, user_id, mensagem)
    cursor.execute(query, values)
    
    return {'success': True, 'message': 'Mensagem publicada com sucesso!'}, 201, None

# Rota para adicionar um novo post a uma aula
@forum_bp.route('/forum/posts/add', methods=['POST'])
def add_forum_post():
    post_data = request.get_json()
    # CHAMA O TEMPLATE METHOD DE ESCRITA
    return execute_db_transaction(_add_forum_post_logic, post_data=post_data, rollback_message='Erro interno do servidor.')