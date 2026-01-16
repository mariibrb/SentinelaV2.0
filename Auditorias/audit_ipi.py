import pandas as pd
import os

def processar_ipi(df, writer, cod_cliente=None):
    df_ipi = df.copy()

    # --- 1. CARREGAMENTO DA BASE TRIBUTÁRIA (GABARITO) ---
    caminho_base = f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    base_gabarito = pd.DataFrame()
    
    if cod_cliente and os.path.exists(caminho_base):
        try:
            # Lemos como string para não perder zeros à esquerda no match do NCM
            base_gabarito = pd.read_excel(caminho_base, dtype=str)
            base_gabarito.columns = [str(c).strip().upper() for c in base_gabarito.columns]
            if 'NCM' in base_gabarito.columns:
                base_gabarito['NCM'] = base_gabarito['NCM'].str.replace(r'\D', '', regex=True).str.strip().str.zfill(8)
        except:
            pass

    def audit_ipi_completa(r):
        # --- Dados do XML ---
        ncm = str(r.get('NCM', '')).strip().zfill(8)
        cst_xml = str(r.get('CST-IPI', '')).strip().zfill(2)
        alq_xml = float(r.get('ALQ-IPI', 0.0))
        vlr_ipi_xml = float(r.get('VLR-IPI', 0.0))
        vprod = float(r.get('VPROD', 0.0))
        
        # --- Gabarito e Regras de Esperado (O Cérebro do IPI) ---
        cst_esp = "50" # Saída Tributada (Padrão)
        alq_esp = 0.0
        
        # PASSO 1: CONSULTA À BASE DE DADOS (PRIORIDADE)
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            
            # Mapeamento dinâmico para CST IPI
            col_cst_gab = [c for c in base_gabarito.columns if 'CST' in c and 'IPI' in c]
            if col_cst_gab:
                cst_esp = str(g[col_cst_gab[0]]).strip().split('.')[0].zfill(2)
                
            # Mapeamento dinâmico para ALIQ IPI
            col_alq_gab = [c for c in base_gabarito.columns if 'ALQ' in c and 'IPI' in c]
            if col_alq_gab:
                alq_esp = float(g[col_alq_gab[0]])

        # --- CÁLCULOS DE AUDITORIA ---
        vlr_ipi_devido = round(vprod * (alq_esp / 100), 2)
        vlr_complementar = round(vlr_ipi_devido - vlr_ipi_xml, 2)
        vlr_comp_final = vlr_complementar if vlr_complementar > 0.01 else 0.0

        # --- DIAGNÓSTICOS ---
        diag_alq = "✅ OK" if abs(alq_xml - alq_esp) < 0.01 else f"❌ Erro (XML: {alq_xml}% | Esp: {alq_esp}%)"
        diag_cst = "✅ OK" if cst_xml == cst_esp else f"❌ Divergente (XML: {cst_xml} | Esp: {cst_esp})"

        status_destaque = "✅ OK"
        if cst_esp in ['50'] and vlr_ipi_xml <= 0 and alq_esp > 0: 
            status_destaque = "❌ Falta Destaque IPI"
        elif cst_esp in ['52', '53'] and vlr_ipi_xml > 0: 
            status_destaque = "⚠️ Destaque Indevido IPI"

        # --- AÇÃO CORRETIVA ---
        acao = "Nenhuma"
        fundamentacao = f"IPI em conformidade com as regras do NCM {ncm}."

        if vlr_comp_final > 0:
            acao = "Emitir NF Complementar"
            fundamentacao = f"Detectada insuficiência de IPI: R$ {vlr_comp_final}."
        elif alq_xml > alq_esp and alq_esp > 0:
            acao = "Recuperar Imposto"
            fundamentacao = f"Alíquota XML ({alq_xml}%) superior à legal ({alq_esp}%)."
        elif "❌" in diag_cst:
            acao = "Registrar CC-e"
            fundamentacao = f"A CST {cst_xml} informada não condiz com a operação esperada {cst_esp}."

        return pd.Series([
            cst_esp, alq_esp, status_destaque, diag_alq, vlr_comp_final, diag_cst, acao, fundamentacao
        ])

    # --- LISTA DE COLUNAS DE ANÁLISE ---
    analises_nomes = [
        'IPI_CST_ESPERADA', 'IPI_ALQUOTA_ESPERADA', 'IPI_STATUS_DESTAQUE', 
        'IPI_DIAG_ALQUOTA', 'VALOR_IPI_COMPLEMENTAR', 'IPI_DIAG_CST', 
        'AÇÃO_CORRETIVA_IPI', 'FUNDAMENTAÇÃO_IPI'
    ]
    
    # Aplica a inteligência
    df_ipi[analises_nomes] = df_ipi.apply(audit_ipi_completa, axis=1)

    # --- REORGANIZAÇÃO RIGOROSA DAS COLUNAS ---
    # 1. Identificamos as tags originais do XML (removendo a situação para não duplicar)
    cols_originais = [c for c in df.columns if c != 'Situação Nota']
    
    # 2. Identificamos o Status de Autenticidade
    cols_status = ['Situação Nota'] if 'Situação Nota' in df.columns else []
    
    # 3. Montamos o DataFrame final: [XML] + [SITUAÇÃO] + [ANÁLISES]
    df_final = pd.concat([df_ipi[cols_originais], df_ipi[cols_status], df_ipi[analises_nomes]], axis=1)

    # Gravação no Excel
    df_final.to_excel(writer, sheet_name='IPI_AUDIT', index=False)
