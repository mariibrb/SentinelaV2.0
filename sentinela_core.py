import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re
import io

def extrair_dados_xml(files):
    """Extrai dados técnicos de múltiplos arquivos XML de NFe."""
    dados_lista = []
    if not files: return pd.DataFrame()
    
    for f in files:
        try:
            f.seek(0)
            conteudo = f.read().decode('utf-8', errors='replace')
            # Remove namespaces para facilitar a busca das tags
            root = ET.fromstring(re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', conteudo))
            
            def buscar(caminho, raiz=root):
                alvo = raiz.find(f'.//{caminho}')
                return alvo.text if alvo is not None and alvo.text is not None else ""

            inf_nfe = root.find('.//infNFe')
            chave = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            emit = root.find('.//emit')
            
            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                linha = {
                    "CHAVE_ACESSO": chave,
                    "NUM_NF": buscar('nNF'),
                    "DATA_EMISSAO": buscar('dhEmi')[:10] if buscar('dhEmi') else "",
                    "CNPJ_EMITENTE": buscar('CNPJ', emit),
                    "ITEM": det.attrib.get('nItem', '0'),
                    "CFOP": buscar('CFOP', prod),
                    "NCM": re.sub(r'\D', '', buscar('NCM', prod)).zfill(8),
                    "COD_PROD": buscar('cProd', prod),
                    "DESCRICAO": buscar('xProd', prod),
                    "VALOR_PRODUTO": float(buscar('vProd', prod) or 0),
                    "CST_ICMS": "",
                    "BC_ICMS": 0.0,
                    "VLR_ICMS": 0.0,
                    "VLR_PIS": 0.0,
                    "VLR_COFINS": 0.0
                }
                
                if imp is not None:
                    # Lógica de ICMS
                    icms_tag = imp.find('.//ICMS')
                    if icms_tag is not None:
                        for n in icms_tag:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST_ICMS"] = cst.text.zfill(2)
                            if n.find('vBC') is not None: linha["BC_ICMS"] = float(n.find('vBC').text)
                            if n.find('vICMS') is not None: linha["VLR_ICMS"] = float(n.find('vICMS').text)
                    
                    # Lógica de PIS/COFINS
                    pis = imp.find('.//PIS')
                    if pis is not None and pis.find('.//vPIS') is not None:
                        linha["VLR_PIS"] = float(pis.find('.//vPIS').text)
                    
                    cofins = imp.find('.//COFINS')
                    if cofins is not None and cofins.find('.//vCOFINS') is not None:
                        linha["VLR_COFINS"] = float(cofins.find('.//vCOFINS').text)
                            
                dados_lista.append(linha)
        except Exception:
            continue
            
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, b_icms=None, b_pc=None, ae=None, as_f=None):
    """Cria o relatório em Excel com abas separadas para auditoria."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Abas Brutas (O que veio do XML)
        if not df_xe.empty: df_xe.to_excel(writer, sheet_name='XML_ENTRADAS', index=False)
        if not df_xs.empty: df_xs.to_excel(writer, sheet_name='XML_SAIDAS', index=False)
        
        # Abas de Referência (As bases que você sobe na Sidebar)
        if b_icms is not None:
            try: pd.read_excel(b_icms).to_excel(writer, sheet_name='BASE_REF_ICMS', index=False)
            except: pass
        if b_pc is not None:
            try: pd.read_excel(b_pc).to_excel(writer, sheet_name='BASE_REF_PIS_COFINS', index=False)
            except: pass
            
        # Abas de Autenticidade (O que você sobe no fluxo principal)
        if ae is not None:
            try: pd.read_excel(ae).to_excel(writer, sheet_name='AUTENTICIDADE_ENT', index=False)
            except: pass
        if as_f is not None:
            try: pd.read_excel(as_f).to_excel(writer, sheet_name='AUTENTICIDADE_SAI', index=False)
            except: pass
            
        # Aba de Resumo para Auditoria Rápida
        if not df_xs.empty:
            resumo = df_xs.groupby('CFOP').agg({'VALOR_PRODUTO': 'sum', 'VLR_ICMS': 'sum'}).reset_index()
            resumo.to_excel(writer, sheet_name='RESUMO_CFOP_SAIDA', index=False)
            
    return output.getvalue()
