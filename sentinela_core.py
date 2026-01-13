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
    st.error(f"Erro Crítico de Dependência: {e}")
    if 'gerar_resumo_uf' not in locals():
        def gerar_resumo_uf(*args, **kwargs): pass
    if 'processar_icms' not in locals():
        def processar_icms(*args, **kwargs): pass
    if 'processar_ipi' not in locals():
        def processar_ipi(*args, **kwargs): pass
    if 'processar_pc' not in locals():
        def processar_pc(*args, **kwargs): pass
    if 'processar_difal' not in locals():
        def processar_difal(*args, **kwargs): pass

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

        inf = root.find('.//infNFe')
        if inf is None: return 
        
        iest_no_xml = buscar_tag_recursiva('IEST', root) or buscar_tag_recursiva('IE_SUBST', root)
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
    
    cols_ent = ["NUM_NF","DATA_EMISSAO","CNPJ","UF","VLR_NF","AC","CFOP","COD_PROD","DESCR","NCM","UNID","VUNIT","QTDE","VPROD","DESC","FRETE","SEG","DESP","VC","CST-ICMS","BC-ICMS","VLR-ICMS","BC-ICMS-ST","ICMS-ST","VLR_IPI","CST_PIS","BC_PIS","VLR_PIS","CST_COF","BC_COF","VLR_COF"]
    cols_sai = ["NF","DATA_EMISSAO","CNPJ","Ufp","VC","AC","CFOP","COD_ITEM","DESC_ITEM","NCM","UND","VUNIT","QTDE","VITEM","DESC","FRETE","SEG","OUTRAS","VC_ITEM","CST","BC_ICMS","ALIQ_ICMS","ICMS","BC_ICMSST","ICMSST","IPI","CST_PIS","BC_PIS","PIS","CST_COF","BC_COF","COF"]

    def ler_csv_estilo_clipboard(arquivos, colunas_alvo):
        if arquivos is None: return pd.DataFrame()
        lista = arquivos if isinstance(arquivos, list) else [arquivos]
        dfs = []
        for f in lista:
            f.seek(0)
            try:
                raw_content = f.read().decode('latin1', errors='replace')
                lines = raw_content.splitlines()
                data_rows = []
                for line in lines:
                    if not line.strip(): continue
                    parts = re.split(r'\t|;', line)
                    if len(parts) > len(colunas_alvo):
                        parts = parts[:len(colunas_alvo)]
                    elif len(parts) < len(colunas_alvo):
                        parts.extend([""] * (len(colunas_alvo) - len(parts)))
                    data_rows.append(parts)
                df = pd.DataFrame(data_rows, columns=colunas_alvo)
                dfs.append(df)
            except Exception as e:
                st.error(f"Erro na leitura manual de {f.name}: {e}")
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    df_ger_ent = ler_csv_estilo_clipboard(ge, cols_ent)
    df_ger_sai = ler_csv_estilo_clipboard(gs, cols_sai)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        try: gerar_aba_resumo(writer)
        except: pass
        
        def gravar_df_como_tabela(df, sheet_name, table_name):
            if df.empty: return
            worksheet = workbook.add_worksheet(sheet_name)
            writer.sheets[sheet_name] = worksheet
            header = df.columns.tolist()
            data = df.values.tolist()
            worksheet.add_table(0, 0, len(df), len(df.columns) - 1, {
                'data': data,
                'columns': [{'header': col} for col in header],
                'name': table_name,
                'style': 'TableStyleMedium2'
            })

        gravar_df_como_tabela(df_ger_ent, 'GERENCIAL_ENTRADAS', 'TabelaEntradas')
        gravar_df_como_tabela(df_ger_sai, 'GERENCIAL_SAIDAS', 'TabelaSaidas')

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
            try: gerar_resumo_uf(df_xs, writer, df_xe)
            except Exception as e: st.warning(f"Aba DIFAL_ST_FECP falhou: {e}")

    # --- REPLICAÇÃO EXATA DAS ABAS DO ARQUIVO DE BASE DO CLIENTE (PASTA RET) ---
    if is_ret:
        try:
            # Caminho atualizado conforme sua solicitação: RET/426-RET_MG.xlsx
            caminho_modelo = f"RET/{cod_cliente}-RET_MG.xlsx"
            
            if os.path.exists(caminho_modelo):
                output.seek(0)
                wb_final = openpyxl.load_workbook(output)
                wb_modelo = openpyxl.load_workbook(caminho_modelo, data_only=False)

                for sheet_name in wb_modelo.sheetnames:
                    # Garantimos que não vamos mexer nas gerenciais geradas via código
                    if sheet_name not in ['GERENCIAL_ENTRADAS', 'GERENCIAL_SAIDAS']:
                        source_sheet = wb_modelo[sheet_name]
                        if sheet_name in wb_final.sheetnames:
                            target_sheet = wb_final[sheet_name]
                        else:
                            target_sheet = wb_final.create_sheet(sheet_name)

                        # Cópia integral de células e estilos
                        for row in source_sheet.iter_rows():
                            for cell in row:
                                new_cell = target_sheet.cell(row=cell.row, column=cell.column, value=cell.value)
                                if cell.has_style:
                                    new_cell.font = copy(cell.font)
                                    new_cell.border = copy(cell.border)
                                    new_cell.fill = copy(cell.fill)
                                    new_cell.number_format = copy(cell.number_format)
                                    new_cell.alignment = copy(cell.alignment)
                        
                        # Mantém as larguras originais das colunas do modelo
                        for col_name, col_dim in source_sheet.column_dimensions.items():
                            target_sheet.column_dimensions[col_name].width = col_dim.width

                output_final = io.BytesIO()
                wb_final.save(output_final)
                return output_final.getvalue()
            else:
                st.error(f"Arquivo de base RET não encontrado na pasta RET: {caminho_modelo}")
        except Exception as e:
            st.error(f"Erro crítico ao anexar abas do arquivo de base: {e}")
            
    return output.getvalue()
