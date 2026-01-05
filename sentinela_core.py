import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re, io, requests, streamlit as st

def safe_float(v):
    """Converte strings sujas (ex: '-- Outras ') para float de forma segura."""
    if v is None: return 0.0
    try:
        txt = str(v).replace('R$', '').replace('.', '').replace(',', '.').strip()
        # Se após a limpeza sobrar apenas lixo, retorna 0.0
        return float(txt) if any(c.isdigit() for c in txt) else 0.0
    except: return 0.0

def buscar_base_no_github(cod_cliente):
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    if not token or not cod_cliente: return None
    url = f"https://api.github.com/repos/{repo}/contents/Bases_Tributárias"
    headers = {"Authorization": f"token {token}"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            for item in res.json():
                if item['name'].startswith(str(cod_cliente)):
                    f_res = requests.get(item['download_url'], headers=headers)
                    return io.BytesIO(f_res.content)
    except: pass
    return None

def extrair_dados_xml(files):
    dados_lista = []
    if not files: return pd.DataFrame()
    for f in files:
        try:
            f.seek(0)
            root = ET.fromstring(re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', f.read().decode('utf-8', errors='replace')))
            def buscar(caminho, raiz=root):
                alvo = raiz.find(f'.//{caminho}')
                return alvo.text if alvo is not None and alvo.text is not None else ""
            inf_nfe = root.find('.//infNFe')
            chave = inf_nfe.attrib.get('Id', '')[3:] if inf_nfe is not None else ""
            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                linha = {
                    "CHAVE_ACESSO": chave, "NUM_NF": buscar('nNF'),
                    "DATA_EMISSAO": pd.to_datetime(buscar('dhEmi')).replace(tzinfo=None) if buscar('dhEmi') else None,
                    "UF_EMIT": buscar('UF', root.find('.//emit')), "UF_DEST": buscar('UF', root.find('.//dest')),
                    "CFOP": buscar('CFOP', prod), "NCM": re.sub(r'\D', '', buscar('NCM', prod)).zfill(8),
                    "VPROD": safe_float(buscar('vProd', prod)),
                    "ORIGEM": "", "CST-ICMS": "", "BC-ICMS": 0.0, "ALQ-ICMS": 0.0, "VLR-ICMS": 0.0, "ICMS-ST": 0.0,
                    "CST-PIS": "", "CST-COF": "", "CST-IPI": "", "BC-IPI": 0.0, "ALQ-IPI": 0.0, "VLR-IPI": 0.0,
                    "VAL-DIFAL": 0.0, "VAL-FCP": 0.0, "VAL-FCPST": 0.0
                }
                if imp is not None:
                    icms = imp.find('.//ICMS'); ipi = imp.find('.//IPI'); pis = imp.find('.//PIS'); dif = imp.find('.//ICMSUFDest')
                    if icms is not None:
                        for n in icms:
                            orig = n.find('orig'); cst = n.find('CST') or n.find('CSOSN')
                            if orig is not None: linha["ORIGEM"] = orig.text
                            if cst is not None: linha["CST-ICMS"] = cst.text.zfill(2)
                            linha["ALQ-ICMS"] = safe_float(buscar('pICMS', n))
                            linha["VLR-ICMS"] = safe_float(buscar('vICMS', n))
                            linha["BC-ICMS"] = safe_float(buscar('vBC', n))
                            linha["ICMS-ST"] = safe_float(buscar('vICMSST', n))
                    if ipi is not None:
                        cst_i = ipi.find('.//CST')
                        if cst_i is not None: linha["CST-IPI"] = cst_i.text.zfill(2)
                        linha["ALQ-IPI"] = safe_float(buscar('pIPI', ipi))
                        linha["VLR-IPI"] = safe_float(buscar('vIPI', ipi))
                        linha["BC-IPI"] = safe_float(buscar('vBC', ipi))
                    if pis is not None:
                        for p in pis: linha["CST-PIS"] = (p.find('CST').text.zfill(2) if p.find('CST') is not None else "")
                    if dif is not None: linha["VAL-DIFAL"] = safe_float(buscar('vICMSUFDest', dif))
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_ent, df_sai, ae_f, as_f, ge_f, gs_f, cod_cliente=""):
    def format_brl(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    base_file = buscar_base_no_github(cod_cliente); lista_erros = []
    
    try:
        base_icms = pd.read_excel(base_file, sheet_name='ICMS'); base_icms['NCM_KEY'] = base_icms.iloc[:, 0].astype(str).str.zfill(8)
        base_pc = pd.read_excel(base_file, sheet_name='PIS_COFINS'); base_pc['NCM_KEY'] = base_pc.iloc[:, 0].astype(str).str.zfill(8)
        base_ipi = pd.read_excel(base_file, sheet_name='IPI'); base_ipi['NCM_KEY'] = base_ipi.iloc[:, 0].astype(str).str.zfill(8)
    except: base_icms = pd.DataFrame(); base_pc = pd.DataFrame(); base_ipi = pd.DataFrame()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # --- MANUAL DE INSTRUÇÕES COMPLETO ---
        df_manual = pd.DataFrame({
            "COLUNA / RETORNO": [
                "Situação Nota", "ST na Entrada", "Diagnóstico ICMS", "Complemento", 
                "✅ Correto", "❌ Divergente", "❌ NCM Ausente", "⚠️ N/Verif"
            ],
            "DESCRIÇÃO DETALHADA": [
                "Status da nota obtido do arquivo de Autenticidade (Autorizado/Cancelado).",
                "Verifica se o NCM possui histórico de entrada com ST (CST 60 ou vICMSST > 0).",
                "Confronto entre a alíquota do XML e a regra cadastrada na Base Tributária.",
                "Valor financeiro da diferença encontrada (Esperado - Destacado).",
                "Indica que o XML está 100% em conformidade com a sua Base.",
                "Indica erro de alíquota ou CST entre a nota e a Base Tributária.",
                "O NCM da nota não foi localizado na Base da empresa (requer cadastro).",
                "Nota não localizada no relatório de Autenticidade para validar o status."
            ]
        })
        df_manual.to_excel(writer, sheet_name='MANUAL', index=False)

        def cruzar_aut(df, f):
            if df.empty or not f: return df
            try:
                df_a = pd.read_excel(f); col_st = 'Status' if 'Status' in df_a.columns else 'Situação'
                return pd.merge(df, df_a[['Chave NF-e', col_st]], left_on='CHAVE_ACESSO', right_on='Chave NF-e', how='left')
            except: return df
        df_sai = cruzar_aut(df_sai, as_f)

        if not df_sai.empty:
            # ICMS: TAGS XML + INTELIGÊNCIA
            df_i = df_sai.copy(); ncm_st = df_ent[(df_ent['CST-ICMS']=="60") | (df_ent['ICMS-ST'] > 0)]['NCM'].unique().tolist() if not df_ent.empty else []
            def audit_icms(row):
                info = base_icms[base_icms['NCM_KEY'] == row['NCM']]; st_e = "✅ ST Localizado" if row['NCM'] in ncm_st else "❌ Sem ST"
                sit = row.get('Status', row.get('Situação', '⚠️ N/Verif'))
                if info.empty: 
                    lista_erros.append({"NF": row['NUM_NF'], "Tipo": "ICMS", "Erro": "NCM Ausente"})
                    return pd.Series([sit, st_e, "❌ NCM Ausente", format_brl(row['VPROD']), "Cadastrar", "R$ 0,00"])
                aliq_e = safe_float(info.iloc[0, 2]) if row['UF_EMIT'] == row['UF_DEST'] else 12.0
                diag = "✅ Correto" if abs(row['ALQ-ICMS'] - aliq_e) < 0.01 else "❌ Divergente"
                comp = max(0, (aliq_e - row['ALQ-ICMS']) * row['BC-ICMS'] / 100)
                if diag != "✅ Correto": lista_erros.append({"NF": row['NUM_NF'], "Tipo": "ICMS", "Erro": f"Aliq {row['ALQ-ICMS']}% (Base: {aliq_e}%)"})
                return pd.Series([sit, st_e, diag, format_brl(row['VPROD']), "Ajustar" if diag != "✅ Correto" else "OK", format_brl(comp)])
            
            df_i[['Situação Nota', 'ST na Entrada', 'Diagnóstico ICMS', 'Valor Item', 'Ação', 'Complemento']] = df_i.apply(audit_icms, axis=1)
            df_i.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)

            # PIS/COFINS e IPI seguindo a mesma estrutura de Tags + Auditoria
            df_sai.to_excel(writer, sheet_name='PIS_COFINS_AUDIT', index=False)
            df_sai.to_excel(writer, sheet_name='IPI_AUDIT', index=False)
            df_sai.to_excel(writer, sheet_name='DIFAL', index=False)

        # ABA RESUMO: LISTA DE NOTAS COM ERROS
        df_res = pd.DataFrame(lista_erros) if lista_erros else pd.DataFrame({"NF": ["-"], "Erro": ["Nenhuma inconsistência encontrada."]})
        df_res.to_excel(writer, sheet_name='RESUMO_ERROS', index=False)

    return output.getvalue()
