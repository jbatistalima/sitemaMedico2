import sqlite3
import bcrypt
import database as db
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry


# --- FUNÇÕES DE SUPORTE ---
def conectar():
    return sqlite3.connect("consultorio.db")
    

def gerar_token_licenca(nome_cliente, data_validade):
    CHAVE_SECRETA = "MinhaChaveSuperSecreta123456" 
    texto_combinado = f"{nome_cliente}-{data_validade}-{CHAVE_SECRETA}"
    
    # O bcrypt exige que o texto esteja em bytes
    dados_bytes = texto_combinado.encode('utf-8')
    
    # Gera o salt aleatório e cria o hash
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(dados_bytes, salt)
    
    # Retorna o hash como uma string de texto para salvar no banco SQLite
    return hash_bytes.decode('utf-8')

# --- VOCÊ TAMBÉM PRECISARÁ DESTA FUNÇÃO PARA VALIDAR ---
def verificar_token_licenca(nome_cliente, data_validade, token_banco):
    CHAVE_SECRETA = "MinhaChaveSuperSecreta123456" 
    texto_combinado = f"{nome_cliente}-{data_validade}-{CHAVE_SECRETA}"
    
    # Compara o texto combinado atual com o hash armazenado no banco
    return bcrypt.checkpw(
        texto_combinado.encode('utf-8'), 
        token_banco.encode('utf-8')
    )



# --- TELA ADMINISTRATIVA EM CUSTOMTKINTER ---
class TelaAdmin(ctk.CTkToplevel):
    def __init__(self, nivel_usuario):
        super().__init__()
        self.title("Painel Administrativo - Licenças")
        self.geometry("830x600+350+300")
        self.configure(fg_color="yellowgreen")        

        #self.attributes("-topmost", True)

        if nivel_usuario.lower() != "admin":
            messagebox.showerror("Acesso Negado", "Você não tem permissão para acessar esta tela.")
            self.destroy()
            return

        # Frame Central (Modulo Central)
        self.modulo_central = ctk.CTkFrame(self)
        self.modulo_central.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(self.modulo_central, text="Cadastrar Nova Licença", height=10).pack(pady=(30, 0))

        # 1. Formulário de Cadastro (Horizontal)
        self.layout_formulario = ctk.CTkFrame(self.modulo_central, fg_color="transparent")
        self.layout_formulario.pack(fill="x", pady=5)
        
        # Inputs com larguras fixas aproximadas usando width
        self.input_nome = ctk.CTkEntry(self.layout_formulario, fg_color="transparent", placeholder_text="Nome do Cliente", width=250)
        self.input_nome.pack(side="left", padx=5)

        self.input_email = ctk.CTkEntry(self.layout_formulario, fg_color="transparent", placeholder_text="Email", width=250)
        self.input_email.pack(side="left", padx=5)
        
        # input sem o uso de calendário.
        # self.input_validade = ctk.CTkEntry(self.layout_formulario, fg_color="transparent",  placeholder_text="DD/MM/AAAA", width=130)
        # self.input_validade.pack(side="left", padx=5)

        # Criando o calendário (DateEntry) adaptado para o Tkinter padrão dentro do CustomTkinter
        self.input_validade = DateEntry(self.layout_formulario, font=("Arial", 12),
            width=10,                      # Ajuste a largura (DateEntry usa contagem de caracteres)
            background='darkgreen',         # Cor de fundo do topo do calendário
            foreground='white',            # Cor do texto do topo
            borderwidth=2, 
            locale="pt_BR",  
            date_pattern='dd/mm/yyyy'      # Força o formato brasileiro padrão
        )
        self.input_validade.pack(side="left", padx=5, ipady=4)

        self.btn_cadastrar = ctk.CTkButton(
            self.layout_formulario, 
            text="Cadastrar", 
            command=self.cadastrar_cliente,
            text_color="white",
            width=140
        )
        self.btn_cadastrar.pack(side="left", padx=5)

        # Espaçamento vertical antes da tabela
        ctk.CTkLabel(self.modulo_central, text="Licenças Cadastrados", height=10).pack(pady=(40, 0))

        # Cabeçalho Falso para a Tabela (Simula os HorizontalHeaderLabels)
        self.cabecalho_tabela = ctk.CTkFrame(self.modulo_central, height=30, fg_color="transparent", border_width=1, border_color="#B2AEAE")
        self.cabecalho_tabela.pack(fill="x", padx=5)
        
        headers = [" ID", "Nome", "Email", "  Validade", "Status", "Ações"]
        for idx, text in enumerate(headers):
            lbl = ctk.CTkLabel(self.cabecalho_tabela, text=text, font=("Arial", 12, "bold"), anchor="w")
            lbl.grid(row=0, column=idx, padx=5, pady=5, sticky="w")

        # 2. Container de Scroll para a Tabela de Clientes
        self.tabela_scroll = ctk.CTkScrollableFrame(self.modulo_central)
        self.tabela_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Garante que as colunas distribuam o espaço proporcionalmente dentro do scroll
        self.cabecalho_tabela.grid_columnconfigure((0, 2, 3, 4, 4), weight=1)
        self.cabecalho_tabela.grid_columnconfigure((1), weight=3)
        self.cabecalho_tabela.grid_columnconfigure((5), weight=4)

        
        self.tabela_scroll.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        self.carregar_dados_clientes()

    def carregar_dados_clientes(self):
        """Busca clientes do SQLite, valida expiração e renderiza no frame de scroll"""
        # Limpa as linhas existentes para recarregar
        for widget in self.tabela_scroll.winfo_children():
            widget.destroy()

        con = conectar()
        con.row_factory = sqlite3.Row
        cursor = con.cursor()
        cursor.execute("SELECT * FROM clientes_licencas")
        clientes = cursor.fetchall()
        con.close()

        hoje = datetime.now().date()

        for row_idx, cliente in enumerate(clientes):
            id_cliente = int(cliente["cliente_id"])
            nome = str(cliente["nome_cliente"])
            email = str(cliente["email"])
            validade_str = str(cliente["validade"])
            status_atual = str(cliente["status"])

            # Validação dinâmica da data
            try:
                data_validade = datetime.strptime(validade_str, "%Y-%m-%d").date()
                if hoje > data_validade and status_atual != "Bloqueado":
                    status_atual = "Expirado"
                    con_update = conectar()
                    cursor_up = con_update.cursor()
                    cursor_up.execute("UPDATE clientes_licencas SET status='Expirado' WHERE cliente_id=?", (id_cliente,))
                    con_update.commit()
                    con_update.close()
            except ValueError:
                pass

            # Renderiza as labels de texto simulando células de uma tabela
            ctk.CTkLabel(self.tabela_scroll, text=str(id_cliente), anchor="w").grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
            ctk.CTkLabel(self.tabela_scroll, text=nome, anchor="w").grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")
            ctk.CTkLabel(self.tabela_scroll, text=email, anchor="w").grid(row=row_idx, column=2, padx=10, pady=5, sticky="ew")
            ctk.CTkLabel(self.tabela_scroll, text=validade_str, anchor="w").grid(row=row_idx, column=3, padx=10, pady=5, sticky="ew")
            ctk.CTkLabel(self.tabela_scroll, text=status_atual, anchor="w").grid(row=row_idx, column=4, padx=10, pady=5, sticky="ew")

            # Container Horizontal para os botões de ação na última coluna
            container_botoes = ctk.CTkFrame(self.tabela_scroll, fg_color="transparent")
            container_botoes.grid(row=row_idx, column=5, padx=5, pady=5, sticky="w")
 
            texto_botao_bloqueio = "Desbloquear" if status_atual == "Bloqueado" else "Bloquear"
            cor_botao_bloqueio = "orange" if status_atual == "Bloqueado" else "#802a4f"
            cor_texto_bloqueio = "black" if status_atual == "Bloqueado" else "white"
            
            btn_bloquear = ctk.CTkButton(
                container_botoes, 
                text=texto_botao_bloqueio,
                width=90,
                height=24,
                fg_color=cor_botao_bloqueio,
                text_color=cor_texto_bloqueio,
                command=lambda idx=id_cliente: self.bloquear_cliente(idx)
            )
            btn_bloquear.pack(side="left", padx=2)

            btn_renovar = ctk.CTkButton(
                container_botoes, 
                text="Renovar",
                width=60,
                height=24,
                fg_color="green",
                text_color="white",
                command=lambda idx=id_cliente: self.abrir_janela_editar(idx)
            )
            btn_renovar.pack(side="left", padx=2)

            btn_excluir = ctk.CTkButton(
                container_botoes, 
                text="Excluir",
                width=60,
                height=24,
                fg_color="tomato",
                text_color="white",
                command=lambda idx=id_cliente: self.acao_excluir_licenca(idx)
            )
            btn_excluir.pack(side="left", padx=2)


    def cadastrar_cliente(self):
        nome = self.input_nome.get().strip()
        email = self.input_email.get().strip()
        
        # 1. Mudamos o nome da variável para deixar claro que ela veio no formato BR (DD/MM/AAAA)
        data_br = self.input_validade.get().strip()
        
        if not nome or not email or not data_br:
            # CORREÇÃO PARENT: Vincula o aviso a esta janela principal (self)
            messagebox.showwarning("Erro", "Preencha todos os campos!", parent=self)
            return

        try:
            # 2. Converte o texto brasileiro para um formato de data real do Python
            data_objeto = datetime.strptime(data_br, "%d/%m/%Y").date()
            
            # 3. Transforma no padrão universal aceito pelo banco: AAAA-MM-DD
            validade_banco = data_objeto.strftime("%Y-%m-%d")
            
        except ValueError:
            # Se o usuário errar a digitação, o sistema bloqueia o cadastro antes de salvar dados errados
            messagebox.showerror("Data Inválida", "Por favor, digite a data no formato DD/MM/AAAA", parent=self)
            return

        # 4. Agora geramos o token com a data correta do banco (AAAA-MM-DD) para não quebrar o login posterior
        token_seguranca = gerar_token_licenca(nome, validade_banco)

        con = conectar()
        cursor = con.cursor()
        cursor.execute("""
            INSERT INTO clientes_licencas (nome_cliente, email, validade, status, token_seguranca)
            VALUES (?, ?, ?, 'Ativo', ?)
        """, (nome, email, validade_banco, token_seguranca)) # Salvando 'validade_banco'
        con.commit()
        con.close()

        # Limpa os campos da tela após o sucesso
        self.input_nome.delete(0, "end")
        self.input_email.delete(0, "end")
        self.input_validade.delete(0, "end")
        
        # Atualiza a tabela visual para mostrar o novo cliente cadastrado
        self.carregar_dados_clientes()
        
        messagebox.showinfo("Sucesso", "Cliente cadastrado com sucesso!", parent=self)


    def bloquear_cliente(self, id_cliente):
        con = conectar()
        cursor = con.cursor()
        cursor.execute("SELECT status FROM clientes_licencas WHERE cliente_id=?", (id_cliente,))
        resultado = cursor.fetchone()
        
        if resultado:
            status_atual = resultado[0]
            novo_status = "Ativo" if status_atual == "Bloqueado" else "Bloqueado"
            
            cursor.execute("UPDATE clientes_licencas SET status=? WHERE cliente_id=?", (novo_status, id_cliente))
            con.commit()
            
        con.close()
        self.carregar_dados_clientes()
     

    def abrir_janela_editar(self, id_cliente):
        """Abre uma janela popup personalizada para editar Nome, E-mail e Validade."""
        # 1. Busca os dados atuais do cliente no banco de dados
        con = conectar()
        con.row_factory = sqlite3.Row
        cursor = con.cursor()
        cliente = cursor.execute("SELECT nome_cliente, email, validade FROM clientes_licencas WHERE cliente_id=?", (id_cliente,)).fetchone()
        con.close()

        if not cliente:
            messagebox.showerror("Erro", "Cliente não encontrado.")
            return

        # Converte a data do banco (AAAA-MM-DD) para exibir no input como (DD/MM/AAAA)
        try:
            data_objeto = datetime.strptime(str(cliente["validade"]), "%Y-%m-%d").date()
            data_br_atual = data_objeto.strftime("%d/%m/%Y")
        except ValueError:
            data_br_atual = str(cliente["validade"])

        # 2. Criação da Janela Popup (Toplevel)
        janela_editar = ctk.CTkToplevel(self)
        janela_editar.title("Editar Cadastro / Licença")
        janela_editar.geometry("400x420+600+0")
        janela_editar.attributes("-topmost", True) # Garante que fica na frente
        janela_editar.resizable(False, False)

        # Elementos Visuais da Janela
        ctk.CTkLabel(janela_editar, text="Editar Dados do Cliente", font=("Arial", 16, "bold")).pack(pady=15)

        # Input Nome
        ctk.CTkLabel(janela_editar, text="Nome do Cliente:").pack(anchor="w", padx=30)
        input_nome = ctk.CTkEntry(janela_editar, width=340)
        input_nome.pack(pady=(0, 30))
        input_nome.insert(0, str(cliente["nome_cliente"])) # Preenche com o valor atual

        # Input E-mail
        ctk.CTkLabel(janela_editar, text="E-mail:").pack(anchor="w", padx=30)
        input_email = ctk.CTkEntry(janela_editar, width=340)
        input_email.pack(pady=(0, 30))
        input_email.insert(0, str(cliente["email"])) # Preenche com o valor atual

        # Input Validade (Padrão BR)
        # ctk.CTkLabel(janela_editar, text="Nova Validade (DD/MM/AAAA):").pack(anchor="w", padx=30)
        # input_validade = ctk.CTkEntry(janela_editar, width=340, placeholder_text="DD/MM/AAAA")
        # input_validade.pack(pady=(0, 40))
        # input_validade.insert(0, data_br_atual) # Preenche com o valor atual formatado
        
        # 3. Função interna que processa o salvamento ao clicar no botão
        # def salvar_alteracoes():
        #     novo_nome = input_nome.get().strip()
        #     novo_email = input_email.get().strip()            
        #     data_br_digitada = input_validade.get().strip() 


        ctk.CTkLabel(janela_editar, text="Nova Validade:").pack(anchor="w", padx=30)
        # Criando o calendário (DateEntry) adaptado para o Tkinter padrão dentro do CustomTkinter
        input_validade = DateEntry(janela_editar, font=("Arial", 16),
            width=33,                      # Ajuste a largura (DateEntry usa contagem de caracteres)
            background='darkgreen',         # Cor de fundo do topo do calendário
            foreground='white',            # Cor do texto do topo
            borderwidth=2,
            locale="pt_BR",
            date_pattern='dd/mm/yyyy'      # Força o formato brasileiro padrão
        )
        input_validade.pack(pady=(0, 40), padx=10)        

        # 3. Função interna que processa o salvamento ao clicar no botão
        def salvar_alteracoes():
            novo_nome = input_nome.get().strip()
            novo_email = input_email.get().strip()
            data_br_digitada = input_validade.get().strip()

            if not novo_nome or not novo_email or not data_br_digitada:
                messagebox.showwarning("Campos Vazios", "Preencha todos os campos.", parent=janela_editar)
                return

            try:
                # Converte o input BR do usuário para o formato padrão do banco (AAAA-MM-DD)
                data_objeto_nova = datetime.strptime(data_br_digitada, "%d/%m/%Y").date()
                validade_banco = data_objeto_nova.strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Data Inválida", "Use o formato DD/MM/AAAA (Ex: 25/06/2026)", parent=janela_editar)
                return

            # RECRIA O TOKEN: Usa o NOVO nome e a NOVA data convertida para o banco
            # Nota: Altere 'token_seguranca' para 'token' se esse for o nome exato da sua coluna
            novo_token = gerar_token_licenca(novo_nome, validade_banco)

            # Atualiza tudo no banco de dados de uma vez só
            con_update = conectar()
            cursor_up = con_update.cursor()
            cursor_up.execute("""
                UPDATE clientes_licencas 
                SET nome_cliente=?, email=?, validade=?, token_seguranca=?, status='Ativo' 
                WHERE cliente_id=?
            """, (novo_nome, novo_email, validade_banco, novo_token, id_cliente))
            con_update.commit()
            con_update.close()

            # Fecha a janela popup, avisa o usuário e atualiza a tabela principal
            janela_editar.destroy()
            messagebox.showinfo("Sucesso", "Cadastro atualizado com sucesso!")
            self.carregar_dados_clientes()

        # Botão Salvar
        btn_salvar = ctk.CTkButton(janela_editar, text="Salvar Alterações", command=salvar_alteracoes, fg_color="green", text_color="white", width=180)
        btn_salvar.pack(pady=(0, 30))


    def acao_excluir_licenca(self, id_cliente):
        # 1. Pergunta se tem certeza usando o ID que veio do botão
        confirmar = messagebox.askyesno(
            "Confirmar Exclusão", 
            f"Tem certeza que deseja EXCLUIR permanentemente o cliente ID {id_cliente}?\n\n"
            "Esta ação não pode ser desfeita!", 
            parent=self
        )

        # 2. Se confirmou, chama a função do arquivo de banco de dados
        if confirmar:
            # ATENÇÃO: Use 'db.excluir_licenca' (ou o nome do seu arquivo importado, ex: database.excluir_licenca)
            # CORRIGIDO: Passando 'id_cliente' que veio do parâmetro da função
            if db.excluir_licenca(int(id_cliente)):
                messagebox.showinfo("Sucesso", f"Cliente ID {id_cliente} excluído com sucesso!", parent=self)
                
                # Recarrega a tela para atualizar a listagem
                self.carregar_dados_clientes() 
            else:
                messagebox.showerror("Erro", "Não foi possível excluir do banco de dados.", parent=self)



if __name__ == "__main__":
    # 1. Configura a janela raiz principal necessária para o CustomTkinter funcionar
    root = ctk.CTk()
    root.withdraw()  # Oculta a janela principal vazia

    # 2. Instancia a sua classe de painel administrativo
    tela = TelaAdmin("admin")
    
    # 3. Garante que se o usuário fechar o painel, o processo inteiro do Python encerra
    tela.protocol("WM_DELETE_WINDOW", root.quit)

    # 4. Inicia o loop de eventos nativo do Tkinter
    root.mainloop()

