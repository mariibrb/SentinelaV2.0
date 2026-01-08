import pandas as pd
import io, zipfile, streamlit as st
import xml.etree.ElementTree as ET
import re

# Importação dos Especialistas (Garantindo que todos estão aqui)
from audit_resumo import gerar_aba_resumo
from audit_gerencial import gerar_abas_gerenciais
from audit_icms import processar_icms
from audit_ipi import processar_ipi
from audit_pis_cofins import processar_pc
from audit_difal import processar_difal
from audit_resumo_uf import gerar_resumo_uf # ESTA É A ABA QUE VOCÊ PRECISA

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
            if n is None: return ""
            for e in n.iter():
                if e.tag.split('}')[-1] in ts: return e.text
            return ""
        
        inf = root.find('.//infNFe'); emit = root.find('.//emit'); dest = root.find('.//dest')
        chave = inf.attrib.get('Id', '')[3:] if inf is not None else ""
        
        for det in root.findall('.//det'):
            prod = det.find('prod'); imp = det.find('imposto')
            icms = imp.find('.//ICMS') if imp is not None else None
            
            linha = {
                "CHAVE_ACESSO": str(chave).strip(), "NUM_NF": tag_val('nNF', root),
                "CNPJ_EMIT": tag_val('CNPJ', emit), "CNPJ_DEST": tag_val('CNPJ', dest), "CPF_DEST": tag_val('CPF', dest),
                "UF_EMIT": tag_val('UF', emit), "UF_DEST": tag_val('UF', dest),
                "indIEDest": tag_val('indIEDest', dest), "CFOP": tag_val('CFOP', prod),
                "NCM": re.sub(r'\D', '', tag_val('NCM', prod)).zfill(8), "VPROD": safe_float(tag_val('vProd', prod)),
                "ORIGEM": rec_val(icms, ['orig']), "CST-ICMS": rec_val(icms, ['CST', 'CSOSN']).zfill(2),
                "BC-ICMS": safe_float(rec_val(imp, ['vBC'])), "ALQ-ICMS": safe_float(rec_val(imp, ['pICMS'])), "VLR-ICMS": safe_float(rec_val(imp, ['vICMS'])),
                "CST-PIS": rec_val(imp.find('.//PIS'), ['CST']), "VAL-PIS": safe_float(rec_val(imp.find('.//PIS'), ['vPIS'])),
                "CST-COF": rec_val(imp.find('.//COFINS'), ['CST']), "VAL-COF": safe_float(rec_val(imp.find('.//COFINS'), ['vCOFINS'])),
                "CST-IPI": rec_val(imp.find('.//IPI'), ['CST']), "ALQ-IPI": safe_float(rec_val(imp.find('.//IPI'), ['pIPI'])), "VAL-IPI": safe_float(rec_val(imp, ['vIPI'])),
                "VAL-DIFAL": safe_float(rec_val(imp, ['vICMSUFDest'])), "VAL-FCP-DEST": safe_float(rec_val(imp, ['vFCPUFDest'])),
                "VAL-ICMS-ST": safe_float(rec_val(imp, ['vICMSST'])), "BC-ICMS-ST": safe_float(rec_val(imp, ['vBCST'])),
                "VAL-FCP-ST": safe_float(rec_val(imp, ['vFCPST'])), "VAL-FCP": safe_float(rec_val(imp, ['vFCP'])),
                "IE_SUBST": tag_val('IEST', icms) if icms is not None else "",
                "VAL-IBS": safe_float(rec_val(imp, ['vIBS'])), "ALQ-IBS": safe_float(rec_val(imp, ['pIBS'])),
                "VAL-CBS": safe_float(rec_val(imp, ['vCBS'])), "ALQ-CBS": safe_float(rec_val(imp, ['pCBS']))
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
        
        # 1. ABA RESUMO
        gerar_aba_resumo(writer)
        
        # 2 e 3. GERENCIAIS
        gerar_abas_gerenciais(writer, ge, gs)

        if not df_xs.empty:
            # Autenticidade
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
            
            # Executando Auditorias (Abas 4, 5, 6, 7)
            processar_icms(df_xs, writer, cod_cliente)
            processar_ipi(df_xs, writer)
            processar_pc(df_xs, writer, cod_cliente)
            processar_difal(df_xs, writer)
            
            # --- EXECUÇÃO DA ABA 8 (DIFAL_ST_FECP) ---
            # Forçamos a chamada aqui
            gerar_resumo_uf(df_xs, writer) 

    return output.getvalue()
