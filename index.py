import sys
import os
import json
import requests
import subprocess
import urllib.request
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QDateEdit, QPushButton,
    QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QAbstractItemView, QFileDialog
)
from PyQt6.QtCore import Qt, QDate, QRegularExpression, QSize
from PyQt6.QtGui import QRegularExpressionValidator, QIcon, QPixmap
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PilImage

CURRENT_VERSION = "v1.5"

CONFIG_FILE = os.path.expanduser("~/.orcamento_config.json")
LOGO_PNG_PATH = os.path.join(os.path.abspath("."), "logo.png")
LOGO_ICO_PATH = os.path.join(os.path.abspath("."), "logo.ico")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    caminho_fonte = resource_path(os.path.join("font", "IntroRust.ttf"))
    if os.path.isfile(caminho_fonte):
        pdfmetrics.registerFont(TTFont('IntroRust', caminho_fonte))
except Exception:
    pass

def load_config():
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Validação mínima
                if "pdf_save_folder" in config and os.path.isdir(config["pdf_save_folder"]):
                    return config
        except Exception:
            pass
    # Retorna padrão
    return {
        "titulo": "Delicatessen trigo de ouro",
        "texto1": "(79) 3015-0626 | (79) 99820-3756 | (79) 99978-0044 | @trigodeouro_",
        "texto2": "Rua Elísio Matos, 235 Estância/SE",
        "texto3": "CNPJ: 266588290001-70",
        "pdf_save_folder": os.path.expanduser("~")
    }

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"Configurações salvas: {config}")
    except Exception as e:
        print(f"Erro ao salvar configurações: {e}")

def formatar_valor(valor):
    return f"{valor:,.2f}".replace(".", ",")

def gerar_orcamento_pdf(nome_arquivo, items, cliente_info, config):
    nome, endereco, numero, data = cliente_info

    pdf = SimpleDocTemplate(nome_arquivo, pagesize=A4)
    elementos = []
    estilos_base = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        'Titulo',
        parent=estilos_base['Normal'],
        fontSize=16,
        leading=18,
        alignment=TA_LEFT,
        spaceAfter=4,
        fontName='IntroRust',
    )
    estilo_texto = ParagraphStyle(
        'Texto',
        parent=estilos_base['Normal'],
        fontSize=12,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=2,
    )
    estilo_descricao = ParagraphStyle(
        'Descricao',
        parent=estilos_base['Normal'],
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=0,
        spaceBefore=0,
    )
    estilo_total_valor = ParagraphStyle(
        'TotalValor',
        parent=estilos_base['Normal'],
        fontSize=12,
        leading=14,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        textColor=colors.black,
    )
    estilo_total_texto = ParagraphStyle(
        'TotalTexto',
        parent=estilos_base['Normal'],
        fontSize=12,
        leading=14,
        alignment=TA_RIGHT,
        fontName='Helvetica-Bold',
        textColor=colors.black,
    )

    texto = [
        Paragraph(config.get("titulo", "Delicatessen trigo de ouro"), estilo_titulo),
        Paragraph(config.get("texto1", ""), estilo_texto),
        Paragraph(config.get("texto2", ""), estilo_texto),
        Paragraph(config.get("texto3", ""), estilo_texto),
    ]

    caminho_logo = LOGO_PNG_PATH if os.path.isfile(LOGO_PNG_PATH) else resource_path(os.path.join("img", "logo.png"))
    if os.path.isfile(caminho_logo):
        imagem_logo = Image(caminho_logo)
        largura_desejada = 80
        proporcao = imagem_logo.imageHeight / imagem_logo.imageWidth
        altura_desejada = largura_desejada * proporcao
        imagem_logo._restrictSize(largura_desejada, altura_desejada)
    else:
        imagem_logo = None

    if imagem_logo:
        tabela_cabecalho = Table(
            [[texto, imagem_logo]],
            colWidths=[400, 80]
        )
        tabela_cabecalho.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (0, 0), 10),
            ('RIGHTPADDING', (0, 0), (0, 0), 10),
            ('TOPPADDING', (0, 0), (0, 0), 6),
            ('TOPPADDING', (1, 0), (1, 0), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elementos.append(tabela_cabecalho)
    else:
        for p in texto:
            elementos.append(p)

    elementos.append(Spacer(1, 10))

    def linha_ou_texto(label, texto_usuario, linha_tamanho=64):
        if texto_usuario:
            restante = linha_tamanho - len(texto_usuario)
            return f"{label} <u>{texto_usuario}</u>" + f"<u>{'_' * restante}</u>"
        else:
            return f"{label} <u>{'_' * linha_tamanho}</u>"

    nome_linha = linha_ou_texto("Nome:", nome)
    endereco_linha = linha_ou_texto("Endereço:", endereco, 51)
    numero_linha = linha_ou_texto("Nº", numero, 6)
    data_linha = linha_ou_texto("Data:", data)

    texto_quadro_html = f"""
    {nome_linha}<br/>
    {endereco_linha} {numero_linha}<br/>
    {data_linha}
    """

    estilo_quadro = ParagraphStyle(
        'Quadro',
        fontSize=12,
        leading=16,
        alignment=TA_LEFT,
        spaceAfter=10,
    )
    paragrafo_quadro = Paragraph(texto_quadro_html, estilo_quadro)

    tabela_quadro = Table([[paragrafo_quadro]], colWidths=[480])
    tabela_quadro.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#ededed")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0, colors.white),
        ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
    ]))

    elementos.append(tabela_quadro)
    elementos.append(Spacer(1, 20))

    cor_cabecalho = HexColor("#ededed")
    cor_linhas = colors.white
    estilo_tabela = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), cor_cabecalho),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Unid
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Desc centralizado
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Valor Unid
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Total
        ('ALIGN', (2, 0), (3, 0), 'CENTER'),  # Cabeçalho Valor Unid e Total centralizados
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), cor_linhas),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])

    max_linhas_por_tabela = 15
    total_itens = len(items)

    for start in range(0, total_itens, max_linhas_por_tabela):
        if start > 0:
            elementos.append(PageBreak())

        dados = [["Unid.", "DESCRIÇÃO DOS SERVIÇOS", "Valor Unid (R$)", "Total (R$)"]]
        slice_itens = items[start:start + max_linhas_por_tabela]

        for unid_str, desc, valor_unid_str, total in slice_itens:
            p_desc = Paragraph(desc, estilo_descricao)
            dados.append([
                str(unid_str),
                p_desc,
                formatar_valor(float(valor_unid_str)),
                formatar_valor(total)
            ])

        linhas_faltando = max_linhas_por_tabela - len(slice_itens)
        for _ in range(linhas_faltando):
            dados.append(["", "", "", ""])

        tabela = Table(dados, colWidths=[50, 230, 100, 100])  # largura total 480
        tabela.setStyle(estilo_tabela)
        elementos.append(tabela)
        elementos.append(Spacer(1, 10))

    soma_total = sum(total for _, _, _, total in items)

    texto_total_label = Paragraph("Total:", estilo_total_texto)
    texto_total_valor = Paragraph(f"R$ {formatar_valor(soma_total)}", estilo_total_valor)

    tabela_total = Table(
        [[texto_total_label, texto_total_valor]],
        colWidths=[400, 80]
    )
    tabela_total.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (1, 0), HexColor("#ededed")),
        ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0, colors.white),
        ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
    ]))

    elementos.append(Spacer(1, 20))
    elementos.append(tabela_total)

    pdf.build(elementos)
    print(f"PDF '{nome_arquivo}' gerado com sucesso.")


def get_latest_release_info():
    # Troque SEU_USUARIO e SEU_REPOSITORIO abaixo
    url = "https://api.github.com/repos/cauanlbp/ProjetoOrcamento/releases/latest"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            tag_name = data["tag_name"]
            assets = data["assets"]
            for asset in assets:
                if asset["name"].endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    return tag_name, download_url
    except Exception as e:
        print(f"Erro ao buscar release: {e}")
    return None, None


def check_update_and_apply():
    latest_version, installer_url = get_latest_release_info()
    if latest_version and latest_version > CURRENT_VERSION:
        print(f"Nova versão disponível: {latest_version}")

        installer_path = os.path.join(os.path.expanduser("~"), "setup_update.exe")

        try:
            print("Baixando instalador da atualização...")
            urllib.request.urlretrieve(installer_url, installer_path)
        except Exception as e:
            print(f"Erro ao baixar o instalador: {e}")
            return

        try:
            print("Executando instalador...")
            subprocess.Popen([installer_path, "/VERYSILENT", "/NORESTART"])
        except Exception as e:
            print(f"Erro ao executar instalador: {e}")
            return

        print("Atualização iniciada. Fechando o programa para atualizar.")
        sys.exit()


class BudgetGenerator(QWidget):
    def __init__(self):
        super().__init__()

        self.config = load_config()

        self.setWindowTitle("Gerador de Orçamentos")
        self.services = []
        self.pdf_save_folder = self.config.get("pdf_save_folder", os.path.expanduser("~"))

        self.init_ui()
        self.update_app_icon()

    def update_app_icon(self):
        if os.path.isfile(LOGO_ICO_PATH):
            self.setWindowIcon(QIcon(LOGO_ICO_PATH))

    def center(self):
        frame_geom = self.frameGeometry()
        screen = QApplication.primaryScreen()
        screen_center = screen.availableGeometry().center()
        frame_geom.moveCenter(screen_center)
        self.move(frame_geom.topLeft())

    def create_gear_icon(self):
        svg_data = b"""
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" >
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.09a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
        """
        pixmap = QPixmap()
        pixmap.loadFromData(svg_data, "SVG")
        return QIcon(pixmap)

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Navbar estreita
        self.navbar_widget = QWidget()
        self.navbar_widget.setFixedWidth(100)  # largura menor
        self.navbar_widget.setStyleSheet("background-color: #1e293b;")

        self.navbar_layout = QVBoxLayout(self.navbar_widget)
        self.navbar_layout.setContentsMargins(10, 10, 10, 10)
        self.navbar_layout.setSpacing(20)

        # Logo menor
        self.logo_label = QLabel()
        if os.path.isfile(LOGO_PNG_PATH):
            pixmap = QPixmap(LOGO_PNG_PATH).scaledToWidth(70, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.navbar_layout.addWidget(self.logo_label)

        # Botão ícone dólar
        self.btn_orcamentos = QPushButton()
        self.btn_orcamentos.setText("$")
        self.btn_orcamentos.setIconSize(QSize(32, 32))
        self.btn_orcamentos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_orcamentos.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: transparent;
                border: none;
                font-size: 32px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #475569;
            }
        """)

        # Botão engrenagem SVG para configuração
        self.btn_config = QPushButton()
        self.btn_config.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_config.setIcon(self.create_gear_icon())
        self.btn_config.setIconSize(QSize(32, 32))
        self.btn_config.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #475569;
            }
        """)

        self.navbar_layout.addWidget(self.btn_orcamentos)
        self.navbar_layout.addWidget(self.btn_config)
        self.navbar_layout.addStretch()

        # Conteúdo principal com duas "telas": orçamento e configurações
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(20, 20, 20, 20)

        self.init_orcamento_ui()
        self.init_config_ui()

        self.content_layout.addWidget(self.orcamento_widget)
        self.content_layout.addWidget(self.config_widget)

        self.config_widget.hide()

        main_layout.addWidget(self.navbar_widget)
        main_layout.addWidget(self.content_widget)

        self.setLayout(main_layout)
        self.resize(1100, 700)
        self.center()

        self.btn_orcamentos.clicked.connect(self.show_orcamento)
        self.btn_config.clicked.connect(self.show_config)

    def init_orcamento_ui(self):
        self.orcamento_widget = QWidget()
        orcamento_layout = QVBoxLayout(self.orcamento_widget)
        orcamento_layout.setSpacing(20)

        header_label = QLabel("Gerador de Orçamentos")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("font-size: 30px; font-weight: 600; color: #334155;")
        subheader_label = QLabel("Crie orçamentos profissionais de forma rápida e fácil")
        subheader_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subheader_label.setStyleSheet("color: #64748b; font-size: 15px;")

        orcamento_layout.addWidget(header_label)
        orcamento_layout.addWidget(subheader_label)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        client_group = QGroupBox("Dados do Cliente")
        client_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px;
                background-color: #f9fafb;
                color: #334155;
            }
        """)
        client_form = QFormLayout()

        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("Digite o nome completo")

        self.client_address_input = QTextEdit()
        self.client_address_input.setPlaceholderText("Digite o endereço completo")
        self.client_address_input.setFixedHeight(60)
        self.client_address_input.setAcceptRichText(False)

        self.client_number_input = QLineEdit()
        self.client_number_input.setPlaceholderText("Número")
        self.client_number_input.setMaximumWidth(100)

        self.client_date_input = QDateEdit()
        self.client_date_input.setDate(QDate.currentDate())
        self.client_date_input.setCalendarPopup(True)

        client_form.addRow("Nome do Cliente:", self.client_name_input)
        client_form.addRow("Endereço:", self.client_address_input)

        phone_date_layout = QHBoxLayout()
        phone_date_layout.addWidget(self.client_number_input)
        phone_date_layout.addWidget(self.client_date_input)
        client_form.addRow("Número / Data:", phone_date_layout)

        client_group.setLayout(client_form)
        cards_layout.addWidget(client_group)

        service_group = QGroupBox("Adicionar Serviço")
        service_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px;
                background-color: #f9fafb;
                color: #334155;
            }
        """)
        service_form = QFormLayout()

        quantity_unit_layout = QHBoxLayout()
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Qtd. Ex: 2")
        self.quantity_input.setMaximumWidth(60)
        self.quantity_input.setValidator(QRegularExpressionValidator(QRegularExpression(r"[1-9][0-9]*")))

        self.unit_price_input = QLineEdit()
        self.unit_price_input.setPlaceholderText("Valor Unit. Ex: 150.00")
        self.unit_price_input.setMaximumWidth(150)
        regex = QRegularExpression(r"[0-9]+([.,][0-9]{0,2})?")
        self.unit_price_input.setValidator(QRegularExpressionValidator(regex))

        quantity_unit_layout.addWidget(self.quantity_input)
        quantity_unit_layout.addWidget(self.unit_price_input)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Descreva detalhadamente o serviço")
        self.description_input.setFixedHeight(60)
        self.description_input.setAcceptRichText(False)

        self.add_service_button = QPushButton("Adicionar Serviço")
        self.add_service_button.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                        stop:0 #60a5fa, stop:1 #3b82f6);
            color: white;
            padding: 8px;
            font-weight: 600;
            border-radius: 6px;
        """)
        self.add_service_button.clicked.connect(self.add_service)

        service_form.addRow("Quantidade / Valor Unitário:", quantity_unit_layout)
        service_form.addRow("Descrição:", self.description_input)
        service_form.addRow(self.add_service_button)

        service_group.setLayout(service_form)
        cards_layout.addWidget(service_group)

        orcamento_layout.addLayout(cards_layout)

        self.services_table = QTableWidget(0, 4)
        self.services_table.setHorizontalHeaderLabels(
            ["Qtd.", "Descrição", "Valor Unit.", "Total"]
        )
        self.services_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.services_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.services_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.services_table.setAlternatingRowColors(True)

        orcamento_layout.addWidget(self.services_table)

        self.remove_service_btn = QPushButton("Remover Serviço Selecionado")
        self.remove_service_btn.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                        stop:0 #ef4444, stop:1 #b91c1c);
            color: white;
            padding: 8px;
            font-weight: 600;
            border-radius: 6px;
        """)
        self.remove_service_btn.clicked.connect(self.remove_service)
        orcamento_layout.addWidget(self.remove_service_btn, alignment=Qt.AlignmentFlag.AlignRight)

        total_layout = QHBoxLayout()
        total_layout.addStretch()
        self.total_label = QLabel("Total Geral: R$ 0,00")
        self.total_label.setStyleSheet("font-weight: 600; font-size: 18px; color: #3b82f6;")
        total_layout.addWidget(self.total_label)
        orcamento_layout.addLayout(total_layout)

        generate_pdf_btn = QPushButton("Gerar Orçamento PDF")
        generate_pdf_btn.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                        stop:0 #60a5fa, stop:1 #3b82f6);
            color: white;
            padding: 12px;
            font-weight: 600;
            border-radius: 8px;
            font-size: 16px;
            margin-top: 20px;
        """)
        generate_pdf_btn.clicked.connect(self.generate_pdf)
        orcamento_layout.addWidget(generate_pdf_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def init_config_ui(self):
        self.config_widget = QWidget()
        config_layout = QVBoxLayout(self.config_widget)
        config_layout.setSpacing(30)
        config_layout.setContentsMargins(20, 20, 20, 20)

        config_title = QLabel("Configurações")
        config_title.setStyleSheet("font-size: 24px; font-weight: 600; color: #334155;")
        config_layout.addWidget(config_title)

        textos_group = QGroupBox("Textos do PDF")
        textos_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 15px;
                background-color: #f9fafb;
                color: #334155;
            }
        """)
        textos_layout = QFormLayout(textos_group)

        self.input_titulo = QLineEdit()
        self.input_titulo.setText(self.config.get("titulo", "Delicatessen trigo de ouro"))
        textos_layout.addRow("Título:", self.input_titulo)

        self.input_texto1 = QLineEdit()
        self.input_texto1.setText(self.config.get("texto1", "(79) 3015-0626 | (79) 99820-3756 | (79) 99978-0044 | @trigodeouro_"))
        textos_layout.addRow("Texto 1:", self.input_texto1)

        self.input_texto2 = QLineEdit()
        self.input_texto2.setText(self.config.get("texto2", "Rua Elísio Matos, 235 Estância/SE"))
        textos_layout.addRow("Texto 2:", self.input_texto2)

        self.input_texto3 = QLineEdit()
        self.input_texto3.setText(self.config.get("texto3", "CNPJ: 266588290001-70"))
        textos_layout.addRow("Texto 3:", self.input_texto3)

        config_layout.addWidget(textos_group)

        pasta_group = QGroupBox("Pasta para salvar PDFs")
        pasta_group.setStyleSheet(textos_group.styleSheet())
        pasta_layout = QHBoxLayout(pasta_group)

        self.path_input = QLineEdit()
        self.path_input.setText(self.pdf_save_folder)
        pasta_layout.addWidget(self.path_input)

        btn_browse = QPushButton("Selecionar Pasta")
        btn_browse.setMaximumWidth(150)
        btn_browse.clicked.connect(self.browse_folder)
        pasta_layout.addWidget(btn_browse)

        config_layout.addWidget(pasta_group)

        logo_group = QGroupBox("Logo do Orçamento")
        logo_group.setStyleSheet(textos_group.styleSheet())
        logo_layout = QVBoxLayout(logo_group)

        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(160, 100)
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setStyleSheet("border: 1px solid #cbd5e1; background-color: white;")
        if os.path.isfile(LOGO_PNG_PATH):
            pixmap = QPixmap(LOGO_PNG_PATH).scaled(self.logo_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_preview.setPixmap(pixmap)
        logo_layout.addWidget(self.logo_preview)

        btn_change_logo = QPushButton("Trocar Logo")
        btn_change_logo.setMaximumWidth(150)
        btn_change_logo.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                        stop:0 #60a5fa, stop:1 #3b82f6);
            color: white;
            padding: 8px;
            font-weight: 600;
            border-radius: 6px;
        """)
        btn_change_logo.clicked.connect(self.change_logo)
        logo_layout.addWidget(btn_change_logo)

        config_layout.addWidget(logo_group)

        btn_save_config = QPushButton("Salvar Configurações")
        btn_save_config.setMaximumWidth(200)
        btn_save_config.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                        stop:0 #60a5fa, stop:1 #3b82f6);
            color: white;
            padding: 10px;
            font-weight: 600;
            border-radius: 6px;
            margin-top: 20px;
        """)
        btn_save_config.clicked.connect(self.save_config)
        config_layout.addWidget(btn_save_config, alignment=Qt.AlignmentFlag.AlignCenter)

        config_layout.addStretch()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecione a pasta")
        if folder:
            self.path_input.setText(folder)

    def change_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar nova logo", "", "Imagens (*.png *.jpg *.jpeg *.bmp *.ico)")
        if path:
            try:
                pil_img = PilImage.open(path)
                pil_img.save(LOGO_PNG_PATH)
                pil_img.save(LOGO_ICO_PATH)

                pixmap = QPixmap(LOGO_PNG_PATH).scaled(self.logo_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.logo_preview.setPixmap(pixmap)

                self.logo_label.setPixmap(pixmap.scaledToWidth(70, Qt.TransformationMode.SmoothTransformation))
                self.update_app_icon()

                QMessageBox.information(self, "Logo Atualizada", "Logo atualizada com sucesso!")

            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao atualizar logo:\n{e}")

    def save_config(self):
        path = self.path_input.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Pasta inválida", "Selecione uma pasta válida para salvar PDFs.")
            return

        self.config["titulo"] = self.input_titulo.text().strip()
        self.config["texto1"] = self.input_texto1.text().strip()
        self.config["texto2"] = self.input_texto2.text().strip()
        self.config["texto3"] = self.input_texto3.text().strip()
        self.config["pdf_save_folder"] = path

        try:
            save_config(self.config)
            self.pdf_save_folder = path
            QMessageBox.information(self, "Configurações Salvas", "Configurações atualizadas com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar configurações:\n{e}")

    def show_orcamento(self):
        self.config_widget.hide()
        self.orcamento_widget.show()

    def show_config(self):
        self.orcamento_widget.hide()
        self.config_widget.show()

    def add_service(self):
        quantity_text = self.quantity_input.text().strip()
        unit_price_text = self.unit_price_input.text().strip()
        description = self.description_input.toPlainText().strip()

        if not quantity_text or not unit_price_text or not description:
            QMessageBox.warning(self, "Campos obrigatórios", "Preencha todos os campos do serviço")
            return

        try:
            quantity = int(quantity_text)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Erro", "Quantidade deve ser um número inteiro positivo")
            return

        try:
            unit_price_text = unit_price_text.replace(",", ".")
            unit_price = float(unit_price_text)
            if unit_price < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Erro", "Valor Unitário deve ser um número válido")
            return

        total = quantity * unit_price

        service = {
            "quantity": quantity,
            "description": description,
            "unit_price": unit_price,
            "total": total,
        }
        self.services.append(service)

        self.update_services_table()

        self.quantity_input.clear()
        self.unit_price_input.clear()
        self.description_input.clear()

    def remove_service(self):
        selected_rows = set(idx.row() for idx in self.services_table.selectionModel().selectedRows())
        if not selected_rows:
            QMessageBox.information(self, "Aviso", "Selecione ao menos um serviço para remover.")
            return

        for row in sorted(selected_rows, reverse=True):
            if 0 <= row < len(self.services):
                del self.services[row]

        self.update_services_table()

    def update_services_table(self):
        self.services_table.setRowCount(len(self.services))
        for row, service in enumerate(self.services):
            self.services_table.setItem(row, 0, QTableWidgetItem(str(service["quantity"])))
            self.services_table.setItem(row, 1, QTableWidgetItem(service["description"]))
            self.services_table.setItem(row, 2, QTableWidgetItem(self.format_currency(service["unit_price"])))
            self.services_table.setItem(row, 3, QTableWidgetItem(self.format_currency(service["total"])))

        self.update_total_label()

    def update_total_label(self):
        total = sum(s["total"] for s in self.services)
        self.total_label.setText(f"Total Geral: {self.format_currency(total)}")

    def generate_pdf(self):
        nome = self.client_name_input.text().strip()
        endereco = self.client_address_input.toPlainText().strip()
        numero = self.client_number_input.text().strip()
        data = self.client_date_input.date().toString("dd/MM/yyyy")

        if len(self.services) == 0:
            QMessageBox.warning(self, "Dados incompletos", "Adicione pelo menos um serviço")
            return

        cliente_info = (nome, endereco, numero, data)

        itens = []
        for s in self.services:
            itens.append((
                s["quantity"],
                s["description"],
                f"{s['unit_price']:.2f}",
                s["total"]
            ))

        pasta_data = data.replace("/", "-")
        pasta_destino = os.path.join(self.pdf_save_folder, pasta_data)
        os.makedirs(pasta_destino, exist_ok=True)

        nome_arquivo_pdf = f"{nome if nome else 'Orcamento'}_{pasta_data}.pdf"
        caminho_pdf = os.path.join(pasta_destino, nome_arquivo_pdf)

        try:
            gerar_orcamento_pdf(caminho_pdf, itens, cliente_info, self.config)
            QMessageBox.information(self, "Sucesso", f"PDF gerado com sucesso:\n{caminho_pdf}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar o PDF:\n{e}")

    def format_currency(self, value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


if __name__ == "__main__":
    check_update_and_apply()  # Verifica e atualiza se houver versão nova

    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QWidget {
            background-color: #f0f4f8;
            color: #334155;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 14px;
        }
        QLineEdit, QTextEdit, QDateEdit, QTableWidget {
            background-color: white;
            color: #334155;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
        }
        QPushButton {
            background-color: #60a5fa;
            color: white;
            border-radius: 6px;
            padding: 6px;
        }
        QPushButton:hover {
            background-color: #3b82f6;
        }
        QHeaderView::section {
            background-color: #e2e8f0;
            color: #334155;
            font-weight: 600;
            border: none;
        }
        QTableWidget {
            gridline-color: #cbd5e1;
        }
        QTableWidget::item:selected {
            background-color: #bfdbfe;
            color: #1e293b;
        }
    """)

    window = BudgetGenerator()
    window.show()
    sys.exit(app.exec())
