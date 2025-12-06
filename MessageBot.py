import sys
import threading
import queue
import asyncio
import discord
from discord.ext import commands
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QColorDialog,
    QScrollArea, QFrame, QGridLayout, QTabWidget, QComboBox,
    QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Slot, Signal, QObject
from PySide6.QtGui import QFont, QPalette, QColor, QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

TOKEN = "tu_token_aqui"
CHANNEL_ID = None

intents = discord.Intents.default()
intents.guilds = True
intents.emojis = True
bot = commands.Bot(command_prefix="!", intents=intents)

msg_queue = queue.Queue()
server_emojis = []

class SignalBridge(QObject):
    emojis_updated = Signal(list)

signal_bridge = SignalBridge()

class ChannelIDDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración del Bot")
        self.setMinimumWidth(500)
        self.channel_id = None
        self.setup_ui()
        self.apply_dark_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        header = QLabel("🔧 Configuración Inicial")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet("color: #ffffff; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        desc = QLabel("Por favor, ingresa el ID del canal donde deseas que el bot envíe los mensajes.")
        desc.setStyleSheet("color: #dcddde; font-size: 13px; line-height: 1.5;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        input_label = QLabel("📌 ID del Canal:")
        input_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(input_label)
        
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Ejemplo: 1409253109536133140")
        self.channel_input.setStyleSheet("""
            QLineEdit {
                background: #202225;
                color: #dcddde;
                border: 2px solid #202225;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border-color: #5865F2;
            }
        """)
        layout.addWidget(self.channel_input)
        
        button_box = QDialogButtonBox()
        
        self.ok_button = QPushButton("✅ Continuar")
        self.ok_button.setStyleSheet("""
            QPushButton {
                background: #5865F2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #4752c4;
            }
            QPushButton:pressed {
                background: #3c45a5;
            }
        """)
        self.ok_button.clicked.connect(self.validate_and_accept)
        
        self.cancel_button = QPushButton("❌ Cancelar")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background: #ed4245;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #c03537;
            }
            QPushButton:pressed {
                background: #a02d2f;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #ed4245; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)
    
    def validate_and_accept(self):
        channel_id_text = self.channel_input.text().strip()
        
        if not channel_id_text:
            self.show_error("⚠️ Por favor ingresa un ID de canal")
            return
        
        try:
            self.channel_id = int(channel_id_text)
            self.accept()
        except ValueError:
            self.show_error("⚠️ El ID del canal debe ser un número válido")
    
    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()
        self.channel_input.setStyleSheet("""
            QLineEdit {
                background: #202225;
                color: #dcddde;
                border: 2px solid #ed4245;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-family: 'Consolas', monospace;
            }
        """)
    
    def apply_dark_theme(self):
        self.setStyleSheet("QDialog { background: #2f3136; }")

async def sender_loop():
    await bot.wait_until_ready()
    print("Sender loop listo")
    
    for guild in bot.guilds:
        emojis = [(emoji.name, str(emoji.id), emoji.animated) for emoji in guild.emojis]
        signal_bridge.emojis_updated.emit(emojis)
        print(f"Cargados {len(emojis)} emojis del servidor: {guild.name}")
    
    while True:
        titulo, descripcion, color_hex, img_url, estatus, version, link, source_code = await asyncio.get_event_loop().run_in_executor(None, msg_queue.get)
        
        try:
            channel = bot.get_channel(CHANNEL_ID)
            if channel is None:
                channel = await bot.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"❌ No pude obtener canal {CHANNEL_ID}: {e}")
            await asyncio.sleep(2)
            continue
        
        try:
            color_int = int(color_hex.replace("#", ""), 16)
        except Exception:
            color_int = 0x5865F2
        
        embed = discord.Embed(
            title=titulo or "\u200b",
            description=descripcion or "\u200b",
            color=color_int
        )
        
        if estatus:
            embed.add_field(name="ESTATUS", value=estatus, inline=False)
        if version:
            embed.add_field(name="VERSIÓN", value=version, inline=False)
        if link:
            embed.add_field(name="LINK", value=link, inline=False)
        if source_code:
            embed.add_field(name="CÓDIGO FUENTE", value=source_code, inline=False)
        if img_url:
            try:
                embed.set_image(url=img_url)
            except Exception:
                pass

        try:
            await channel.send(embed=embed)
            print("✅ Embed enviado correctamente")
        except discord.Forbidden:
            print("❌ Error: el bot no tiene permisos")
        except discord.NotFound:
            print("❌ Error: canal no encontrado")
        except Exception as e:
            print(f"❌ Error al enviar embed: {e}")

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    bot.loop.create_task(sender_loop())

def run_bot():
    bot.run(TOKEN)

class EmojiPicker(QWidget):
    emoji_selected = Signal(str, str, bool, object)
    
    def __init__(self, target_widget=None):
        super().__init__()
        self.target_widget = target_widget
        self.setWindowTitle("Selector de Emojis")
        self.setMinimumSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Buscar emoji...")
        self.search.textChanged.connect(self.filter_emojis)
        layout.addWidget(self.search)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: #2f3136; border: none;")
        
        self.emoji_container = QWidget()
        self.emoji_layout = QGridLayout(self.emoji_container)
        self.emoji_layout.setSpacing(5)
        
        scroll.setWidget(self.emoji_container)
        layout.addWidget(scroll)
        
        self.emoji_buttons = []
        
    def load_emojis(self, emojis):
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import QUrl
        
        for btn in self.emoji_buttons:
            btn.deleteLater()
        self.emoji_buttons.clear()
        
        self.network_manager = QNetworkAccessManager()
        
        row, col = 0, 0
        for name, emoji_id, animated in emojis:
            btn = QPushButton()
            btn.setFixedSize(60, 60)
            btn.setToolTip(f":{name}:")
            btn.setStyleSheet("""
                QPushButton {
                    background: #36393f;
                    border: 2px solid #202225;
                    border-radius: 8px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background: #40444b;
                    border-color: #5865F2;
                }
            """)
            
            ext = 'gif' if animated else 'png'
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=48&quality=lossless"
            
            request = QNetworkRequest(QUrl(emoji_url))
            reply = self.network_manager.get(request)
            
            reply.finished.connect(lambda r=reply, b=btn: self.on_emoji_loaded(r, b))
            
            btn.clicked.connect(lambda checked, n=name, i=emoji_id, a=animated: self.on_emoji_click(n, i, a))
            
            self.emoji_layout.addWidget(btn, row, col)
            self.emoji_buttons.append(btn)
            
            col += 1
            if col > 5:
                col = 0
                row += 1
    
    def on_emoji_loaded(self, reply, button):
        from PySide6.QtGui import QPixmap
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled_pixmap = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                button.setIcon(QIcon(scaled_pixmap))
                button.setIconSize(scaled_pixmap.size())
        reply.deleteLater()
    
    def on_emoji_click(self, name, emoji_id, animated):
        self.emoji_selected.emit(name, emoji_id, animated, self.target_widget)
        self.close()
    
    def filter_emojis(self, text):
        for btn in self.emoji_buttons:
            if text.lower() in btn.toolTip().lower():
                btn.show()
            else:
                btn.hide()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discord Message Bot - Professional Edition")
        self.setMinimumSize(1400, 800)
        self.color_hex = "#5865F2"
        self.emojis = []
        self.emoji_picker = None
        self.current_focus_widget = None
        
        self.setup_ui()
        self.apply_dark_theme()
        
        signal_bridge.emojis_updated.connect(self.on_emojis_loaded)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        left_panel = QFrame()
        left_panel.setStyleSheet("background: #2f3136;")
        left_panel.setMinimumWidth(450)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)
        
        header = QLabel("📨 Discord Embed Creator")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #ffffff; padding: 10px;")
        left_layout.addWidget(header)
        
        self.channel_info = QLabel(f"📡 Canal ID: {CHANNEL_ID}")
        self.channel_info.setStyleSheet("""
            background: #202225;
            color: #dcddde;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-family: 'Consolas', monospace;
        """)
        left_layout.addWidget(self.channel_info)
        
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #202225;
                background: #36393f;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #202225;
                color: #b9bbbe;
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #5865F2;
                color: #ffffff;
            }
        """)
        
        content_tab = QWidget()
        content_layout = QVBoxLayout(content_tab)
        content_layout.setSpacing(10)
        
        self.title_input = self.create_input("Título del Embed", single_line=True)
        self.desc_input = self.create_input("Descripción del embed (soporta markdown)", single_line=False)
        self.img_input = self.create_input("URL de imagen (opcional)", single_line=True)
        
        self.title_input.focusInEvent = lambda e: self.set_focus_widget(self.title_input, e)
        self.desc_input.focusInEvent = lambda e: self.set_focus_widget(self.desc_input, e)
        
        content_layout.addWidget(QLabel("📝 Título:"))
        content_layout.addWidget(self.title_input)
        content_layout.addWidget(QLabel("📄 Descripción:"))
        content_layout.addWidget(self.desc_input)
        content_layout.addWidget(QLabel("🖼️ Imagen:"))
        content_layout.addWidget(self.img_input)
        content_layout.addStretch()
        
        fields_tab = QWidget()
        fields_layout = QVBoxLayout(fields_tab)
        fields_layout.setSpacing(10)
        
        self.status_input = self.create_input("Estado del proyecto/sistema", single_line=True)
        self.version_input = self.create_input("Versión actual", single_line=True)
        self.link_input = self.create_input("https://ejemplo.com", single_line=True)
        self.source_code_input = self.create_input("https://github.com/usuario/proyecto", single_line=True)
        
        self.status_input.focusInEvent = lambda e: self.set_focus_widget(self.status_input, e)
        self.version_input.focusInEvent = lambda e: self.set_focus_widget(self.version_input, e)
        self.link_input.focusInEvent = lambda e: self.set_focus_widget(self.link_input, e)
        self.source_code_input.focusInEvent = lambda e: self.set_focus_widget(self.source_code_input, e)
        
        fields_layout.addWidget(QLabel("📊 ESTATUS:"))
        fields_layout.addWidget(self.status_input)
        fields_layout.addWidget(QLabel("🔖 VERSIÓN:"))
        fields_layout.addWidget(self.version_input)
        fields_layout.addWidget(QLabel("🔗 LINK:"))
        fields_layout.addWidget(self.link_input)
        fields_layout.addWidget(QLabel("💻 CÓDIGO FUENTE:"))
        fields_layout.addWidget(self.source_code_input)
        fields_layout.addStretch()
        
        tabs.addTab(content_tab, "📋 Contenido")
        tabs.addTab(fields_tab, "⚙️ Campos")
        
        left_layout.addWidget(tabs)
        
        color_section = QHBoxLayout()
        color_label = QLabel("🎨 Color del embed:")
        color_label.setStyleSheet("color: #dcddde; font-size: 13px;")
        
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setStyleSheet(f"background: {self.color_hex}; border-radius: 6px; border: 2px solid #202225;")
        
        self.color_btn = QPushButton("Cambiar Color")
        self.color_btn.clicked.connect(self.open_color_dialog)
        self.style_button(self.color_btn, "#4752c4")
        
        color_section.addWidget(color_label)
        color_section.addWidget(self.color_preview)
        color_section.addWidget(self.color_btn)
        color_section.addStretch()
        
        left_layout.addLayout(color_section)
        
        self.emoji_btn = QPushButton("😀 Insertar Emoji del Servidor")
        self.emoji_btn.clicked.connect(self.open_emoji_picker)
        self.style_button(self.emoji_btn, "#3ba55d")
        left_layout.addWidget(self.emoji_btn)
        
        self.send_btn = QPushButton("🚀 ENVIAR EMBED")
        self.send_btn.clicked.connect(self.on_send)
        self.style_button(self.send_btn, "#5865F2", large=True)
        left_layout.addWidget(self.send_btn)
        
        self.status_label = QLabel("✅ Listo para enviar")
        self.status_label.setStyleSheet("color: #3ba55d; font-size: 12px; padding: 5px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_label)
        
        right_panel = QFrame()
        right_panel.setStyleSheet("background: #36393f;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        self.preview = QWebEngineView()
        self.preview.setStyleSheet("border-radius: 8px;")
        right_layout.addWidget(self.preview)
        
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
        self.title_input.textChanged.connect(self.update_preview)
        self.desc_input.textChanged.connect(self.update_preview)
        self.img_input.textChanged.connect(self.update_preview)
        self.status_input.textChanged.connect(self.update_preview)
        self.version_input.textChanged.connect(self.update_preview)
        self.link_input.textChanged.connect(self.update_preview)
        self.source_code_input.textChanged.connect(self.update_preview)
        
        self.update_preview()
    
    def create_input(self, placeholder, single_line=True):
        if single_line:
            widget = QLineEdit()
            widget.setPlaceholderText(placeholder)
            widget.setStyleSheet("""
                QLineEdit {
                    background: #202225;
                    color: #dcddde;
                    border: 2px solid #202225;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 14px;
                }
                QLineEdit:focus {
                    border-color: #5865F2;
                }
            """)
        else:
            widget = QTextEdit()
            widget.setPlaceholderText(placeholder)
            widget.setMaximumHeight(120)
            widget.setStyleSheet("""
                QTextEdit {
                    background: #202225;
                    color: #dcddde;
                    border: 2px solid #202225;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 14px;
                }
                QTextEdit:focus {
                    border-color: #5865F2;
                }
            """)
        return widget
    
    def style_button(self, button, color, large=False):
        size = "16px" if large else "14px"
        padding = "15px" if large else "10px"
        button.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: {padding};
                font-size: {size};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {self.adjust_color(color, 1.2)};
            }}
            QPushButton:pressed {{
                background: {self.adjust_color(color, 0.8)};
            }}
        """)
    
    def adjust_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, int(c * factor)) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(47, 49, 54))
        palette.setColor(QPalette.WindowText, QColor(220, 221, 222))
        self.setPalette(palette)
    
    def set_focus_widget(self, widget, event):
        self.current_focus_widget = widget
        if isinstance(widget, QLineEdit):
            QLineEdit.focusInEvent(widget, event)
        else:
            QTextEdit.focusInEvent(widget, event)
    
    @Slot(list)
    def on_emojis_loaded(self, emojis):
        self.emojis = emojis
        print(f"GUI: {len(emojis)} emojis cargados")
    
    @Slot()
    def open_emoji_picker(self):
        if not self.emojis:
            self.status_label.setText("⚠️ No hay emojis disponibles aún")
            self.status_label.setStyleSheet("color: #faa61a; font-size: 12px; padding: 5px;")
            return
        
        target = self.current_focus_widget if self.current_focus_widget else self.desc_input
        
        self.emoji_picker = EmojiPicker(target)
        self.emoji_picker.load_emojis(self.emojis)
        self.emoji_picker.emoji_selected.connect(self.insert_emoji)
        
        self.emoji_picker.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.emoji_picker.show()
        self.emoji_picker.raise_()
        self.emoji_picker.activateWindow()
    
    @Slot(str, str, bool, object)
    def insert_emoji(self, name, emoji_id, animated, target_widget):
        emoji_format = f"<{'a' if animated else ''}:{name}:{emoji_id}>"
        
        if isinstance(target_widget, QTextEdit):
            cursor = target_widget.textCursor()
            cursor.insertText(emoji_format)
            target_widget.setTextCursor(cursor)
        elif isinstance(target_widget, QLineEdit):
            cursor_pos = target_widget.cursorPosition()
            current_text = target_widget.text()
            new_text = current_text[:cursor_pos] + emoji_format + current_text[cursor_pos:]
            target_widget.setText(new_text)
            target_widget.setCursorPosition(cursor_pos + len(emoji_format))
        
        self.update_preview()
    
    @Slot()
    def open_color_dialog(self):
        color = QColorDialog.getColor(QColor(self.color_hex))
        if color.isValid():
            self.color_hex = color.name()
            self.color_preview.setStyleSheet(f"background: {self.color_hex}; border-radius: 6px; border: 2px solid #202225;")
            self.update_preview()
    
    @Slot()
    def on_send(self):
        titulo = self.title_input.text()
        desc = self.desc_input.toPlainText()
        img = self.img_input.text()
        est = self.status_input.text()
        ver = self.version_input.text()
        link = self.link_input.text()
        source = self.source_code_input.text()
        
        msg_queue.put((titulo, desc, self.color_hex, img, est, ver, link, source))
        
        self.status_label.setText("Enviando mensaje...")
        self.status_label.setStyleSheet("color: #faa61a; font-size: 12px; padding: 5px;")
        print("Mensaje en cola para enviar.")
    
    def update_preview(self):
        titulo = self.title_input.text() or "Título del embed"
        desc = self.desc_input.toPlainText() or "Descripción del embed..."
        img = self.img_input.text() or ""
        est = self.status_input.text() or ""
        ver = self.version_input.text() or ""
        link = self.link_input.text() or ""
        source = self.source_code_input.text() or ""
        color = self.color_hex
        
        import re
        emoji_pattern = r'<(a?):(\w+):(\d+)>'
        
        def replace_emoji(match):
            animated = match.group(1) == 'a'
            name = match.group(2)
            emoji_id = match.group(3)
            ext = 'gif' if animated else 'png'
            return f'<img src="https://cdn.discordapp.com/emojis/{emoji_id}.{ext}" alt=":{name}:" style="width:22px;height:22px;vertical-align:middle;margin:0 2px;">'
        
        desc_with_emojis = re.sub(emoji_pattern, replace_emoji, desc)
        
        desc_with_emojis = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', desc_with_emojis)
        desc_with_emojis = re.sub(r'\*(.+?)\*', r'<em>\1</em>', desc_with_emojis)
        desc_with_emojis = re.sub(r'__(.+?)__', r'<u>\1</u>', desc_with_emojis)
        desc_with_emojis = re.sub(r'~~(.+?)~~', r'<s>\1</s>', desc_with_emojis)
        desc_with_emojis = desc_with_emojis.replace('\n', '<br>')
        
        bot_name = str(bot.user) if bot.user else "Message Bot"
        bot_avatar = bot.user.display_avatar.url if bot.user else "https://cdn.discordapp.com/embed/avatars/0.png"
        
        html = f"""
        <!doctype html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Whitney:wght@400;500;600;700&display=swap');
        
        body {{
          background: #36393f;
          margin: 0;
          font-family: 'Whitney', 'Helvetica Neue', Helvetica, Arial, sans-serif;
          color: #dcddde;
          padding: 20px;
          font-size: 16px;
        }}
        .message-container {{
          max-width: 800px;
          margin: 0 auto;
        }}
        .message {{
          display: flex;
          gap: 16px;
          padding: 8px 0;
        }}
        .avatar {{
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: linear-gradient(135deg, #5865F2, #7289da);
          flex-shrink: 0;
          background-size: cover;
          background-position: center;
        }}
        .message-content {{
          flex: 1;
          min-width: 0;
        }}
        .author {{
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 4px;
        }}
        .author-name {{
          color: #ffffff;
          font-weight: 500;
          font-size: 16px;
        }}
        .bot-tag {{
          background: #5865F2;
          color: #ffffff;
          font-size: 10px;
          font-weight: 600;
          padding: 2px 4px;
          border-radius: 3px;
          text-transform: uppercase;
        }}
        .timestamp {{
          color: #72767d;
          font-size: 12px;
          margin-left: 4px;
        }}
        .embed-container {{
          display: flex;
          margin-top: 8px;
          max-width: 520px;
        }}
        .embed {{
          background: #2f3136;
          border-radius: 4px;
          padding: 8px 16px 16px 12px;
          border-left: 4px solid {color};
          display: flex;
          flex-direction: column;
          width: 100%;
        }}
        .embed-title {{
          color: #ffffff;
          font-weight: 600;
          font-size: 16px;
          margin-bottom: 8px;
          line-height: 1.375;
        }}
        .embed-description {{
          color: #dcddde;
          font-size: 14px;
          line-height: 1.375;
          white-space: pre-wrap;
          word-wrap: break-word;
        }}
        .embed-field {{
          margin-top: 12px;
        }}
        .embed-field-name {{
          color: #ffffff;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 4px;
        }}
        .embed-field-value {{
          color: #dcddde;
          font-size: 14px;
          line-height: 1.375;
        }}
        .embed-field-value a {{
          color: #00b0f4;
          text-decoration: none;
        }}
        .embed-field-value a:hover {{
          text-decoration: underline;
        }}
        .embed-image {{
          margin-top: 16px;
          border-radius: 4px;
          max-width: 100%;
          max-height: 300px;
          object-fit: contain;
        }}
        </style>
        </head>
        <body>
        <div class="message-container">
          <div class="message">
            <div class="avatar" style="background-image: url('{bot_avatar}');"></div>
            <div class="message-content">
              <div class="author">
                <span class="author-name">{bot_name}</span>
                <span class="bot-tag">Bot</span>
              </div>
              <div class="embed-container">
                <div class="embed">
                  <div class="embed-title">{titulo}</div>
                  <div class="embed-description">{desc_with_emojis}</div>
        """
        
        if est:
            html += f'''
                  <div class="embed-field">
                    <div class="embed-field-name">ESTATUS</div>
                    <div class="embed-field-value">{est}</div>
                  </div>
            '''
        
        if ver:
            html += f'''
                  <div class="embed-field">
                    <div class="embed-field-name">VERSIÓN</div>
                    <div class="embed-field-value">{ver}</div>
                  </div>
            '''
        
        if link:
            html += f'''
                  <div class="embed-field">
                    <div class="embed-field-name">LINK</div>
                    <div class="embed-field-value"><a href="{link}" target="_blank">{link}</a></div>
                  </div>
            '''

        if source:
            html += f'''
                  <div class="embed-field">
                    <div class="embed-field-name">CÓDIGO FUENTE</div>
                    <div class="embed-field-value"><a href="{source}" target="_blank">{source}</a></div>
                  </div>
            '''
        
        if img:
            html += f'<img class="embed-image" src="{img}" alt="Embed Image">'
        
        html += '''
                </div>
              </div>
            </div>
          </div>
        </div>
        </body>
        </html>
        '''
        
        self.preview.setHtml(html)

def main():
    global CHANNEL_ID
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    dialog = ChannelIDDialog()
    if dialog.exec() == QDialog.Accepted:
        CHANNEL_ID = dialog.channel_id
        print(f"✅ ID del canal configurado: {CHANNEL_ID}")
    else:
        print("❌ Configuración cancelada. Saliendo...")
        sys.exit(0)
    
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()