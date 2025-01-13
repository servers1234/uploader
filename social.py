from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
import sqlite3
from datetime import datetime
from auth_manager import AuthManager
from post_manager import PostManager

class LoginDialog(QDialog):
    def __init__(self, platform):
        super().__init__()
        self.platform = platform
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        form_layout = QFormLayout()
        form_layout.addRow("Kullanıcı Adı:", self.username_input)
        form_layout.addRow("Şifre:", self.password_input)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
            
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self.setWindowTitle(f"{self.platform} Giriş")

class SocialMediaScheduler(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auth_manager = AuthManager()
        self.post_manager = PostManager(self.auth_manager)
        self.post_manager.status_updated.connect(self.update_post_status)
        self.initUI()
        
    def initUI(self):
        # Mevcut UI kodunuz...
        # Ana menü ekleme
        menubar = self.menuBar()
        auth_menu = menubar.addMenu('Hesaplar')
        
        # YouTube hesap menüsü
        youtube_auth = QAction('YouTube Hesabı', self)
        youtube_auth.triggered.connect(self.authenticate_youtube)
        auth_menu.addAction(youtube_auth)
        
        # Instagram hesap menüsü
        instagram_auth = QAction('Instagram Hesabı', self)
        instagram_auth.triggered.connect(self.authenticate_instagram)
        auth_menu.addAction(instagram_auth)
        
        # Diğer UI bileşenleri...
        
    def authenticate_youtube(self):
        try:
            if self.auth_manager.authenticate_youtube():
                QMessageBox.information(self, "Başarılı", "YouTube kimlik doğrulaması başarılı!")
        except Exception as e:
            QMessageBox.warning(self, "Hata", str(e))

    def authenticate_instagram(self):
        dialog = LoginDialog("Instagram")
        if dialog.exec_() == QDialog.Accepted:
            try:
                username = dialog.username_input.text()
                password = dialog.password_input.text()
                if self.auth_manager.authenticate_instagram(username, password):
                    QMessageBox.information(self, "Başarılı", "Instagram kimlik doğrulaması başarılı!")
            except Exception as e:
                QMessageBox.warning(self, "Hata", str(e))

    def schedule_post(self):
        if not hasattr(self, 'selected_file'):
            QMessageBox.warning(self, "Hata", "Lütfen bir dosya seçin!")
            return
            
        platform = "YouTube" if self.youtube_radio.isChecked() else "Instagram"
        
        # Platforma göre kimlik doğrulama kontrolü
        if platform == "YouTube" and not self.auth_manager.is_authenticated_youtube():
            QMessageBox.warning(self, "Hata", "Lütfen önce YouTube hesabınıza giriş yapın!")
            return
        elif platform == "Instagram" and not self.auth_manager.is_authenticated_instagram():
            QMessageBox.warning(self, "Hata", "Lütfen önce Instagram hesabınıza giriş yapın!")
            return
            
        scheduled_time = self.date_edit.dateTime().toPyDateTime()
        
        # Veritabanına kaydet
        conn = sqlite3.connect('scheduler.db')
        c = conn.cursor()
        c.execute('''INSERT INTO scheduled_posts 
                    (platform, file_path, scheduled_time, status)
                    VALUES (?, ?, ?, ?)''',
                 (platform, self.selected_file, scheduled_time.isoformat(), "Bekliyor"))
        row_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Gönderiyi planla
        self.post_manager.schedule_post(
            platform, 
            self.selected_file, 
            scheduled_time,
            self.posts_table.rowCount() - 1
        )
        
        self.update_posts_table()
        QMessageBox.information(self, "Başarılı", "Gönderi planlandı!")

    def update_post_status(self, row_index, new_status):
        self.posts_table.setItem(row_index, 3, QTableWidgetItem(new_status))
        
    def closeEvent(self, event):
        self.post_manager.stop_scheduler()
        event.accept()

def main():
    app = QApplication(sys.argv)
    scheduler = SocialMediaScheduler()
    scheduler.show()
    scheduler.post_manager.start_scheduler()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()