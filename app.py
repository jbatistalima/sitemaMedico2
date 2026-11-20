from tkinter import ttk
import customtkinter as ctk
import database as db
from tkinter import messagebox
import sqlite3, sys, os, backup, bcrypt
from datetime import datetime
from tkcalendar import DateEntry
from janela_pagamento import JanelaPagamento
import gerador_pdf as gp


def obter_caminho_recurso(caminho_relativo):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, caminho_relativo)


def obter_conexao():
    if getattr(sys, 'frozen', False):  
        db_path = os.path.join(os.path.dirname(sys.executable), "consultorio.db")
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, "consultorio.db")
    return sqlite3.connect(db_path)


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


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


def conectar():
    return sqlite3.connect("consultorio.db")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("  Sistema Médico - Painel de Controle  ")
        self.geometry("830x500+350+200")
        self.withdraw()  # Esconde a janela principal até o login ser bem-sucedido
        self.conteudo_frame = None
        self.nivel_logado = None
        self.usuario_logado = "Médico Não Identificado" # Padrão
        db.iniciar_banco()
        self.login_screen()
        self.id_consulta_selecionada = None
        # Configuração do Layout de Grid (1 linha, 2 colunas)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.efetuar_logout)
 

        style = ttk.Style()
        # Define a altura de cada linha para 30 pixels (o padrão costuma ser 20)
        style.configure("Custom.Treeview", fg_color="red",  font=('Arial', 10), rowheight=39)
        # Se quiser que o cabeçalho também mude:
        style.configure("Treeview.Heading", font=('Arial', 12, 'bold'))  
        # Adicione isso no seu __init__ para interceptar o clique no "X" da janela
    
    
    def fechar_sistema_completo(self):
        """Encerra o loop do tkinter e garante a liberação imediata do terminal."""
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass
        finally:
            # FORÇA BRUTA: Se o sys.exit() falhar por conta de threads/banco,
            # o comando abaixo mata o processo atual diretamente no gerenciador do Windows.
            os._exit(0) 


    def login_screen(self):
        if self.conteudo_frame:
            for widget in self.conteudo_frame.winfo_children():
                widget.destroy()
        self.janela_login = ctk.CTkToplevel(self)
        self.janela_login.title("Login")
        self.janela_login.geometry("350x300+600+300")
        self.janela_login.configure(fg_color="yellowgreen")
        self.janela_login.lift()
        self.janela_login.focus_force()
        self.janela_login.attributes("-topmost", True)
        self.janela_login.protocol("WM_DELETE_WINDOW", self.fechar_sistema_completo)
        self.frame_login = ctk.CTkFrame(self.janela_login)
        self.frame_login.place(relx=0.5, rely=0.5, relwidth=0.95, relheight=0.95, anchor="center")
        
        
        ctk.CTkLabel(self.frame_login, text="Entrar no Sistema", font=("Arial", 25, "bold")).place(relx=0.2, rely=0.05)
        
        self.user_in = ctk.CTkEntry(self.frame_login, width=200, placeholder_text="👤Usuário", justify="center")
        self.user_in.place(relx=0.25, rely=0.3)
        
        self.pass_in = ctk.CTkEntry(self.frame_login, width=200, placeholder_text="🔒Senha", show="*", justify="center")
        self.pass_in.place(relx=0.25, rely=0.55)
        
        ctk.CTkButton(self.frame_login, text="🚪 Entrar", command=self.auth).place(relx=0.33, rely=0.8)
        
        self.after(100, lambda: self.user_in.focus())


    def auth(self):
        usuario_digitado = self.user_in.get().strip()
        senha_digitada = self.pass_in.get().strip()
        
        # 1. AUTENTICAÇÃO PRIMÁRIA: Consulta o banco de dados para checar usuário e senha
        dados_usuario = db.verificar_login(usuario_digitado, senha_digitada)
        if not dados_usuario:
            messagebox.showerror("Erro de Acesso", "Usuário ou senha incorretos!", parent=self.janela_login)
            return
        # Recupera o e-mail cadastrado para este usuário específico
        email_usuario = dados_usuario["email"]

        # 2. VALIDAÇÃO INDIVIDUAL DE LICENÇA (VINCULADA AO EMAIL DO USUÁRIO)
        try:
            con = sqlite3.connect("consultorio.db")
            con.row_factory = sqlite3.Row
            cursor = con.cursor()
            
            # Busca a licença usando o e-mail do usuário que acabou de tentar logar
            cursor.execute("""
                SELECT nome_cliente, validade, status, token_seguranca 
                FROM clientes_licencas 
                WHERE email = ?
            """, (email_usuario,))
            
            licenca = cursor.fetchone()
            con.close()
            
            # Se não encontrar nenhuma licença para o e-mail deste usuário
            if not licenca:
                messagebox.showerror(
                    "Acesso Negado", 
                    f"O usuário '{dados_usuario['nome']}' não possui uma licença vinculada ao e-mail:\n{email_usuario}", 
                    parent=self.janela_login
                )
                return

            validade_str = str(licenca["validade"]).strip()
            token_salvo = str(licenca["token_seguranca"]).strip() if licenca["token_seguranca"] else ""
            nome_cliente = str(licenca["nome_cliente"]).strip()

            # A) TESTE ANTIFRAUDE BCRYPT DA LICENÇA
            if token_salvo:
                # Usa a função de validação global do topo do arquivo
                eh_valido = verificar_token_licenca(nome_cliente, validade_str, token_salvo)
                
                if not eh_valido:
                    messagebox.showerror(
                        "ERRO CRÍTICO", 
                        "Violação Detectada!\nA licença deste usuário foi alterada ilegalmente por fora do sistema.", 
                        parent=self.janela_login
                    )
                    return  # Bloqueia a entrada na hora

            # B) TESTE DE DATA DE EXPIRAÇÃO E STATUS
            validade_data = datetime.strptime(validade_str, "%Y-%m-%d").date()
            hoje = datetime.now().date()
            
            # CRIADO: Variável com a data formatada no padrão brasileiro (Ex: 25/06/2026)
            validade_br = validade_data.strftime("%d/%m/%Y")
            
            if licenca["status"] == "Bloqueado":
                messagebox.showerror("Licença Bloqueada", f"A licença vinculada ao e-mail {email_usuario} está bloqueada.", parent=self.janela_login)
                return
                
            if validade_data < hoje:
                # CORRIGIDO: Mudado de 'validade_str' para 'validade_br'
                messagebox.showerror("Licença Expirada", f"A licença de {dados_usuario['nome']} expirou em {validade_br}.\nPor favor, renove seu plano.", parent=self.janela_login)
                return
            
            # 2. AVISO PRÉVIO: Só avisa se estiver no intervalo entre 0 e 15 dias para vencer
            elif 0 <= (validade_data - hoje).days <= 15:
                # CORRIGIDO: Mudado de 'validade_data' para 'validade_br'
                messagebox.showinfo("Aviso de Vencimento", f"Sua Licença Vencerá em: ({validade_br}).\nEntre em Contato: jedceaij@outlook.com", parent=self.janela_login)

        except Exception as e:
            messagebox.showwarning("Erro de Integridade", f"Falha ao validar chaves de licença: {e}", parent=self.janela_login)
            return        

        # 3. SE PASSOU POR TUDO (SENHA + LICENÇA OK): Salva na sessão e libera o sistema
        self.usuario_logado = dados_usuario["usuario"]
        self.nome_completo = dados_usuario["nome"]
        self.nivel_logado = dados_usuario["nivel"]
        
        self.deiconify()
        self.mudar_tela(1)  
        self.update()
        
        # CORREÇÃO 2: Destrói o frame de login para liberar espaço no frame principal
        self.janela_login.destroy()

        messagebox.showinfo("Sucesso", f"Olá, {self.nome_completo}\nLicença válida até: {validade_br}", parent=self)
        self.focus_force()


        # 1. Criar o Menu Lateral
        self.menu_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.menu_frame.grid(row=0, column=0, sticky="nsew")
        self.menu_frame.grid_rowconfigure(10, weight=1) # Empurra o final se necessário
        
        # Título do Menu
        self.menu_title = ctk.CTkLabel(self.menu_frame, text="MENU", font=ctk.CTkFont(size=20, weight="bold"))
        self.menu_title.grid(row=0, column=0, padx=20, pady=20)

        nomes_telas = [
        "👤Cadastrar Pacientes",
        "📈 Relatório Financeiro",
        "📅 Agendar Consultas",
        "📝 Gerar Receitas",
        "💾 Backup",
        "🚪 Sair",
        "🌓Tema"
        ]
        if (self.nivel_logado).lower() == "admin":        
            nomes_telas.insert(8, "👤Cadastrar Usuários")
            nomes_telas.insert(9, "⚙️Administração") 
    
        # Criar os Botões do Menu
        for i, nome in enumerate(nomes_telas, start=1):
            # 1. Define o comando correto para cada tipo de botão
            if "Tema" in nome:
                comando_btn = self.alternar_tema
            elif "Backup" in nome:
                comando_btn = self.executar_backup  # Crie uma função para o backup, se tiver
            elif "⚙️Administração" in nome:
                comando_btn = self.abrir_painel 
            elif "🚪 Sair" in nome:
                comando_btn = self.sair     
            else:
                # Mantém a função lambda apenas para as telas normais
                comando_btn = lambda n=i: self.mudar_tela(n)

            # 2. Cria um ÚNICO botão usando o comando definido acima
            btn = ctk.CTkButton(
                self.menu_frame,
                text=nome,
                command=comando_btn
            )    
            
            # 3. Posiciona o botão na linha correspondente
            btn.grid(row=i, column=0, padx=20, pady=9, sticky="ew")

            
            # 3. Frame de Conteúdo (Onde as telas secundárias vão aparecer)
            self.conteudo_frame = None

            # Abrir a Tela 1 por padrão ao iniciar
            self.mudar_tela(1)


    def mudar_tela(self, numero_tela):

        # Se já existe uma tela aberta, destrói ela para limpar a memória e o espaço
        if self.conteudo_frame is not None:
            self.conteudo_frame.destroy()

        # Cria o novo container para a tela selecionada
        self.conteudo_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.conteudo_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=1)

        # Roteamento: Define o que carregar em cada tela
        if numero_tela == 1:
            self.criar_tela_1()
        elif numero_tela == 2:
            self.criar_tela_2()
        elif numero_tela == 3:
            self.criar_tela_3()
        elif numero_tela == 4:
            self.criar_tela_4()
        elif numero_tela == 5:
            self.criar_tela_5()
        elif numero_tela == 6:
            self.criar_tela_6()
        elif numero_tela == 7:
            self.criar_tela_7()
        elif numero_tela == 8:
            self.criar_tela_8()
        elif numero_tela == 9:
            self.criar_tela_9()    
        

    def atualizar_dados_dashboard(self):
        # 1. Pega os números novos no banco
        p_count, u_count, c_count = db.buscar_estatisticas()
        self.cb_pacientes.configure(values=self.obter_nomes_pacientes())
        
        # 2. Atualiza APENAS o texto, sem criar novos frames
        if hasattr(self, "lbl_pacientes_count") and self.lbl_pacientes_count.winfo_exists():
            self.lbl_pacientes_count.configure(text=f"Pacientes Totais: {p_count}")

        if hasattr(self, "lbl_usuarios_count") and self.lbl_usuarios_count.winfo_exists():
            self.lbl_usuarios_count.configure(text=f"Usuários Totais: {u_count}")

        if hasattr(self, "lbl_consultas_count") and self.lbl_consultas_count.winfo_exists():
            self.lbl_consultas_count.configure(text=f"Consultas Agendadas Para Hoje: {c_count}")

        # 3. Atualiza a tabela de pacientes na aba Cadastro
        self.atualizar_tabela_pacientes()
    

    
    def efetuar_logout(self):
        # 1. Pergunta se o usuário realmente deseja sair
        messagebox.showwarning("Sair", "Deseja realmente sair do sistema?", parent=self)
        if messagebox.askyesno("Backup", "Deseja fazer backup?", parent=self):
            backup.fazer_backup_sistema()
        # 2. Oculta a janela principal do sistema instantaneamente
        self.withdraw()
        
        # 3. Limpa as variáveis de sessão para que o próximo usuário não herde os privilégios
        self.usuario_logado = None
        self.nome_completo = None
        self.nivel_logado = None
        
        # 4. Destrói todos os elementos visuais do menu e do conteúdo para não acumular lixo na memória
        for widget in self.menu_frame.winfo_children():
            widget.destroy()
        for widget in self.conteudo_frame.winfo_children():
            widget.destroy()
            
        # 5. Chama a tela de login novamente (ela cuidará de se desenhar e dar o self.deiconify() quando pronta)
        self.login_screen()


    # --- DEFINIÇÃO DAS TELAS SECUNDÁRIAS ---
    def criar_tela_1(self):
        p_count, u_count, c_count = db.buscar_estatisticas()    
        self.lbl_cadastrar_paciente = ctk.CTkLabel(self.conteudo_frame, text="Cadastrar Novo Paciente ou Alterar Cadastrado", font=("Arial", 18, "bold"))
        self.lbl_cadastrar_paciente.place(relx=0.21, rely=0.001)
        
        self.lbl_pacientes_count = ctk.CTkLabel(self.conteudo_frame, text=f"Total de Pacientes Cadastrados: {p_count}", font=("Arial", 14, "bold"))
        self.lbl_pacientes_count.place(relx=0.3, rely=0.06) # O place vai expandir o lbl conforme o texto
                
        self.frame_paciente = ctk.CTkFrame(self.conteudo_frame, corner_radius=0, border_width=10, border_color="yellowgreen")
        self.frame_paciente.place(relx=0.01, rely=0.15, relwidth=0.99, relheight=0.85)
        
        
       
        # Seus campos de Entry e Label aqui (Nome, CPF, etc)        
        self.ent_nome = ctk.CTkEntry(self.frame_paciente, placeholder_text="Nome Completo")
        self.ent_nome.place(relx=0.25, rely=0.1, relwidth=0.42)
        
        self.ent_nasc = ctk.CTkEntry(self.frame_paciente, placeholder_text="Data nascimento")
        self.ent_nasc.place(relx=0.7, rely=0.1, relwidth=0.25)
        
        self.ent_cpf = ctk.CTkEntry(self.frame_paciente, placeholder_text="CPF")
        self.ent_cpf.place(relx=0.25, rely=0.28, relwidth=0.42)

        self.ent_rg = ctk.CTkEntry(self.frame_paciente, placeholder_text="RG")
        self.ent_rg.place(relx=0.7, rely=0.28, relwidth=0.25)
        
        self.ent_tel = ctk.CTkEntry(self.frame_paciente, placeholder_text="Telefone")
        self.ent_tel.place(relx=0.7, rely=0.48, relwidth=0.25)
        
        self.ent_endereco = ctk.CTkEntry(self.frame_paciente, placeholder_text="Endereço")
        self.ent_endereco.place(relx=0.25, rely=0.48, relwidth=0.42)

        self.btn_salvar = ctk.CTkButton(self.frame_paciente, text="💾 Salvar Paciente", fg_color="green", command=self.acao_salvar_paciente)
        self.btn_salvar.place(relx=0.03, rely=0.1, relwidth=0.21)
            
        self.btn_limpar = ctk.CTkButton(self.frame_paciente, text="🧹  Limpar", fg_color="goldenrod",  command=self.limpar_campos)
        self.btn_limpar.place(relx=0.03, rely=0.28, relwidth=0.21)

        self.btn_excluir = ctk.CTkButton(self.frame_paciente, text="🗑️  Excluir", fg_color="#922b21", command=self.btn_excluir_paciente)
        self.btn_excluir.place(relx=0.03, rely=0.48, relwidth=0.21)
                        
        # --- TABELA DE PACIENTES ---
        self.lbl_treeview_paciente = ctk.CTkLabel(self.frame_paciente, text="Pacientes Cadastrados(Dois Cliques Para Alterar)", font=("Arial", 14, "bold"))
        self.lbl_treeview_paciente.place(relx=0.25, rely=0.61) # O place vai expandir o lbl conforme o texto
        
        self.tree_p = ttk.Treeview(self.frame_paciente, columns=("ID", "Nome", "Nascimento", "CPF", "RG"),  show="headings", height=6, style="Custom.Treeview")
        self.tree_p.heading("ID", text="ID", anchor="w")
        self.tree_p.heading("Nome", text="NOME", anchor="w")
        self.tree_p.heading("Nascimento", text="NASCIMENTO", anchor="w")
        self.tree_p.heading("CPF", text="CPF", anchor="w") 
        self.tree_p.heading("RG", text="RG", anchor="w")

        self.tree_p.column("ID", width=25) 
        self.tree_p.column("Nome", width=250)
        self.tree_p.column("Nascimento", width=90)
        self.tree_p.column("CPF", width=65)
        self.tree_p.column("RG", width=65)
        self.tree_p.place(relx=0.02, rely=0.67, relwidth=0.94, relheight=0.3)

        # 3. Criar a Scrollbar (VINCULADA À TREEVIEW)
        scrollbar = ctk.CTkScrollbar(self.frame_paciente, fg_color="white", orientation="vertical", width=10, command=self.tree_p.yview)
        scrollbar.place(relx=0.96, rely=0.67, relheight=0.3)

        # 4. Configurar a Treeview para usar a Scrollbar
        self.tree_p.configure(yscrollcommand=scrollbar.set)
        self.tree_p.bind("<Double-1>", lambda e: self.btn_editar_paciente())

        self.atualizar_tabela_pacientes()
    
    def atualizar_tabela_pacientes(self):
        if hasattr(self, "tree_p") and self.tree_p.winfo_exists():
            for i in self.tree_p.get_children():
                self.tree_p.delete(i)
            for p, row in enumerate(db.buscar_lista_pacientes()):
                tag = "par" if p % 2 == 0 else "impar"
                self.tree_p.insert("", "end", values=row, tags=(tag,))
            self.tree_p.tag_configure("par", background="#777")
            self.tree_p.tag_configure("impar", background="#555")

    def btn_excluir_paciente(self):
        selecionado = self.tree_p.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um paciente na tabela!")
            return
        
        item = self.tree_p.item(selecionado)
        id_p = item['values'][0]
        nome_p = item['values'][1]

        if messagebox.askyesno("Confirmar", f"Deseja excluir o paciente {nome_p}?"):
            db.excluir_paciente(id_p)
            self.atualizar_tabela_pacientes()
            self.montar_interface_principal() # Atualiza o Dashboard


    def btn_editar_paciente(self):
        selecionado = self.tree_p.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um paciente!")
            return        
        
        item = self.tree_p.item(selecionado)
        dados = item['values']

        # 1. Limpa os campos antes de preencher
        self.limpar_campos() 

        # 2. GUARDA O ID (use o mesmo nome que usará na função salvar)
        self.id_paciente_edicao = dados[0] 

        # 3. Preenche os campos
        self.ent_nome.insert(0, dados[1])
        self.ent_nasc.insert(0, dados[2])
        self.ent_cpf.insert(0, dados[3])
        self.ent_rg.insert(0, dados[4])
        self.ent_tel.insert(0, dados[5]) 
        self.ent_endereco.insert(0, dados[6])

        # 4. Muda o botão para modo edição
        self.btn_salvar.configure(text="💾 Salvar Alterações", fg_color="#483D8B")


    def acao_salvar_paciente(self):
        # 1. CAPTURA os dados dos campos (Isso define as variáveis)
        nome = self.ent_nome.get().strip()
        nasc = self.ent_nasc.get().strip()  
        cpf  = self.ent_cpf.get().strip()   
        rg   = self.ent_rg.get().strip()
        tel  = self.ent_tel.get().strip()
        end  = self.ent_endereco.get().strip()

        if not nome:
            messagebox.showwarning("Aviso", "O nome é obrigatório!", parent=self.janela_paciente)
            return

        # MODO EDIÇÃO
        if hasattr(self, 'id_paciente_edicao') and self.id_paciente_edicao:
            if db.atualizar_paciente(self.id_paciente_edicao, nome, nasc, cpf, rg, tel, end):
                messagebox.showinfo("Sucesso", "Paciente atualizado!")
                self.limpar_campos() # Isso já volta o botão para verde e limpa o ID
            else:
                messagebox.showerror("Erro", "Falha ao atualizar no banco de dados.")
        
        # MODO NOVO CADASTRO
        else:
            if db.cadastrar_paciente(nome, nasc, cpf, rg, tel, end):
                messagebox.showinfo("Sucesso", "Paciente cadastrado!")
                self.limpar_campos()
            else:
                messagebox.showerror("Erro", "Falha Para Cadastrar! CPF ou RG Já Cadastrados.")

        self.atualizar_tabela_pacientes()


    def limpar_campos(self):
        self.ent_nome.delete(0, ctk.END) 
        self.ent_nasc.delete(0, ctk.END)
        self.ent_cpf.delete(0, ctk.END)
        self.ent_rg.delete(0, ctk.END)
        self.ent_tel.delete(0, ctk.END)
        self.ent_endereco.delete(0, ctk.END)
        self.id_paciente_edicao = None
        self.btn_salvar.configure(text="💾 Salvar Paciente", fg_color="green")
        

    def criar_tela_2(self):
        # Título Principal
        self.label = ctk.CTkLabel(self.conteudo_frame, text="📊 RELATÓRIO FINANCEIRO", font=("Arial", 22, "bold"))
        self.label.pack(pady=20)

        # Container para os Cards (Resumo)
        self.container_cards = ctk.CTkFrame(self.conteudo_frame, fg_color="transparent")
        self.container_cards.pack(fill="x", padx=10, pady=10)

        # Criar os Widgets de Card 
        self.card_total = self.criar_card(self.container_cards, "Faturamento Total", "R$ 0.00", "#e67e22")
        self.card_corrente_= self.criar_card(self.container_cards, "Faturamen Ano Atual", "R$ 0.00", "#2ecc71")
        self.card_mes = self.criar_card(self.container_cards, "Faturamento Mensal", "R$ 0.00", "#34aedb")
        self.card_pendente = self.criar_card(self.container_cards, "Consultas a Receber (Qtd)", "0", "#E72323")

        # Área de detalhes por Método (Lista)
        ctk.CTkLabel(self.conteudo_frame, text="Receita por Método de Pagamento", font=("Arial", 14, "bold")).pack(pady=(20, 5))
        self.frame_detalhes = ctk.CTkScrollableFrame(self.conteudo_frame, width=450, height=200)
        self.frame_detalhes.pack(pady=10, padx=10, fill="both", expand=True)

        # Carregar os dados reais
        self.atualizar_dados()


    def criar_card(self, master, titulo, valor, cor):
        card = ctk.CTkFrame(master, width=200, height=100, border_width=2, border_color=cor)
        card.pack(side="left", padx=10, expand=True, fill="both")
        
        lbl_titulo = ctk.CTkLabel(card, text=titulo, font=("Arial", 12))
        lbl_titulo.pack(pady=(10, 0))
        
        lbl_valor = ctk.CTkLabel(card, text=valor, font=("Arial", 20, "bold"), text_color=cor)
        lbl_valor.pack(pady=10)
        
        return lbl_valor # Retornamos o label para podermos atualizar o texto depois

    def atualizar_dados(self):
        conn = sqlite3.connect('consultorio.db')
        cursor = conn.cursor()

        # 1. TOTAL GERAL (Soma de todos os valores > 0)
        ano_atual = datetime.now().strftime('%Y')
        # O % antes garante que pegamos qualquer dia/mês, mas o ano deve ser o final
        cursor.execute("SELECT SUM(valor) FROM consultas WHERE data LIKE ? AND metodo_pagamento != 'Pendente'", (f'%{ano_atual}',))
        #cursor.execute("SELECT SUM(valor) FROM consultas WHERE valor > 0 AND metodo_pagamento != 'Pendente'")
        total_geral = cursor.fetchone()[0] or 0.0
        total_formatado = f"R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.card_corrente_.configure(text=total_formatado)

        # 1. TOTAL GERAL (Soma de todos os valores maio que 0 e diferente de Pendente)
        cursor.execute("SELECT SUM(valor) FROM consultas WHERE valor > 0 AND metodo_pagamento != 'Pendente'")
        total_geral = cursor.fetchone()[0] or 0.0
        total_formatado = f"R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.card_total.configure(text=total_formatado)
        
        
        # 2. FATURAMENTO MENSAL (Mês atual)
        mes_atual = datetime.now().strftime('%m/%Y') # Busca por string 'MM/AAAA'
        cursor.execute("SELECT SUM(valor) FROM consultas WHERE data LIKE ?", (f'%{mes_atual}%',))
        total_mes = cursor.fetchone()[0] or 0.0
        texto_mes_formatado = f"R$ {total_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self.card_mes.configure(text=texto_mes_formatado)

        # 3. QUANTIDADE PENDENTE (Consultas com valor 0)
        cursor.execute("SELECT COUNT(*) FROM consultas WHERE metodo_pagamento = 'Pendente'")
        pendentes = cursor.fetchone()[0] or 0
        self.card_pendente.configure(text=str(pendentes))

        # 4. DETALHES POR MÉTODO
        cursor.execute("SELECT metodo_pagamento, SUM(valor) FROM consultas WHERE valor > 0 GROUP BY metodo_pagamento")
        metodos = cursor.fetchall()
        
        for widget in self.frame_detalhes.winfo_children():
            widget.destroy()

        for m, valor in metodos:
            if valor > 0:
                linha = ctk.CTkFrame(self.frame_detalhes, fg_color="transparent")
                linha.pack(fill="x", pady=2)
                ctk.CTkLabel(linha, text=f"• {m}:", font=("Arial", 12)).pack(side="left")
                ctk.CTkLabel(linha, text=f"R$ {valor:,.2f}", font=("Arial", 12, "bold")).pack(side="right", padx=(0, 20))
            conn.close()


    def criar_tela_3(self):
        p_count, u_count, c_count = db.buscar_estatisticas() 
                
        self.frame_agenda = ctk.CTkFrame(self.conteudo_frame, corner_radius=0, border_width=10, border_color="yellowgreen")
        self.frame_agenda.place(relx=0.5, rely=0.15, anchor="n", relwidth=0.98, relheight=0.85)
       
        # Contador de consultas diárias
        if c_count > 0:
            self.lbl_consultas_count = ctk.CTkLabel(self.conteudo_frame, text=f"Consultas Agendadas Para Hoje: {c_count}", text_color="goldenrod", font=("Arial", 20, "bold"))
            self.lbl_consultas_count.place(relx=0.2, rely=0.1, anchor="w")
        lbl = ctk.CTkLabel(self.conteudo_frame, text="Agendar Alterar Receber Consulta", font=ctk.CTkFont(size=22))
        lbl.place(relx=0.2, rely=0.03, anchor="w")

        # Dentro de configurar_aba_agenda
        ctk.CTkLabel(self.frame_agenda, text="Paciente:", font=("Arial", 14, "bold")).place(relx=0.45, rely=0.05)
        lista_nomes = self.obter_nomes_pacientes()

        self.cb_pacientes = ctk.CTkComboBox(self.frame_agenda, values=lista_nomes, width=200)
        self.cb_pacientes.place(relx=0.557, rely=0.05, relwidth=0.28)

        ctk.CTkLabel(self.frame_agenda, text="Data:", font=("Arial", 14, "bold")).place(relx=0.45, rely=0.15)
        
        self.cal = DateEntry(self.frame_agenda, font=("Arial", 12), background="darkgreen", borderwidth=2, locale="pt_BR")
        self.cal.place(relx=0.556, rely=0.15, relwidth=0.28, relheight=0.06)

        ctk.CTkLabel(self.frame_agenda, text="Hora:", font=("Arial", 14, "bold")).place(relx=0.45, rely=0.25)
        self.combo_hora = ctk.CTkComboBox(self.frame_agenda,
        values=["08:00", "09:00", "10:00", "14:00", "15:00", "16:00", "17:00", "18:00"], width=115)
        self.combo_hora.place(relx=0.556, rely=0.25, relwidth=0.28)

        # --- NOVOS CAMPOS: Financeiro ---
        ctk.CTkLabel(self.frame_agenda, text="Custo:", font=("Arial", 14, "bold")).place(relx=0.45, rely=0.35)
        self.ent_valor = ctk.CTkEntry(self.frame_agenda, width=115, placeholder_text="Valor R$ (Ex: 150.00)")
        self.ent_valor.place(relx=0.556, rely=0.35, relwidth=0.28)
        
        # Campo de Método
        ctk.CTkLabel(self.frame_agenda, text="Método:", font=("Arial", 14, "bold")).place(relx=0.45, rely=0.45)
        self.combo_metodo = ctk.CTkOptionMenu(self.frame_agenda, values=["Convênio", "Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Pendente"], width=115, fg_color="gray50")
        self.combo_metodo.place(relx=0.556, rely=0.45, relwidth=0.28)        
        
        self.lbl_situacao = ctk.CTkLabel(self.frame_agenda, text="", font=("Arial", 14, "bold"))
        self.lbl_situacao.place(relx=0.45, rely=0.55)
        self.container_dinamico = ctk.CTkFrame(self.frame_agenda, width=100, height=30, fg_color="transparent", border_width=0)
        self.container_dinamico.place(relx=0.56, rely=0.555, relwidth=0.28, relheight=0.06)

        self.btn_agendar = ctk.CTkButton(self.frame_agenda, text="💾 Confirmar Agendamento", fg_color="#2ecc71", command=self.acao_agendar)
        self.btn_agendar.place(relx=0.1, rely=0.05, relwidth=0.24)
        
        self.btn_limpar = ctk.CTkButton(self.frame_agenda, text="🧹  Limpar", fg_color="goldenrod", command=self.limpar_campos_consulta)
        self.btn_limpar.place(relx=0.1, rely=0.25, relwidth=0.24)

        self.btn_excluir_consulta = ctk.CTkButton(self.frame_agenda, text="🗑️Excluir Selecionada", fg_color="#FF0000", 
        command=self.acao_excluir_consulta)
        self.btn_excluir_consulta.place(relx=0.1, rely=0.45, relwidth=0.24) 

        self.lbl_treeview_agenda = ctk.CTkLabel(self.frame_agenda, text="Consultas agendadas (Dois Cliques Para Alterar)")
        self.lbl_treeview_agenda.place(relx=0.3, rely=0.65, anchor="w")

        # Tabela de Consultas (Treeview)
        self.tree_agenda = ttk.Treeview(self.frame_agenda, height=8, columns=("Paciente", "Data", "Hora", "Valor", "Metodo"), show="headings", style="Custom.Treeview")
        self.tree_agenda.heading("Paciente", text="Paciente", anchor="w")
        self.tree_agenda.heading("Data", text="Data", anchor="w")
        self.tree_agenda.heading("Hora", text="Hora", anchor="w")
        self.tree_agenda.heading("Valor", text="Valor", anchor="w")
        self.tree_agenda.heading("Metodo", text="Método", anchor="w")
        #self.tree_agenda.heading("ID", text="ID", anchor="w")

        self.tree_agenda.column("Paciente", width=200)
        self.tree_agenda.column("Data", width=15)
        self.tree_agenda.column("Hora", width=15)
        self.tree_agenda.column("Valor", width=30)
        self.tree_agenda.column("Metodo", width=60)
        #self.tree_agenda.column("ID", width=10)

        self.tree_agenda.place(relx=0.02, rely=0.67, relwidth=0.93, relheight=0.3)

        # 3. Criar a Scrollbar (VINCULADA À TREEVIEW)
        scrollbar = ctk.CTkScrollbar(self.frame_agenda, fg_color="white", orientation="vertical", width=14, command=self.tree_agenda.yview)
        scrollbar.place(relx=0.95, rely=0.67, relheight=0.3)

        # 4. Configurar a Treeview para usar a Scrollbar
        self.tree_agenda.configure(yscrollcommand=scrollbar.set)

        self.tree_agenda.bind("<Double-1>", self.btn_carregar_consulta_para_editar)
        
        self.atualizar_tabela_agenda()


    def padrao_data(self, event):
        if event.keysym == "Backspace":
            return
        texto_atual = self.input_validade.get().replace("/", "")
        novo_texto = ""

        if len(texto_atual) > 8:
            texto_atual = texto_atual[:8]

        for i, caractere in enumerate(texto_atual):
            if i == 2 or i == 4:
                novo_texto += "/"
            novo_texto += caractere
        self.input.validade.delete(0, "end")
        self.input_validade.insert(0, novo_texto)            


    def acao_agendar(self):
        nome_sel = self.cb_pacientes.get()
        data_texto = self.cal.get()  # O que vem do DateEntry
        hora_sel = self.combo_hora.get()
        valor = self.ent_valor.get().replace(',', '.')
        metodo = self.combo_metodo.get()
        
        # --- 1. VALIDAÇÃO DE DATA RETROATIVA (OBRIGATÓRIA) ---
        try:
            # Converte para objeto de data para comparar
            data_hora_sel = datetime.strptime(f"{data_texto} {hora_sel}", "%d/%m/%Y %H:%M")
            #data_obj = datetime.strptime(data_texto, "%d/%m/%Y").date()
            #hoje = datetime.now().date()
            agora = datetime.now()
            #if data_obj < hoje:
            if data_hora_sel < agora:
                messagebox.showwarning("Data Inválida", f"A data: {data_texto} e a Hora: {hora_sel} já passaram!", parent=self.conteudo_frame)
                return # Para a execução aqui e não salva nada
        except Exception as e:
            messagebox.showerror("Erro", "Formato de data inválido!", parent=self.conteudo_frame)
            return

        # --- 2. VALIDAÇÃO DE PACIENTE ---
        if nome_sel not in self.dict_pacientes:
            messagebox.showwarning("Aviso", "Selecione um paciente cadastrado!", parent=self.conteudo_frame)
            return
            
        id_p = self.dict_pacientes[nome_sel]

        # --- 3. DECISÃO: EDITAR OU NOVO ---
        if self.id_consulta_selecionada:
            # MODO EDIÇÃO
            if db.atualizar_consulta(self.id_consulta_selecionada, data_texto, hora_sel, valor, metodo, id_p):
                messagebox.showinfo("Sucesso", "Consulta alterada com sucesso!", parent=self.conteudo_frame)
                self.id_consulta_selecionada = None # Reseta para o próximo ser "Novo"
                self.btn_agendar.configure(text="Confirmar Agendamento", fg_color="#2ecc71")
                self.limpar_campos_consulta()
            else:
                messagebox.showerror("Erro", "Falha ao atualizar consulta.", parent=self.conteudo_frame)
        else:
            # MODO NOVO AGENDAMENTO
            if db.agendar_consulta(id_p, data_texto, hora_sel, valor, metodo):
                messagebox.showinfo("Sucesso", "Consulta agendada!", parent=self.conteudo_frame)
            else:
                messagebox.showerror("Erro", "Falha ao agendar.", parent=self.conteudo_frame)

        # --- 4. FINALIZAÇÃO ---
        self.atualizar_tabela_agenda()
        self.atualizar_dados_dashboard()
    

    def limpar_campos_consulta(self):
        # 1. Reseta os campos da interface
        self.cb_pacientes.set("")         # Limpa o ComboBox de pacientes
        self.combo_hora.set("")           # Limpa o ComboBox de horas
        self.cal.set_date(datetime.now()) # Volta o calendário para hoje
        self.ent_valor.delete(0, "end")
        self.combo_metodo.set("")
        self.lbl_situacao.configure(text="")

        if hasattr(self, 'container_dinamico'):
            for widget in self.container_dinamico.winfo_children():
                widget.destroy()

            # 2. Reseta a lógica de edição
        self.id_consulta_selecionada = None
        
        # 3. Volta o botão para o estado original (Verde / Novo)
        self.btn_agendar.configure(text="Confirmar Agendamento", fg_color="#2ecc71", hover_color="#27ae60")
        
        # Desmarca qualquer linha selecionada na Treeview
        if self.tree_agenda is not None:
            for item in self.tree_agenda.selection():
                self.tree_agenda.selection_remove(item)


    def atualizar_tabela_agenda(self):
        # 1. Limpa a Treeview
        if self.tree_agenda is not None:
            for i in self.tree_agenda.get_children():
                self.tree_agenda.delete(i)
                
        # 2. Busca dados do banco
        dados = db.buscar_lista_consultas()

        for i, item in enumerate(dados):
            lista_item = list(item)
            
            try:
                valor_float = float(lista_item[3])
                lista_item[3] = f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except (ValueError, TypeError, IndexError):
                valor_float = 0.0
                lista_item[3] = "R$ 0,00"

            # # Se for admin, só mostra valores pendentes 0.00
            # if self.nivel_logado == "Admin" and valor_float != 0.0:
            #     continue

            # Define a cor alternada (zebra)
            tag = "par" if i % 2 == 0 else "impar"
            
            # Insere na Treeview
            if self.tree_agenda is not None:
                self.tree_agenda.insert("", "end", values=lista_item, tags=(tag,))

            # 3. Configura as cores das tags (fora do loop, apenas uma vez)
            if self.tree_agenda is not None:
                self.tree_agenda.tag_configure("par", background="#777")
                self.tree_agenda.tag_configure("impar", background="#555555")


            # Insere a lista já formatada na Treeview
            # self.tree_agenda.insert("", "end", values=lista_item)
            
            # 3. LIMPA O BOTÃO DA TELA (Importante!)
            # Se não limpar aqui, o botão "Pagar" continuará lá até você clicar em outra consulta
            if hasattr(self, 'container_dinamico'):
                for widget in self.container_dinamico.winfo_children():
                    widget.destroy()


    def abrir_pagamento(self, id_da_consulta):
        # 'self' é a sua classe principal, 'id_da_consulta' vem do botão
        # 'self.atualizar_tabela_agenda' é o callback que a janela vai disparar ao fechar
        JanelaPagamento(self, id_da_consulta, self.atualizar_tabela_agenda)


    def btn_carregar_consulta_para_editar(self, event=None):
        selecionado = self.tree_agenda.selection()
        if not selecionado:
            return
        
        item = self.tree_agenda.item(selecionado)
        dados = item['values'] 
        
        # 1. O ID da consulta agora está no índice 5 (último da lista)
        self.id_consulta_selecionada = dados[5] 
        self.btn_agendar.configure(text="💾Salvar Alterações", fg_color="#483D8B")
        # 2. Preenche os campos básicos:
        self.cb_pacientes.set(str(dados[0]))  # Nome
        self.combo_hora.set(str(dados[2]))    # Hora
        
        # 3. Preenche os NOVOS campos financeiros:
        self.ent_valor.delete(0, "end")
        self.ent_valor.insert(0, str(dados[3]))  # Valor (Índice 3)
        self.combo_metodo.set(str(dados[4]))     # Método (Índice 4)

        # 4. TRATAMENTO DA DATA
        try:
            data_str = str(dados[1])
            data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()
            self.cal.set_date(data_obj) 
        except Exception as e:
            print(f"Erro ao converter data: {e}")
            self.cal.set_date(str(dados[1]))

        # 2. LIMPA o container dinâmico para não acumular lixo
        for widget in self.container_dinamico.winfo_children():
            widget.destroy()

        # 3. Lógica do ADMIN para Pagar ou Pago
        try:
            # Pega o valor da coluna 3 (índice 3 do seu SELECT)
            valor_texto = str(dados[3]).replace("R$", "").strip()
            valor_limpo = valor_texto.replace("R$", "").replace(" ", "").replace(",", ".")
            valor_num = float(valor_limpo)
        except:
            valor_num = 0.0
        self.ent_valor.delete(0, "end")
        self.ent_valor.insert(0, f"{valor_num:.2f}") 

        if valor_num == 0.0:
            # Mostra botão PAGAR
            self.lbl_situacao.configure(text="Situação:")
            ctk.CTkButton(self.container_dinamico, text="💵 Pagar", fg_color="#2ecc71", width=90,
            command=lambda: self.abrir_pagamento(self.id_consulta_selecionada)).pack()                
        else:
            # Mostra texto PAGO
            self.lbl_situacao.configure(text="Situação:")
            ctk.CTkLabel(self.container_dinamico, text="✅ Pago", text_color="#2ecc71", font=("Arial", 14, "bold")).pack()             

 
    def acao_excluir_consulta(self):
        # 1. Verifica se algo foi selecionado na tabela da agenda
        selecionado = self.tree_agenda.selection()
        
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma consulta na tabela para excluir!")
            return

        # 2. Pega os dados da linha (O ID deve ser a primeira coluna oculta ou visível)
        # Importante: Se sua busca no banco retorna (Data, Hora, Nome), você precisa do ID.
        # Vamos ajustar a busca no database para trazer o ID também.
        item = self.tree_agenda.item(selecionado)
        dados = item['values'] 
        
        # Se você ajustou a busca para trazer o ID, ele estará em dados[0]
        if messagebox.askyesno("Confirmar", f"Deseja desmarcar a consulta?"):
            # Como as consultas costumam ser buscadas por Data/Hora/Nome, 
            # o ideal é buscar o ID no banco antes ou trazer o ID na Treeview.
            
            # Exemplo simples deletando pela Data e Hora (se não tiver ID na tela):
            # db.excluir_consulta_por_detalhes(dados[0], dados[1]) 
            
            # Se você usa ID (Recomendado):
            id_c = dados[5] 
            if db.excluir_consulta(id_c):
                messagebox.showinfo("Sucesso", "Consulta removida!")
                self.atualizar_tabela_agenda()
                self.atualizar_dados_dashboard()


    def obter_nomes_pacientes(self):
        pacientes = db.buscar_lista_pacientes()
        # Cria o dicionário: { "Nome do Paciente": ID_Numerico }
        self.dict_pacientes = {p[1]: p[0] for p in pacientes} 
        return list(self.dict_pacientes.keys())



    def criar_tela_4(self):
        p_count, u_count, c_count = db.buscar_estatisticas()
        lbl = ctk.CTkLabel(self.conteudo_frame, text="Selecione Paciente Para Gerar Receita", font=ctk.CTkFont(size=24))
        lbl.place(relx=0.5, rely=0.02, anchor="n")

        # --- CONTEÚDO DA ABA RECEITA ---
        self.frame_receita = ctk.CTkFrame(self.conteudo_frame, corner_radius=0, border_width=10, border_color="yellowgreen")
        self.frame_receita.place(relx=0.5, rely=0.15, anchor="n", relwidth=0.98, relheight=0.85)

        ctk.CTkLabel(self.frame_receita, text="Paciente:").place(relx=0.25, rely=0.1, anchor="w")
        lista_nomes = self.obter_nomes_pacientes()
        self.cb_paciente_receita = ctk.CTkComboBox(self.frame_receita, values=lista_nomes, width=300)
        self.cb_paciente_receita.place(relx=0.35, rely=0.1, relwidth=0.3, anchor="w")

        ctk.CTkLabel(self.frame_receita, text="Medicamentos e Posologia:").place(relx=0.25, rely=0.25, anchor="w")
        self.txt_prescricao = ctk.CTkTextbox(self.frame_receita, height=100)
        self.txt_prescricao.place(relx=0.25, rely=0.4, relwidth=0.6, anchor="w")
        
        btn_pdf = ctk.CTkButton(self.frame_receita, text="💊Gerar Receita PDF", fg_color="#5E0808", command=self.acao_gerar_pdf)
        btn_pdf.place(relx=0.35, rely=0.62, anchor="w", relwidth=0.3)

        # --- TABELA DE HISTÓRICO ---
        style = ttk.Style()
        # Define a altura de cada linha para 30 pixels (o padrão costuma ser 20)
        style.configure("Custom.Treeview", font=('Arial', 10), rowheight=48) 

        # Se quiser que o cabeçalho também mude:
        style.configure("Treeview.Heading", font=('Arial', 12, 'bold'))

        ctk.CTkLabel(self.frame_receita, text="Histórico de Receitas Anteriores (Dois cliques para carregar e editar medicamentos)", font=("Arial", 12, "bold")).place(relx=0.1, rely=0.71)

        self.tree_historico = ttk.Treeview(self.frame_receita, columns=("Data", "Médico", "Prescrição"), show="headings", style="Custom.Treeview")
        self.tree_historico.heading("Data", text="Data/Hora", anchor="w")
        self.tree_historico.heading("Médico", text="Médico", anchor="w")
        self.tree_historico.heading("Prescrição", text="Prescrição", anchor="w")

        # Ajuste das colunas
        self.tree_historico.column("Data", width=120)
        self.tree_historico.column("Médico", width=100)
        self.tree_historico.column("Prescrição", width=300)
        self.tree_historico.place(relx=0.02, rely=0.76, relwidth=0.94, relheight=0.2)
        
        # Criar scrollbar
        # 3. Criar a Scrollbar (VINCULADA À TREEVIEW)
        scrollbar = ctk.CTkScrollbar(self.frame_receita, fg_color="white", orientation="vertical", width=10, command=self.tree_historico.yview)
        scrollbar.place(relx=0.96, rely=0.76, relheight=0.199)

        # 4. Configurar a Treeview para usar a Scrollbar
        self.tree_historico.configure(yscrollcommand=scrollbar.set)

        # EVENTO: Quando mudar o paciente no ComboBox, atualiza a tabela
        self.cb_paciente_receita.configure(command=self.atualizar_tabela_historico)
        self.tree_historico.bind("<Double-1>", self.carregar_receita_antiga)

    
    def carregar_receita_antiga(self, event):
        # 1. Identifica qual linha da tabela de histórico foi clicada
        item_sel = self.tree_historico.selection()
        
        if item_sel:
            # 2. Pega os valores da linha. 
            # No nosso caso: índice 0=Data, 1=Médico, 2=Prescrição Completa
            valores = self.tree_historico.item(item_sel)['values']
            texto_historico = valores[2] # Pega o texto da prescrição

            # 3. Pergunta se o usuário quer carregar o texto
            if messagebox.askyesno("Copiar Histórico", "Deseja carregar esta prescrição antiga para editar?", parent=self.frame_receita):
                
                # 4. Limpa o campo de texto da prescrição (CTKTextbox)
                self.txt_prescricao.delete("1.0", "end")
                
                # 5. Insere o texto que veio do histórico
                self.txt_prescricao.insert("1.0", texto_historico)
                
                messagebox.showinfo("Sucesso", "Texto carregado! Agora você pode editá-lo.", parent=self.frame_receita)


    def acao_gerar_pdf(self):
        paciente_nome = self.cb_paciente_receita.get()
        texto = self.txt_prescricao.get("1.0", "end-1c")
        
        if not paciente_nome or not texto.strip():
            messagebox.showwarning("Aviso", "Selecione um paciente e preencha a prescrição!", parent=self.frame_receita)
            return        

        # 1. Recupera o ID do paciente pelo nome selecionado
        id_p = self.dict_pacientes.get(paciente_nome)

        if id_p:
            try:
                todos_pacientes = db.buscar_lista_pacientes()
                endereco = "Não informado"
                telefone = "Não informado"
                for p in todos_pacientes:
                    if p[0] == id_p:
                        telefone = p[5] # Índice 5 conforme seu SELECT
                        endereco = p[6] # Índice 6 conforme seu SELECT
                        break


                # 2. Gera o arquivo físico (PDF)
                arquivo = gp.gerar_receita_pdf(paciente_nome, endereco, telefone, texto, self.nome_completo.title())
                
                # 3. SALVA NO BANCO (Histórico)
                db.salvar_receita_historico(id_p, texto, self.usuario_logado)
                
                messagebox.showinfo("Sucesso", f"PDF gerado e salvo no histórico!\nArquivo: {arquivo}", parent=self.frame_receita)
                
                # Opcional: Limpar o campo de texto após gerar
                self.txt_prescricao.delete("1.0", "end")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Falha na operação: {e}", parent=self.frame_receita)
        else:
            messagebox.showerror("Erro", "Paciente não identificado no sistema.", parent=self.frame_receita)


    def atualizar_tabela_historico(self, escolha=None):
        # Limpa a tabela
        for i in self.tree_historico.get_children():
            self.tree_historico.delete(i)
        
        nome_sel = self.cb_paciente_receita.get()
        id_p = self.dict_pacientes.get(nome_sel)

        if id_p:
            historico = db.buscar_historico_por_paciente(id_p)
            for j, h in enumerate(historico):
                tag = "par" if j % 2 == 0 else "impar"
                # h[0]=Data, h[1]=Médico, h[2]=Prescrição Completa
                self.tree_historico.insert("", "end", values=(h[0], h[1], h[2]), tags=(tag,))
            self.tree_historico.tag_configure("par", background="#555")
            self.tree_historico.tag_configure("impar", background="#777")


    def executar_backup(self):
        backup.fazer_backup_sistema()  # Chama a função de backup do módulo backup.py


    def sair(self):
        self.efetuar_logout() 
    

    # Função para alternar entre temas
    def alternar_tema(self):
        # 1. Altera o modo visual (Sem mexer em frames ou labels)
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("dark")

    

    def criar_tela_8(self):
        lbl = ctk.CTkLabel(self.conteudo_frame, text="💾Cadastrar Usuário ou Editar Cadastrado", font=ctk.CTkFont(size=24))
        lbl.place(relx=0.5, rely=0.02, anchor="n")
        
        self.frame_user = ctk.CTkFrame(self.conteudo_frame, corner_radius=0, border_width=10, border_color="yellowgreen")
        self.frame_user.place(relx=0.001, rely=0.1, relwidth=0.99, relheight=0.9)
        
        self.ent_nome = ctk.CTkEntry(self.frame_user, placeholder_text="👤 Nome Completo")
        self.ent_nome.place(relx=0.23, rely=0.14, relwidth=0.7, anchor="w")

        self.ent_user = ctk.CTkEntry(self.frame_user, placeholder_text="👤Usuário")
        self.ent_user.place(relx=0.23, rely=0.22, relwidth=0.7, anchor="w")

        self.ent_pass = ctk.CTkEntry(self.frame_user, placeholder_text="🔒 Senha do usuário", show="*")
        self.ent_pass.place(relx=0.23, rely=0.3, relwidth=0.7, anchor="w")

        self.cb_nivel = ctk.CTkOptionMenu(self.frame_user, fg_color="#333", values=["Admin", "Médico"])
        self.cb_nivel.place(relx=0.23, rely=0.38, relwidth=0.7, anchor="w")
        
        self.lbl_email = ctk.CTkLabel(self.frame_user, text="Email:", font=("Arial", 16, "bold"))
        self.lbl_email.place(relx=0.05, rely=0.46, anchor="w")

        self.ent_email = ctk.CTkEntry(self.frame_user, placeholder_text="🔒 Email do usuário")
        self.ent_email.place(relx=0.23, rely=0.46, relwidth=0.7, anchor="w")
        
        # Botões: Salvar, Limpar, Excluir (Ações)
        self.btn_usuario = ctk.CTkButton(self.frame_user, text="💾 Salvar", fg_color="green", width=90, command=self.salvar)
        self.btn_usuario.place(relx=0.05, rely=0.14, anchor="w")

        self.btn_limpar = ctk.CTkButton(self.frame_user, text="🧹   Limpar", width=90, fg_color="goldenrod", command=self.limpar_campos_usuario)
        self.btn_limpar.place(relx=0.05, rely=0.3, anchor="w")

        self.btn_excluir = ctk.CTkButton(self.frame_user, text="🗑️  Excluir", fg_color="red", width=90, command=self.acao_excluir_usuario)
        self.btn_excluir.place(relx=0.05, rely=0.46, anchor="w")

        self.lbl_treeview_usuario = ctk.CTkLabel(self.frame_user, text="Usuários cadastrados(Dois Cliques Para Alterar)")
        self.lbl_treeview_usuario.place(relx=0.3, rely=0.65, anchor="w")

        # --- PASSO 3: A TREEVIEW (EMBAIXO DOS BOTÕES) ---
        # Como os botões já foram "empacotados" acima, a Treeview aparece abaixo deles
        self.tree_usuarios = ttk.Treeview(self.frame_user, columns=("nome", "usuario", "nivel", "email"), show="headings", style="Custom.Treeview")
        #self.tree_usuarios.heading("usuario_id", text="Usuário_Id", anchor="w")
        self.tree_usuarios.heading("nome", text="Nome", anchor="w")
        self.tree_usuarios.heading("usuario", text="Usuário", anchor="w")
        self.tree_usuarios.heading("nivel", text="Nível", anchor="w")
        self.tree_usuarios.heading("email", text="Email", anchor="w")

        # fill="both" e expand=True faz ela ocupar todo o resto da tela
        self.tree_usuarios.place(relx=0.02, rely=0.675, relwidth=0.96, relheight=0.3)

        # 3. Criar a Scrollbar (VINCULADA À TREEVIEW)
        # scrollbar = ctk.CTkScrollbar(self.frame_user, fg_color="white", orientation="vertical", width=15, command=self.tree_usuarios.yview)
        # scrollbar.place(relx=0.95, rely=0.675, relheight=0.3) # Ajuste de posição e altura

        # # 4. Configurar a Treeview para usar a Scrollbar
        # self.tree_usuarios.configure(yscrollcommand=scrollbar.set)

        self.tree_usuarios.bind("<Double-1>", lambda event: self.carregar_usuario_edicao())        
        
        self.atualizar_tabela_usuarios()


    def limpar_campos_usuario(self):
        # 1. Limpa os campos de texto usando o self
        self.ent_nome.delete(0, "end")
        self.ent_user.delete(0, "end")
        self.ent_pass.delete(0, "end")
        self.cb_nivel.set("medico") # Volta para o padrão
        self.ent_email.delete(0, "end")

        # 2. Reseta as variáveis de controle de edição
        self.usuario_antigo = None
        if hasattr(self, 'usuario_em_edicao'):
            self.usuario_em_edicao = None
        
        # 3. Volta o botão para o estado original (Azul ou Verde)
        self.btn_usuario.configure(text="💾Salvar", fg_color="green") # Cor padrão do seu sistema
        
        
        # 4. Desmarca a seleção na tabela
        for item in self.tree_usuarios.selection():
            self.tree_usuarios.selection_remove(item)


    def atualizar_tabela_usuarios(self):
        # Limpa a tabela
        for i in self.tree_usuarios.get_children():
            self.tree_usuarios.delete(i)
        
        # Busca usuários no banco (Crie essa função no db.py: SELECT usuario, nivel FROM usuarios)
        usuarios = db.listar_todos_usuarios()
        for user, row in enumerate(usuarios):
            tag = "par" if user % 2 == 0 else "impar"
            self.tree_usuarios.insert("", "end", values=row, tags=(tag,))
        self.tree_usuarios.tag_configure("par", background="#777")
        self.tree_usuarios.tag_configure("impar", background="#555")

    
    def acao_excluir_usuario(self):
        selecionado = self.tree_usuarios.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um usuário na tabela!")
            return

        item = self.tree_usuarios.item(selecionado)
        nome_user = item['values'][1] # Pega o nome da primeira coluna
        


        nome_user = self.tree_usuarios.item(selecionado)['values'][1]

        # Impede de excluir o próprio admin logado por segurança!
        if nome_user == self.usuario_logado:
            messagebox.showerror("Erro", "Você não pode excluir a si mesmo!")
            return

        if messagebox.askyesno("Confirmar", f"Excluir o usuário '{nome_user}'?"):
            if db.excluir_usuario(nome_user):
                messagebox.showinfo("Sucesso", "Usuário removido!")
                self.atualizar_tabela_usuarios()    
    

    def atualizar_tabela_historico(self, scolha=None):
        # Limpa a tabela
        for i in self.tree_historico.get_children():
            self.tree_historico.delete(i)
        
        nome_sel = self.cb_paciente_receita.get()
        id_p = self.dict_pacientes.get(nome_sel)

        if id_p:
            historico = db.buscar_historico_por_paciente(id_p)
            for j, h in enumerate(historico):
                tag = "par" if j % 2 == 0 else "impar"
                # h[0]=Data, h[1]=Médico, h[2]=Prescrição Completa
                self.tree_historico.insert("", "end", values=(h[0], h[1], h[2]), tags=(tag,))
            self.tree_historico.tag_configure("par", background="#555")
            self.tree_historico.tag_configure("impar", background="#777")

        
    def carregar_usuario_edicao(self):
        selecionado = self.tree_usuarios.selection()
        if not selecionado:
            return

        item = self.tree_usuarios.item(selecionado)
        dados = item['values'] # [Usuario, Nivel]

        # Limpa e preenche os campos lá de cima
        self.ent_nome.delete(0, "end")
        self.ent_nome.insert(0, str(dados[0]))

        self.ent_user.delete(0, "end")
        self.ent_user.insert(0, str(dados[1]))
        
        self.cb_nivel.set(str(dados[2]))

        self.ent_email.delete(0, "end")
        self.ent_email.insert(0, str(dados[3]))
        
        self.usuario_em_edicao = dados[0] 
        
        # Muda o texto do botão para indicar edição
        self.btn_usuario.configure(text="Atualizar", fg_color="#483D8B")
        
        # Guarda o nome original para o WHERE do SQL (caso o admin queira mudar o nome)
        self.usuario_antigo = dados[1]


    def salvar(self):
        m = self.ent_nome.get().strip()
        u = self.ent_user.get().strip()
        s = self.ent_pass.get().strip()
        n = self.cb_nivel.get()
        e = self.ent_email.get().strip()

        
        if not u:
            messagebox.showwarning("Aviso", "O nome de usuário é obrigatório!", parent=self.janela)
            return

        # Se existe 'self.usuario_antigo', estamos EDITANDO
        if hasattr(self, 'usuario_antigo') and self.usuario_antigo:
            if db.atualizar_usuario(self.usuario_antigo, m, u, s, n, e): # Crie essa no db.py
                messagebox.showinfo("Sucesso", "Usuário atualizado!", parent=self.conteudo_frame)
                self.usuario_antigo = None
                self.btn_usuario.configure(text="💾Alterar Usuário", fg_color="#1f6aa5")
            else:
                messagebox.showerror("Erro", "Falha ao atualizar.", parent=self.conteudo_frame)
        else:
            # MODO CRIAÇÃO (Seu código original)
            if db.cadastrar_usuario(m, u, s, n, e):
                messagebox.showinfo("Sucesso", "Usuário criado!", parent=self.conteudo_frame)
            else:
                messagebox.showerror("Erro", "Usuário já existe!", parent=self.conteudo_frame)

        self.atualizar_tabela_usuarios()        

        self.ent_nome.delete(0, 'end')
        self.ent_user.delete(0, 'end')        
        self.ent_pass.delete(0, 'end')
        self.cb_nivel.set('Médico')
        self.ent_email.delete(0, 'end')


    def abrir_painel(self):         
        # 3. Importa e abre a janela externa de forma totalmente isolada de memória
        from painel_admin import TelaAdmin
        
        nivel_atual = getattr(self, "nivel_logado", "admin")
        
        # Executa a chamada da janela separada sem risco de travar a tela principal
        self.janela_admin = TelaAdmin(nivel_usuario=nivel_atual)

        #CORREÇÃO: Verifica se a janela realmente existe (evita erro se o login falhar e der .destroy())
        if self.janela_admin.winfo_exists():
            # Agenda os comandos de foco para 100 milissegundos após a criação
            # Isso dá tempo para o Tkinter registrar o caminho ".!telaadmin2" com sucesso
            self.after(100, lambda: self.garantir_foco_janela())

    def garantir_foco_janela(self):
        """Função auxiliar segura para puxar o painel para a frente sem travar o app"""
        try:
            if hasattr(self, 'janela_admin') and self.janela_admin.winfo_exists():
                self.janela_admin.lift()
                self.janela_admin.focus_force()
                self.janela_admin.grab_set()  # Prende o mouse/teclado nela até fechar
        except Exception:
            pass  # Ignora caso a janela tenha sido fechada muito rápido pelo usuário

            
if __name__ == "__main__":
    app = App()
    app.mainloop()

# nomes_telas = [
#         "👤Cadastrar Pacientes",
#         "📈 Relatório Financeiro",
#         "📅 Agendar Consultas",
#         "📝 Gerar Receitas",
#         "💾 Backup",
#         "🚪 Sair",
#         "👤Cadastrar Usuários",
#         "⚙️Administração"        
#     ]