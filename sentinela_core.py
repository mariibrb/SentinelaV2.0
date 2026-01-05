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
            root = ET.fromstring(re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', f.read().decode('utf-8', errors='replace')))
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
                    "NCM": ncm, "VPROD": float(buscar('vProd', prod) or 0.0),
                    "CST-ICMS": "", "ALQ-ICMS": 0.0, "BC-ICMS": 0.0, "ICMS-ST": 0.0,
                    "CST-PIS": "", "CST-COF": "", "CST-IPI": "", "VAL-IPI": 0.0, "BC-IPI": 0.0, "ALQ-IPI": 0.0, "VAL-DIFAL": 0.0
                }
                if imp is not None:
                    # Lógica de extração de impostos restaurada
                    icms = imp.find('.//ICMS')
                    if icms is not None:
                        for n in icms:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            if n.find('pICMS') is not None: linha["ALQ-ICMS"] = float(n.find('pICMS').text)
                            if n.find('vBC') is not None: linha["BC-ICMS"] = float(n.find('vBC').text)
                    pis = imp.find('.//PIS')
                    if pis is not None:
                        for p in pis:
                            if p.find('CST') is not None: linha["CST-PIS"] = p.find('CST').text.zfill(2)
                    cof = imp.find('.//COFINS')
                    if cof is not None:
                        for c in cof:
                            if c.find('CST') is not None: linha["CST-COF"] = c.find('CST').text.zfill(2)
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_ent, df_sai, ae, as_f, ge_file, gs_file, cod_cliente=""):
    def format_brl(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    base_file = buscar_base_no_github(cod_cliente)
    
    # Carregamento de Bases
    try:
        base_icms = pd.read_excel(base_file, sheet_name='ICMS')
        base_pc = pd.read_excel(base_file, sheet_name='PIS_COFINS')
    except: base_icms = pd.DataFrame(); base_pc = pd.DataFrame()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # ABA 1: MANUAL
        pd.DataFrame({"SENTINELA": ["MANUAL DE INSTRUÇÕES", "Aba ICMS: Auditoria de Alíquotas e CST.", "Aba PIS_COFINS: Auditoria de Créditos."]}).to_excel(writer, sheet_name='MANUAL', index=False)

        # Lógica de Auditoria Restaurada conforme o motor enviado
        if not df_sai.empty and not base_icms.empty:
            df_icms_audit = df_sai.copy()
            def audit_icms(row):
                info = base_icms[base_icms.iloc[:, 0].astype(str).str.zfill(8) == row['NCM']]
                if info.empty: return pd.Series(["NCM Ausente", "Cadastrar", format_brl(0)])
                aliq_e = float(info.iloc[0, 2])
                return pd.Series(["✅ Correto" if row['ALQ-ICMS'] == aliq_e else "❌ Divergente", "Ajustar" if row['ALQ-ICMS'] != aliq_e else "OK", format_brl(aliq_e)])
            df_icms_audit[['Diagnóstico', 'Ação', 'Esperado']] = df_icms_audit.apply(audit_icms, axis=1)
            df_icms_audit.to_excel(writer, sheet_name='ICMS', index=False)

        # Lógica Gerencial Flexível
        def load_gerencial(f, aba):
            if not f: return
            df = pd.read_csv(f, sep=None, engine='python', on_bad_lines='skip')
            df.to_excel(writer, sheet_name=aba, index=False)
        
        load_gerencial(ge_file, 'Gerenc. Entradas')
        load_gerencial(gs_file, 'Gerenc. Saídas')

        if ae: pd.read_excel(ae).to_excel(writer, sheet_name='AUTENTICIDADE_ENT', index=False)
        if as_f: pd.read_excel(as_f).to_excel(writer, sheet_name='AUTENTICIDADE_SAI', index=False)

    return output.getvalue()
