# factories.py

from abc import ABC, abstractmethod
from werkzeug.security import generate_password_hash
from utils import generate_username, generate_random_password

# --- Produto Abstrato (Interface do que será criado) ---
# Para simplificar, nosso "produto" será um dicionário com os dados do usuário.

# --- Fábrica Abstrata ---
class UserFactory(ABC):
    @abstractmethod
    def create_user(self, data, connection):
        """
        O método de fábrica.
        'data' é um dicionário com informações como nome, email, etc.
        'connection' é a conexão com o banco de dados.
        """
        pass

# --- Fábricas Concretas ---

class StudentFactory(UserFactory):
    def create_user(self, data, connection):
        """ Cria um usuário do tipo 'student' a partir dos dados de um aluno. """
        aluno_full_name = data.get('nome')
        aluno_id = data.get('aluno_id') # Esperamos o ID do aluno já criado

        if not aluno_full_name or not aluno_id:
            raise ValueError("Nome completo e ID do aluno são necessários para criar um usuário estudante.")

        # Encapsula a lógica que antes estava na rota
        generated_username = generate_username(aluno_full_name, connection)
        generated_password = generate_random_password()
        hashed_password = generate_password_hash(generated_password)

        return {
            "username": generated_username,
            "password_hash": hashed_password,
            "full_name": aluno_full_name,
            "role": "student",
            "student_id": aluno_id,
            # Retornamos a senha para exibição, como no código original
            "generated_password": generated_password
        }

class TeacherFactory(UserFactory):
    def create_user(self, data, connection):
        """ Cria um usuário genérico, como um professor. """
        password = data.get('password')
        if not password:
            raise ValueError("A senha é obrigatória para criar um professor.")

        hashed_password = generate_password_hash(password)

        return {
            "username": data.get('username'),
            "password_hash": hashed_password,
            "full_name": data.get('full_name'),
            "role": "teacher",
            "student_id": None
        }

# --- Helper para obter a fábrica correta ---
def get_user_factory(role):
    factories = {
        "student": StudentFactory(),
        "teacher": TeacherFactory()
    }
    factory = factories.get(role)
    if not factory:
        raise ValueError(f"Perfil de usuário inválido: {role}")
    return factory