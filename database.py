import sqlite3
from datetime import datetime
import bcrypt  # Importado corretamente no escopo global

def conectar():
    return sqlite3.connect("consultorio.db", timeout=20)  # Timeout de 20 segundos para evitar erros de banco ocupado


def iniciar_banco():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario TEXT UNIQUE,
            senha TEXT,
            nivel TEXT,
            email TEXT UNIQUE)""")
    
    # Cria a tabela de licenças com a coluna de segurança
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes_licencas (
            cliente_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_cliente TEXT,
            email TEXT,
            validade TEXT,
            status TEXT,
            token_seguranca TEXT)""")
    
    # Tabela de Pacientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, data_nascimento TEXT,
            cpf TEXT UNIQUE, rg TEXT UNIQUE,
            telefone TEXT, endereco TEXT)""")
        
    # Tabela de Consultas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            id_paciente INTEGER, 
            data TEXT, 
            hora TEXT,
            valor REAL DEFAULT 0.0, 
            metodo_pagamento TEXT DEFAULT 'Convênio',
            FOREIGN KEY(id_paciente) REFERENCES pacientes(id))""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_receitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_paciente INTEGER,
        data TEXT,
        prescricao TEXT,
        medico TEXT,
        FOREIGN KEY(id_paciente) REFERENCES pacientes(id))""")

    
    # 1. INJEÇÃO DE DADOS INICIAIS DE USUÁRIO
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        # Define uma senha padrão (ex: 'admin123') e gera o hash com bcrypt
        senha_padrao = "admin123".encode('utf-8')
        senha_hash = bcrypt.hashpw(senha_padrao, bcrypt.gensalt()).decode('utf-8')
        
        # Cria o primeiro usuário administrador do sistema
        cursor.execute("INSERT INTO usuarios (nome, usuario, senha, nivel, email) VALUES (?, ?, ?, ?, ?)", 
                       ("Admin", "admin", senha_hash, "Admin", "admin@email.com"))
        conn.commit()  # <-- CORRIGIDO: O commit é na CONEXÃO (conn)
        print("Usuário padrão 'admin' criado com a senha 'admin123'")

    # 2. INJEÇÃO DE LICENÇA MESTRE (CORRIGIDO PARA BCRYPT SEM IMPORTAR TKINTER)
    cursor.execute("SELECT COUNT(*) FROM clientes_licencas")
    if cursor.fetchone()[0] == 0:
        nome_master = "Admin"
        email_master = "admin@email.com" 
        data_validade = "2026-12-19"  # Válido por 30 dias
        
        # CHAVE ANTIFRAUDE (Deve ser identica à string usada dentro do LicencaApp)
        CHAVE_SECRETA = "MinhaChaveSuperSecreta123456"
        texto_combinado = f"{nome_master}-{data_validade}-{CHAVE_SECRETA}"
        
        # Gera o token bcrypt correto diretamente aqui
        salt = bcrypt.gensalt()
        token_master = bcrypt.hashpw(texto_combinado.encode('utf-8'), salt).decode('utf-8')
        
        cursor.execute("""
            INSERT INTO clientes_licencas (nome_cliente, email, validade, status, token_seguranca)
            VALUES (?, ?, ?, ?, ?)
        """, (nome_master, email_master, data_validade, "Ativo", token_master))
        conn.commit()  # <-- CORRIGIDO: O commit é na CONEXÃO (conn)
        print("Licença mestre inicial gerada em Bcrypt com sucesso!")

    cursor.close()
    conn.close()


def cadastrar_paciente(nome, nasc, cpf, rg, telefone, endereco):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pacientes (nome, data_nascimento, cpf, rg, telefone, endereco) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nome, nasc, cpf, rg, telefone, endereco))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False


def buscar_estatisticas():
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM pacientes")
    total_p = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_u = cursor.fetchone()[0]

    hoje = datetime.now().strftime('%d/%m/%Y')
    cursor.execute("SELECT COUNT(*) FROM consultas WHERE data = ?", (hoje,))
    total_c = cursor.fetchone()[0]
    
    conn.close()
    return total_p, total_u, total_c


def agendar_consulta(id_paciente, data, hora, valor, metodo_pagamento):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO consultas (id_paciente, data, hora, valor, metodo_pagamento) 
            VALUES (?, ?, ?, ?, ?)
        """, (id_paciente, data, hora, valor, metodo_pagamento))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao agendar: {e}")
        return False


def buscar_lista_consultas():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.nome, c.data, c.hora, c.valor, c.metodo_pagamento, c.id 
        FROM consultas c
        INNER JOIN pacientes p ON c.id_paciente = p.id
        ORDER BY c.data ASC
    """)
    dados = cursor.fetchall()
    conn.close()
    return dados


def listar_todos_pacientes():
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, data_nascimento, cpf, telefone, endereco FROM pacientes")
        pacientes = cursor.fetchall()
        conn.close()
        
        print("\n" + "="*50)
        print(f"{'ID':<4} | {'NOME':<20} | {'CPF':<12} | {'TEL'}")
        print("-" * 50)
        for p in pacientes:
            print(f"{p[0]:<4} | {p[1]:<20} | {p[2]:<12} | {p[3]}")
        print("="*50 + "\n")
        return pacientes
    except Exception as e:
        print(f"Erro ao listar: {e}")
        return []


def buscar_lista_pacientes():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, data_nascimento, cpf, rg, telefone, endereco FROM pacientes ORDER BY id")
    dados = cursor.fetchall()
    conn.close()
    return dados


def excluir_paciente(id_paciente):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pacientes WHERE id = ?", (id_paciente,))
    conn.commit()
    conn.close()


def atualizar_paciente(id_p, nome, nasc, cpf, rg, tel, end):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pacientes 
            SET nome=?, data_nascimento=?, cpf=?, rg=?, telefone=?, endereco=? 
            WHERE id=?
        """, (nome, nasc, cpf, rg, tel, end, id_p))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar no banco: {e}")
        return False


def resetar_pacientes():
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pacientes")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='pacientes'")
        conn.commit()
        conn.close()
        print("Tabela de usuários resetada com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao resetar: {e}")
        return False


# --- FUNÇÃO QUE ESTAVA CORTADA FOI COMPLETADA CORRETAMENTE ABAIXO ---
def atualizar_consulta(id_consulta, nova_data, nova_hora, novo_valor, novo_metodo_pagamento, novo_id_paciente):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE consultas 
            SET data = ?, hora = ?, valor = ?, metodo_pagamento = ?, id_paciente = ? 
            WHERE id = ?
        """, (nova_data, nova_hora, novo_valor, novo_metodo_pagamento, novo_id_paciente, id_consulta))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar consulta: {e}")
        return False
    finally:
        if conn:
            conn.close()

def excluir_consulta(id_consulta):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM consultas WHERE id = ?", (id_consulta,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao excluir consulta: {e}")
        return False


def salvar_receita_historico(id_paciente, prescricao, medico):
    conn = None
    try:
        conn = conectar()
        conn.execute("PRAGMA busy_timeout = 20000")  # Define um tempo limite para evitar erros de banco ocupado
        cursor = conn.cursor()
        data_hoje = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        cursor.execute("""
            INSERT INTO historico_receitas (id_paciente, data, prescricao, medico) 
            VALUES (?, ?, ?, ?)
        """, (id_paciente, data_hoje, prescricao, medico))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar histórico de receita: {e}")
        return False


def buscar_historico_por_paciente(id_paciente):    
    conn = None
    try:
        conn = conectar()
        conn.execute("PRAGMA busy_timeout = 20000")  # Define um tempo limite para evitar erros de banco ocupado
        cursor = conn.cursor()
        # Busca Data, Médico e Prescrição (limitando às 10 últimas)
        cursor.execute("""
            SELECT data, medico, prescricao 
            FROM historico_receitas 
            WHERE id_paciente = ? 
            ORDER BY id DESC LIMIT 10
        """, (id_paciente,))
        dados = cursor.fetchall()
        conn.close()
        return dados
    except Exception as e:
        print(f"Erro ao buscar histórico: {e}")
        return []



def cadastrar_usuario(nome, usuario, senha, nivel, email):
    try:
        conn = conectar()
        cursor = conn.cursor()
        
        # Criptografa a senha com bcrypt antes de salvar
        senha_bytes = senha.encode('utf-8')
        senha_hash = bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute("""
            INSERT INTO usuarios (nome, usuario, senha, nivel, email) 
            VALUES (?, ?, ?, ?, ?)
        """, (nome, usuario, senha_hash, nivel, email))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Cai aqui se o 'usuario' ou 'email' já existirem (UNIQUE)
        print("Erro: Usuário ou E-mail já cadastrado.")
        return False
    except Exception as e:
        print(f"Erro ao cadastrar usuário: {e}")
        return False


def verificar_login(usuario, senha_digitada):
    conn = conectar()
    cursor = conn.cursor()
    # Ordem: 0 = senha, 1 = nivel
    cursor.execute("SELECT senha, nivel FROM usuarios WHERE usuario = ?", (usuario,))
    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        senha_hash = resultado[0] # Pega a senha (índice 0)
        nivel = resultado[1]      # Pega o nível (índice 1)

        # O bcrypt compara a senha digitada com a do banco
        if bcrypt.checkpw(senha_digitada.encode('utf-8'), senha_hash):
            return resultado  # Retorna a tupla completa (senha, nivel)
            
    return None


def listar_todos_usuarios():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT usuario, nivel FROM usuarios")
    dados = cursor.fetchall()
    conn.close()
    return dados


def excluir_usuario(nome):
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE usuario = ?", (nome,))
        conn.commit()
        conn.close()
        return True
    except:
        return False


def atualizar_usuario(usuario_antigo, nome, usuario_novo, senha, nivel, email):
    conn = None
    try:
        conn = sqlite3.connect("consultorio.db")
        cursor = conn.cursor()
        conn.execute("PRAGMA busy_timeout = 20000")  # Ativa a verificação de chaves estrangeiras

        if senha: # Se o admin digitou uma nova senha, atualiza ela com Bcrypt
            salt = bcrypt.gensalt()
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')
            
            cursor.execute("""
                UPDATE usuarios 
                SET nome=?, usuario=?, senha=?, nivel=?, email=? 
                WHERE usuario=?
            """, (nome, usuario_novo, senha_hash, nivel, email, usuario_antigo))
        else: # Se a senha veio em branco, atualiza os dados sem mexer na senha atual
            cursor.execute("""
                UPDATE usuarios 
                SET nome=?, usuario=?, nivel=?, email=? 
                WHERE usuario=?
            """, (nome, usuario_novo, nivel, email, usuario_antigo))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar banco: {e}")
        return False



def verificar_login(usuario, senha_digitada):
    """
    Busca o usuário no banco de dados e valida a senha usando Bcrypt.
    Retorna os dados do usuário (dict) se for válido, ou None se falhar.
    """
    try:
        conn = conectar()
        # Configura para retornar os dados como um dicionário/chave para facilitar o acesso
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Busca o usuário pelo nome de usuário único
        cursor.execute("SELECT usuario_id, nome, usuario, senha, nivel, email FROM usuarios WHERE usuario = ?", (usuario,))
        usuario_db = cursor.fetchone()
        cursor.close()
        conn.close()

        if usuario_db:
            senha_hash_banco = usuario_db["senha"]
            
            # Converte as senhas para bytes (exigência do bcrypt)
            senha_digitada_bytes = senha_digitada.encode('utf-8')
            senha_hash_bytes = senha_hash_banco.encode('utf-8')
            
            # Compara a senha digitada com o Hash do banco de dados
            if bcrypt.checkpw(senha_digitada_bytes, senha_hash_bytes):
                # Se a senha estiver correta, retorna os dados mapeados
                return {
                    "id": usuario_db["usuario_id"],
                    "nome": usuario_db["nome"],
                    "usuario": usuario_db["usuario"],
                    "nivel": usuario_db["nivel"],
                    "email": usuario_db["email"]
                }
                
        # Se o usuário não existir ou a senha estiver incorreta
        return None
        
    except Exception as e:
        print(f"Erro ao verificar login: {e}")
        return None


def listar_todos_usuarios():
    """
    Busca todos os usuários cadastrados no sistema para exibir na tabela da interface.
    Retorna uma lista de tuplas contendo os dados públicos dos usuários.
    """
    try:
        conn = conectar()
        cursor = conn.cursor()
        
        # Seleciona os dados necessários (pulando a senha por segurança)
        cursor.execute("SELECT nome, usuario, nivel, email FROM usuarios ORDER BY nome")
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return usuarios
    except Exception as e:
        print(f"Erro ao listar usuários no banco: {e}")
        return []


def excluir_licenca(id_cliente):
    try:
        # Abre a conexão usando a sua função conectar
        con = conectar() 
        cursor = con.cursor()
        
        # Deleta o registro pelo ID
        cursor.execute("DELETE FROM clientes_licencas WHERE cliente_id = ?", (id_cliente,))
        
        con.commit()
        con.close()
        return True
    except Exception as e:
        print(f"Erro no banco: {e}")
        return False
