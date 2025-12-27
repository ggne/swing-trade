# mobile_auth.py - Mobil uyumlu giriş
import streamlit as st

def mobile_login():
    """Mobil için optimize edilmiş giriş"""
    # Tam ekran giriş
    st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
    
    # CSS ile güzel arayüz
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    .login-title {
        text-align: center;
        color: #333;
        font-size: 28px;
        margin-bottom: 10px;
    }
    .login-subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Giriş konteyneri
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown('<h1 class="login-title">🔐 SWING TRADE</h1>', unsafe_allow_html=True)
    st.markdown('<p class="login-subtitle">Mobil Analiz Platformu</p>', unsafe_allow_html=True)
    
    # Basit şifre
    PASSWORD = "mobile123"  # Bu şifreyi değiştirin!
    
    # PIN girişi (mobil için daha kolay)
    pin = st.text_input("📱 4 Haneli PIN:", type="password", max_chars=4)
    
    # Veya QR kodu
    st.markdown("---")
    st.caption("Veya QR kodu ile giriş yapın")
    
    # Basit QR kodu (gerçek implementasyon için qrcode kütüphanesi gerekir)
    if st.button("📷 QR Kodu Göster"):
        st.info("QR kodu özelliği premium versiyonda mevcut")
    
    if st.button("🔓 Giriş Yap"):
        if pin == PASSWORD:
            st.session_state["mobile_logged_in"] = True
            st.success("✅ Giriş başarılı!")
            st.rerun()
        else:
            st.error("❌ Yanlış PIN!")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    return st.session_state.get("mobile_logged_in", False)