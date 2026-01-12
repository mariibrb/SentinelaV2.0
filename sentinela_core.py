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

# --- MOTOR DE PROCESSAMENTO XML (SCANNER TOTAL) ---

def processar_conteudo_xml(content, dados_lista):
    try:
        xml_str = content.decode('utf-8', errors='replace')
        # Remove qualquer menção a namespace para não travar a busca
        xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
        root = ET.fromstring(xml_str)
        
        # FUNÇÃO SCANNER: Varre o nó em busca da tag, ignore onde ela esteja
        def scanner(tag_alvo, no):
            if no is None: return ""
            for elemento in no.iter():
                # Pega apenas o nome da tag (ignora o que vem antes do '}')
                if elemento.tag.split('}')[-1] == tag_alvo:
                    return elemento.text if elemento.text else ""
            return ""

        # Captura a IEST da nota toda (independente de estar no emitente ou no imposto)
        iest_da_nota = scanner('IEST', root)

        inf = root.find('.//infNFe')
        if inf is None: return 
        
        chave = inf.attrib.get('Id', '')[3:]
        n_nf = scanner('nNF', root)
        emit = root.find('.//emit')
        dest = root.find('.//dest')

        for det in root.findall('.//det'):
            prod = det.find('prod')
            imp = det.find('imposto')
            if prod is None or imp is None: continue
            
            # Se o item tiver uma IEST específica, ela manda. Se não, usa a da nota.
            iest_item = scanner('IEST', det)
            ie_final = iest_item if iest_item else iest_da_nota

            linha = {
                "CHAVE_ACESSO": str(chave).strip(),
                "NUM_NF": n_nf,
                "CNPJ_EMIT": scanner('CNPJ', emit),
                "CNPJ_DEST": scanner('CNPJ', dest),
                "CPF_DEST": scanner('CPF', dest),
                "UF_EMIT": scanner('UF', emit),
                "UF_DEST": scanner('UF', dest),
                "indIEDest": scanner('indIEDest', dest),
                "CFOP": scanner('CFOP', prod),
                "NCM": re.sub(r'\D', '', scanner('NCM', prod)).zfill(8),
                "VPROD": safe_float(scanner('vProd', prod)),
                
                # Impostos (Busca direta pela tag dentro do grupo do item)
                "ORIGEM": scanner('orig', det),
                "CST-ICMS": scanner('CST', det) or scanner('CSOSN', det),
                "BC-ICMS": safe_float(scanner('vBC', det)),
                "ALQ-ICMS": safe_float(scanner('pICMS', det)),
                "VLR-ICMS": safe_float(scanner('vICMS', det)),
                
                "CST-PIS": scanner('CST', det.find('.//PIS')) if det.find('.//PIS') is not None else "",
                "VAL-PIS": safe_float(scanner('vPIS', det)),
                "CST-COF": scanner('CST', det.find('.//COFINS')) if det.find('.//COFINS') is not None else "",
                "VAL-COF": safe_float(scanner('vCOFINS', det)),
                
                "VAL-DIFAL": safe_float(scanner('vICMSUFDest', det)) + safe_float(scanner('vFCPUFDest', det)),
                "VAL-FCP-DEST": safe_float(scanner('vFCPUFDest', det)),
                "VAL-ICMS-ST": safe_float(scanner('vICMSST', det)),
                "VAL-FCP-ST": safe_float(scanner('vFCPST', det)),
                "VAL-FCP": safe_float(scanner('vFCP', det)),
                
                # COLUNA B - IE SUBSTITUTO (Pega o que o Scanner achou)
                "IE_SUBST": str(ie_final).strip(),
                
                "VAL-IBS": safe_float(scanner('vIBS', det)),
                "VAL-CBS": safe_float(scanner('vCBS', det))
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
