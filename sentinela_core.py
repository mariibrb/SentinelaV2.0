import pandas as pd
import io
import zipfile
import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
from datetime import datetime

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
    st.error(f"Erro Crítico de Dependência: {e}")

# --- UTILITÁRIOS DE CONVERSÃO MAXIMALISTA ---

def safe_float(v):
    """Converte valores do XML para float com alta tolerância e precisão fiscal."""
    if v is None or pd.isna(v):
        return 0.0
    txt = str(v).strip().upper()
    if txt in ['NT', '', 'N/A', 'ISENTO', 'NULL', 'NONE']:
        return 0.0
    try:
        txt = txt.replace('R$', '').replace(' ', '').replace('%', '').strip()
        if ',' in txt and '.' in txt:
            txt = txt.replace('.', '').replace(',', '.')
        elif ',' in txt:
            txt = txt.replace(',', '.')
        return round(float(txt), 4)
    except (ValueError, TypeError):
        return 0.0

# --- MOTOR DE PROCESSAMENTO XML ---

def processar_conteudo_xml(content, dados_lista):
    """
    Analisa o XML removendo namespaces e mapeando todas as tags fiscais.
    Varre o arquivo recursivamente para encontrar a IEST no cabeçalho ou itens.
    """
    try:
        xml_str = content.decode('utf-8', errors='replace')
        # Limpeza total de Namespaces para garantir a localização das tags
        xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
        root = ET.fromstring(xml_str)
        
        def buscar_tag_recursiva(tag_alvo, no):
            """Busca a tag em qualquer profundidade do nó para garantir captura."""
            if no is None: return ""
            for elemento in no.iter():
                if elemento.tag.split('}')[-1] == tag_alvo:
                    return elemento.text if elemento.text else ""
            return ""

        # CAPTURA GLOBAL DA IEST (AQUI PEGA O SEU NÚMERO 813032863112)
        iest_global = buscar_tag_recursiva('IEST', root) or buscar_tag_recursiva('IE_SUBST', root)

        inf = root.find('.//infNFe')
        if inf is None: return 
        
        emit = root.find('.//emit')
        dest = root.find('.//dest')
        chave = inf.attrib.get('Id', '')[3:] if inf is not None else ""
        n_nf = buscar_tag_recursiva('nNF', root)

        # Iteração sobre os Itens (det)
        for det in root.findall('.//det'):
            prod = det.find('prod')
            imp = det.find('imposto')
            if prod is None or imp is None: continue
            
            icms = imp.find('.//ICMS')
            
            # Captura DIFAL/FCP Destino
            v_difal_dest = safe_float(buscar_tag_recursiva('vICMSUFDest', imp))
            v_fcp_dest = safe_float(buscar_tag_recursiva('vFCPUFDest', imp))
            
            # Prioridade IEST: Item -> Cabeçalho
            iest_item = buscar_tag_recursiva('IEST', icms)
            ie_final = iest_item if iest_item != "" else iest_global

            linha = {
                "CHAVE_ACESSO": str(chave).strip(),
                "NUM_NF": n_nf,
                "CNPJ_EMIT": buscar_tag_recursiva('CNPJ', emit),
                "CNPJ_DEST": buscar_tag_recursiva('CNPJ', dest),
                "UF_EMIT": buscar_tag_recursiva('UF', emit),
                "UF_DEST": buscar_tag_recursiva('UF', dest),
                "CFOP": buscar_tag_recursiva('CFOP', prod),
                "NCM": re.sub(r'\D', '', buscar_tag_recursiva('NCM', prod)).zfill(8),
                "VPROD": safe_float(buscar_tag_recursiva('vProd', prod)),
                
                "ORIGEM": buscar_tag_recursiva('orig', icms),
                "CST-ICMS": buscar_tag_recursiva('CST', icms) or buscar_tag_recursiva('CSOSN', icms),
                "BC-ICMS": safe_float(buscar_tag_recursiva('vBC', icms)),
                "ALQ-ICMS": safe_float(buscar_tag_recursiva('pICMS', icms)),
                "VLR-ICMS": safe_float(buscar_tag_recursiva('vICMS', icms)),
                
                # Campos de Apuração UF
                "VAL-DIFAL": v_difal_dest + v_fcp_dest,
                "VAL-FCP-DEST": v_fcp_dest,
                "VAL-ICMS-ST": safe_float(buscar_tag_recursiva('vICMSST', imp)),
                "BC-ICMS-ST": safe_float(buscar_tag_recursiva('vBCST', imp)),
                "VAL-FCP-ST": safe_float(buscar_tag_recursiva('vFCPST', imp)),
                "VAL-FCP": safe_float(buscar_tag_recursiva('vFCP', imp)),
                
                # --- COLUNA B (IEST) ---
                "IE_SUBST": str(ie_final).strip(),
                
                # Reforma Tributária
                "VAL-IBS": safe_float(buscar_tag_recursiva('vIBS', imp)),
                "VAL-CBS": safe_float(buscar_tag_recursiva('vCBS', imp))
            }
            dados_lista.append(linha)
            
    except Exception as e:
        pass

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
                        df_auth = pd.read_excel(f_auth, header=None) if f_auth.name.endswith('.xlsx') else pd.read_csv(f_auth, header=None, sep=None, engine='python')
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
