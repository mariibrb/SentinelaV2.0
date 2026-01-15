import pandas as pd
import os
import streamlit as st
import re

def processar_icms(df_saidas, writer, cod_cliente, df_entradas=pd.DataFrame()):
    colunas_xml_originais = list(df_saidas.columns)
    df_i = df_saidas.copy()

    # --- 1. CARREGAMENTO DO GABARITO (PRIORIDADE TOTAL) ---
    caminho_base = os.path.join("Bases_Tributárias", f"{cod_cliente}-Bases_Tributarias.xlsx")
    base_gabarito = pd.DataFrame()
    if os.path.exists(caminho_base):
        try:
            # Lemos como texto puro para match exato com os zeros que você colocou
            base_gabarito = pd.read_excel(caminho_base, dtype=str)
            base_gabarito.columns = [str(c).strip().upper() for c in base_gabarito.columns]
            
            col_ncm_gab = [c for c in base_gabarito.columns if 'NCM' in c]
            if col_ncm_gab:
                # Normaliza apenas removendo sujeira, mantendo o texto exato
                base_gabarito['NCM_KEY'] = base_gabarito[col_ncm_gab[0]].apply(lambda x: re.sub(r'\D', '', str(x)).strip())
        except Exception as e:
            st.error(f"Erro ao ler Gabarito Tributário: {e}")

    # --- 2. MAPEAMENTO DE ST NAS ENTRADAS ---
    ncms_com_st_na_compra = []
    if not df_entradas.empty:
        df_entradas['NCM_LIMP'] = df_entradas['NCM'].apply(lambda x: re.sub(r'\D', '', str(x)).strip())
        mask_st = (df_entradas['VAL-ICMS-ST'] > 0) | (df_entradas['CST-ICMS'].isin(['10', '60', '70']))
        ncms_com_st_na_compra = df_entradas[mask_st]['NCM_LIMP'].unique().tolist()

    def audit_icms_linha(r):
        uf_orig = str(r.get('UF_EMIT', '')).strip().upper()
        uf_dest = str(r.get('UF_DEST', '')).strip().upper()
        cfop = str(r.get('CFOP', '')).strip()
        # NCM do XML já vem tratado como texto pelo Core
        ncm_xml = str(r.get('NCM', '')).strip()
        
        cst_xml = str(r.get('CST-ICMS', '00')).zfill(2)
        alq_xml = float(r.get('ALQ-ICMS', 0.0))
        bc_icms_xml = float(r.get('BC-ICMS', 0.0))
        vprod = float(r.get('VPROD', 0.0))
        vlr_icms_xml = float(r.get('VLR-ICMS', 0.0))

        # VARIÁVEIS DE CONTROLE
        alq_esp = None
        cst_esp = None
        fundamentacao = ""

        # ==========================================================
        # PASSO 1: CONSULTA À BASE DE DADOS (USANDO OS NOMES DA SUA IMAGEM)
        # ==========================================================
        if not base_gabarito.empty and 'NCM_KEY' in base_gabarito.columns:
            if ncm_xml in base_gabarito['NCM_KEY'].values:
                g = base_gabarito[base_gabarito['NCM_KEY'] == ncm_xml].iloc[0]
                
                # Mapeamento para ALÍQUOTA INTERNA (Conforme sua imagem: ALIQ (INTERNA))
                if uf_orig == uf_dest:
                    col_aliq_interna = [c for c in base_gabarito.columns if 'ALIQ' in c and 'INTERNA' in c]
                    col_cst_interna = [c for c in base_gabarito.columns if 'CST' in c and 'IN' in c] # Busca CST (IN...)
                    
                    if col_aliq_interna: alq_esp = float(g[col_aliq_interna[0]])
                    if col_cst_interna: cst_esp = str(g[col_cst_interna[0]]).strip().split('.')[0].zfill(2)
                
                # Mapeamento para ALÍQUOTA INTERESTADUAL (Se existir coluna correspondente)
                else:
                    col_aliq_ext = [c for c in base_gabarito.columns if 'ALIQ' in c and ('EXT' in c or 'FORA' in c or 'INTEREST' in c)]
                    col_cst_ext = [c for c in base_gabarito.columns if 'CST' in c and ('ES' in c or 'EXT' in c)] # Busca CST (ES...)
                    
                    if col_aliq_ext: alq_esp = float(g[col_aliq_ext[0]])
                    if col_cst_ext: cst_esp = str(g[col_cst_ext[0]]).strip().split('.')[0].zfill(2)

                if alq_esp is not None:
                    fundamentacao = f"Prevalece base de dados: Alíquota {alq_esp}% para NCM {ncm_xml}."

        # ==========================================================
        # PASSO 2: REGRAS DE ST (QUANDO NÃO ACHOU NO GABARITO OU É CFOP ESPECÍFICO)
        # ==========================================================
        if alq_esp is None:
            if cfop in ['5405', '6405', '6404', '5667'] or ncm_xml in ncms_com_st_na_compra:
                cst_esp = "60"; alq_esp = 0.0
                fundamentacao = "Identificado como ST (CFOP ou Histórico de Compra)."

        # ==========================================================
        # PASSO 3: REGRAS GERAIS (ÚLTIMO RECURSO)
        # ==========================================================
        if alq_esp is None:
            if uf_orig != uf_dest:
                if str(r.get('ORIGEM', '0')) in ['1', '2', '3', '8']: alq_esp = 4.0
                else:
                    sul_sudeste = ['SP', 'RJ', 'MG', 'PR', 'RS', 'SC']
                    alq_esp = 7.0 if (uf_orig in sul_sudeste and uf_dest not in sul_sudeste + ['ES']) else 12.0
            else:
                alq_esp = 18.0
            
            if cst_esp is None: cst_esp = "00"
            fundamentacao = "Aplicada regra geral estadual (NCM não localizado na base)."

        # --- CÁLCULOS FINAIS ---
        vlr_icms_devido = round(bc_icms_xml * (alq_esp / 100), 2)
        vlr_comp_final = max(0.0, round(vlr_icms_devido - vlr_icms_xml, 2))

        diag_alq = "✅ OK" if abs(alq_xml - alq_esp) < 0.01 else f"❌ Erro (XML:{alq_xml}%|Esp:{alq_esp}%)"
        diag_cst = "✅ OK" if cst_xml == cst_esp else f"❌ Divergente (XML:{cst_xml}|Esp:{cst_esp})"
        
        status_base = "✅ Integral"
        if cst_xml in ['60', '10', '70']: status_base = "✅ ST/Retido"
        elif cst_xml == '20' or cst_esp == '20': status_base = "✅ Redução Base (CST 20)"
        elif abs(bc_icms_xml - vprod) > 0.10: status_base = "⚠️ Base Reduzida"
        
        return pd.Series([cst_esp, alq_esp, diag_cst, diag_alq, status_base, vlr_comp_final, fundamentacao])

    # --- MONTAGEM FINAL ---
    analises_nomes = ['CST_ESPERADA', 'ALQ_ESPERADA', 'DIAG_CST', 'DIAG_ALQUOTA', 'STATUS_BASE', 'ICMS_COMPLEMENTAR', 'FUNDAMENTAÇÃO']
    df_analise = df_i.apply(audit_icms_linha, axis=1)
    df_analise.columns = analises_nomes
    
    cols_xml = [c for c in colunas_xml_originais if c != 'Situação Nota']
    cols_aut = ['Situação Nota'] if 'Situação Nota' in colunas_xml_originais else []
    
    df_final = pd.concat([df_i[cols_xml], df_i[cols_aut], df_analise], axis=1)
    df_final.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)
