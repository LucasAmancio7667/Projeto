import mysql.connector
from mysql.connector import Error
from faker import Faker
import random

# Configurações do seu banco de dados
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root', # Lembre-se de usar sua senha
    'database': 'scratch'
}

# Inicializa o Faker para gerar dados em português do Brasil
fake = Faker('pt_BR')

def insert_fake_students(num_students=1000):
    """Gera e insere alunos fictícios no banco de dados."""

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print(f"Conectado ao banco de dados. Gerando {num_students} alunos...")

        for i in range(num_students):
            turma = random.choice(['25.1 - T1', '25.1 - T2', '25.2 - T1'])
            nome = fake.name()
            email = fake.unique.email()
            telefone = fake.msisdn()[3:] # Gera um número de telefone
            data_nascimento = fake.date_of_birth(minimum_age=12, maximum_age=15).strftime('%Y-%m-%d')
            rg = str(fake.unique.random_number(digits=9, fix_len=True))
            cpf = fake.unique.cpf().replace('.', '').replace('-', '')
            endereco = fake.address().replace('\n', ', ')
            escolaridade = random.choice(['8º ano', '9º ano'])
            escola = random.choice(['Pública', 'Privada'])
            responsavel = fake.name()

            query = """
            INSERT INTO alunos (turma, nome, email, telefone, data_nascimento, rg, cpf, endereco, escolaridade, escola, responsavel)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (turma, nome, email, telefone, data_nascimento, rg, cpf, endereco, escolaridade, escola, responsavel)

            cursor.execute(query, values)
            print(f"Inserindo aluno {i+1}/{num_students}: {nome}")

        conn.commit()
        print(f"\n{num_students} alunos inseridos com sucesso!")

    except Error as e:
        print(f"Erro ao inserir dados: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("Conexão fechada.")

if __name__ == '__main__':
    # Antes de popular, vamos garantir que a tabela de alunos está vazia para não duplicar
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print("Limpando a tabela de alunos antes de inserir novos dados...")
        cursor.execute("DELETE FROM users WHERE student_id IS NOT NULL") # Deleta usuários de alunos
        cursor.execute("DELETE FROM alunos")
        cursor.execute("ALTER TABLE alunos AUTO_INCREMENT = 1") # Reseta o contador de ID
        conn.commit()
        print("Tabela 'alunos' limpa.")
    except Error as e:
        print(f"Erro ao limpar a tabela: {e}")
    finally:
         if conn and conn.is_connected():
            cursor.close()
            conn.close()

    # Chama a função para inserir os 1000 alunos
    insert_fake_students(6000)