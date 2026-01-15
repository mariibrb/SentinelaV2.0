import streamlit as st

def aplicar_estilo_sentinela():
    st.markdown("""
    <style>
        header {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        .stApp { background-color: #F0F2F6; }

        /* SIDEBAR BRANCA COM BORDA LARANJA */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 3px solid #FF6F00;
        }

        /* BOTÃO PÍLULA (SIDEBAR E CORPO) */
        div.stDownloadButton > button, 
        div.stButton > button {
            background: linear-gradient(135deg, #FF6F00 0%, #FF9100 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 0.7rem 1.5rem !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 15px rgba(255, 111, 0, 0.3) !important;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            width: 100% !important;
        }

        div.stDownloadButton > button:hover, 
        div.stButton > button:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 20px rgba(255, 111, 0, 0.4) !important;
        }

        /* TEXTOS E CONTAINERS */
        .titulo-principal { color: #FF6F00; font-weight: 800; font-size: 2.2rem; }
        .barra-laranja {
            height: 2px;
            background: linear-gradient(to right, #FF6F00, #FF9100, transparent);
            margin-bottom: 25px;
        }
        .status-container {
            padding: 15px;
            border-left: 5px solid #FF6F00;
            background-color: #FFFFFF;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)
