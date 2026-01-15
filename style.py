import streamlit as st

def aplicar_estilo_sentinela():
    st.markdown("""
    <style>
        /* Importando fontes e limpando padrões */
        header {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        .stApp { background-color: #E6D8C8; } /* Fundo creme sofisticado igual à imagem */

        /* SIDEBAR PREMIUM */
        [data-testid="stSidebar"] {
            background-color: #E6D8C8 !important;
            border-right: 1px solid rgba(0,0,0,0.1);
        }

        /* O BOTÃO ESTILO GARIMPEIRO (Dourado Metálico e Redondo) */
        div.stDownloadButton > button, 
        div.stButton > button {
            background: linear-gradient(180deg, #E8C866 0%, #B39233 100%) !important;
            color: #1A1A1A !important;
            border: 1px solid #8A6D1B !important;
            border-radius: 50px !important; /* Totalmente pílula */
            padding: 0.7rem 2rem !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4) !important;
            transition: all 0.2s ease-in-out !important;
            width: 100% !important;
        }

        div.stDownloadButton > button:hover, 
        div.stButton > button:hover {
            transform: scale(1.02) !important;
            box-shadow: 0 6px 12px rgba(0,0,0,0.3) !important;
            filter: brightness(1.1);
        }

        /* INPUTS E CAMPOS (Estilo da imagem) */
        .stTextInput > div > div > input {
            border-radius: 15px !important;
            border: 2px solid #FFFFFF !important;
            padding: 10px !important;
            font-weight: 800 !important;
            color: #1A1A1A !important;
        }

        /* TÍTULOS E SUBTÍTULOS */
        .titulo-sentinela {
            color: #332211;
            font-weight: 800;
            font-size: 2rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .label-custom {
            color: #332211;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }
    </style>
    """, unsafe_allow_html=True)
