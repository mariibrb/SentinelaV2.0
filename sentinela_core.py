import pd
import numpy as np
import xml.etree.ElementTree as ET
import re
import io

def extrair_dados_xml(files):
    dados_lista = []
    if not files: return pd.DataFrame()
    for f in files:
        try:
            f.seek(0)
            conteudo = f.read().decode('utf-8', errors='replace')
            root = ET.fromstring(re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', conteudo))
            
            def buscar(caminho, raiz=root):
                alvo = raiz.find(f'.//{caminho}')
                return alvo.text if alvo is not None and alvo.text is not None else ""

            inf_nfe = root.find('.//infNFe')
            chave = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            
            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                linha = {
                    "CHAVE_ACESSO": chave, "NUM_NF": buscar('nNF'),
                    "ITEM": det.attrib.get('nItem', '0'),
                    "NCM_XML": re.sub(r'\D', '', buscar('NCM', prod)).zfill(8),
                    "DESCRICAO_XML": buscar('xProd', prod),
                    "VALOR_PRODUTO": float(buscar('vProd', prod) or 0),
                    "CST_ICMS_XML": "", "ALIQ_ICMS_XML": 0.0,
                    "VLR_IPI_XML": 0.0, "VLR_PIS_XML": 0.0, "VLR_COFINS_XML": 0.0
                }
                if imp is not None:
                    # ICMS
                    icms_tag = imp.find('.//ICMS')
                    if icms_tag is not None:
                        for n in icms_tag:
                            cst = n.find('CST') or n.find('CSOSN')
                            if cst is not None: linha["CST_ICMS_XML"] = cst.text.zfill(2)
                            if n.find('pICMS') is not None: linha["ALIQ_ICMS_XML"] = float(n.find('pICMS').text)
                    
                    # IPI, PIS, COFINS
                    vIpi = imp.find('.//IPI/vIPI')
                    if vIpi is not None: linha["VLR_IPI_XML"] = float(vIpi.text)
                    vPis = imp.find('.//PIS//vPIS')
                    if vPis is not None: linha["VLR_PIS_XML"] = float(vPis.text)
                    vCofins = imp.find('.//COFINS//vCOFINS')
                    if vCofins is not None: linha["VLR_COFINS_XML"] = float(vCofins.text)
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, b_unica, ge, gs, cod_cliente=""):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # Se houver base única e XML, fazemos o cruzamento (Análise)
        if b_unica is not None and not df_xe.empty:
            try:
                df_base = pd.read_excel(b_unica)
                # Garante que o NCM seja string para o cruzamento
                df_base['NCM'] = df_base['NCM'].astype(str).str.zfill(8)
                
                # Cruzamento das Entradas com a Base (pelo NCM)
                df_analise_ent = pd.merge(df_xe, df_base, left_on='NCM_XML', right_on='NCM', how='left')
                
                # Exemplo de lógica de Status
                df_analise_ent['STATUS_ICMS'] = np.where(df_analise_ent['CST_ICMS_XML'] == df_analise_ent['CST'], '✅ OK', '❌ DIVERGENTE')
                
                df_analise_ent.to_excel(writer, sheet_name='ANALISE_ENTRADAS', index=False)
            except:
                df_xe.to_excel(writer, sheet_name='XML_ENTRADAS', index=False)
        else:
            if not df_xe.empty: df_xe.to_excel(writer, sheet_name='XML_ENTRADAS', index=False)
        
        if not df_xs.empty: df_xs.to_excel(writer, sheet_name='XML_SAIDAS', index=False)
        if ge: pd.read_csv(ge, sep=None, engine='python').to_excel(writer, sheet_name='GERENCIAL_ENT', index=False)
        if gs: pd.read_csv(gs, sep=None, engine='python').to_excel(writer, sheet_name='GERENCIAL_SAI', index=False)
            
    return output.getvalue()
