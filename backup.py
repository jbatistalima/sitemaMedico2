import os
import shutil
from datetime import datetime
from tkinter import messagebox

def fazer_backup_sistema(): # Removi o self
    try:
        if not os.path.exists("backups"):
            os.makedirs("backups")

        data_hora = datetime.now().strftime("%d%m%Y%H%M%S")
        nome_backup = f"backups/backup_medico_{data_hora}.db"

        # Verifique se o nome do banco está igual ao que você criou no database.py
        if messagebox.askyesno("Backup", "Gerar Cópia de segurança?"):
            shutil.copy2("consultorio.db", nome_backup)
            messagebox.showinfo("Backup", f"Cópia de segurança criada com sucesso!\nSalvo em: {nome_backup}")
    except Exception as e:
        messagebox.showerror("Erro de Backup", f"Erro: {e}")
