import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re, io, requests, streamlit as st

# TABELA DE ALÍQUOTAS INTERNAS PADRÃO POR UF
ALIQUOTAS_UF = {
    'AC': 19.0, 'AL': 19.0, 'AM': 20.0, 'AP': 18.0, 'BA': 20.5, 'CE': 20.0,
    'DF': 20.0, 'ES': 17.0, 'GO': 19.0, 'MA': 22.0, 'MG': 18.0, 'MS': 17.0,
    'MT': 17.0, 'PA': 19.0, 'PB': 20.0, 'PE': 20.5, 'PI': 21.0, 'PR': 19.5,
    'RJ': 20.0, 'RN': 20.0, 'RO': 19.5, 'RR': 20.0, 'RS': 17.0, 'SC': 17.0,
    'SE': 19.0, 'SP': 18.0, 'TO': 20.0
}

def safe_float(v):
    if v is None or pd.isna(v): return None
    try:
        txt = str(v).replace('R$', '').replace(' ', '').strip()
        if ',' in txt and '.' in txt: txt = txt.replace('.', '').replace(',', '.')
        elif ',' in txt: txt = txt.replace(',', '.')
        return round(float(txt), 4)
    except: return None

def buscar_base_no_repositorio(cod_cliente):
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    if not token or not cod_cliente: return None
    url = f"https://api.github.com/repos/{repo}/contents/Bases_Tributárias"
    headers = {"Authorization": f"token {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
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
            xml_data = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', f.read().decode('utf-8', errors='replace'))
            root = ET.fromstring(xml_data)
            def buscar_tag(tag, raiz):
                alvo = raiz.find(f'.//{tag}')
                return alvo.text if alvo is not None and alvo.text is not None else ""
            def buscar_recursivo(node, tags_alvo):
                for elem in node.iter():
                    tag_limpa = elem.tag.split('}')[-1]
                    if tag_limpa in tags_alvo: return elem.text
                return ""

            inf = root.find('.//infNFe'); chave = inf.attrib.get('Id', '')[3:] if inf is not None else ""
            emit = root.find('.//emit'); dest = root.find('.//dest')
            uf_e = emit.find('.//UF').text if emit is not None else ""
            uf_d = dest.find('.//UF').text if dest is not None else ""

            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                icms_node = imp.find('.//ICMS') if imp is not None else None
                cst_ex = buscar_recursivo(icms_node, ['CST', 'CSOSN']) if icms_node is not None else ""
                orig_ex = buscar_recursivo(icms_node, ['orig']) if icms_node is not None else ""
                
                linha = {
                    "CHAVE_ACESSO": str(chave).strip(), "NUM_NF": buscar_tag('nNF', root),
                    "CNPJ_EMIT": (emit.find('.//CNPJ').text if emit.find('.//CNPJ') is not None else emit.find('.//CPF').text) if emit is not None else "",
                    "CNPJ_DEST": (dest.find('.//CNPJ').text if dest.find('.//CNPJ') is not None else dest.find('.//CPF').text) if dest is not None else "",
                    "UF_EMIT": uf_e, "UF_DEST": uf_d,
                    "CFOP": prod.find('CFOP').text if prod is not None else "", 
                    "NCM": re.sub(r'\D', '', prod.find('NCM').text).zfill(8) if prod is not None else "",
                    "VPROD": safe_float(prod.find('vProd').text) if prod is not None else 0.0,
                    "ORIGEM": orig_ex, "CST-ICMS": cst_ex.zfill(2) if cst_ex else "",
                    "BC-ICMS": safe_float(buscar_recursivo(imp, ['vBC'])), 
                    "ALQ-ICMS": safe_float(buscar_recursivo(imp, ['pICMS'])), 
                    "VLR-ICMS": safe_float(buscar_recursivo(imp, ['vICMS'])),
                    "VLR-ICMS-ST": safe_float(buscar_recursivo(imp, ['vICMSST'])),
                    "CST-PIS": buscar_recursivo(imp.find('.//PIS'), ['CST']) if imp.find('.//PIS') is not None else "",
                    "VAL-PIS": safe_float(buscar_recursivo(imp, ['vPIS'])),
                    "CST-COF": buscar_recursivo(imp.find('.//COFINS'), ['CST']) if imp.find('.//COFINS') is not None else "",
                    "VAL-COF": safe_float(buscar_recursivo(imp, ['vCOFINS'])),
                    "CST-IPI": buscar_recursivo(imp.find('.//IPI'), ['CST']) if imp.find('.//IPI') is not None else "",
                    "ALQ-IPI": safe_float(buscar_recursivo(imp, ['pIPI'])),
                    "VAL-IPI": safe_float(buscar_recursivo(imp, ['vIPI'])),
                    "VAL-DIFAL": safe_float(buscar_recursivo(imp, ['vICMSUFDest']))
                }
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_ent, df_xs, ae_f, as_f, ge_f, gs_f, cod_cliente=""):
    base_f = buscar_base_no_repositorio(cod_cliente)
    try:
        base_icms = pd.read_excel(base_f, sheet_name='ICMS'); base_icms['NCM_KEY'] = base_icms['NCM'].astype(str).str.zfill(8)
        base_pc = pd.read_excel(base_f, sheet_name='PIS_COFINS'); base_pc['NCM_KEY'] = base_pc['NCM'].astype(str).str.zfill(8)
        base_ipi = pd.read_excel(base_f, sheet_name='IPI'); base_ipi['NCM_KEY'] = base_ipi['NCM_TIPI'].astype(str).str.zfill(8)
    except: base_icms, base_pc, base_ipi = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        man_l = [
            ["SENTINELA - MANUAL MAXIMALISTA DE AUDITORIA FISCAL"], [""],
            ["1. GERENCIAIS: Auditoria de estoque e valores unitários via arquivos CSV."],
            ["2. CST 10: Valida se há destaque de ICMS-ST para o CST 10."],
            ["3. CROSS-CHECK CFOP: Identifica conflitos de operação ST com CFOP Normal."],
            ["4. ESPELHO DE TAGS: Todas as bases e alíquotas extraídas aparecem no relatório."]
        ]
        pd.DataFrame(man_l).to_excel(writer, sheet_name='MANUAL', index=False, header=False)

        def cruzar_aut(df, f):
            if df.empty or f is None: return df
            try:
                df_a = pd.read_excel(f, header=None)
                df_a[0] = df_a[0].astype(str).str.replace('NFe', '').str.strip()
                status_map = df_a.set_index(0)[5].to_dict()
                df['Situação Nota'] = df['CHAVE_ACESSO'].map(status_map).fillna('⚠️ N/Encontrada')
                return df
            except: return df
        df_xs = cruzar_aut(df_xs, as_f)

        if not df_xs.empty:
            # --- ABA ICMS MAXIMALISTA ---
            df_i = df_xs.copy(); ncm_st = df_ent[(df_ent['CST-ICMS']=="60")]['NCM'].unique().tolist() if not df_ent.empty else []
            def audit_icms(row):
                info = base_icms[base_icms['NCM_KEY'] == row['NCM']]
                sit = row.get('Situação Nota', '⚠️ N/V')
                cfop_st = ['5401', '5403', '5405', '6401', '6403', '6404']
                diag_cross = "✅ CFOP/CST OK"
                if row['CFOP'] in cfop_st and row['CST-ICMS'] in ['00', '20']: diag_cross = "❌ Erro: CFOP ST c/ CST Tributado"
                if row['CST-ICMS'] == '10' and row['VLR-ICMS-ST'] == 0: diag_cross = "❌ Alerta: CST 10 sem destaque de ST"
                
                val_github = safe_float(info['ALÍQUOTA'].iloc[0]) if not info.empty and 'ALÍQUOTA' in info.columns else None
                if row['UF_EMIT'] != row['UF_DEST']:
                    alq_esp = 4.0 if str(row['ORIGEM']) in ['1', '2', '3', '8'] else 12.0
                else:
                    alq_esp = val_github if val_github is not None else ALIQUOTAS_UF.get(row['UF_EMIT'], 18.0)
                
                diag_alq = "✅ Alq OK" if abs(row['ALQ-ICMS'] - alq_esp) < 0.01 else f"❌ XML {row['ALQ-ICMS']}% diverge de {alq_esp}%"
                comp = max(0, (alq_esp - row['ALQ-ICMS']) * row['BC-ICMS'] / 100)
                return pd.Series([sit, diag_cross, diag_alq, f"R$ {comp:,.2f}"])
            
            df_i[['Situação Nota', 'Cross-Check CFOP/CST', 'Diagnóstico ICMS', 'Complemento ICMS']] = df_i.apply(audit_icms, axis=1)
            df_i['Carga Efetiva (%)'] = ((df_i['VLR-ICMS'] + df_i['VAL-PIS'] + df_i['VAL-COF'] + df_i['VAL-IPI']) / df_i['VPROD'] * 100).round(2)
            df_i.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)

            # --- DEMAIS ABAS ---
            
            df_xs.to_excel(writer, sheet_name='PIS_COFINS_AUDIT', index=False)
            df_xs.to_excel(writer, sheet_name='IPI_AUDIT', index=False)
            df_xs.to_excel(writer, sheet_name='DIFAL_AUDIT', index=False)

    return output.getvalue()
