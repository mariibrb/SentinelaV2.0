import pandas as pd
import os
import streamlit as st
import re

def processar_icms(df_saidas, writer, cod_cliente, df_entradas=pd.DataFrame()):
    df_i = df_saidas.copy()

    # --- 1. CARREGAMENTO DO GABARITO ---
    caminho_base = os.path.join("Bases_Tributárias", f"{cod_cliente}-Bases_Tributarias.xlsx")
    base_gabarito = pd.DataFrame()
    if os.path.exists(caminho_base):
        try:
            # Lemos forçando NCM como string
            base_gabarito = pd.read_excel(caminho_base, dtype={'NCM': str})
            base_gabarito.columns = base_gabarito.columns.str.strip().str.upper()
            # Limpeza radical de NCM (remove pontos, espaços e traços)
            base_gabarito['NCM'] = base_gabarito['NCM'].apply(lambda x: re.sub(r'\D', '', str(x)).zfill(8))
        except: pass

    # --- 2. MAPEAMENTO DE ST NAS ENTRADAS ---
    ncms_com_st_na_compra = []
    if not df_entradas.empty:
        # Normaliza NCM das entradas para bater
        df_entradas['NCM_LIMP'] = df_entradas['NCM'].apply(lambda x: re.sub(r'\D', '', str(x)).zfill(8))
        mask_st = (df_entradas['VAL-ICMS-ST'] > 0) | (df_entradas['CST-ICMS'].isin(['10', '60', '70']))
        ncms_com_st_na_compra = df_entradas[mask_st]['NCM_LIMP'].unique().tolist()

    def audit_icms_linha(r):
        uf_orig = str(r.get('UF_EMIT', '')).strip().upper()
        uf_dest = str(r.get('UF_DEST', '')).strip().upper()
        cfop = str(r.get('CFOP', '')).strip()
        # Limpa o NCM do XML
        ncm_xml = re.sub(r'\D', '', str(r.get('NCM', ''))).zfill(8)
        
        cst_xml = str(r.get('CST-ICMS', '00')).zfill(2)
        alq_xml = float(r.get('ALQ-ICMS', 0.0))
        bc_icms_xml = float(r.get('BC-ICMS', 0.0))
        vprod = float(r.get('VPROD', 0.0))
        vlr_icms_xml = float(r.get('VLR-ICMS', 0.0))

        # --- REGRAS DE OURO (VALORES ESPERADOS) ---
        alq_esp = 18.0
        cst_esp = "00"
        fundamentacao = "Regra Geral Estadual."

        # PASSO 1: VALIDAÇÃO POR CFOP DE ST (5405 / 6405 / 6404 / 5667)
        if cfop in ['5405', '6405', '6404', '5667']:
            cst_esp = "60"
            alq_esp = 0.0
            fundamentacao = "CFOP de ST: Esperado CST 60."

        # PASSO 2: CRUZAMENTO COM COMPRAS
        elif ncm_xml in ncms_com_st_na_compra:
            cst_esp = "60"
            alq_esp = 0.0
            fundamentacao = "Histórico de ST na entrada para este NCM."

        # PASSO 3: GABARITO (Soberania do seu Excel do GitHub)
        if not base_gabarito.empty and ncm_xml in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm_xml].iloc[0]
            
            # Busca alíquota no gabarito (prioridade absoluta)
            col_alq = [c for c in base_gabarito.columns if 'ALQ' in c]
            if col_alq:
                # Se houver alíquota interestadual no gabarito, usa ela. Senão usa a geral da linha.
                col_inter = [c for c in col_alq if 'INTER' in c]
                if col_inter and uf_orig != uf_dest:
                    alq_esp = float(g[col_inter[0]])
                else:
                    alq_esp = float(g[col_alq[0]])
                fundamentacao = "Alíquota e CST definidos conforme seu Gabarito Tributário."

            col_cst = [c for c in base_gabarito.columns if 'CST' in c]
            if col_cst:
                novo_cst = str(g[col_cst[0]]).strip().split('.')[0].zfill(2)
                # Mantém 60 se houver conflito óbvio de ST, senão aceita o do Gabarito
                if cst_xml == "60" and novo_cst != "60" and (cfop in ['5405', '6405'] or ncm_xml in ncms_com_st_na_compra):
                    cst_esp = "60"
                    alq_esp = 0.0
                else:
                    cst_esp = novo_cst

        # PASSO 4: LÓGICA INTERESTADUAL PADRÃO (SÓ SE NÃO TIVER GABARITO NEM ST)
        elif uf_orig != uf_dest and cst_esp not in ['60', '10']:
            if str(r.get('ORIGEM', '0')) in ['1', '2', '3', '8']: alq_esp = 4.0
            else:
                sul_sudeste = ['SP', 'RJ', 'MG', 'PR', 'RS', 'SC']
                alq_esp = 7.0 if (uf_orig in sul_sudeste and uf_dest not in sul_sudeste + ['ES']) else 12.0

        # --- CÁLCULOS E DIAGNÓSTICOS ---
        vlr_icms_devido = round(bc_icms_xml * (alq_esp / 100), 2)
        vlr_comp_final = max(0.0, round(vlr_icms_devido - vlr_icms_xml, 2))

        diag_alq = "✅ OK" if abs(alq_xml - alq_esp) < 0.01 else f"❌ Erro (XML:{alq_xml}%|Esp:{alq_esp}%)"
        diag_cst = "✅ OK" if cst_xml == cst_esp else f"❌ Divergente (XML:{cst_xml}|Esp:{cst_esp})"
        
        # Ajuste visual para CST 20
        if cst_xml == '20' or cst_esp == '20':
            status_base = "✅ Redução Base (CST 20)"
        elif cst_xml in ['60', '10', '70']:
            status_base = "✅ ST/Retido"
        else:
            status_base = "✅ Integral" if abs(bc_icms_xml - vprod) < 0.10 else "⚠️ Base Reduzida"
        
        status_destaque = "✅ OK"
        if cst_xml in ['00', '10', '20', '70'] and vlr_icms_xml <= 0 and alq_esp > 0: status_destaque = "❌ Falta Destaque"
        elif cst_xml in ['40', '41', '50', '60'] and vlr_icms_xml > 0: status_destaque = "⚠️ Destaque Indevido"

        return pd.Series([cst_esp, alq_esp, diag_cst, diag_alq, status_destaque, status_base, vlr_comp_final, fundamentacao])

    # --- EXECUÇÃO ---
    analises = ['CST_ESPERADA', 'ALQ_ESPERADA', 'DIAG_CST', 'DIAG_ALQUOTA', 'STATUS_DESTAQUE', 'STATUS_BASE', 'ICMS_COMPLEMENTAR', 'FUNDAMENTAÇÃO']
    df_i[analises] = df_i.apply(audit_icms_linha, axis=1)

    prioridade = ['NUM_NF', 'CFOP', 'NCM', 'VPROD', 'CST-ICMS', 'CST_ESPERADA', 'DIAG_CST', 'ALQ-ICMS', 'ALQ_ESPERADA', 'DIAG_ALQUOTA', 'Situação Nota']
    outras = [c for c in df_i.columns if c not in analises and c not in prioridade]
    df_final = df_i[prioridade + outras + [c for c in analises if c not in prioridade]]
    df_final.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)
