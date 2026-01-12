import pandas as pd
import io, zipfile, streamlit as st
import xml.etree.ElementTree as ET
import re

# Importação dos Especialistas
from audit_resumo import gerar_aba_resumo
from audit_gerencial import gerar_abas_gerenciais
from audit_icms import processar_icms
from audit_ipi import processar_ipi
from audit_pis_cofins import processar_pc
from audit_difal import processar_difal
from audit_resumo_uf import gerar_resumo_uf 

def safe_float(v):
    if v is None or pd.isna(v) or str(v).strip().upper() in ['NT', '']: return 0.0
    try:
        txt = str(v).replace('R$', '').replace(' ', '').replace('%', '').strip()
        if ',' in txt and '.' in txt: txt = txt.replace('.', '').replace(',', '.')
        elif ',' in txt: txt = txt.replace(',', '.')
        return round(float(txt), 4)
    except: return 0.0

def processar_conteudo_xml(content, dados_lista):
    try:
        xml_str = content.decode('utf-8', errors='replace')
        xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
        root = ET.fromstring(xml_str)
        
        def tag_val(t, n):
            v = n.find(f'.//{t}')
            return v.text if v is not None and v.text else ""
        
        def rec_val(n, ts):
            if n is None: return 0.0
            for t in ts:
                v = n.find(f'.//{t}')
                if v is not None: return safe_float(v.text)
            return 0.0
        
        inf = root.find('.//infNFe'); emit = root.find('.//emit'); dest = root.find('.//dest')
        chave = inf.attrib.get('Id', '')[3:] if inf is not None else ""
        
        for det in root.findall('.//det'):
            prod = det.find('prod'); imp = det.find('imposto')
            icms = imp.find('.//ICMS') if imp is not None else None
            
            # --- CORREÇÃO CRÍTICA: CAPTURA DE DIFAL PARA CONTRIBUINTE (6102) E NÃO-CONTRIBUINTE ---
            # vICMSPart é a tag onde o DIFAL se esconde em vendas para CNPJ (Contribuinte)
            v_difal_base = rec_val(imp, ['vICMSUFDest', 'vICMSPart', 'vICMSDIFAL'])
            v_fcp_partilha = rec_val(imp, ['vFCPUFDest', 'vFCPPart'])
            
            linha = {
                "CHAVE_ACESSO": str(chave).strip(), "NUM_NF": tag_val('nNF', root),
                "CNPJ_EMIT": tag_val('CNPJ', emit), "CNPJ_DEST": tag_val('CNPJ', dest), "CPF_DEST": tag_val('CPF', dest),
                "UF_EMIT": tag_val('UF', emit), "UF_DEST": tag_val('UF', dest),
                "indIEDest": tag_val('indIEDest', dest), "CFOP": tag_val('CFOP', prod),
                "NCM": re.sub(r'\D', '', tag_val('NCM', prod)).zfill(8), "VPROD": safe_float(tag_val('vProd', prod)),
                "ORIGEM": tag_val('orig', icms) if icms is not None else "", 
                "CST-ICMS": tag_val('CST', icms).zfill(2) if icms is not None else "00",
                "BC-ICMS": rec_val(imp, ['vBC']), "ALQ-ICMS": rec_val(imp, ['pICMS']), "VLR-ICMS": rec_val(imp, ['vICMS']),
                "CST-PIS": tag_val('CST', imp.find('.//PIS')) if imp.find('.//PIS') is not None else "", 
                "VAL-PIS": rec_val(imp.find('.//PIS'), ['vPIS']),
                "CST-COF": tag_val('CST', imp.find('.//COFINS')) if imp.find('.//COFINS') is not None else "", 
                "VAL-COF": rec_val(imp.find('.//COFINS'), ['vCOFINS']),
                "CST-IPI": tag_val('CST', imp.find('.//IPI')) if imp.find('.//IPI') is not None else "", 
                "ALQ-IPI": rec_val(imp.find('.//IPI'), ['pIPI']), "VAL-IPI": rec_val(imp, ['vIPI']),
                "VAL-DIFAL": v_difal_base + v_fcp_partilha, # SOMA TUDO PARA BATER COM A GUIA
                "VAL-FCP-DEST": v_fcp_partilha,
                "VAL-ICMS-ST": rec_val(imp, ['vICMSST']), "BC-ICMS-ST": rec_val(imp, ['vBCST']),
                "VAL-FCP-ST": rec_val(imp, ['vFCPST']), "VAL-FCP": rec_val(imp, ['vFCP']),
                "IE_SUBST": tag_val('IEST', icms) if icms is not None else "",
                "VAL-IBS": rec_val(imp, ['vIBS']), "VAL-CBS": rec_val(imp, ['vCBS']),
                "Situação Nota": "" 
            }
            dados_lista.append(linha)
    except: pass

def extrair_dados_xml(f):
    dados_lista = []
    if not f: return pd.DataFrame()
    with zipfile.ZipFile(f) as z:
        for filename in z.namelist():
            if filename.endswith('.xml'):
                with z.open(filename) as xml_file: processar_conteudo_xml(xml_file.read(), dados_lista)
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        gerar_aba_resumo(writer)
        gerar_abas_gerenciais(writer, ge, gs)

        if not df_xs.empty:
            st_map = {}
            if as_f:
                try:
                    as_f.seek(0)
                    if as_f.name.endswith('.xlsx'): df_auth = pd.read_excel(as_f, header=None)
                    else: df_auth = pd.read_csv(as_f, header=None, sep=None, engine='python', on_bad_lines='skip')
                    df_auth[0] = df_auth[0].astype(str).str.replace('NFe', '').str.strip()
                    st_map = df_auth.set_index(0)[5].to_dict()
                except: pass
            
            df_xs['Situação Nota'] = df_xs['CHAVE_ACESSO'].map(st_map).fillna('⚠️ N/Encontrada')
            
            # Auditorias
            processar_icms(df_xs, writer, cod_cliente)
            processar_ipi(df_xs, writer)
            processar_pc(df_xs, writer, cod_cliente)
            processar_difal(df_xs, writer)
            gerar_resumo_uf(df_xs, writer) 

    return output.getvalue()

# --- ABAIXO ESTÁ A PARTE QUE GERA A LISTA NO STREAMLIT ---
# Certifique-se de que o seu código de interface (geralmente no final do arquivo ou no main.py)
# tenha a nova empresa incluída aqui:

def main():
    st.title("Auditor Fiscal XML")
    
    # REGISTRE A NOVA EMPRESA AQUI PARA ELA APARECER NA LISTA
    empresas = {
        "Selecione uma empresa": "0",
        "Empresa Original": "COD_1",
        "Nova Empresa": "COD_2"  # <--- Adicione a nova aqui
    }
    
    label_selecionada = st.selectbox("Escolha a Base Tributária", list(empresas.keys()))
    cod_cliente = empresas[label_selecionada]
    
    # Restante do código de upload e botão de processar...
