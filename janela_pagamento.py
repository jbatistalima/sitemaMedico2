import customtkinter as ctk


class JanelaPagamento(ctk.CTkToplevel):
    def __init__(self, master, consulta_id, callback_atualizar, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Finalizar Pagamento")
        self.geometry("400x600+1420+1")
        self.attributes("-topmost", True) 

        
        self.consulta_id = consulta_id
        self.callback_atualizar = callback_atualizar

        # --- Widgets ---
        ctk.CTkLabel(self, text="💰 Registrar Pagamento", font=("Arial", 20, "bold")).pack(pady=30)

        ctk.CTkLabel(self, text="Valor da Consulta (R$):").pack(pady=(45, 0))
        self.entry_valor = ctk.CTkEntry(self, placeholder_text="Ex: 150.00")
        self.entry_valor.pack(pady=3)

        ctk.CTkLabel(self, text="Forma de Pagamento:").pack(pady=(90, 0))
        self.combo_metodo = ctk.CTkOptionMenu(self, values=["Convênio", "Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Pendente"])
        self.combo_metodo.pack(pady=3)

        # Botão Confirmar
        self.btn_confirmar = ctk.CTkButton(self, text="✅ Confirmar Pagamento", fg_color="#2ecc71", hover_color="#27ae60",
        command=self.salvar_pagamento)
        self.btn_confirmar.pack(pady=95)

        self.wait_visibility()
        self.grab_set() # Faz a janela ficar na frente e bloqueia a principal


    def salvar_pagamento(self):
        valor_raw = self.entry_valor.get()
        metodo = self.combo_metodo.get()
        valor_formatado = float(valor_raw.replace(",", "."))

        if not valor_raw:
            print("Erro: Insira um valor") # Substitua por um CTkMessagebox se tiver
            return

        # 2. Lógica de Banco de Dados
        import sqlite3
        conn = sqlite3.connect('consultorio.db')
        cursor = conn.cursor()
        
        # Atualiza a consulta com o valor e marca como finalizada (se tiver status)
        cursor.execute("""
            UPDATE consultas 
            SET valor = ?, metodo_pagamento = ? 
            WHERE id = ?
        """, (float(valor_formatado), metodo, self.consulta_id))
        
        conn.commit()
        conn.close()
        
        self.callback_atualizar() # Avisa a tela anterior para atualizar a lista
        self.destroy() # Fecha a janela

      