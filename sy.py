from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import sqlite3
from datetime import datetime, timedelta, date, time
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from instagrapi import Client
import json
from moviepy.editor import VideoFileClip
import tempfile
import shutil

class PostSchedulerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sosyal Medya Gönderi Planlayıcı")
        self.setGeometry(100, 100, 1200, 800)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)
        
        # UI bileşenlerini oluştur
        self.create_ui_components()
        
        # Veritabanını başlat
        self.init_database()
        
        # Kimlik bilgileri
        self.youtube_credentials = None
        self.instagram_client = None
        
        # YouTube categories
        self.youtube_categories = self.get_youtube_categories()
        
        # Planlanan gönderileri yükle
        self.load_scheduled_posts()
        
        # Zamanlayıcıyı başlat
        self.start_scheduler()
        self.init_database()
    def create_ui_components(self):
        # Üst kısım - Gönderi ekleme alanı
        top_group = QGroupBox("Yeni Gönderi Planla")
        top_layout = QVBoxLayout()
        
        # Platform seçimi
        platform_layout = QHBoxLayout()
        self.youtube_radio = QRadioButton("YouTube")
        self.instagram_radio = QRadioButton("Instagram")
        self.instagram_reels_radio = QRadioButton("Instagram Reels")
        self.instagram_story_radio = QRadioButton("Instagram Story")
        platform_layout.addWidget(self.youtube_radio)
        platform_layout.addWidget(self.instagram_radio)
        platform_layout.addWidget(self.instagram_reels_radio)
        platform_layout.addWidget(self.instagram_story_radio)
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
        
        # YouTube Ayarları
        self.youtube_settings = QGroupBox("YouTube Ayarları")
        youtube_settings_layout = QFormLayout()

        # Privacy Status
        self.privacy_status = QComboBox()
        self.privacy_status.addItems(["public", "private", "unlisted"])
        youtube_settings_layout.addRow("Gizlilik:", self.privacy_status)

        # Made for Kids setting
        self.made_for_kids = QComboBox()
        self.made_for_kids.addItems(["Hayır", "Evet"])
        youtube_settings_layout.addRow("Çocuklar için mi?", self.made_for_kids)

        # Category
        self.category = QComboBox()
        youtube_settings_layout.addRow("Kategori:", self.category)

        # Tags
        self.tags = QLineEdit()
        youtube_settings_layout.addRow("Etiketler (virgülle ayrılmış):", self.tags)

        self.youtube_settings.setLayout(youtube_settings_layout)
        top_layout.addWidget(self.youtube_settings)
        
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
        self.instagram_story_radio.toggled.connect(self.toggle_instagram_credentials)

    def init_database(self):
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()

            # Mevcut verileri yedekle (eğer tablo varsa)
            try:
                c.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts_backup AS 
                            SELECT * FROM scheduled_posts''')
                has_backup = True
            except:
                has_backup = False

            # Yeni tabloyu oluştur
            c.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts_new
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         platform TEXT NOT NULL,
                         file_path TEXT NOT NULL,
                         scheduled_time TEXT NOT NULL,
                         status TEXT NOT NULL DEFAULT 'Bekliyor',
                         title TEXT,
                         description TEXT,
                         privacy_status TEXT,
                         made_for_kids TEXT,
                         category TEXT,
                         tags TEXT,
                         upload_time TEXT,
                         error_message TEXT,
                         last_attempt TEXT)''')

            # Eğer yedek varsa, verileri yeni tabloya aktar
            if has_backup:
                try:
                    c.execute('''INSERT INTO scheduled_posts_new 
                                (id, platform, file_path, scheduled_time, status,
                                 title, description, privacy_status, made_for_kids,
                                 category, tags)
                                SELECT id, platform, file_path, scheduled_time, status,
                                       title, description, privacy_status, made_for_kids,
                                       category, tags
                                FROM scheduled_posts_backup''')
                except Exception as transfer_error:
                    print(f"Veri transfer hatası: {str(transfer_error)}")

            # Eski tabloyu kaldır ve yeni tabloyu yeniden adlandır
            c.execute('DROP TABLE IF EXISTS scheduled_posts')
            c.execute('ALTER TABLE scheduled_posts_new RENAME TO scheduled_posts')

            # Yedek tabloyu temizle
            c.execute('DROP TABLE IF EXISTS scheduled_posts_backup')

            conn.commit()
            conn.close()
            print("Veritabanı başarıyla güncellendi!")

        except Exception as e:
            print(f"Veritabanı güncelleme hatası: {str(e)}")
            if 'conn' in locals():
                try:
                    # Hata durumunda yedek tabloyu geri yükle
                    if has_backup:
                        c.execute('DROP TABLE IF EXISTS scheduled_posts')
                        c.execute('ALTER TABLE scheduled_posts_backup RENAME TO scheduled_posts')
                    conn.commit()
                except:
                    pass
                conn.close()

            QMessageBox.critical(self, "Hata", 
                               "Veritabanı güncellenemedi!\nProgram kapatılacak.")
            sys.exit(1)

    def setup_table(self):
        self.posts_table.setColumnCount(10)
        self.posts_table.setHorizontalHeaderLabels([
            "Platform", "Dosya", "Tarih/Saat", "Durum", "Başlık", "Açıklama", "Gizlilik", "Çocuklar için mi?", "Kategori", "Etiketler"
        ])
        
        header = self.posts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.Stretch)
        
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
            self.instagram_reels_radio.isChecked() or
            self.instagram_story_radio.isChecked()
        )

    def schedule_posts(self):
        if not self.validate_inputs():
            return
            
        try:
            start_date = self.start_date.date().toPyDate()
            start_time = self.start_time.time().toPyTime()
            start_datetime = datetime(
                start_date.year,
                start_date.month,
                start_date.day,
                start_time.hour,
                start_time.minute,
                start_time.second
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
                          "Instagram Story" if self.instagram_story_radio.isChecked() else \
                          "Instagram"

                privacy_status = self.privacy_status.currentText()
                made_for_kids = self.made_for_kids.currentText()
                category = self.youtube_categories[self.category.currentText()]
                tags = self.tags.text()
                
                if self.save_post_to_db(
                    platform, file_path, scheduled_time, title, description, privacy_status, made_for_kids, category, tags
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
                f"Gönderiler planlanırken bir hata oluştu: {str(e)}"
            )

    def validate_inputs(self):
        if self.files_list.count() == 0:
            QMessageBox.warning(self, "Hata", "Lütfen en az bir dosya seçin!")
            return False
            
        if not (self.youtube_radio.isChecked() or 
                self.instagram_radio.isChecked() or 
                self.instagram_reels_radio.isChecked() or
                self.instagram_story_radio.isChecked()):
            QMessageBox.warning(self, "Hata", "Lütfen bir platform seçin!")
            return False
            
        if (self.instagram_radio.isChecked() or 
            self.instagram_reels_radio.isChecked() or
            self.instagram_story_radio.isChecked()):
            if not self.insta_username.text() or not self.insta_password.text():
                QMessageBox.warning(
                    self, 
                    "Hata", 
                    "Lütfen Instagram kullanıcı adı ve şifresini girin!"
                )
                return False
                
        if self.interval_hours.value() == 0 and self.interval_minutes.value() == 0:
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
        self.instagram_story_radio.setChecked(False)
        self.insta_username.clear()
        self.insta_password.clear()
        self.start_date.setDateTime(QDateTime.currentDateTime())
        self.start_time.setTime(QTime.currentTime())
        self.interval_hours.setValue(0)
        self.interval_minutes.setValue(0)
        self.privacy_status.setCurrentIndex(1)  # Default to 'private'
        self.made_for_kids.setCurrentIndex(0)  # Default to 'Hayır'
        self.category.setCurrentIndex(0)  # Default to first category
        self.tags.clear()

    def load_scheduled_posts(self):
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()
            
            posts = c.execute('''
                SELECT id, platform, file_path, scheduled_time, status, 
                       title, description, privacy_status, made_for_kids, category, tags
                FROM scheduled_posts 
                ORDER BY scheduled_time
            ''').fetchall()
            
            self.posts_table.setRowCount(len(posts))
            for i, post in enumerate(posts):
                self.posts_table.setItem(i, 0, QTableWidgetItem(str(post[1])))  # Platform
                self.posts_table.setItem(i, 1, QTableWidgetItem(os.path.basename(str(post[2]))))  # Dosya
                self.posts_table.setItem(i, 2, QTableWidgetItem(str(post[3])))  # Tarih/Saat
                self.posts_table.setItem(i, 3, QTableWidgetItem(str(post[4])))  # Durum
                self.posts_table.setItem(i, 4, QTableWidgetItem(str(post[5] or "")))  # Başlık
                self.posts_table.setItem(i, 5, QTableWidgetItem(str(post[6] or "")))  # Açıklama
                self.posts_table.setItem(i, 6, QTableWidgetItem(str(post[7])))  # Gizlilik
                self.posts_table.setItem(i, 7, QTableWidgetItem(str(post[8])))  # Çocuklar için mi?
                self.posts_table.setItem(i, 8, QTableWidgetItem(str(post[9] or "")))  # Kategori
                self.posts_table.setItem(i, 9, QTableWidgetItem(str(post[10] or "")))  # Etiketler
            
            conn.close()
        except Exception as e:
            print(f"Veritabanı okuma hatası: {str(e)}")
            QMessageBox.warning(self, "Hata", "Planlanan gönderiler yüklenirken bir hata oluştu!")

    def save_post_to_db(self, platform, file_path, scheduled_time, title='', description='', privacy_status='private', made_for_kids='Hayır', category='', tags=''):
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()
            
            c.execute('''INSERT INTO scheduled_posts 
                        (platform, file_path, scheduled_time, status, title, description, privacy_status, made_for_kids, category, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (platform, file_path, scheduled_time.isoformat(), 
                      "Bekliyor", title, description, privacy_status, made_for_kids, category, tags))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Veritabanı kayıt hatası: {str(e)}")
            QMessageBox.warning(self, "Hata", "Gönderi kaydedilirken bir hata oluştu!")
            return False

    def upload_youtube_video(self, file_path, title, description, privacy_status, made_for_kids, category, tags):
        try:
            if not self.youtube_credentials:
                if not self.authenticate_youtube():
                    raise Exception("YouTube kimlik doğrulaması başarısız!")
                    
            youtube = build('youtube', 'v3', credentials=self.youtube_credentials)
            
            request_body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'categoryId': category,
                    'tags': tags.split(',')
                },
                'status': {
                    'privacyStatus': privacy_status,  # 'private', 'public', 'unlisted'
                    'madeForKids': made_for_kids == "Evet"
                }
            }
            
            media_file = MediaFileUpload(
                file_path,
                chunksize=-1,
                resumable=True
            )
            
            print(f"YouTube'a yükleniyor: {title}")
            
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
                    
            print(f"YouTube'a yükleme başarılı: {title}")
            return True, response['id']
            
        except Exception as e:
            print(f"YouTube yükleme hatası: {str(e)}")
            return False, str(e)

    def authenticate_youtube(self):
        try:
            SCOPES = [
                'https://www.googleapis.com/auth/youtube.upload',
                'https://www.googleapis.com/auth/youtube.force-ssl',
                'https://www.googleapis.com/auth/youtube.readonly'
            ]
            creds = None
            
            if os.path.exists('youtube_token.json'):
                os.remove('youtube_token.json')  # Delete existing token file to force re-authentication
                
            if os.path.exists('youtube_token.json'):
                creds = Credentials.from_authorized_user_file('youtube_token.json',creds, SCOPES)
                
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

    def fetch_youtube_categories(self):
        try:
            if not self.youtube_credentials:
                if not self.authenticate_youtube():
                    raise Exception("YouTube kimlik doğrulaması başarısız!")

            youtube = build('youtube', 'v3', credentials=self.youtube_credentials)

            request = youtube.videoCategories().list(
                part="snippet",
                regionCode="TR"
            )
            response = request.execute()

            categories = response.get('items', [])
            for category in categories:
                print(f"Category ID: {category['id']}, Title: {category['snippet']['title']}")
        
        except Exception as e:
            print(f"YouTube kategorileri alınırken hata oluştu: {str(e)}")
    def validate_video_for_reels(self, file_path):
        try:
            from moviepy.editor import VideoFileClip

            if not os.path.exists(file_path):
                raise Exception("Video dosyası bulunamadı")

            clip = VideoFileClip(file_path)

            max_duration = 90  # saniye
            min_duration = 3   # saniye
            allowed_aspect_ratios = [(9, 16), (4, 5)]
            max_size = 500 * 1024 * 1024  # 500MB

            if clip.duration > max_duration:
                raise Exception(f"Video süresi {max_duration} saniyeden az olmalıdır")
            if clip.duration < min_duration:
                raise Exception(f"Video süresi en az {min_duration} saniye olmalıdır")

            video_ratio = (clip.size[0], clip.size[1])
            if not any(abs(video_ratio[0]/video_ratio[1] - ratio[0]/ratio[1]) < 0.01 for ratio in allowed_aspect_ratios):
                raise Exception("Video 9:16 (dikey) veya 4:5 (kare) oranında olmalıdır")

            if os.path.getsize(file_path) > max_size:
                raise Exception("Video dosya boyutu 500MB'dan küçük olmalıdır")

            clip.close()
            return True, None

        except Exception as e:
            return False, str(e)

    def preprocess_video_for_reels(self, file_path):
        try:
            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, "processed_" + os.path.basename(file_path))

            clip = VideoFileClip(file_path)

            if clip.size[0]/clip.size[1] != 9/16:
                target_width = min(1080, clip.size[0])
                target_height = int(target_width * 16/9)
                clip = clip.resize((target_width, target_height))

            clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=30
            )

            clip.close()
            return output_path

        except Exception as e:
            raise Exception(f"Video önişleme hatası: {str(e)}")


    def upload_instagram_post(self, file_path, caption, is_reels=False, is_story=False):
        try:
            if not self.instagram_client:
                self.instagram_client = Client()
                self.instagram_client.login(
                    self.insta_username.text(),
                    self.insta_password.text()
                )
            
            print(f"Instagram'a yükleniyor: {os.path.basename(file_path)}")
            
            # Dosya uzantısını kontrol et
            is_video = file_path.lower().endswith('.mp4')
            
            if is_reels:
                if not is_video:
                    raise Exception("Reels için sadece MP4 formatı desteklenir!")
                    
                is_valid, error_msg = self.validate_video_for_reels(file_path)
                if not is_valid:
                    raise Exception(f"Video doğrulama hatası: {error_msg}")
                    
                try:
                    media = self.instagram_client.clip_upload(
                        file_path,
                        caption=caption,
                        extra_data={
                            "custom_accessibility_caption": "",
                            "like_and_view_counts_disabled": False,
                            "disable_comments": False
                        }
                    )
                except Exception as upload_error:
                    raise Exception(f"Reels yükleme hatası: {str(upload_error)}")
            
            elif is_story:
                if is_video:
                    media = self.instagram_client.video_upload_to_story(
                        file_path,
                        caption=caption
                    )
                else:
                    media = self.instagram_client.photo_upload_to_story(
                        file_path,
                        caption=caption
                    )
            
            else:
                if is_video:
                    media = self.instagram_client.video_upload(
                        file_path,
                        caption=caption
                    )
                else:
                    media = self.instagram_client.photo_upload(
                        file_path,
                        caption=caption
                    )
                        
            print(f"Instagram'a yükleme başarılı: {os.path.basename(file_path)}")
            return True, media.pk
                
        except Exception as e:
            print(f"Instagram yükleme hatası: {str(e)}")
            return False, str(e)

    def check_scheduled_posts(self):
        try:
            conn = sqlite3.connect('scheduler.db')
            c = conn.cursor()
            
            current_time = datetime.now()
            
            # Bekleyen gönderileri getir
            posts = c.execute('''
                SELECT id, platform, file_path, scheduled_time, status, 
                       title, description, privacy_status, made_for_kids, category, tags
                FROM scheduled_posts 
                WHERE status = 'Bekliyor' 
                AND datetime(scheduled_time) <= datetime(?)
                ORDER BY scheduled_time ASC
            ''', (current_time.isoformat(),)).fetchall()
            
            for post in posts:
                post_id, platform, file_path, scheduled_time, status, title, description, privacy_status, made_for_kids, category, tags = post
                
                # Dosyanın varlığını kontrol et
                if not os.path.exists(file_path):
                    error_status = f"Hata: Dosya bulunamadı - {file_path}"
                    c.execute('UPDATE scheduled_posts SET status = ? WHERE id = ?', 
                            (error_status, post_id))
                    continue
                
                try:
                    success = False
                    result = ""
                    processed_file = None
                    
                    # Platform bazlı yükleme işlemleri
                    if platform == "YouTube":
                        success, result = self.upload_youtube_video(
                            file_path, title, description, privacy_status, made_for_kids, category, tags
                        )
                    else:
                        is_reels = (platform == "Instagram Reels")
                        is_story = (platform == "Instagram Story")
                        
                        # Video işleme gerekiyorsa
                        if is_reels or (is_story and file_path.lower().endswith('.mp4')):
                            try:
                                processed_file = self.preprocess_video_for_reels(file_path)
                                upload_file = processed_file
                            except Exception as process_error:
                                raise Exception(f"Video işleme hatası: {str(process_error)}")
                        else:
                            upload_file = file_path
                            
                        try:
                            # Instagram yükleme işlemi
                            success, result = self.upload_instagram_post(
                                upload_file, 
                                f"{title}\n\n{description}" if title or description else "",
                                is_reels=is_reels,
                                is_story=is_story
                            )
                        finally:
                            # İşlenmiş geçici dosyayı temizle
                            if processed_file and os.path.exists(processed_file):
                                try:
                                    os.remove(processed_file)
                                except Exception as cleanup_error:
                                    print(f"Geçici dosya temizleme hatası: {str(cleanup_error)}")
                        
                    # Durumu güncelle
                    new_status = "Yüklendi" if success else f"Hata: {result}"
                    upload_time = datetime.now().isoformat()
                    
                    c.execute('''
                        UPDATE scheduled_posts 
                        SET status = ?,
                            upload_time = ?
                        WHERE id = ?
                    ''', (new_status, upload_time, post_id))
                    
                    # Başarılı yükleme logunu kaydet
                    if success:
                        print(f"Başarılı yükleme: {platform} - {os.path.basename(file_path)} - {upload_time}")
                    
                except Exception as e:
                    error_status = f"Hata: {str(e)}"
                    c.execute('''
                        UPDATE scheduled_posts 
                        SET status = ?,
                            error_message = ?,
                            last_attempt = ?
                        WHERE id = ?
                    ''', (error_status, str(e), datetime.now().isoformat(), post_id))
                    print(f"Gönderi yükleme hatası ({platform}): {str(e)}")
                
                # Her işlemden sonra değişiklikleri kaydet
                conn.commit()
            
            conn.close()
            
            # Tabloyu güncelle
            self.load_scheduled_posts()
            
        except Exception as e:
            print(f"Zamanlayıcı hatası: {str(e)}")
            if 'conn' in locals() and conn:
                conn.close()

    def start_scheduler(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_scheduled_posts)
        self.timer.start(60000)  # Her dakika kontrol et

    def get_youtube_categories(self):
        try:
            if not self.youtube_credentials:
                if not self.authenticate_youtube():
                    raise Exception("YouTube kimlik doğrulaması başarısız!")
                    
            youtube = build('youtube', 'v3', credentials=self.youtube_credentials)
            request = youtube.videoCategories().list(part="snippet", regionCode="TR")
            response = request.execute()
            
            categories = {item["snippet"]["title"]: item["id"] for item in response["items"]}
            self.category.addItems(categories.keys())
            return categories
            
        except Exception as e:
            print(f"YouTube kategorileri alınırken hata oluştu: {str(e)}")
            QMessageBox.warning(self, "Hata", "YouTube kategorileri alınırken hata oluştu!")
            return {}

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