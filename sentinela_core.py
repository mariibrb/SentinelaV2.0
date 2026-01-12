import pandas as pd
import io
import zipfile
import streamlit as st
import xml.etree.ElementTree as ET
import re
import os

# --- IMPORTAÇÃO DOS MÓDULOS ESPECIALISTAS ---
try:
    from audit_resumo import gerar_aba_resumo
    from audit_gerencial import gerar_abas_gerenciais
    from audit_icms import processar_icms
    from audit_ipi import processar_ipi
    from audit_pis_cofins import processar_pc
    from audit_difal import processar_difal
    from apuracao_difal import gerar_resumo_uf
except ImportError as e:
    st.error(f"Erro ao importar módulos especialistas: {e}")

# --- UTILITÁRIOS DE CONVERSÃO ---

def safe_float(v):
    if v is None or pd.isna(v): return 0.0
    txt = str(v).strip().upper()
    if txt in ['NT', '', 'N/A', 'ISENTO', 'NULL']: return 0.0
    try:
        txt = txt.replace('R$', '').replace(' ', '').replace('%', '').strip()
        if ',' in txt and '.' in txt: txt = txt.replace('.', '').replace(',', '.')
        elif ',' in txt: txt = txt.replace(',', '.')
        return round(float(txt), 4)
    except: return 0.0

# --- MOTOR DE PROCESSAMENTO XML ---

def processar_conteudo_xml(content, dados_lista):
    try:
        # 1. Decodifica e limpa ABSOLUTAMENTE tudo que pareça um Namespace
        xml_str = content.decode('utf-8', errors='replace')
        xml_str = re.sub(r'xmlns="[^"]+"', '', xml_str)
        xml_str = re.sub(r'xmlns:xsi="[^"]+"', '', xml_str)
        xml_str = re.sub(r'xsi:type="[^"]+"', '', xml_str)
        
        root = ET.fromstring(xml_str)
        
        # 2. Helper de busca universal (ignora níveis e namespaces)
        def find_anywhere(tag_name, node):
            # Procura a tag em qualquer profundidade a partir do nó fornecido
            for elem in node.iter():
                if elem.tag.split('}')[-1] == tag_name:
                    return elem.text if elem.text else ""
            return ""

        # --- CAPTURA DE DADOS DO CABEÇALHO ---
        inf = root.find('.//infNFe')
        if inf is None: return 
        
        emit = root.find('.//emit')
        dest = root.find('.//dest')
        
        # BUSCA DA IEST NO CABEÇALHO (ENDEREMIT) - BUSCA FORÇADA
        # Tentamos primeiro dentro do emitente, que é o lugar correto
        iest_final_nota = find_anywhere('IEST', emit) if emit is not None else ""
        
        chave = inf.attrib.get('Id', '')[3:] 
        n_nf = find_anywhere('nNF', root)

        # --- PROCESSAMENTO DOS ITENS ---
        for det in root.findall('.//det'):
            prod = det.find('prod')
            imp = det.find('imposto')
            if prod is None or imp is None: continue
            
            # Grupos de Impostos
            icms = imp.find('.//ICMS')
            pis = imp.find('.//PIS')
            cofins = imp.find('.//COFINS')
            ipi = imp.find('.//IPI')
            
            # Captura de Valores Interestaduais
            v_difal_dest = safe_float(find_anywhere('vICMSUFDest', imp))
            v_fcp_dest = safe_float(find_anywhere('vFCPUFDest', imp))
            
            # IEST DO ITEM: Se o sistema destacou no item, prevalece. Se não, usa a da nota.
            iest_item = find_anywhere('IEST', icms) if icms is not None else ""
            ie_subst_final = iest_item if iest_item else iest_final_nota

            linha = {
                "CHAVE_ACESSO": str(chave).strip(),
                "NUM_NF": n_nf,
                "CNPJ_EMIT": find_anywhere('CNPJ', emit),
                "CNPJ_DEST": find_anywhere('CNPJ', dest),
                "CPF_DEST": find_anywhere('CPF', dest),
                "UF_EMIT": find_anywhere('UF', emit),
                "UF_DEST": find_anywhere('UF', dest),
                "indIEDest": find_anywhere('indIEDest', dest),
                "CFOP": find_anywhere('CFOP', prod),
                "NCM": re.sub(r'\D', '', find_anywhere('NCM', prod)).zfill(8),
                "VPROD": safe_float(find_anywhere('vProd', prod)),
                
                # ICMS
                "ORIGEM": find_anywhere('orig', icms),
                "CST-ICMS": find_anywhere('CST', icms) or find_anywhere('CSOSN', icms),
                "BC-ICMS": safe_float(find_anywhere('vBC', icms)),
                "ALQ-ICMS": safe_float(find_anywhere('pICMS', icms)),
                "VLR-ICMS": safe_float(find_anywhere('vICMS', icms)),
                
                # PIS/COFINS/IPI
                "CST-PIS": find_anywhere('CST', pis),
                "VAL-PIS": safe_float(find_anywhere('vPIS', pis)),
                "CST-COF": find_anywhere('CST', cofins),
                "VAL-COF": safe_float(find_anywhere('vCOFINS', cofins)),
                "CST-IPI": find_anywhere('CST', ipi),
                "ALQ-IPI": safe_float(find_anywhere('pIPI', ipi)),
                "VAL-IPI": safe_float(find_anywhere('vIPI', ipi)),
                
                # DIFAL / ST
                "VAL-DIFAL": v_difal_dest + v_fcp_dest,
                "VAL-FCP-DEST": v_fcp_dest,
                "VAL-ICMS-ST": safe_float(find_anywhere('vICMSST', icms)),
                "BC-ICMS-ST": safe_float(find_anywhere('vBCST', icms)),
                "VAL-FCP-ST": safe_float(find_anywhere('vFCPST', icms)),
                "VAL-FCP": safe_float(find_anywhere('vFCP', icms)),
                
                # COLUNA B - IE SUBSTITUTO (IEST)
                "IE_SUBST": str(ie_subst_final).strip(),
                
                # Reforma
                "VAL-IBS": safe_float(find_anywhere('vIBS', imp)),
                "VAL-CBS": safe_float(find_anywhere('vCBS', imp))
            }
            dados_lista.append(linha)
    except: pass

def extrair_dados_xml(files):
    dados_lista = []
    if not files: return pd.DataFrame()
    lista_trabalho = files if isinstance(files, list) else [files]
    for f in lista_trabalho:
        try:
            with zipfile.ZipFile(f) as z:
                for filename in z.namelist():
                    if filename.lower().endswith('.xml'):
                        with z.open(filename) as xml_file:
                            processar_conteudo_xml(xml_file.read(), dados_lista)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        try: gerar_aba_resumo(writer)
        except: pass
        try: gerar_abas_gerenciais(writer, ge, gs)
        except: pass

        if not df_xs.empty:
            st_map = {}
            if as_f:
                try:
                    f_auth_list = as_f if isinstance(as_f, list) else [as_f]
                    for f_auth in f_auth_list:
                        f_auth.seek(0)
                        df_auth = pd.read_excel(f_auth, header=None) if f_auth.name.endswith('.xlsx') else pd.read_csv(f_auth, header=None, sep=None, engine='python', on_bad_lines='skip')
                        df_auth[0] = df_auth[0].astype(str).str.replace('NFe', '').str.strip()
                        st_map.update(df_auth.set_index(0)[5].to_dict())
                except: pass
            
            df_xs['Situação Nota'] = df_xs['CHAVE_ACESSO'].map(st_map).fillna('⚠️ N/Encontrada')
            processar_icms(df_xs, writer, cod_cliente)
            processar_ipi(df_xs, writer, cod_cliente)
            processar_pc(df_xs, writer, cod_cliente, regime)
            processar_difal(df_xs, writer)
            gerar_resumo_uf(df_xs, writer)
    return output.getvalue()

def main(): pass
if __name__ == "__main__": main()
