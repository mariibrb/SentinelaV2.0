import pandas as pd
import io
import zipfile
import streamlit as st
import xml.etree.ElementTree as ET
import re
import os
from datetime import datetime
import openpyxl
from copy import copy

# --- IMPORTAÇÃO DOS MÓDULOS ESPECIALISTAS ---
try:
    from audit_resumo import gerar_aba_resumo
    from Auditorias.audit_icms import processar_icms
    from Auditorias.audit_ipi import processar_ipi
    from Auditorias.audit_pis_cofins import processar_pc
    from Auditorias.audit_difal import processar_difal
    from Apuracoes.apuracao_difal import gerar_resumo_uf
except ImportError as e:
    st.error(f"⚠️ Erro de Dependência: Verifique as pastas Auditorias e Apuracoes. Detalhe: {e}")

# --- UTILITÁRIOS DE TRATAMENTO ---
def safe_float(v):
    if v is None or pd.isna(v): return 0.0
    txt = str(v).strip().upper()
    if txt in ['NT', '', 'N/A', 'ISENTO', 'NULL', 'ZERO']: return 0.0
    try:
        txt = txt.replace('R$', '').replace(' ', '').replace('%', '').strip()
        if ',' in txt and '.' in txt: txt = txt.replace('.', '').replace(',', '.')
        elif ',' in txt: txt = txt.replace(',', '.')
        return round(float(txt), 4)
    except: return 0.0

def buscar_tag_recursiva(tag_alvo, no):
    if no is None: return ""
    for elemento in no.iter():
        if elemento.tag.split('}')[-1] == tag_alvo:
            return elemento.text if elemento.text else ""
    return ""

# --- MOTOR DE PROCESSAMENTO XML ---
def processar_conteudo_xml(content, dados_lista, cnpj_empresa_auditada):
    try:
        xml_str = content.decode('utf-8', errors='replace')
        xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
        root = ET.fromstring(xml_str)
        
        inf = root.find('.//infNFe')
        if inf is None: return 
        
        ide = root.find('.//ide')
        tp_nf = buscar_tag_recursiva('tpNF', ide)
        emit = root.find('.//emit')
        dest = root.find('.//dest')
        
        cnpj_emit = re.sub(r'\D', '', buscar_tag_recursiva('CNPJ', emit))
        cnpj_alvo = re.sub(r'\D', '', str(cnpj_empresa_auditada))
        
        tipo_operacao = "SAIDA" if (cnpj_emit == cnpj_alvo and tp_nf == '1') else "ENTRADA"
        chave = inf.attrib.get('Id', '')[3:]
        n_nf = buscar_tag_recursiva('nNF', ide)

        for det in root.findall('.//det'):
            prod = det.find('prod'); imp = det.find('imposto')
            if prod is None or imp is None: continue
            
            icms_no = det.find('.//ICMS')
            ipi_no = det.find('.//IPI')
            pis_no = det.find('.//PIS')
            cof_no = det.find('.//COFINS')

            linha = {
                "TIPO_SISTEMA": tipo_operacao,
                "CHAVE_ACESSO": str(chave).strip(),
                "NUM_NF": n_nf,
                "CNPJ_EMIT": cnpj_emit,
                "CNPJ_DEST": re.sub(r'\D', '', buscar_tag_recursiva('CNPJ', dest)),
                "UF_EMIT": buscar_tag_recursiva('UF', emit),
                "UF_DEST": buscar_tag_recursiva('UF', dest),
                "CFOP": buscar_tag_recursiva('CFOP', prod),
                "NCM": re.sub(r'\D', '', buscar_tag_recursiva('NCM', prod)).zfill(8),
                "VPROD": safe_float(buscar_tag_recursiva('vProd', prod)),
                "ORIGEM": buscar_tag_recursiva('orig', icms_no),
                "CST-ICMS": buscar_tag_recursiva('CST', icms_no) or buscar_tag_recursiva('CSOSN', icms_no),
                "BC-ICMS": safe_float(buscar_tag_recursiva('vBC', icms_no)),
                "ALQ-ICMS": safe_float(buscar_tag_recursiva('pICMS', icms_no)),
                "VLR-ICMS": safe_float(buscar_tag_recursiva('vICMS', icms_no)),
                "BC-ICMS-ST": safe_float(buscar_tag_recursiva('vBCST', icms_no)),
                "VAL-ICMS-ST": safe_float(buscar_tag_recursiva('vICMSST', icms_no)),
                "IE_SUBST": str(buscar_tag_recursiva('IEST', icms_no)).strip(),
                "ALQ-IPI": safe_float(buscar_tag_recursiva('pIPI', ipi_no)),
                "VLR-IPI": safe_float(buscar_tag_recursiva('vIPI', ipi_no)),
                "CST-IPI": buscar_tag_recursiva('CST', ipi_no),
                "VAL-IBS": safe_float(buscar_tag_recursiva('vIBS', imp)),
                "VAL-CBS": safe_float(buscar_tag_recursiva('vCBS', imp)),
                "CST-PIS": buscar_tag_recursiva('CST', pis_no),
                "VLR-PIS": safe_float(buscar_tag_recursiva('vPIS', pis_no)),
                "CST-COFINS": buscar_tag_recursiva('CST', cof_no),
                "VLR-COFINS": safe_float(buscar_tag_recursiva('vCOFINS', cof_no)),
                "VAL-FCP": safe_float(buscar_tag_recursiva('vFCP', imp)),
                "VAL-DIFAL": safe_float(buscar_tag_recursiva('vICMSUFDest', imp)) + safe_float(buscar_tag_recursiva('vFCPUFDest', imp)),
                "VAL-FCP-DEST": safe_float(buscar_tag_recursiva('vFCPUFDest', imp))
            }
            dados_lista.append(linha)
    except Exception as e:
        print(f"Erro item XML: {e}")

def extrair_dados_xml_recursivo(files, cnpj_empresa_auditada):
    dados_lista = []
    if not files: return pd.DataFrame(), pd.DataFrame()
    lista_trabalho = files if isinstance(files, list) else [files]
    
    def ler_zip(zip_data):
        with zipfile.ZipFile(zip_data) as z:
            for filename in z.namelist():
                if filename.lower().endswith('.xml'):
                    with z.open(filename) as f:
                        processar_conteudo_xml(f.read(), dados_lista, cnpj_empresa_auditada)
                elif filename.lower().endswith('.zip'):
                    with z.open(filename) as nested_zip:
                        ler_zip(io.BytesIO(nested_zip.read()))

    for f in lista_trabalho:
        f.seek(0)
        if f.name.lower().endswith('.xml'):
            processar_conteudo_xml(f.read(), dados_lista, cnpj_empresa_auditada)
        elif f.name.lower().endswith('.zip'):
            ler_zip(f)
            
    df_total = pd.DataFrame(dados_lista)
    if df_total.empty: return pd.DataFrame(), pd.DataFrame()
    return df_total[df_total['TIPO_SISTEMA'] == "ENTRADA"].copy(), df_total[df_total['TIPO_SISTEMA'] == "SAIDA"].copy()

def ler_gerencial_robusto(arquivos, colunas_alvo):
    if not arquivos: return pd.DataFrame(columns=colunas_alvo)
    lista = arquivos if isinstance(arquivos, list) else [arquivos]
    dfs = []
    for f in lista:
        f.seek(0)
        try:
            if f.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(f)
            else:
                raw = f.read().decode('latin1', errors='replace')
                sep = '\t' if '\t' in raw.splitlines()[0] else ';'
                df = pd.read_csv(io.StringIO(raw), sep=sep, on_bad_lines='skip', dtype=str)
            
            df.columns = [c.strip().upper() for c in df.columns]
            df_fmt = pd.DataFrame(columns=[c.upper() for c in colunas_alvo])
            for col in colunas_alvo:
                c_up = col.upper()
                df_fmt[c_up] = df[c_up] if c_up in df.columns else "0"
            
            for col in df_fmt.columns:
                if any(k in col for k in ['VLR', 'BC', 'VAL', 'QTDE', 'ICMS', 'PIS', 'COF', 'IPI']):
                    df_fmt[col] = df_fmt[col].apply(safe_float)
            dfs.append(df_fmt)
        except: continue
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=colunas_alvo)

def gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret):
    output = io.BytesIO()
    cols_ent = ["NUM_NF","DATA_EMISSAO","CNPJ","UF","VLR_NF","AC","CFOP","COD_PROD","DESCR","NCM","UNID","VUNIT","QTDE","VPROD","DESC","FRETE","SEG","DESP","VC","CST-ICMS","BC-ICMS","VLR-ICMS","BC-ICMS-ST","ICMS-ST","VLR_IPI","CST_PIS","BC_PIS","VLR_PIS","CST_COF","BC_COF","VLR_COF"]
    cols_sai = ["NF","DATA_EMISSAO","CNPJ","Ufp","VC","AC","CFOP","COD_ITEM","DESC_ITEM","NCM","UND","VUNIT","QTDE","VITEM","DESC","FRETE","SEG","OUTRAS","VC_ITEM","CST","BC_ICMS","ALIQ_ICMS","ICMS","BC_ICMSST","ICMSST","IPI","CST_PIS","BC_PIS","PIS","CST_COF","BC_COF","COF"]

    df_ger_ent = ler_gerencial_robusto(ge, cols_ent)
    df_ger_sai = ler_gerencial_robusto(gs, cols_sai)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        try: gerar_aba_resumo(writer)
        except: pass
        df_ger_ent.to_excel(writer, sheet_name='GERENCIAL_ENTRADAS', index=False)
        df_ger_sai.to_excel(writer, sheet_name='GERENCIAL_SAIDAS', index=False)

        if not df_xs.empty:
            st_map = {}
            for f_auth in ([ae] if ae else []) + ([as_f] if as_f else []):
                if not f_auth: continue
                try:
                    f_auth.seek(0)
                    df_a = pd.read_excel(f_auth, header=None) if f_auth.name.endswith('.xlsx') else pd.read_csv(f_auth, header=None, sep=None, engine='python')
                    df_a[0] = df_a[0].astype(str).str.replace('NFe', '').str.strip()
                    st_map.update(df_a.set_index(0)[5].to_dict())
                except: pass
            
            df_xs['Situação Nota'] = df_xs['CHAVE_ACESSO'].map(st_map).fillna('⚠️ N/Encontrada')
            
            # --- CHAMADA DOS ESPECIALISTAS COM DF_XE PARA CRUZAMENTO ---
            processar_icms(df_xs, writer, cod_cliente, df_xe)
            processar_ipi(df_xs, writer, cod_cliente)
            processar_pc(df_xs, writer, cod_cliente, regime)
            processar_difal(df_xs, writer)
            try: gerar_resumo_uf(df_xs, writer, df_xe)
            except: pass

    if is_ret:
        try:
            caminho_modelo = f"RET/{cod_cliente}-RET_MG.xlsx"
            if os.path.exists(caminho_modelo):
                output.seek(0)
                wb_final = openpyxl.load_workbook(output)
                wb_modelo = openpyxl.load_workbook(caminho_modelo, data_only=False)
                for sheet_name in wb_modelo.sheetnames:
                    if sheet_name not in wb_final.sheetnames:
                        source = wb_modelo[sheet_name]; target = wb_final.create_sheet(sheet_name)
                        for row in source.iter_rows():
                            for cell in row:
                                new_cell = target.cell(row=cell.row, column=cell.column, value=cell.value)
                                if cell.has_style:
                                    new_cell.font, new_cell.border, new_cell.fill, new_cell.number_format, new_cell.alignment = copy(cell.font), copy(cell.border), copy(cell.fill), copy(cell.number_format), copy(cell.alignment)
                output_ret = io.BytesIO()
                wb_final.save(output_ret)
                return output_ret.getvalue()
        except: pass
    return output.getvalue()
