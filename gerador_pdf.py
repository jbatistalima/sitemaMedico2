from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime
import os


def gerar_receita_pdf(nome_paciente, endereco_paciente, telefone_paciente, texto_receita, medico_responsavel):
    pasta_receitas = "Receitas"
    if not os.path.exists(pasta_receitas):
        os.makedirs(pasta_receitas)
    data_atual = datetime.now().strftime("%d-%m-%Y")
    nome_limpo = nome_paciente.replace(' ', '_')
    nome_arquivo = f"receita_{nome_limpo}_{data_atual}.pdf"
    caminho_final = os.path.join(pasta_receitas, nome_arquivo)

    c = canvas.Canvas(caminho_final, pagesize=A4)
    largura, altura = A4

    # --- LOGOMARCA ---
    # Coloca o logo no canto superior esquerdo (x, y, largura, altura)
    # Certifique-se de que o arquivo 'logo.png' esteja na mesma pasta
    try:
        c.drawImage("logo.png", 2*cm, altura - 3.5*cm, width=3*cm, height=3*cm, mask='auto')
    except:
        pass # Se não achar a imagem, ele pula e não trava o sistema
 

    # --- CABEÇALHO ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*cm + 1*cm, altura - 4.5*cm, "CLÍNICA MÉDICA ESPECIALIDADES")
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(largura/2, altura - 5*cm, "Rua Exemplo, 123 - Centro | Tel: (11) 9999-9999")
    c.line(1*cm, altura - 5.5*cm, largura - 1*cm, altura - 5.5*cm)

    # --- DADOS DO PACIENTE ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, altura - 6.5*cm, f"PACIENTE:")
    c.setFont("Helvetica", 12)
    c.drawString(4.7*cm, altura - 6.5*cm, f"{nome_paciente}") 

    # --- Endereço do Paciente ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, altura - 7*cm, f"ENDEREÇO:")
    c.setFont("Helvetica", 12)
    c.drawString(4.7*cm, altura - 7*cm, f"{endereco_paciente}")

    # --- Endereço do Paciente ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, altura - 7.5*cm, f"TELEFONE:")
    c.setFont("Helvetica", 12)
    c.drawString(4.7*cm, altura - 7.5*cm, f"{telefone_paciente}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, altura - 8*cm, f"DATA:")
    c.setFont("Helvetica", 12)
    c.drawString(4.7*cm, altura - 8*cm, f"{datetime.now().strftime('%d/%m/%Y')}")

    # --- CORPO DA RECEITA (PRESCRICAO) ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, altura - 11.5*cm, "PRESCRICAO MÉDICA:")
    
    # Texto da Receita (Medicamentos)
    textobject = c.beginText(2*cm, altura - 12.5*cm)
    textobject.setFont("Helvetica", 12)
    textobject.setLeading(18) # Espaçamento entre linhas
    
    # Divide o texto por linhas caso seja longo
    for linha in texto_receita.split('\n'):
        textobject.textLine(linha)
    
    c.drawText(textobject)

    # --- RODAPÉ / ASSINATURA ---
    c.drawCentredString(largura/2, 5*cm, f"Médico responsável: Dr(a). {medico_responsavel}")
    c.drawCentredString(largura/2, 4.5*cm, "CRM: 123456-SP")
    c.line(largura/2 - 5*cm, 3.5*cm, largura/2 + 5*cm, 3.5*cm)
    c.drawCentredString(largura/2, 3*cm, "Assinatura")

    c.save()
    return nome_arquivo
