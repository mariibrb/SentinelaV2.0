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
                ncm = re.sub(r'\D', '', buscar('NCM', prod)).zfill(8)
                linha = {
                    "CHAVE_ACESSO": chave, "NUM_NF": buscar('nNF'),
                    "UF_EMIT": buscar('UF', root.find('.//emit')), "UF_DEST": buscar('UF', root.find('.//dest')),
                    "CFOP": buscar('CFOP', prod), "NCM": ncm, "VPROD": float(buscar('vProd', prod) or 0.0),
                    "CST-ICMS": "", "ALQ-ICMS": 0.0, "BC-ICMS": 0.0, "VLR-ICMS": 0.0, "ICMS-ST": 0.0,
                    "CST-PIS": "", "CST-COF": "", "CST-IPI": "", "VAL-IPI": 0.0, "BC-IPI": 0.0, "VAL-DIFAL": 0.0
                }
                if imp is not None:
                    icms_n = imp.find('.//ICMS')
                    if icms_n is not None:
                        for n in icms_n:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('pICMS') is not None: linha["ALQ-ICMS"] = float(n.find('pICMS').text)
                    pis = imp.find('.//PIS')
                    if pis is not None:
                        for p in pis:
                            if p.find('CST') is not None: linha["CST-PIS"] = p.find('CST').text.zfill(2)
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_ent, df_sai, ge_file, gs_file, cod_cliente=""):
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
        df_manual = pd.DataFrame({
            "CAMPO": [
                "Diagnóstico (ICMS)", "Ação (ICMS)", "ST na Entrada", 
                "Diagnóstico (PIS/COFINS)", "Esperado (PIS/COFINS)",
                "DIFAL XML", "Status Resumo"
            ],
            "SIGNIFICADO / RETORNO": [
                "Indica se a alíquota no XML confere com a Base Tributária (✅ Correto / ❌ Divergente).",
                "Sugestão de correção (Cc-e ou Ajustar Alíquota).",
                "Verifica se houve nota de entrada com ST para este NCM (✅ Localizado / ❌ Sem ST).",
                "Validação do CST de Saída conforme regras de crédito/débito da Base.",
                "Informa qual o código de CST correto deveria constar no item.",
                "Valor do imposto interestadual localizado no XML.",
                "Confirmação se a base da empresa foi localizada no servidor GitHub."
            ]
        })
        df_manual.to_excel(writer, sheet_name='MANUAL', index=False)

        # PROCESSAMENTO TRIBUTÁRIO RESTAURADO
        if not df_sai.empty and not base_icms.empty:
            # ICMS
            df_i = df_sai.copy()
            ncm_st = df_ent[(df_ent['CST-ICMS']=="60") | (df_ent['ICMS-ST'] > 0)]['NCM'].unique().tolist() if not df_ent.empty else []
            def audit_icms(row):
                info = base_icms[base_icms['NCM_KEY'] == row['NCM']]
                st_e = "✅ ST Localizado" if row['NCM'] in ncm_st else "❌ Sem ST"
                if info.empty: return pd.Series([st_e, "❌ NCM Ausente na Base", "Cadastrar NCM"])
                aliq_e = float(info.iloc[0, 2]) if row['UF_EMIT'] == row['UF_DEST'] else 12.0
                diag = "✅ Correto" if abs(row['ALQ-ICMS'] - aliq_e) < 0.01 else "❌ Divergente"
                return pd.Series([st_e, diag, "Ajustar Alíquota" if diag != "✅ Correto" else "✅ OK"])
            df_i[['ST na Entrada', 'Diagnóstico', 'Ação']] = df_i.apply(audit_icms, axis=1)
            df_i.to_excel(writer, sheet_name='ANALISE_ICMS', index=False)

            # PIS_COFINS
            df_pc = df_sai.copy()
            def audit_pc(row):
                info = base_pc[base_pc['NCM_KEY'] == row['NCM']]
                if info.empty: return pd.Series(["❌ NCM Ausente", "Cadastrar"])
                cc_e = str(info.iloc[0, 2]).zfill(2) # Coluna CST Saída
                diag = "✅ Correto" if str(row['CST-PIS']) == cc_e else "❌ Divergente"
                return pd.Series([diag, f"Esperado: {cc_e}" if diag != "✅ Correto" else "✅ OK"])
            df_pc[['Diagnóstico', 'Ação']] = df_pc.apply(audit_pc, axis=1)
            df_pc.to_excel(writer, sheet_name='ANALISE_PISCOFINS', index=False)

        # GERENCIAIS FLEXÍVEIS (Blindados)
        def load_gerencial_flexible(f, target_cols):
            if not f: return pd.DataFrame()
            try:
                f.seek(0)
                raw = f.read().decode('utf-8-sig', errors='replace')
                sep = ';' if raw.count(';') > raw.count(',') else ','
                df = pd.read_csv(io.StringIO(raw), sep=sep, header=None, engine='python', on_bad_lines='skip')
                if df.shape[0] > 0 and not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:]
                df = df.iloc[:, :len(target_cols)]
                df.columns = target_cols
                return df
            except: return pd.DataFrame()

        c_sai = ['NF','DATA_EMISSAO','CNPJ','Ufp','VC','AC','CFOP','COD_ITEM','VUNIT','QTDE','VITEM','DESC','FRETE','SEG','OUTRAS','VC_ITEM','CST','Coluna2','Coluna3','BC_ICMS','ALIQ_ICMS','ICMS','BC_ICMSST','ICMSST','IPI','CST_PIS','BC_PIS','PIS','CST_COF','BC_COF','COF']
        c_ent = ['NUM_NF','DATA_EMISSAO','CNPJ','UF','VLR_NF','AC','CFOP','COD_PROD','DESCR','NCM','UNID','VUNIT','QTDE','VPROD','DESC','FRETE','SEG','DESP','VC','CST-ICMS','Coluna2','BC-ICMS','VLR-ICMS','BC-ICMS-ST','ICMS-ST','VLR_IPI','CST_PIS','BC_PIS','VLR_PIS','CST_COF','BC_COF','VLR_COF']
        
        load_gerencial_flexible(ge_file, c_ent).to_excel(writer, sheet_name='Gerencial_Ent', index=False)
        load_gerencial_flexible(gs_file, c_sai).to_excel(writer, sheet_name='Gerencial_Sai', index=False)

        # RESUMO
        pd.DataFrame({"STATUS": ["Sucesso"] if base_file else ["Aviso: Base não localizada no GitHub."]}).to_excel(writer, sheet_name='RESUMO', index=False)

    return output.getvalue()
