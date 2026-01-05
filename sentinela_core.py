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
                    "UF_EMIT": buscar('UF', root.find('.//emit')), "UF_DEST": buscar('UF', root.find('.//dest')),
                    "NCM": re.sub(r'\D', '', buscar('NCM', prod)).zfill(8),
                    "VPROD": float(buscar('vProd', prod) or 0.0), "CST-ICMS": "", "ALQ-ICMS": 0.0,
                    "CST-PIS": "", "CST-COF": "", "ICMS-ST": 0.0
                }
                if imp is not None:
                    icms = imp.find('.//ICMS')
                    if icms is not None:
                        for n in icms:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('pICMS') is not None: linha["ALQ-ICMS"] = float(n.find('pICMS').text)
                            if n.find('vICMSST') is not None: linha["ICMS-ST"] = float(n.find('vICMSST').text)
                    pis = imp.find('.//PIS')
                    if pis is not None:
                        for p in pis:
                            if p.find('CST') is not None: linha["CST-PIS"] = p.find('CST').text.zfill(2)
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
    except: base_icms = pd.DataFrame(); base_pc = pd.DataFrame()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # ABA 1: MANUAL COMPLETO
        pd.DataFrame({
            "CAMPO": ["Status Autenticidade", "Diagnóstico (ICMS)", "ST na Entrada"],
            "DESCRIÇÃO": [
                "Verifica se a nota está CANCELADA ou AUTORIZADA via cruzamento de protocolos.",
                "Validação de alíquota vs Base Tributária.",
                "Confirma se houve retenção de ST na entrada do produto."
            ]
        }).to_excel(writer, sheet_name='MANUAL', index=False)

        # Lógica de Cruzamento com Autenticidade (Canceladas)
        def cruzar_status(df_xml, file_aut):
            if df_xml.empty or not file_aut: return df_xml
            try:
                df_a = pd.read_excel(file_aut)
                # Cruzamento por Chave de Acesso para ver o Status real da nota
                df_xml = pd.merge(df_xml, df_a[['Chave de Acesso', 'Situação']], left_on='CHAVE_ACESSO', right_on='Chave de Acesso', how='left')
                return df_xml
            except: return df_xml

        df_ent = cruzar_status(df_ent, ae_f); df_sai = cruzar_status(df_sai, as_f)

        # ANÁLISES
        if not df_sai.empty:
            df_i = df_sai.copy()
            ncm_st = df_ent[(df_ent['CST-ICMS']=="60") | (df_ent['ICMS-ST'] > 0)]['NCM'].unique().tolist() if not df_ent.empty else []
            def audit_icms(row):
                info = base_icms[base_icms['NCM_KEY'] == row['NCM']]
                st_e = "✅ ST Localizado" if row['NCM'] in ncm_st else "❌ Sem ST"
                status_n = row.get('Situação', '⚠️ Não Verificado')
                if info.empty: return pd.Series([status_n, st_e, "❌ NCM Ausente", format_brl(row['VPROD'])])
                aliq_e = float(info.iloc[0, 2]) if row['UF_EMIT'] == row['UF_DEST'] else 12.0
                diag = "✅ Correto" if abs(row['ALQ-ICMS'] - aliq_e) < 0.01 else "❌ Divergente"
                return pd.Series([status_n, st_e, diag, format_brl(row['VPROD'])])
            df_i[['Status Nota', 'ST na Entrada', 'Diagnóstico', 'Valor']] = df_i.apply(audit_icms, axis=1)
            df_i.to_excel(writer, sheet_name='ANALISE_ICMS', index=False)

        # GERENCIAIS FLEXÍVEIS
        def load_g(f, aba, cols):
            if not f: return
            try:
                raw = f.read().decode('utf-8-sig', errors='replace'); f.seek(0)
                sep = ';' if raw.count(';') > raw.count(',') else ','
                df = pd.read_csv(f, sep=sep, header=None, engine='python', on_bad_lines='skip')
                if df.shape[0] > 0 and not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:]
                df = df.iloc[:, :len(cols)]; df.columns = cols
                df.to_excel(writer, sheet_name=aba, index=False)
            except: pass

        c_s = ['NF','DATA_EMISSAO','CNPJ','Ufp','VC','AC','CFOP','COD_ITEM','VUNIT','QTDE','VITEM','DESC','FRETE','SEG','OUTRAS','VC_ITEM','CST','Coluna2','Coluna3','BC_ICMS','ALIQ_ICMS','ICMS','BC_ICMSST','ICMSST','IPI','CST_PIS','BC_PIS','PIS','CST_COF','BC_COF','COF']
        c_e = ['NUM_NF','DATA_EMISSAO','CNPJ','UF','VLR_NF','AC','CFOP','COD_PROD','DESCR','NCM','UNID','VUNIT','QTDE','VPROD','DESC','FRETE','SEG','DESP','VC','CST-ICMS','Coluna2','BC-ICMS','VLR-ICMS','BC-ICMS-ST','ICMS-ST','VLR_IPI','CST_PIS','BC_PIS','VLR_PIS','CST_COF','BC_COF','VLR_COF']
        load_g(ge_f, 'Gerencial_Ent', c_e); load_g(gs_f, 'Gerencial_Sai', c_s)

        pd.DataFrame({"STATUS": ["Sucesso"] if base_file else ["Aviso: Base não localizada."]}).to_excel(writer, sheet_name='RESUMO', index=False)

    return output.getvalue()
