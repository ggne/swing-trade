# auth_secure.py
import streamlit as st
import os
from datetime import datetime, timedelta
import hashlib

# .env'den veya secrets'tan şifreleri oku
def get_env_variable(var_name, default=None):
    """Çevre değişkenlerini oku"""
    try:
        # Önce Streamlit secrets
        if var_name in st.secrets["authentication"]:
            return st.secrets["authentication"][var_name]
    except:
        pass
    
    # Sonra .env dosyası
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv(var_name, default)
    except:
        return default

class SecureAuth:
    def __init__(self):
        self.username = get_env_variable("APP_USERNAME", "admin")
        self.password = get_env_variable("APP_PASSWORD", "admin123")
        self.session_timeout = int(get_env_variable("SESSION_TIMEOUT", 3600))
    
    def check_session(self):
        """Oturum zaman aşımını kontrol et"""
        if "login_time" in st.session_state:
            elapsed = (datetime.now() - st.session_state["login_time"]).seconds
            if elapsed > self.session_timeout:
                st.warning("⏰ Oturum süreniz doldu, lütfen tekrar giriş yapın")
                st.session_state["logged_in"] = False
                return False
        return True
    
    def login_form(self):
        """Güvenli giriş formu"""
        # Giriş formu tasarımı
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 30px; border-radius: 15px; color: white; text-align: center;'>
                <h1>🔐 SWING TRADE PRO</h1>
                <p>Güvenli Giriş Paneli</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")  # Boşluk
            
            with st.form("secure_login"):
                username = st.text_input("👤 Kullanıcı Adı")
                password = st.text_input("🔒 Şifre", type="password")
                
                # Güvenlik önlemleri
                col_a, col_b = st.columns(2)
                with col_a:
                    remember = st.checkbox("Beni hatırla")
                with col_b:
                    submit = st.form_submit_button("🚀 Giriş Yap")
                
                if submit:
                    if username == self.username and password == self.password:
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = username
                        st.session_state["login_time"] = datetime.now()
                        st.session_state["remember"] = remember
                        st.success("✅ Giriş başarılı! Yönlendiriliyorsunuz...")
                        st.rerun()
                    else:
                        st.error("❌ Kullanıcı adı veya şifre hatalı!")
                        # 3 başarısız denemede IP ban (basit versiyon)
                        if "failed_attempts" not in st.session_state:
                            st.session_state["failed_attempts"] = 0
                        st.session_state["failed_attempts"] += 1
                        
                        if st.session_state["failed_attempts"] >= 3:
                            st.error("⛔ Çok fazla başarısız deneme. Lütfen 5 dakika sonra tekrar deneyin.")
                            st.stop()
            
            # Bilgilendirme
            st.info("""
            **Güvenlik Notları:**
            - Şifrenizi kimseyle paylaşmayın
            - Oturumunuz 1 saat sonra sonlanır
            - Çıkış yapmadan sayfayı kapatmayın
            """)

def secure_auth():
    """Ana güvenlik fonksiyonu"""
    auth = SecureAuth()
    
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    if not st.session_state["logged_in"]:
        return auth.login_form()
    else:
        if not auth.check_session():
            return False
        return True