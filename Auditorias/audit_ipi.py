import pandas as pd
import os

def processar_ipi(df, writer, cod_cliente=None):
    df_ipi = df.copy()

    # --- 1. CARREGAMENTO DA BASE TRIBUTÁRIA (GABARITO) ---
    # Ajustado para o padrão de pastas que você usa
    caminho_base = f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    base_gabarito = pd.DataFrame()
    
    if cod_cliente and os.path.exists(caminho_base):
        try:
            base_gabarito = pd.read_excel(caminho_base)
            base_gabarito['NCM'] = base_gabarito['NCM'].astype(str).str.strip().str.zfill(8)
        except:
            pass

    def audit_ipi_completa(r):
        # --- Dados do XML (Conectando com as tags do Core) ---
        ncm = str(r.get('NCM', '')).zfill(8)
        cst_xml = str(r.get('CST-IPI', '')).zfill(2)
        alq_xml = float(r.get('ALQ-IPI', 0.0))
        vlr_ipi_xml = float(r.get('VLR-IPI', 0.0)) # Tag corrigida para VLR-IPI
        vprod = float(r.get('VPROD', 0.0))
        
        # --- Gabarito e Regras de Esperado (O Cérebro do IPI) ---
        cst_esp = "50" # Saída Tributada (Padrão)
        alq_esp = 0.0
        
        # Cruzamento com Gabarito (Busca CST e Alíquota de IPI por NCM)
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            
            # Tenta buscar colunas específicas de IPI no seu Excel de Gabarito
            if 'CST_IPI_ESPERADA' in base_gabarito.columns: 
                cst_esp = str(g['CST_IPI_ESPERADA']).zfill(2)
            elif 'CST_IPI' in base_gabarito.columns:
                cst_esp = str(g['CST_IPI']).zfill(2)
                
            if 'ALQ_IPI_ESPERADA' in base_gabarito.columns: 
                alq_esp = float(g['ALQ_IPI_ESPERADA'])
            elif 'ALQ_IPI' in base_gabarito.columns:
                alq_esp = float(g['ALQ_IPI'])

        # --- CÁLCULOS DE AUDITORIA ---
        # A Base de Cálculo do IPI via de regra é o Valor do Produto
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
        motivo = "IPI em conformidade com as regras do NCM."

        if vlr_comp_final > 0:
            acao = "Emitir NF Complementar"
            motivo = f"Detectada insuficiência de IPI: R$ {vlr_comp_final}."
        elif alq_xml > alq_esp and alq_esp > 0:
            acao = "Recuperar Imposto Pagado a Maior"
            motivo = f"Alíquota XML ({alq_xml}%) superior à alíquota legal ({alq_esp}%)."
        elif "❌" in diag_cst:
            acao = "Registrar CC-e"
            motivo = f"A CST {cst_xml} informada não condiz com a operação esperada {cst_esp}."

        return pd.Series([
            cst_esp, alq_esp, status_destaque, diag_alq, vlr_comp_final, diag_cst, acao, motivo
        ])

    # --- LISTA DE COLUNAS DE ANÁLISE ---
    analises = [
        'IPI_CST_ESPERADA',
        'IPI_ALQUOTA_ESPERADA',
        'IPI_STATUS_DESTAQUE', 
        'IPI_DIAG_ALQUOTA', 
        'VALOR_IPI_COMPLEMENTAR',
        'IPI_DIAG_CST', 
        'AÇÃO_CORRETIVA_IPI', 
        'FUNDAMENTAÇÃO_IPI'
    ]
    
    # Aplica a inteligência linha a linha
    df_ipi[analises] = df_ipi.apply(audit_ipi_completa, axis=1)

    # --- REORGANIZAÇÃO FINAL DAS COLUNAS ---
    # Mantém as tags do XML (incluindo as novas da reforma) e joga as análises para o fim
    cols_atuais = df_ipi.columns.tolist()
    
    # Define as colunas que devem vir no início para facilitar a leitura
    prioridade = ['NUM_NF', 'NCM', 'VPROD', 'CST-IPI', 'ALQ-IPI', 'VLR-IPI', 'VAL-IBS', 'VAL-CBS', 'Situação Nota']
    
    # Pega as demais colunas que não são análise nem prioridade
    outras_cols = [c for c in cols_atuais if c not in analises and c not in prioridade]
    
    # Monta o DataFrame final na ordem correta
    df_final = df_ipi[prioridade + outras_cols + analises]

    # Gravação no Excel
    df_final.to_excel(writer, sheet_name='IPI_AUDIT', index=False)
