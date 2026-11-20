import sys
import os
import sqlite3
import bcrypt  # <-- SUBSTITUI O HASHLIB
from datetime import datetime
import customtkinter as ctk

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class LicencaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Validação de Licença (SQLite + Bcrypt)")
        self.geometry("350x250")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)

        # Campo de email
        self.email_input = ctk.CTkEntry(self, placeholder_text="Digite seu email", width=280, font=("Arial", 14))
        self.email_input.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        # Resultado
        self.resultado = ctk.CTkLabel(self, text="Status da licença aparecerá aqui", font=("Arial", 14), wraplength=300)
        self.resultado.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Botão de verificação
        self.botao = ctk.CTkButton(
            self, text="Verificar Licença", width=150, font=("Arial", 14, "bold"),
            fg_color="#4CAF50", hover_color="#45a049", text_color="white", command=self.verificar
        )
        self.botao.grid(row=2, column=0, padx=20, pady=20)
    
    # 1. NOVA FUNÇÃO DE VALIDAÇÃO (Substitui a geração antiga)
    def validar_token_bcrypt(self, nome_cliente, data_validade, token_salvo_str):
        # ATENÇÃO: Esta chave deve ser IDENTICA à chave usada no seu admin.py
        CHAVE_SECRETA = "MinhaChaveSuperSecreta123456" 
        texto_combinado = f"{nome_cliente}-{data_validade}-{CHAVE_SECRETA}"
        
        # Converte o texto combinado e o token salvo do banco para bytes (exigência do bcrypt)
        texto_bytes = texto_combinado.encode('utf-8')
        token_salvo_bytes = token_salvo_str.encode('utf-8')
        
        # O bcrypt verifica internamente se o texto corresponde ao hash armazenado
        return bcrypt.checkpw(texto_bytes, token_salvo_bytes)

    def verificar(self):
        email = self.email_input.get()
        try:
            if getattr(sys, 'frozen', False):
                db_path = os.path.join(os.path.dirname(sys.executable), "consultorio.db")
            else:
                db_path = "consultorio.db"

            con = sqlite3.connect(db_path)
            con.row_factory = sqlite3.Row
            cursor = con.cursor()
            
            cursor.execute("SELECT nome_cliente, validade, status, token_seguranca FROM clientes_licencas WHERE email=?", (email,))
            cliente = cursor.fetchone()
            con.close()

            if cliente:
                validade_str = str(cliente["validade"]).strip()
                token_salvo = str(cliente["token_seguranca"]).strip() if cliente["token_seguranca"] else ""
                nome_cliente = str(cliente["nome_cliente"]).strip()

                # 2. ANTIFRAUDE COM BCRYPT
                if token_salvo:
                    # Chame a função passando o token vindo do banco para validação
                    eh_valido = self.validar_token_bcrypt(nome_cliente, validade_str, token_salvo)
                    
                    if not eh_valido:
                        self.resultado.configure(
                            text="VIOLAÇÃO DETECTADA!\nBanco alterado ilegalmente.",
                            text_color="red"
                        )
                        return  # Bloqueia o acesso imediatamente

                # 3. CHECAGEM PADRÃO DE DATA
                validade = datetime.strptime(validade_str, "%Y-%m-%d").date()
                hoje = datetime.now().date()
                validade_br = validade.strftime("%d/%m/%Y")

                if cliente["status"] != "Ativo" or validade < hoje:
                    self.resultado.configure(text=f"Licença expirada em {validade_br}", text_color="red")
                else:
                    self.resultado.configure(text=f"Licença válida até {validade_br}", text_color="#4CAF50")
            else:
                self.resultado.configure(text="Cliente não encontrado", text_color="gray")
        except Exception as e:
            self.resultado.configure(text=f"Erro: {e}", text_color="red")


if __name__ == "__main__":
    janela = LicencaApp()
    janela.mainloop()
