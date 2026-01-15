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
    try:
        from Apuracoes.apuracao_difal import gerar_resumo_uf
    except ImportError:
        from Apuracoes.apuracao_difal import gerar_resumo_uf
except ImportError as e:
    st.error(f"Erro Crítico de Dependência no Core: {e}")
    # Fallbacks para evitar crash total se um módulo falhar
    if 'gerar_aba_resumo' not in locals(): def gerar_aba_resumo(*args): pass
    if 'processar_icms' not in locals(): def processar_icms(*args): pass
    if 'processar_ipi' not in locals(): def processar_ipi(*args): pass
    if 'processar_pc' not in locals(): def processar_pc(*args): pass
    if 'processar_difal' not in locals(): def processar_difal(*args): pass
    if 'gerar_resumo_uf' not in locals(): def gerar_resumo_uf(*args): pass

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

def buscar_tag_recursiva(tag_alvo, no):
    if no is None: return ""
    for elemento in no.iter():
        if elemento.tag.split('}')[-1] == tag_alvo:
            return elemento.text if elemento.text else ""
    return ""

def processar_conteudo_xml(content, dados_lista, cnpj_empresa_auditada):
    try:
        xml_str = content.decode('utf-8', errors='replace')
        xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
        root = ET.fromstring(xml_str)
        
        inf = root.find('.//infNFe')
        if inf is None: return 
        
        ide = root.find('.//ide')
        tp_nf = buscar_tag_recursiva('tpNF', ide) # 0=Entrada, 1=Saída
        emit = root.find('.//emit')
        dest = root.find('.//dest')
        
        cnpj_emit = re.sub(r'\D', '', buscar_tag_recursiva('CNPJ', emit))
        cnpj_alvo = re.sub(r'\D', '', str(cnpj_empresa_auditada))
        
        # TRIAGEM AUTOMÁTICA
        tipo_operacao = "SAIDA" if (cnpj_emit == cnpj_alvo and tp_nf == '1') else "ENTRADA"

        chave = inf.attrib.get('Id', '')[3:]
        n_nf = buscar_tag_recursiva('nNF', ide)

        for det in root.findall('.//det'):
            prod = det.find('prod'); imp = det.find('imposto')
            if prod is None or imp is None: continue
            
            v_difal_dest = safe_float(buscar_tag_recursiva('vICMSUFDest', imp))
            v_fcp_dest = safe_float(buscar_tag_recursiva('vFCPUFDest', imp))
            iest_no_xml = buscar_tag_recursiva('IEST', root) or buscar_tag_recursiva('IE_SUBST', root)
            iest_item = buscar_tag_recursiva('IEST', det.find('.//ICMS'))
            ie_final = iest_item if iest_item != "" else iest_no_xml

            linha = {
                "TIPO_SISTEMA": tipo_operacao,
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
        if f.name.lower().endswith('.xml'):
            f.seek(0); processar_conteudo_xml(f.read(), dados_lista, cnpj_empresa_auditada)
        elif f.name.lower().endswith('.zip'):
            f.seek(0); ler_zip(f)
            
    df_total = pd.DataFrame(dados_lista)
    if df_total.empty: return pd.DataFrame(), pd.DataFrame()
    return df_total[df_total['TIPO_SISTEMA'] == "ENTRADA"].copy(), df_total[df_total['TIPO_SISTEMA'] == "SAIDA"].copy()

# --- GERAÇÃO DO EXCEL FINAL ---

def gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret):
    output = io.BytesIO()
    cols_ent = ["NUM_NF","DATA_EMISSAO","CNPJ","UF","VLR_NF","AC","CFOP","COD_PROD","DESCR","NCM","UNID","VUNIT","QTDE","VPROD","DESC","FRETE","SEG","DESP","VC","CST-ICMS","BC-ICMS","VLR-ICMS","BC-ICMS-ST","ICMS-ST","VLR_IPI","CST_PIS","BC_PIS","VLR_PIS","CST_COF","BC_COF","VLR_COF"]
    cols_sai = ["NF","DATA_EMISSAO","CNPJ","Ufp","VC","AC","CFOP","COD_ITEM","DESC_ITEM","NCM","UND","VUNIT","QTDE","VITEM","DESC","FRETE","SEG","OUTRAS","VC_ITEM","CST","BC_ICMS","ALIQ_ICMS","ICMS","BC_ICMSST","ICMSST","IPI","CST_PIS","BC_PIS","PIS","CST_COF","BC_COF","COF"]

    def ler_csv_estilo_clipboard(arquivos, colunas_alvo):
        if arquivos is None: return pd.DataFrame(columns=colunas_alvo)
        lista = arquivos if isinstance(arquivos, list) else [arquivos]
        dfs = []
        for f in lista:
            f.seek(0)
            try:
                raw_content = f.read().decode('latin1', errors='replace')
                lines = raw_content.splitlines()
                data_rows = [re.split(r'\t|;', line) for line in lines if line.strip()]
                df = pd.DataFrame(data_rows, columns=colunas_alvo)
                for col in df.columns:
                    if any(key in col.upper() for key in ['VLR', 'BC', 'VAL', 'VC', 'QTDE', 'VUNIT', 'ICMS', 'PIS', 'COF', 'IPI']):
                        df[col] = df[col].apply(safe_float)
                dfs.append(df)
            except: pass
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=colunas_alvo)

    df_ger_ent = ler_csv_estilo_clipboard(ge, cols_ent)
    df_ger_sai = ler_csv_estilo_clipboard(gs, cols_sai)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        try: gerar_aba_resumo(writer)
        except: pass
        
        def gravar_df_como_tabela(df, sheet_name, table_name):
            if df.empty: return
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            (max_row, max_col) = df.shape
            worksheet.add_table(0, 0, max_row, max_col - 1, {
                'columns': [{'header': col} for col in df.columns],
                'name': table_name, 'style': 'TableStyleMedium2'
            })

        gravar_df_como_tabela(df_ger_ent, 'GERENCIAL_ENTRADAS', 'TabelaEntradas')
        gravar_df_como_tabela(df_ger_sai, 'GERENCIAL_SAIDAS', 'TabelaSaidas')

        if not df_xs.empty:
            st_map = {}
            arquivos_auth = []
            if ae: arquivos_auth.extend(ae if isinstance(ae, list) else [ae])
            if as_f: arquivos_auth.extend(as_f if isinstance(as_f, list) else [as_f])
            
            if arquivos_auth:
                for f in arquivos_auth:
                    try:
                        f.seek(0)
                        df_a = pd.read_excel(f, header=None) if f.name.endswith('.xlsx') else pd.read_csv(f, header=None, sep=None, engine='python')
                        df_a[0] = df_a[0].astype(str).str.replace('NFe', '').str.strip()
                        st_map.update(df_a.set_index(0)[5].to_dict())
                    except: pass
            
            df_xs['Situação Nota'] = df_xs['CHAVE_ACESSO'].map(st_map).fillna('⚠️ N/Encontrada')
            
            # Chamadas dos especialistas
            processar_icms(df_xs, writer, cod_cliente)
            processar_ipi(df_xs, writer, cod_cliente)
            processar_pc(df_xs, writer, cod_cliente, regime)
            processar_difal(df_xs, writer)
            try: gerar_resumo_uf(df_xs, writer, df_xe)
            except: pass

    # --- LÓGICA DE CLONAGEM DO RET (OPENPYXL) ---
    if is_ret:
        try:
            # Importante: No Streamlit Cloud, o arquivo de modelo precisa ser baixado ou estar no repo
            caminho_modelo = f"RET/{cod_cliente}-RET_MG.xlsx"
            if os.path.exists(caminho_modelo):
                output.seek(0)
                wb_final = openpyxl.load_workbook(output)
                wb_modelo = openpyxl.load_workbook(caminho_modelo, data_only=False)
                for sheet_name in wb_modelo.sheetnames:
                    if sheet_name not in wb_final.sheetnames:
                        source = wb_modelo[sheet_name]
                        target = wb_final.create_sheet(sheet_name)
                        for row in source.iter_rows():
                            for cell in row:
                                new_cell = target.cell(row=cell.row, column=cell.column, value=cell.value)
                                if cell.has_style:
                                    new_cell.font = copy(cell.font)
                                    new_cell.border = copy(cell.border)
                                    new_cell.fill = copy(cell.fill)
                                    new_cell.number_format = copy(cell.number_format)
                                    new_cell.alignment = copy(cell.alignment)
                output_ret = io.BytesIO()
                wb_final.save(output_ret)
                return output_ret.getvalue()
        except Exception as e:
            st.warning(f"Aviso: Erro ao mesclar modelo RET: {e}")
    
    return output.getvalue()
