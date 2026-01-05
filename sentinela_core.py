import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re, io, requests, streamlit as st

def buscar_base_no_github(cod_cliente):
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    if not token or not cod_cliente: return None
    url = f"https://api.github.com/repos/{repo}/contents/Bases_Tributárias"
    headers = {"Authorization": f"token {token}"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            for item in res.json():
                if item['name'].startswith(str(cod_cliente)):
                    f_res = requests.get(item['download_url'], headers=headers)
                    return io.BytesIO(f_res.content)
    except: pass
    return None

def extrair_dados_xml(files):
    dados_lista = []
    if not files: return pd.DataFrame()
    for f in files:
        try:
            f.seek(0)
            texto_xml = f.read().decode('utf-8', errors='replace')
            texto_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', texto_xml)
            root = ET.fromstring(texto_xml)
            def buscar(caminho, raiz=root):
                alvo = raiz.find(f'.//{caminho}')
                return alvo.text if alvo is not None and alvo.text is not None else ""
            inf_nfe = root.find('.//infNFe')
            chave = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                linha = {
                    "CHAVE_ACESSO": chave, "NUM_NF": buscar('nNF'),
                    "DATA_EMISSAO": pd.to_datetime(buscar('dhEmi')).replace(tzinfo=None) if buscar('dhEmi') else None,
                    "UF_EMIT": buscar('UF', root.find('.//emit')), "UF_DEST": buscar('UF', root.find('.//dest')),
                    "NCM": re.sub(r'\D', '', buscar('NCM', prod)).zfill(8),
                    "VPROD": float(buscar('vProd', prod) or 0.0), "CST-ICMS": "", "ALQ-ICMS": 0.0,
                    "CST-PIS": "", "CST-IPI": "", "ALQ-IPI": 0.0, "ICMS-ST": 0.0
                }
                if imp is not None:
                    icms = imp.find('.//ICMS'); pis = imp.find('.//PIS'); ipi = imp.find('.//IPI')
                    if icms is not None:
                        for n in icms:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('pICMS') is not None: linha["ALQ-ICMS"] = float(n.find('pICMS').text)
                            if n.find('vICMSST') is not None: linha["ICMS-ST"] = float(n.find('vICMSST').text)
                    if pis is not None:
                        for p in pis:
                            if p.find('CST') is not None: linha["CST-PIS"] = p.find('CST').text.zfill(2)
                    if ipi is not None:
                        cst_i = ipi.find('.//CST')
                        if cst_i is not None: linha["CST-IPI"] = cst_i.text.zfill(2)
                        if ipi.find('.//pIPI') is not None: linha["ALQ-IPI"] = float(ipi.find('.//pIPI').text)
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_ent, df_sai, ae_f, as_f, ge_f, gs_f, cod_cliente=""):
    def format_brl(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    base_file = buscar_base_no_github(cod_cliente)
    
    try:
        base_icms = pd.read_excel(base_file, sheet_name='ICMS')
        base_icms['NCM_KEY'] = base_icms.iloc[:, 0].astype(str).str.zfill(8)
        base_pc = pd.read_excel(base_file, sheet_name='PIS_COFINS')
        base_pc['NCM_KEY'] = base_pc.iloc[:, 0].astype(str).str.zfill(8)
        base_ipi = pd.read_excel(base_file, sheet_name='IPI')
        base_ipi['NCM_KEY'] = base_ipi.iloc[:, 0].astype(str).str.zfill(8)
    except: base_icms = pd.DataFrame(); base_pc = pd.DataFrame(); base_ipi = pd.DataFrame()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 1. MANUAL
        pd.DataFrame({"INSTRUÇÕES": ["Confira o Resumo para identificar todas as notas com erros de uma só vez."]}).to_excel(writer, sheet_name='MANUAL', index=False)

        # Cruzamento Autenticidade
        def cruzar_aut(df, f):
            if df.empty or not f: return df
            try:
                df_a = pd.read_excel(f)
                return pd.merge(df, df_a[['Chave de Acesso', 'Situação']], left_on='CHAVE_ACESSO', right_on='Chave de Acesso', how='left')
            except: return df
        df_ent = cruzar_aut(df_ent, ae_f); df_sai = cruzar_aut(df_sai, as_f)

        # PROCESSAMENTO E COLETA DE ERROS
        lista_erros = []
        if not df_sai.empty:
            # Auditoria ICMS
            df_i = df_sai.copy()
            ncm_st = df_ent[(df_ent['CST-ICMS']=="60") | (df_ent['ICMS-ST'] > 0)]['NCM'].unique().tolist() if not df_ent.empty else []
            def audit_icms(row):
                info = base_icms[base_icms['NCM_KEY'] == row['NCM']]
                st_e = "✅ ST Localizado" if row['NCM'] in ncm_st else "❌ Sem ST"
                status = row.get('Situação', '⚠️ Não Verificado')
                if info.empty: 
                    lista_erros.append({"NF": row['NUM_NF'], "Erro": "ICMS: NCM Ausente na Base"})
                    return pd.Series([status, st_e, "❌ NCM Ausente", format_brl(row['VPROD'])])
                aliq_e = float(info.iloc[0, 2]) if row['UF_EMIT'] == row['UF_DEST'] else 12.0
                diag = "✅ Correto" if abs(row['ALQ-ICMS'] - aliq_e) < 0.01 else "❌ Divergente"
                if diag != "✅ Correto": lista_erros.append({"NF": row['NUM_NF'], "Erro": f"ICMS: Alíquota divergente ({row['ALQ-ICMS']}% vs {aliq_e}%)"})
                return pd.Series([status, st_e, diag, format_brl(row['VPROD'])])
            df_i[['Status Nota', 'ST na Entrada', 'Diagnóstico ICMS', 'Valor']] = df_i.apply(audit_icms, axis=1)
            df_i.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)

            # Auditoria PIS_COFINS
            df_pc = df_sai.copy()
            def audit_pc(row):
                info = base_pc[base_pc['NCM_KEY'] == row['NCM']]
                if info.empty: 
                    lista_erros.append({"NF": row['NUM_NF'], "Erro": "P/C: NCM Ausente na Base"})
                    return pd.Series(["❌ NCM Ausente", "Cadastrar"])
                cc_e = str(info.iloc[0, 2]).zfill(2)
                diag = "✅ Correto" if str(row['CST-PIS']) == cc_e else "❌ Divergente"
                if diag != "✅ Correto": lista_erros.append({"NF": row['NUM_NF'], "Erro": f"P/C: CST Divergente ({row['CST-PIS']} vs {cc_e})"})
                return pd.Series([diag, f"Esperado: {cc_e}" if diag != "✅ Correto" else "OK"])
            df_pc[['Diagnóstico PIS/COFINS', 'Ação']] = df_pc.apply(audit_pc, axis=1)
            df_pc.to_excel(writer, sheet_name='PIS_COFINS_AUDIT', index=False)

        # ABA RESUMO CONSOLIDADA
        df_resumo = pd.DataFrame(lista_erros) if lista_erros else pd.DataFrame({"NF": ["-"], "Erro": ["Nenhuma nota com erro encontrada."]})
        df_resumo.to_excel(writer, sheet_name='RESUMO', index=False)

    return output.getvalue()
