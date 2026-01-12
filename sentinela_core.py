import pandas as pd
import io, zipfile, streamlit as st
import xml.etree.ElementTree as ET
import re

# --- IMPORTAÇÃO DOS ESPECIALISTAS ---
from audit_resumo import gerar_aba_resumo
from audit_gerencial import gerar_abas_gerenciais
from audit_icms import processar_icms
from audit_ipi import processar_ipi
from audit_pis_cofins import processar_pc
from audit_difal import processar_difal
from apuracao_difal import gerar_resumo_uf # Certifique-se de renomear no GitHub para sem acento

def safe_float(v):
    """Tratamento robusto para conversão de valores fiscais"""
    if v is None or pd.isna(v) or str(v).strip().upper() in ['NT', '', 'N/A']: return 0.0
    try:
        txt = str(v).replace('R$', '').replace(' ', '').replace('%', '').strip()
        if ',' in txt and '.' in txt: txt = txt.replace('.', '').replace(',', '.')
        elif ',' in txt: txt = txt.replace(',', '.')
        return round(float(txt), 4)
    except: 
        return 0.0

def processar_conteudo_xml(content, dados_lista):
    """Motor principal de captura de Tags XML"""
    try:
        xml_str = content.decode('utf-8', errors='replace')
        # Limpeza de Namespaces para facilitar a busca de tags
        xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
        root = ET.fromstring(xml_str)
        
        def tag_val(t, n):
            v = n.find(f'.//{t}')
            return v.text if v is not None and v.text else ""
            
        def rec_val(n, ts):
            """Busca recursiva em lista de tags possíveis"""
            if n is None: return ""
            for e in n.iter():
                tag_name = e.tag.split('}')[-1]
                if tag_name in ts: return e.text
            return ""
        
        # Identificação básica da NF-e
        inf = root.find('.//infNFe')
        emit = root.find('.//emit')
        dest = root.find('.//dest')
        chave = inf.attrib.get('Id', '')[3:] if inf is not None else ""
        
        # Iteração sobre os Itens (det)
        for det in root.findall('.//det'):
            prod = det.find('prod')
            imp = det.find('imposto')
            
            # Grupos específicos de impostos
            icms = imp.find('.//ICMS') if imp is not None else None
            pis = imp.find('.//PIS') if imp is not None else None
            cofins = imp.find('.//COFINS') if imp is not None else None
            ipi = imp.find('.//IPI') if imp is not None else None
            
            # Captura de DIFAL e Partilha (Tags de destino)
            v_difal_base = safe_float(rec_val(imp, ['vICMSUFDest', 'vICMSPart', 'vICMSDIFAL']))
            v_fcp_difal = safe_float(rec_val(imp, ['vFCPUFDest', 'vFCPPart']))
            
            # Montagem do dicionário de dados (O Coração do Core)
            linha = {
                "CHAVE_ACESSO": str(chave).strip(),
                "NUM_NF": tag_val('nNF', root),
                "CNPJ_EMIT": tag_val('CNPJ', emit),
                "CNPJ_DEST": tag_val('CNPJ', dest),
                "CPF_DEST": tag_val('CPF', dest),
                "UF_EMIT": tag_val('UF', emit),
                "UF_DEST": tag_val('UF', dest),
                "indIEDest": tag_val('indIEDest', dest),
                "CFOP": tag_val('CFOP', prod),
                "NCM": re.sub(r'\D', '', tag_val('NCM', prod)).zfill(8),
                "VPROD": safe_float(tag_val('vProd', prod)),
                
                # --- ICMS ---
                "ORIGEM": rec_val(icms, ['orig']),
                "CST-ICMS": rec_val(icms, ['CST', 'CSOSN']).zfill(2),
                "BC-ICMS": safe_float(rec_val(imp, ['vBC'])),
                "ALQ-ICMS": safe_float(rec_val(imp, ['pICMS'])),
                "VLR-ICMS": safe_float(rec_val(imp, ['vICMS'])),
                
                # --- PIS ---
                "CST-PIS": rec_val(pis, ['CST']),
                "VAL-PIS": safe_float(rec_val(pis, ['vPIS'])),
                
                # --- COFINS ---
                "CST-COF": rec_val(cofins, ['CST']),
                "VAL-COF": safe_float(rec_val(cofins, ['vCOFINS'])),
                
                # --- IPI ---
                "CST-IPI": rec_val(ipi, ['CST']),
                "ALQ-IPI": safe_float(rec_val(ipi, ['pIPI'])),
                "VAL-IPI": safe_float(rec_val(ipi, ['vIPI'])),
                
                # --- DIFAL / FCP / ST ---
                "VAL-DIFAL": v_difal_base + v_fcp_difal,
                "VAL-FCP-DEST": v_fcp_difal,
                "VAL-ICMS-ST": safe_float(rec_val(imp, ['vICMSST'])),
                "BC-ICMS-ST": safe_float(rec_val(imp, ['vBCST'])),
                "VAL-FCP-ST": safe_float(rec_val(imp, ['vFCPST'])),
                "VAL-FCP": safe_float(rec_val(imp, ['vFCP'])),
                
                # --- IDENTIFICAÇÃO DE INSCRIÇÃO (IEST) ---
                "IE_SUBST": rec_val(icms, ['IEST', 'IESTDest']),
                
                # --- REFORMA TRIBUTÁRIA / OUTROS ---
                "VAL-IBS": safe_float(rec_val(imp, ['vIBS'])),
                "ALQ-IBS": safe_float(rec_val(imp, ['pIBS'])),
                "VAL-CBS": safe_float(rec_val(imp, ['vCBS'])),
                "ALQ-CBS": safe_float(rec_val(imp, ['pCBS']))
            }
            dados_lista.append(linha)
    except Exception as e:
        # Silencioso para não travar o loop, mas poderia ser logado
        pass

def extrair_dados_xml(files):
    """Suporta um ou múltiplos arquivos ZIP enviados pelo Streamlit"""
    dados_lista = []
    if not files: return pd.DataFrame()
    
    # Normaliza para lista se for arquivo único
    if not isinstance(files, list):
        lista_trabalho = [files]
    else:
        lista_trabalho = files
        
    for f in lista_trabalho:
        try:
            with zipfile.ZipFile(f) as z:
                for filename in z.namelist():
                    if filename.endswith('.xml'):
                        with z.open(filename) as xml_file:
                            processar_conteudo_xml(xml_file.read(), dados_lista)
        except:
            continue
            
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime):
    """Orquestrador final de abas e auditorias"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # 1. ABA RESUMO (Manual/Legenda)
        gerar_aba_resumo(writer)
        
        # 2 e 3. GERENCIAIS (Cruza dados de ERP se houver)
        gerar_abas_gerenciais(writer, ge, gs)

        if not df_xs.empty:
            # Lógica de Autenticidade (Situação da Nota SEFAZ)
            st_map = {}
            if as_f:
                try:
                    # Suporte a múltiplos arquivos de autenticidade se necessário
                    f_auth_list = as_f if isinstance(as_f, list) else [as_f]
                    for f_auth in f_auth_list:
                        f_auth.seek(0)
                        if f_auth.name.endswith('.xlsx'): 
                            df_auth = pd.read_excel(f_auth, header=None)
                        else: 
                            df_auth = pd.read_csv(f_auth, header=None, sep=None, engine='python', on_bad_lines='skip')
                        
                        # Limpa a chave de acesso e mapeia o status (geralmente coluna 5)
                        df_auth[0] = df_auth[0].astype(str).str.replace('NFe', '').str.strip()
                        st_map.update(df_auth.set_index(0)[5].to_dict())
                except: 
                    pass
            
            df_xs['Situação Nota'] = df_xs['CHAVE_ACESSO'].map(st_map).fillna('⚠️ N/Encontrada')
            
            # --- EXECUÇÃO DOS ESPECIALISTAS DE AUDITORIA ---
            processar_icms(df_xs, writer, cod_cliente)
            processar_ipi(df_xs, writer, cod_cliente)
            processar_pc(df_xs, writer, cod_cliente, regime)
            processar_difal(df_xs, writer)
            gerar_resumo_uf(df_xs, writer) 

    return output.getvalue()

# --- INTERFACE STREAMLIT (INTEGRADA PARA TESTE LOCAL) ---
def main():
    # Este bloco só roda se você executar o core diretamente como script
    pass

if __name__ == "__main__":
    main()
