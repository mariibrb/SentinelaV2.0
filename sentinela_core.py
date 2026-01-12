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
    """Converte valores do XML para float de forma segura, tratando formatos brasileiros."""
    if v is None or pd.isna(v):
        return 0.0
    txt = str(v).strip().upper()
    if txt in ['NT', '', 'N/A', 'ISENTO', 'NULL']:
        return 0.0
    try:
        # Remove símbolos monetários e ajusta separadores decimais
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
    Analisa o conteúdo binário de um XML, remove namespaces e extrai 
    todas as tags relevantes para a auditoria fiscal maximalista.
    """
    try:
        xml_str = content.decode('utf-8', errors='replace')
        # Remove namespaces para permitir buscas simplificadas com find/findall
        xml_str = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_str)
        root = ET.fromstring(xml_str)
        
        def tag_val(t, n):
            """Busca valor de uma tag simples em um nó específico."""
            if n is None: return ""
            v = n.find(f'.//{t}')
            return v.text if v is not None and v.text else ""
            
        def rec_val(n, ts):
            """Busca o valor da primeira tag encontrada em uma lista de possibilidades."""
            if n is None: return ""
            for e in n.iter():
                tag_name = e.tag.split('}')[-1]
                if tag_name in ts:
                    return e.text if e.text else ""
            return ""

        # --- CABEÇALHO DA NOTA ---
        inf = root.find('.//infNFe')
        if inf is None: return # Ignora se não for uma NF-e válida
        
        emit = root.find('.//emit')
        dest = root.find('.//dest')
        enderEmit = emit.find('.//enderEmit') if emit is not None else None
        
        chave = inf.attrib.get('Id', '')[3:] # Remove o prefixo 'NFe'
        n_nf = tag_val('nNF', root)
        
        # BUSCA A IEST (Inscrição de Substituto) NO CABEÇALHO (Grupo enderEmit)
        iest_cabecalho = tag_val('IEST', enderEmit)

        # --- PROCESSAMENTO DOS ITENS (DET) ---
        for det in root.findall('.//det'):
            prod = det.find('prod')
            imp = det.find('imposto')
            
            if prod is None or imp is None: continue
            
            # Subgrupos de Impostos
            icms = imp.find('.//ICMS')
            pis = imp.find('.//PIS')
            cofins = imp.find('.//COFINS')
            ipi = imp.find('.//IPI')
            
            # Captura de DIFAL e Partilha (Interestadual)
            # Busca valores de destino em diferentes possíveis tags da SEFAZ
            v_difal_dest = safe_float(rec_val(imp, ['vICMSUFDest', 'vICMSPart', 'vICMSDIFAL']))
            v_fcp_dest = safe_float(rec_val(imp, ['vFCPUFDest', 'vFCPPart']))
            
            # Captura a IEST: Tenta no item, se vazio, usa a do cabeçalho do emitente
            ie_subst_final = rec_val(icms, ['IEST', 'IESTDest'])
            if not ie_subst_final or ie_subst_final.strip() == "":
                ie_subst_final = iest_cabecalho

            # Mapeamento Maximalista de Colunas
            linha = {
                # Identificação
                "CHAVE_ACESSO": str(chave).strip(),
                "NUM_NF": n_nf,
                "CNPJ_EMIT": tag_val('CNPJ', emit),
                "CNPJ_DEST": tag_val('CNPJ', dest),
                "CPF_DEST": tag_val('CPF', dest),
                "UF_EMIT": tag_val('UF', emit),
                "UF_DEST": tag_val('UF', dest),
                "indIEDest": tag_val('indIEDest', dest),
                
                # Dados do Produto
                "CFOP": tag_val('CFOP', prod),
                "NCM": re.sub(r'\D', '', tag_val('NCM', prod)).zfill(8),
                "VPROD": safe_float(tag_val('vProd', prod)),
                
                # Detalhamento ICMS
                "ORIGEM": rec_val(icms, ['orig']),
                "CST-ICMS": rec_val(icms, ['CST', 'CSOSN']).zfill(2),
                "BC-ICMS": safe_float(rec_val(imp, ['vBC'])),
                "ALQ-ICMS": safe_float(rec_val(imp, ['pICMS'])),
                "VLR-ICMS": safe_float(rec_val(imp, ['vICMS'])),
                
                # Detalhamento PIS
                "CST-PIS": rec_val(pis, ['CST']),
                "VAL-PIS": safe_float(rec_val(pis, ['vPIS'])),
                
                # Detalhamento COFINS
                "CST-COF": rec_val(cofins, ['CST']),
                "VAL-COF": safe_float(rec_val(cofins, ['vCOFINS'])),
                
                # Detalhamento IPI
                "CST-IPI": rec_val(ipi, ['CST']),
                "ALQ-IPI": safe_float(rec_val(ipi, ['pIPI'])),
                "VAL-IPI": safe_float(rec_val(ipi, ['vIPI'])),
                
                # DIFAL / ST / FCP
                "VAL-DIFAL": v_difal_dest + v_fcp_dest,
                "VAL-FCP-DEST": v_fcp_dest,
                "VAL-ICMS-ST": safe_float(rec_val(imp, ['vICMSST'])),
                "BC-ICMS-ST": safe_float(rec_val(imp, ['vBCST'])),
                "VAL-FCP-ST": safe_float(rec_val(imp, ['vFCPST'])),
                "VAL-FCP": safe_float(rec_val(imp, ['vFCP'])),
                
                # Inscrição de Substituto (Sua IEST na UF Destino)
                "IE_SUBST": ie_subst_final,
                
                # Reforma Tributária (IBS/CBS)
                "VAL-IBS": safe_float(rec_val(imp, ['vIBS'])),
                "ALQ-IBS": safe_float(rec_val(imp, ['pIBS'])),
                "VAL-CBS": safe_float(rec_val(imp, ['vCBS'])),
                "ALQ-CBS": safe_float(rec_val(imp, ['pCBS']))
            }
            dados_lista.append(linha)
            
    except Exception as e:
        # Em produção, você pode logar este erro em um arquivo
        pass

# --- GESTÃO DE ARQUIVOS E ZIP ---

def extrair_dados_xml(files):
    """
    Gerencia a descompactação de um ou mais arquivos ZIP, 
    processando todos os XMLs encontrados dentro deles.
    """
    dados_lista = []
    if not files:
        return pd.DataFrame()
    
    # Normaliza a entrada para uma lista, permitindo múltiplos uploads
    lista_trabalho = files if isinstance(files, list) else [files]
        
    for f in lista_trabalho:
        try:
            with zipfile.ZipFile(f) as z:
                for filename in z.namelist():
                    if filename.lower().endswith('.xml'):
                        try:
                            with z.open(filename) as xml_file:
                                processar_conteudo_xml(xml_file.read(), dados_lista)
                        except:
                            continue
        except Exception:
            continue
            
    return pd.DataFrame(dados_lista)

# --- GERADOR DO RELATÓRIO FINAL ---

def gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime):
    """
    Orquestra a criação do arquivo Excel consolidado, chamando cada módulo 
    especialista de auditoria e formatando o resultado final.
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # 1. ABA RESUMO: Manual de Diagnósticos
        try:
            gerar_aba_resumo(writer)
        except:
            pass
        
        # 2 e 3. ABAS GERENCIAIS: Cruzamento com ERP
        try:
            gerar_abas_gerenciais(writer, ge, gs)
        except:
            pass

        # 4. PROCESSAMENTO DE AUDITORIA (SAÍDAS)
        if not df_xs.empty:
            # Lógica de Autenticidade (Situação da Nota na SEFAZ)
            st_map = {}
            if as_f:
                try:
                    f_auth_list = as_f if isinstance(as_f, list) else [as_f]
                    for f_auth in f_auth_list:
                        f_auth.seek(0)
                        if f_auth.name.endswith('.xlsx'):
                            df_auth = pd.read_excel(f_auth, header=None)
                        else:
                            df_auth = pd.read_csv(f_auth, header=None, sep=None, engine='python', on_bad_lines='skip')
                        
                        # Limpa chaves de acesso e mapeia status (coluna 5 conforme padrão Sentinela)
                        df_auth[0] = df_auth[0].astype(str).str.replace('NFe', '').str.strip()
                        st_map.update(df_auth.set_index(0)[5].to_dict())
                except:
                    pass
            
            # Adiciona Situação da Nota ao DataFrame Principal
            df_xs['Situação Nota'] = df_xs['CHAVE_ACESSO'].map(st_map).fillna('⚠️ N/Encontrada')
            
            # CHAMADA DOS ESPECIALISTAS DE AUDITORIA
            processar_icms(df_xs, writer, cod_cliente)
            processar_ipi(df_xs, writer, cod_cliente)
            processar_pc(df_xs, writer, cod_cliente, regime)
            processar_difal(df_xs, writer)
            gerar_resumo_uf(df_xs, writer)

    return output.getvalue()

def main():
    """Ponto de entrada para execução direta (debug)."""
    pass

if __name__ == "__main__":
    main()
