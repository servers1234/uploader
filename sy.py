from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import sqlite3
from datetime import datetime, timedelta
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from instagrapi import Client
import json

class PostSchedulerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sosyal Medya Gönderi Planlayıcı")
        self.setGeometry(100, 100, 1200, 800)
        
        # Veritabanını başlat
        self.init_database()
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)
        
        # UI bileşenlerini oluştur
        self.create_ui_components()
        
        # Zamanlayıcıyı başlat
        self.start_scheduler()
        
        # YouTube kimlik bilgileri
        self.youtube_credentials = None
        
    def create_ui_components(self):
        # Üst kısım - Gönderi ekleme alanı
        top_group = QGroupBox("Yeni Gönderi Planla")
        top_layout = QVBoxLayout()
        
        # Platform seçimi
        platform_layout = QHBoxLayout()
        self.youtube_radio = QRadioButton("YouTube")
        self.instagram_radio = QRadioButton("Instagram")
        self.instagram_reels_radio = QRadioButton("Instagram Reels")
        platform_layout.addWidget(self.youtube_radio)
        platform_layout.addWidget(self.instagram_radio)
        platform_layout.addWidget(self.instagram_reels_radio)
        top_layout.addLayout(platform_layout)
        
        # Dosya seçimi
        file_layout = QHBoxLayout()
        self.files_list = QListWidget()
        self.files_list.setMinimumHeight(100)
        add_file_btn = QPushButton("Dosya Ekle")
        remove_file_btn = QPushButton("Seçili Dosyayı Kaldır")
        file_buttons_layout = QVBoxLayout()
        file_buttons_layout.addWidget(add_file_btn)
        file_buttons_layout.addWidget(remove_file_btn)
        file_layout.addWidget(self.files_list)
        file_layout.addLayout(file_buttons_layout)
        top_layout.addLayout(file_layout)
        
        # Zamanlama ayarları
        schedule_layout = QGridLayout()
        self.start_date = QDateEdit(calendarPopup=True)
        self.start_date.setDateTime(QDateTime.currentDateTime())
        self.start_time = QTimeEdit()
        self.start_time.setTime(QTime.currentTime())
        schedule_layout.addWidget(QLabel("Başlangıç Tarihi:"), 0, 0)
        schedule_layout.addWidget(self.start_date, 0, 1)
        schedule_layout.addWidget(QLabel("Saat:"), 0, 2)
        schedule_layout.addWidget(self.start_time, 0, 3)
        
        # Gönderi aralığı
        self.interval_hours = QSpinBox()
        self.interval_hours.setRange(0, 24)
        self.interval_minutes = QSpinBox()
        self.interval_minutes.setRange(0, 59)
        schedule_layout.addWidget(QLabel("Gönderi Aralığı:"), 1, 0)
        schedule_layout.addWidget(self.interval_hours, 1, 1)
        schedule_layout.addWidget(QLabel("saat"), 1, 2)
        schedule_layout.addWidget(self.interval_minutes, 1, 3)
        schedule_layout.addWidget(QLabel("dakika"), 1, 4)
        
        top_layout.addLayout(schedule_layout)
        
        # Başlık ve açıklama şablonu
        template_layout = QFormLayout()
        self.title_template = QLineEdit()
        self.description_template = QTextEdit()
        self.description_template.setMaximumHeight(100)
        template_layout.addRow("Başlık Şablonu:", self.title_template)
        template_layout.addRow("Açıklama Şablonu:", self.description_template)
        top_layout.addLayout(template_layout)
        
        # Instagram hesap bilgileri
        self.instagram_credentials = QGroupBox("Instagram Hesap Bilgileri")
        instagram_form = QFormLayout()
        self.insta_username = QLineEdit()
        self.insta_password = QLineEdit()
        self.insta_password.setEchoMode(QLineEdit.Password)
        instagram_form.addRow("Kullanıcı Adı:", self.insta_username)
        instagram_form.addRow("Şifre:", self.insta_password)
        self.instagram_credentials.setLayout(instagram_form)
        self.instagram_credentials.hide()
        top_layout.addWidget(self.instagram_credentials)
        
        # Planlama butonu
        self.schedule_button = QPushButton("Gönderileri Planla")
        self.schedule_button.setMinimumHeight(40)
        top_layout.addWidget(self.schedule_button)
        
        top_group.setLayout(top_layout)
        self.layout.addWidget(top_group)
        
        # Alt kısım - Planlanan gönderiler tablosu
        bottom_group = QGroupBox("Planlanan Gönderiler")
        bottom_layout = QVBoxLayout()
        
        self.posts_table = QTableWidget()
        self.setup_table()
        bottom_layout.addWidget(self.posts_table)
        
        bottom_group.setLayout(bottom_layout)
        self.layout.addWidget(bottom_group)
        
        # Sinyalleri bağla
        add_file_btn.clicked.connect(self.add_files)
        remove_file_btn.clicked.connect(self.remove_selected_file)
        self.schedule_button.clicked.connect(self.schedule_posts)
        self.youtube_radio.toggled.connect(self.toggle_instagram_credentials)
        self.instagram_radio.toggled.connect(self.toggle_instagram_credentials)
        self.instagram_reels_radio.toggled.connect(self.toggle_instagram_credentials)
        
        # Planlanan gönderileri yükle
        self.load_scheduled_posts()
        
    def init_database(self):
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()
            
            c.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         platform TEXT NOT NULL,
                         file_path TEXT NOT NULL,
                         scheduled_time TEXT NOT NULL,
                         status TEXT NOT NULL DEFAULT 'Bekliyor',
                         title TEXT,
                         description TEXT,
                         created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            
            conn.commit()
            conn.close()
            print("Veritabanı başarıyla başlatıldı!")
        except Exception as e:
            print(f"Veritabanı başlatma hatası: {str(e)}")
            QMessageBox.critical(self, "Hata", 
                               "Veritabanı oluşturulamadı!\nProgram kapatılacak.")
            sys.exit(1)
            
    def setup_table(self):
        self.posts_table.setColumnCount(6)
        self.posts_table.setHorizontalHeaderLabels([
            "Platform", "Dosya", "Tarih/Saat", "Durum", "Başlık", "Açıklama"
        ])
        
        header = self.posts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        
        self.posts_table.setAlternatingRowColors(True)
        
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Medya Dosyaları Seç",
            "",
            "Medya Dosyaları (*.mp4 *.jpg *.jpeg *.png)"
        )
        for file in files:
            self.files_list.addItem(file)
            
    def remove_selected_file(self):
        current_row = self.files_list.currentRow()
        if current_row >= 0:
            self.files_list.takeItem(current_row)
            
    def toggle_instagram_credentials(self):
        self.instagram_credentials.setVisible(
            self.instagram_radio.isChecked() or 
            self.instagram_reels_radio.isChecked()
        )
        
    def schedule_posts(self):
        if not self.validate_inputs():
            return
            
        try:
            start_datetime = datetime.combine(
                self.start_date.date().toPyDate(),
                self.start_time.time().toPyTime()
            )
            
            interval = timedelta(
                hours=self.interval_hours.value(),
                minutes=self.interval_minutes.value()
            )
            
            for i in range(self.files_list.count()):
                scheduled_time = start_datetime + (interval * i)
                file_path = self.files_list.item(i).text()
                
                title = self.title_template.text().replace("{n}", str(i+1))
                description = self.description_template.toPlainText().replace(
                    "{n}", str(i+1)
                )
                
                platform = "YouTube" if self.youtube_radio.isChecked() else \
                          "Instagram Reels" if self.instagram_reels_radio.isChecked() else \
                          "Instagram"
                
                if self.save_post_to_db(
                    platform, file_path, scheduled_time, title, description
                ):
                    print(f"Gönderi planlandı: {platform} - {scheduled_time}")
                
            self.load_scheduled_posts()
            QMessageBox.information(
                self,
                "Başarılı",
                f"{self.files_list.count()} gönderi planlandı!"
            )
            
            self.clear_form()
            
        except Exception as e:
            print(f"Planlama hatası: {str(e)}")
            QMessageBox.critical(
                self,
                "Hata",
                "Gönderiler planlanırken bir hata oluştu!"
            )
            
    def validate_inputs(self):
        if self.files_list.count() == 0:
            QMessageBox.warning(self, "Hata", "Lütfen en az bir dosya seçin!")
            return False
            
        if not (self.youtube_radio.isChecked() or 
                self.instagram_radio.isChecked() or 
                self.instagram_reels_radio.isChecked()):
            QMessageBox.warning(self, "Hata", "Lütfen bir platform seçin!")
            return False
            
        if (self.instagram_radio.isChecked() or 
            self.instagram_reels_radio.isChecked()):
            if not self.insta_username.text() or not self.insta_password.text():
                QMessageBox.warning(
                    self, 
                    "Hata", 
                    "Lütfen Instagram kullanıcı adı ve şifresini girin!"
                )
                return False
                
        interval = timedelta(
            hours=self.interval_hours.value(),
            minutes=self.interval_minutes.value()
        )
        
        if interval.total_seconds() == 0:
            QMessageBox.warning(
                self, 
                "Hata", 
                "Lütfen gönderi aralığını belirleyin!"
            )
            return False
            
        return True
        
    def clear_form(self):
        self.files_list.clear()
        self.title_template.clear()
        self.description_template.clear()
        self.youtube_radio.setChecked(False)
        self.instagram_radio.setChecked(False)
        self.instagram_reels_radio.setChecked(False)
        self.insta_username.clear()
        self.insta_password.clear()
        self.start_date.setDateTime(QDateTime.currentDateTime())
        self.start_time.setTime(QTime.currentTime())
        self.interval_hours.setValue(0)
        self.interval_minutes.setValue(0)
        
    def save_post_to_db(self, platform, file_path, scheduled_time, title, description):
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()
            
            c.execute('''INSERT INTO scheduled_posts 
                        (platform, file_path, scheduled_time, status, title, description)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (platform, file_path, scheduled_time.isoformat(), 
                      "Bekliyor", title or '', description or ''))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Veritabanı kayıt hatası: {str(e)}")
            return False
            
    def load_scheduled_posts(self):
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()
            
            posts = c.execute('''
                SELECT platform, file_path, scheduled_time, status, title, description 
                FROM scheduled_posts 
                ORDER BY scheduled_time
            ''').fetchall()
            
            self.posts_table.setRowCount(len(posts))
            for i, post in enumerate(posts):
                self.posts_table.setItem(i, 0, QTableWidgetItem(str(post[0])))  # Platform
                self.posts_table.setItem(i, 1, QTableWidgetItem(os.path.basename(str(post[1]))))  # Dosya adı
                self.posts_table.setItem(i, 2, QTableWidgetItem(str(post[2])))  # Tarih/Saat
                self.posts_table.setItem(i, 3, QTableWidgetItem(str(post[3])))  # Durum
                self.posts_table.setItem(i, 4, QTableWidgetItem(str(post[4])))  # Başlık
                self.posts_table.setItem(i, 5, QTableWidgetItem(str(post[5])))  # Açıklama
            
            conn.close()
        except Exception as e:
            print(f"Veritabanı okuma hatası: {str(e)}")
            
    def authenticate_youtube(self):
        try:
            SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
            creds = None
            
            if os.path.exists('youtube_token.json'):
                creds = Credentials.from_authorized_user_file('youtube_token.json', SCOPES)
                
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'client_secrets.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                with open('youtube_token.json', 'w') as token:
                    token.write(creds.to_json())
                    
            self.youtube_credentials = creds
            return True
        except Exception as e:
            print(f"YouTube kimlik doğrulama hatası: {str(e)}")
            return False
            
    def upload_youtube_video(self, file_path, title, description):
        try:
            if not self.youtube_credentials:
                if not self.authenticate_youtube():
                    raise Exception("YouTube kimlik doğrulaması başarısız!")
                    
            youtube = build('youtube', 'v3', credentials=self.youtube_credentials)
            
            request_body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'categoryId': '22'
                },
                'status': {
                    'privacyStatus': 'private'
                }
            }
            
            media_file = MediaFileUpload(
                file_path,
                chunksize=-1,
                resumable=True
            )
            
            insert_request = youtube.videos().insert(
                part='snippet,status',
                body=request_body,
                media_body=media_file
            )
            
            response = None
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    print(f"Yükleme durumu: {int(status.progress() * 100)}%")
                    
            return True, response['id']
            
        except Exception as e:
            return False, str(e)
            
    def upload_instagram_post(self, file_path, caption, is_reels=False):
        try:
            client = Client()
            client.login(self.insta_username.text(), self.insta_password.text())
            
            if is_reels:
                if not file_path.lower().endswith('.mp4'):
                    raise Exception("Reels için sadece MP4 formatı desteklenir!")
                media = client.clip_upload(file_path, caption=caption)
            else:
                if file_path.lower().endswith('.mp4'):
                    media = client.video_upload(file_path, caption=caption)
                else:
                    media = client.photo_upload(file_path, caption=caption)
                    
            return True, media.pk
            
        except Exception as e:
            return False, str(e)
            
    def start_scheduler(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_scheduled_posts)
        self.timer.start(60000)  # Her dakika kontrol et
        
    def check_scheduled_posts(self):
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()
            
            current_time = datetime.now()
            
            posts = c.execute('''
                SELECT * FROM scheduled_posts 
                WHERE status = 'Bekliyor' 
                AND datetime(scheduled_time) <= datetime(?)
            ''', (current_time.isoformat(),)).fetchall()
            
            for post in posts:
                post_id, platform, file_path, scheduled_time, status, title, description = post
                
                success = False
                result = ""
                
                try:
                    if platform == "YouTube":
                        success, result = self.upload_youtube_video(
                            file_path, title, description
                        )
                    else:
                        is_reels = (platform == "Instagram Reels")
                        success, result = self.upload_instagram_post(
                            file_path, 
                            f"{title}\n\n{description}",
                            is_reels
                        )
                        
                    new_status = "Yüklendi" if success else f"Hata: {result}"
                    
                    c.execute('''
                        UPDATE scheduled_posts 
                        SET status = ? 
                        WHERE id = ?
                    ''', (new_status, post_id))
                    
                except Exception as e:
                    c.execute('''
                        UPDATE scheduled_posts 
                        SET status = ? 
                        WHERE id = ?
                    ''', (f"Hata: {str(e)}", post_id))
                    
            conn.commit()
            conn.close()
            
            self.load_scheduled_posts()
            
        except Exception as e:
            print(f"Zamanlayıcı hatası: {str(e)}")

def main():
    app = QApplication(sys.argv)
    
    # Stil ayarları
    app.setStyle('Fusion')
    
    # Koyu tema
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    
    app.setPalette(palette)
    
    window = PostSchedulerUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()