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
    from RET.motor_ret import executar_motor_ret
except ImportError as e:
    st.error(f"Erro Crítico de Dependência: {e}")

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
        xml_str = content.decode('utf-8', errors='replace')
        xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
        root = ET.fromstring(xml_str)
        
        def buscar_tag_recursiva(tag_alvo, no):
            if no is None: return ""
            for elemento in no.iter():
                if elemento.tag.split('}')[-1] == tag_alvo:
                    return elemento.text if elemento.text else ""
            return ""

        iest_no_xml = buscar_tag_recursiva('IEST', root) or buscar_tag_recursiva('IE_SUBST', root)
        inf = root.find('.//infNFe')
        if inf is None: return 
        
        emit = root.find('.//emit')
        dest = root.find('.//dest')
        chave = inf.attrib.get('Id', '')[3:] if inf is not None else ""
        n_nf = buscar_tag_recursiva('nNF', root)

        for det in root.findall('.//det'):
            prod = det.find('prod'); imp = det.find('imposto')
            if prod is None or imp is None: continue
            
            v_difal_dest = safe_float(buscar_tag_recursiva('vICMSUFDest', imp))
            v_fcp_dest = safe_float(buscar_tag_recursiva('vFCPUFDest', imp))
            
            iest_item = buscar_tag_recursiva('IEST', det.find('.//ICMS'))
            ie_final = iest_item if iest_item != "" else iest_no_xml

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
                "ORIGEM": buscar_tag_recursiva('orig', det.find('.//ICMS')),
                "CST-ICMS": buscar_tag_recursiva('CST', det.find('.//ICMS')) or buscar_tag_recursiva('CSOSN', det.find('.//ICMS')),
                "VAL-DIFAL": v_difal_dest + v_fcp_dest,
                "VAL-FCP-DEST": v_fcp_dest,
                "VAL-ICMS-ST": safe_float(buscar_tag_recursiva('vICMSST', imp)),
                "BC-ICMS-ST": safe_float(buscar_tag_recursiva('vBCST', imp)),
                "VAL-FCP-ST": safe_float(buscar_tag_recursiva('vFCPST', imp)),
                "VAL-FCP": safe_float(buscar_tag_recursiva('vFCP', imp)),
                "IE_SUBST": str(ie_final).strip(),
                "VAL-IBS": safe_float(buscar_tag_recursiva('vIBS', imp)),
                "VAL-CBS": safe_float(buscar_tag_recursiva('vCBS', imp))
            }
            dados_lista.append(linha)
    except: pass

def extrair_dados_xml(files):
    dados_lista = []
    if not files: return pd.DataFrame()
    lista_trabalho = files if isinstance(files, list) else [files]
    for f in lista_trabalho:
        try:
            if f.name.lower().endswith('.xml'):
                f.seek(0)
                processar_conteudo_xml(f.read(), dados_lista)
            elif f.name.lower().endswith('.zip'):
                f.seek(0)
                with zipfile.ZipFile(f) as z:
                    for filename in z.namelist():
                        if filename.lower().endswith('.xml'):
                            with z.open(filename) as xml_file:
                                processar_conteudo_xml(xml_file.read(), dados_lista)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret):
    output = io.BytesIO()
    
    # Cabeçalhos exatos conforme sua solicitação
    cols_ent = ["NUM_NF","DATA_EMISSAO","CNPJ","UF","VLR_NF","AC","CFOP","COD_PROD","DESCR","NCM","UNID","VUNIT","QTDE","VPROD","DESC","FRETE","SEG","DESP","VC","CST-ICMS","BC-ICMS","VLR-ICMS","BC-ICMS-ST","ICMS-ST","VLR_IPI","CST_PIS","BC_PIS","VLR_PIS","CST_COF","BC_COF","VLR_COF"]
    cols_sai = ["NF","DATA_EMISSAO","CNPJ","Ufp","VC","AC","CFOP","COD_ITEM","DESC_ITEM","NCM","UND","VUNIT","QTDE","VITEM","DESC","FRETE","SEG","OUTRAS","VC_ITEM","CST","BC_ICMS","ALIQ_ICMS","ICMS","BC_ICMSST","ICMSST","IPI","CST_PIS","BC_PIS","PIS","CST_COF","BC_COF","COF"]

    def ler_dominio_limpo(arquivos, colunas_alvo):
        if arquivos is None: return pd.DataFrame()
        lista = arquivos if isinstance(arquivos, list) else [arquivos]
        dfs = []
        for f in lista:
            f.seek(0)
            # Lemos forçando separador para evitar o "formato estranho"
            # header=None para ignorar cabeçalhos originais e names para aplicar os seus
            df = pd.read_csv(f, sep=None, engine='python', encoding='latin1', on_bad_lines='skip', header=None, names=colunas_alvo, dtype=str)
            # Limpa espaços em branco que o sistema da domínio costuma exportar
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    # Core alimenta os gerenciais com as colunas corretas
    df_ger_ent = ler_dominio_limpo(ge, cols_ent)
    df_ger_sai = ler_dominio_limpo(gs, cols_sai)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        try: gerar_aba_resumo(writer)
        except: pass
        
        # Criação das abas com a réplica exata e cabeçalhos solicitados
        if not df_ger_ent.empty:
            df_ger_ent.to_excel(writer, sheet_name='GERENCIAL_ENTRADAS', index=False)
        if not df_ger_sai.empty:
            df_ger_sai.to_excel(writer, sheet_name='GERENCIAL_SAIDAS', index=False)

        if is_ret:
            try:
                executar_motor_ret(writer, df_xs, df_xe, df_ger_ent, df_ger_sai, cod_cliente)
            except Exception as e:
                st.error(f"Erro no Motor RET: {e}")

        if not df_xs.empty:
            st_map = {}
            if as_f:
                try:
                    for f in (as_f if isinstance(as_f, list) else [as_f]):
                        f.seek(0)
                        df_a = pd.read_excel(f, header=None) if f.name.endswith('.xlsx') else pd.read_csv(f, header=None, sep=None, engine='python')
                        df_a[0] = df_a[0].astype(str).str.replace('NFe', '').str.strip()
                        st_map.update(df_a.set_index(0)[5].to_dict())
                except: pass
            
            df_xs['Situação Nota'] = df_xs['CHAVE_ACESSO'].map(st_map).fillna('⚠️ N/Encontrada')
            processar_icms(df_xs, writer, cod_cliente)
            processar_ipi(df_xs, writer, cod_cliente)
            processar_pc(df_xs, writer, cod_cliente, regime)
            processar_difal(df_xs, writer)
            gerar_resumo_uf(df_xs, writer, df_xe) 
            
    return output.getvalue()
