import pandas as pd
import os

def processar_ipi(df, writer, cod_cliente=None):
    df_ipi = df.copy()

    # 1. Carregamento da Base Tributária da Empresa (Gabarito)
    caminho_base = f"bases/base_tributaria_{cod_cliente}.xlsx"
    base_gabarito = pd.DataFrame()
    if cod_cliente and os.path.exists(caminho_base):
        try:
            base_gabarito = pd.read_excel(caminho_base)
            base_gabarito['NCM'] = base_gabarito['NCM'].astype(str).str.strip().str.zfill(8)
        except: pass

    def audit_ipi_completa(r):
        # --- Dados do XML ---
        ncm = str(r.get('NCM', '')).zfill(8)
        cst_xml = str(r.get('CST-IPI', '')).zfill(2)
        alq_xml = float(r.get('ALQ-IPI', 0.0))
        vlr_ipi_xml = float(r.get('VAL-IPI', 0.0))
        vprod = float(r.get('VPROD', 0.0))
        
        # --- Gabarito e Regras de Esperado ---
        cst_esp = "50" # Default (Saída Tributada)
        alq_esp = 0.0
        
        # Cruzamento com Gabarito por Empresa (Busca CST e Alíquota de IPI por NCM)
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            if 'CST_IPI_ESPERADA' in base_gabarito.columns: 
                cst_esp = str(g['CST_IPI_ESPERADA']).zfill(2)
            if 'ALQ_IPI_ESPERADA' in base_gabarito.columns: 
                alq_esp = float(g['ALQ_IPI_ESPERADA'])

        # --- CÁLCULO DO VALOR COMPLEMENTAR ---
        # Base de cálculo do IPI geralmente é o valor do produto
        vlr_ipi_devido = round(vprod * (alq_esp / 100), 2)
        vlr_complementar = round(vlr_ipi_devido - vlr_ipi_xml, 2)
        vlr_comp_final = vlr_complementar if vlr_complementar > 0.01 else 0.0

        # --- DIAGNÓSTICOS CONDICIONAIS ---
        
        # 1. Alíquota IPI
        diag_alq = "✅ OK" if abs(alq_xml - alq_esp) < 0.01 else f"❌ Erro (XML: {alq_xml}% | Esp: {alq_esp}%)"

        # 2. CST IPI
        diag_cst = "✅ OK" if cst_xml == cst_esp else f"❌ Divergente (XML: {cst_xml} | Esp: {cst_esp})"

        # 3. Status Destaque
        status_destaque = "✅ OK"
        if cst_esp in ['50'] and vlr_ipi_xml <= 0 and alq_esp > 0: 
            status_destaque = "❌ Falta Destaque IPI"
        elif cst_esp in ['52', '53'] and vlr_ipi_xml > 0: 
            status_destaque = "⚠️ Destaque Indevido IPI"

        # --- AÇÃO CORRETIVA ---
        acao = "Nenhuma"
        motivo = "IPI em conformidade."

        if vlr_comp_final > 0:
            acao = "Emitir NF Complementar"
            motivo = f"Faltou destacar R$ {vlr_comp_final} de IPI."
        elif "❌" in diag_cst:
            acao = "Registrar CC-e"
            motivo = "Correção de CST de IPI sem alteração de valores."

        return pd.Series([
            status_destaque, diag_alq, vlr_comp_final, diag_cst, acao, motivo
        ])

    # Colunas de Análise (Definição da Ordem Pós AG)
    analises = [
        'IPI_STATUS_DESTAQUE', 
        'IPI_DIAG_ALQUOTA', 
        'VALOR_IPI_COMPLEMENTAR',
        'IPI_DIAG_CST', 
        'AÇÃO_CORRETIVA_IPI', 
        'FUNDAMENTAÇÃO_IPI'
    ]
    
    df_ipi[analises] = df_ipi.apply(audit_ipi_completa, axis=1)

    # Reorganização Final das Colunas (Dados XML + Situação Nota + Análises)
    cols_xml = [c for c in df_ipi.columns if c not in analises and c != 'Situação Nota']
    df_final = df_ipi[cols_xml + ['Situação Nota'] + analises]

    # Gravação no Excel
    df_final.to_excel(writer, sheet_name='IPI_AUDIT', index=False)
