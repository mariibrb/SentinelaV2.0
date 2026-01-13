import pandas as pd
import streamlit as st

def executar_motor_ret(writer, df_xs, df_xe, df_ger_ent, df_ger_sai, cod_cliente):
    """
    Motor RET (MG) - Cruzamento de Auditoria.
    Replica dados do sistema Domínio cruzados com XML.
    """
    try:
        st.info(f"Processando Memória RET MG: {cod_cliente}")

        # --- ABA MAPA_RET (Saídas) ---
        if not df_ger_sai.empty:
            # Padroniza NF para o cruzamento
            df_ger_sai['NF_JOIN'] = df_ger_sai['NF'].astype(str).str.lstrip('0').str.strip()
            
            if not df_xs.empty:
                df_xs['NF_JOIN'] = df_xs['NUM_NF'].astype(str).str.lstrip('0').str.strip()
                # Merge: Gerencial como base + dados do XML
                df_mapa = pd.merge(df_ger_sai, df_xs, on='NF_JOIN', how='left', suffixes=('_GER', '_XML'))
                df_mapa.drop(columns=['NF_JOIN'], inplace=True)
            else:
                df_mapa = df_ger_sai.copy()
            
            df_mapa.to_excel(writer, sheet_name='MAPA_RET', index=False)

        # --- ABA ENTRADAS_AC (Entradas) ---
        if not df_ger_ent.empty:
            df_ger_ent['NF_JOIN'] = df_ger_ent['NUM_NF'].astype(str).str.lstrip('0').str.strip()
            
            if not df_xe.empty:
                df_xe['NF_JOIN'] = df_xe['NUM_NF'].astype(str).str.lstrip('0').str.strip()
                df_ent_ac = pd.merge(df_ger_ent, df_xe, on='NF_JOIN', how='left', suffixes=('_GER', '_XML'))
                df_ent_ac.drop(columns=['NF_JOIN'], inplace=True)
            else:
                df_ent_ac = df_ger_ent.copy()
                
            df_ent_ac.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

    except Exception as e:
        st.error(f"Erro ao processar as abas RET: {e}")
