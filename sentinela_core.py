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
    if not files: return pd.DataFrame() 
    dados_lista = []
    for f in files:
        try:
            f.seek(0)
            root = ET.fromstring(re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', f.read().decode('utf-8', errors='replace')))
            inf_nfe = root.find('.//infNFe')
            chave = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                linha = {
                    "CHAVE_ACESSO": chave, 
                    "NCM_XML": re.sub(r'\D', '', prod.find('NCM').text).zfill(8) if prod.find('NCM') is not None else "",
                    "CST_ICMS_XML": "", "CST_PIS_XML": "", "CST_IPI_XML": ""
                }
                if imp is not None:
                    # ICMS
                    icms = imp.find('.//ICMS')
                    if icms is not None:
                        for n in icms:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST_ICMS_XML"] = cst.text.zfill(2)
                    # PIS
                    pis = imp.find('.//PIS')
                    if pis is not None:
                        for n in pis:
                            cst = n.find('CST')
                            if cst is not None: linha["CST_PIS_XML"] = cst.text.zfill(2)
                    # IPI
                    ipi = imp.find('.//IPI')
                    if ipi is not None:
                        for n in ipi:
                            cst = n.find('CST')
                            if cst is not None: linha["CST_IPI_XML"] = cst.text.zfill(2)
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, b_unica, ae, as_f, ge, gs, cod_cliente=""):
    base_final = buscar_base_no_github(cod_cliente)
    output = io.BytesIO()
    avisos = [] 

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # ABA 1: MANUAL (Apenas texto limpo conforme solicitado)
        pd.DataFrame({
            "INSTRUÇÕES SENTINELA": [
                "1. Aba RESUMO: Confira se todos os arquivos foram processados.",
                "2. Abas ANALISE_ICMS: Validação de CST ICMS vs Base Tributária.",
                "3. Abas ANALISE_IPI: Validação de NCM vs Tabela TIPI.",
                "4. Abas ANALISE_PISCOFINS: Validação de CST de Entrada e Saída.",
                "5. Abas GERENCIAL/AUTENTICIDADE: Dados espelhados para conferência."
            ]
        }).to_excel(writer, sheet_name='MANUAL', index=False)

        # PROCESSAMENTO DAS ANÁLISES POR TRIBUTO
        if base_final and (not df_xe.empty or not df_xs.empty):
            try:
                # Carrega as tabelas da base
                df_b_icms = pd.read_excel(base_final, sheet_name='ICMS')
                df_b_ipi = pd.read_excel(base_final, sheet_name='IPI')
                df_b_pc = pd.read_excel(base_final, sheet_name='PIS_COFINS')

                def processar_tributos(df_xml, tipo):
                    if df_xml.empty: return
                    # Análise ICMS
                    df_icms = pd.merge(df_xml, df_b_icms, left_on='NCM_XML', right_on='NCM', how='left')
                    df_icms['CHECK_ICMS'] = np.where(df_icms['CST_ICMS_XML'] == df_icms['CST (INTERNA)'].astype(str).str.zfill(2), "✅", "❌")
                    df_icms.to_excel(writer, sheet_name=f'ANALISE_ICMS_{tipo}', index=False)
                    # Análise IPI
                    df_ipi = pd.merge(df_xml, df_b_ipi, left_on='NCM_XML', right_on='NCM_TIPI', how='left')
                    df_ipi.to_excel(writer, sheet_name=f'ANALISE_IPI_{tipo}', index=False)
                    # Análise PIS/COFINS
                    df_pc = pd.merge(df_xml, df_b_pc, left_on='NCM_XML', right_on='NCM', how='left')
                    col_base = 'CST Entrada' if tipo == 'ENT' else 'CST Saída'
                    df_pc['CHECK_PC'] = np.where(df_pc['CST_PIS_XML'] == df_pc[col_base].astype(str).str.zfill(2), "✅", "❌")
                    df_pc.to_excel(writer, sheet_name=f'ANALISE_PISCOFINS_{tipo}', index=False)

                processar_tributos(df_xe, 'ENT')
                processar_tributos(df_xs, 'SAI')
            except: avisos.append("Erro ao ler abas da base tributária.")

        # ABAS DE APOIO
        if ge: pd.read_csv(ge, sep=None, engine='python').to_excel(writer, sheet_name='GERENCIAL_ENT', index=False)
        if gs: pd.read_csv(gs, sep=None, engine='python').to_excel(writer, sheet_name='GERENCIAL_SAI', index=False)
        if ae: pd.read_excel(ae).to_excel(writer, sheet_name='AUTENTICIDADE_ENT', index=False)
        if as_f: pd.read_excel(as_f).to_excel(writer, sheet_name='AUTENTICIDADE_SAI', index=False)

        # ABA DE STATUS (Última)
        pd.DataFrame({"STATUS": avisos if avisos else ["Sucesso"]}).to_excel(writer, sheet_name='RESUMO', index=False)
            
    return output.getvalue()
