import pandas as pd

def gerar_resumo_uf(df, writer):
    """
    Gera a aba DIFAL_ST_FECP filtrando pela coluna de situação da autenticidade.
    """
    # Se o DataFrame estiver vazio, cancela
    if df.empty:
        return

    # Criamos uma cópia para não estragar os dados das outras abas
    df_temp = df.copy()

    # Ajuste da Situação: 
    # O motor busca na coluna 'Situação Nota' que foi preenchida no Maestro 
    # cruzando a chave com a sua planilha de Autenticidade.
    
    # Vamos tornar o filtro mais flexível: ele aceita "Autorizada", "Autorizado", "AUTORIZADA"
    # e ignora "Cancelada", "Inutilizada" ou "Substituída".
    
    df_aut = df_temp[
        df_temp['Situação Nota'].astype(str).str.upper().str.contains('AUTORIZAD', na=False)
    ].copy()
    
    if not df_aut.empty:
        # Agrupamento por Estado e IE de Substituto
        res = df_aut.groupby(['UF_DEST', 'IE_SUBST']).agg({
            'VAL-ICMS-ST': 'sum',
            'VAL-DIFAL': 'sum',
            'VAL-FCP': 'sum',
            'VAL-FCP-ST': 'sum'
        }).reset_index()
        
        # Renomeando para o seu padrão de conferência
        res.columns = ['ESTADO (UF)', 'IE SUBSTITUTO', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']
        
        # Grava a aba solicitada
        res.to_excel(writer, sheet_name='DIFAL_ST_FECP', index=False)
    else:
        # Se ele cair aqui, significa que o texto na sua planilha de autenticidade 
        # não contém a palavra "AUTORIZADA". 
        # Vou listar os status encontrados para você ver o que o Python está lendo:
        status_encontrados = df_temp['Situação Nota'].unique().tolist()
        pd.DataFrame({
            "Aviso": ["Nenhuma nota autorizada encontrada"],
            "Status lidos na sua planilha": [str(status_encontrados)],
            "Dica": ["Verifique se na planilha de Autenticidade o status está escrito como 'Autorizada'"]
        }).to_excel(writer, sheet_name='DIFAL_ST_FECP', index=False)
