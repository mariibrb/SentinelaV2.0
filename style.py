import streamlit as st

def aplicar_estilo_premium():
    st.markdown("""
    <style>
        header {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        .stApp { background-color: #F0F2F6; }
        [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 3px solid #FF6F00; }
        
        /* O seu botão de pílula que finalmente acertamos */
        div[data-testid="stSidebar"] .stDownloadButton > button {
            background: linear-gradient(135deg, #FF6F00 0%, #FF9100 100%) !important;
            color: white !important;
            border-radius: 50px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 10px rgba(255, 111, 0, 0.3) !important;
            transition: 0.3s !important;
            width: 100% !important;
        }
        
        div[data-testid="stSidebar"] .stDownloadButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 15px rgba(255, 111, 0, 0.5) !important;
        }

        .titulo-principal { color: #FF6F00; font-family: 'Segoe UI', sans-serif; font-weight: 800; font-size: 2.2rem; }
        /* Adicione aqui todos os outros estilos que conversamos */
    </style>
    """, unsafe_allow_html=True)
