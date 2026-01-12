import pandas as pd
import streamlit as st

def executar_motor_ret(writer, df_xs, df_xe, df_ger_e, df_ger_s, cod_cliente):
    """
    Analisa os dados já processados pelo Core para o regime RET de MG.
    """
    try:
        # CRUZAMENTO SAÍDAS (MAPA RET)
        if not df_xs.empty and not df_ger_s.empty:
            df_xs['NF_JOIN'] = df_xs['NUM_NF'].astype(str).str.lstrip('0')
            df_ger_s['NF_JOIN'] = df_ger_s['NF'].astype(str).str.lstrip('0')
            
            # Aqui ele replica exatamente o gerencial cruzado com o XML
            mapa_ret = pd.merge(df_ger_s, df_xs, left_on='NF_JOIN', right_on='NF_JOIN', how='left', suffixes=('_GER', '_XML'))
            mapa_ret.to_excel(writer, sheet_name='MAPA_RET', index=False)

        # CRUZAMENTO ENTRADAS (ENTRADAS AC)
        if not df_xe.empty and not df_ger_e.empty:
            df_xe['NF_JOIN'] = df_xe['NUM_NF'].astype(str).str.lstrip('0')
            df_ger_e['NF_JOIN'] = df_ger_e['NUM_NF'].astype(str).str.lstrip('0')
            
            # Traz o arquivo da Higietop (Gerencial Entradas) cruzado com XML
            entradas_ac = pd.merge(df_ger_e, df_xe, on='NF_JOIN', how='left', suffixes=('_GER', '_XML'))
            entradas_ac.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

    except Exception as e:
        st.error(f"Falha no cruzamento do Motor RET: {e}")
