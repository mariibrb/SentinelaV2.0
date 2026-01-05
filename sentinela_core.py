import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re, io, requests, streamlit as st

def safe_float(v):
    if v is None: return 0.0
    try:
        txt = str(v).replace('R$', '').replace(' ', '').strip()
        if ',' in txt and '.' in txt: txt = txt.replace('.', '').replace(',', '.')
        elif ',' in txt: txt = txt.replace(',', '.')
        return round(float(txt), 4)
    except: return 0.0

def buscar_base_no_github(cod_cliente):
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
            def buscar(tag, raiz):
                alvo = raiz.find(f'.//{tag}')
                return alvo.text if alvo is not None and alvo.text is not None else ""
            def buscar_recursivo(node, tags_alvo):
                for elem in node.iter():
                    tag_limpa = elem.tag.split('}')[-1]
                    if tag_limpa in tags_alvo: return elem.text
                return ""

            inf = root.find('.//infNFe'); chave = inf.attrib.get('Id', '')[3:] if inf is not None else ""
            emit = root.find('.//emit'); dest = root.find('.//dest')
            cnpj_e = buscar('CNPJ', emit) or buscar('CPF', emit)
            cnpj_d = buscar('CNPJ', dest) or buscar('CPF', dest)

            for det in root.findall('.//det'):
                prod = det.find('prod'); imp = det.find('imposto')
                icms_node = imp.find('.//ICMS') if imp is not None else None
                cst_ex = buscar_recursivo(icms_node, ['CST', 'CSOSN']) if icms_node is not None else ""
                orig_ex = buscar_recursivo(icms_node, ['orig']) if icms_node is not None else ""
                
                linha = {
                    "CHAVE_ACESSO": str(chave).strip(), "NUM_NF": buscar('nNF', root),
                    "CNPJ_EMIT": cnpj_e, "CNPJ_DEST": cnpj_d, "UF_EMIT": buscar('UF', emit), "UF_DEST": buscar('UF', dest),
                    "CFOP": buscar('CFOP', prod), "NCM": re.sub(r'\D', '', buscar('NCM', prod)).zfill(8),
                    "VPROD": safe_float(buscar('vProd', prod)), "ORIGEM": orig_ex, "CST-ICMS": cst_ex.zfill(2) if cst_ex else "",
                    "BC-ICMS": safe_float(buscar('vBC', imp)), "ALQ-ICMS": safe_float(buscar('pICMS', imp)), "VLR-ICMS": safe_float(buscar('vICMS', imp)),
                    "CST-PIS": buscar_recursivo(imp.find('.//PIS'), ['CST']) if imp.find('.//PIS') is not None else "",
                    "CST-IPI": buscar_recursivo(imp.find('.//IPI'), ['CST']) if imp.find('.//IPI') is not None else "",
                    "ALQ-IPI": safe_float(buscar('pIPI', imp.find('.//IPI'))) if imp.find('.//IPI') is not None else 0.0,
                    "VAL-DIFAL": safe_float(buscar('vICMSUFDest', imp))
                }
                dados_lista.append(linha)
        except: continue
    return pd.DataFrame(dados_lista)

def gerar_excel_final(df_ent, df_sai, ae_f, as_f, ge_f, gs_f, cod_cliente=""):
    base_f = buscar_base_no_github(cod_cliente); lista_erros = []
    try:
        base_icms = pd.read_excel(base_f, sheet_name='ICMS'); base_icms['NCM_KEY'] = base_icms.iloc[:, 0].astype(str).str.zfill(8)
        base_pc = pd.read_excel(base_f, sheet_name='PIS_COFINS'); base_pc['NCM_KEY'] = base_pc.iloc[:, 0].astype(str).str.zfill(8)
        base_ipi = pd.read_excel(base_f, sheet_name='IPI'); base_ipi['NCM_KEY'] = base_ipi.iloc[:, 0].astype(str).str.zfill(8)
    except: base_icms, base_pc, base_ipi = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # --- MANUAL MAXIMALISTA ---
        man_l = [
            ["SENTINELA - MANUAL TÉCNICO E OPERACIONAL (MAXIMALISTA)"],
            ["1. OBJETIVO: Este sistema audita a integridade tributária cruzando XMLs com regras do GitHub."],
            ["2. SITUAÇÃO DA NOTA: A Chave de Acesso do XML é buscada no arquivo de Autenticidade."],
            ["   Se a chave não for encontrada, o status será '⚠️ N/Verif' por falta de prova."],
            ["3. LÓGICA DO CST 60: Operações com CST 60 (ST Retido anteriormente) exigem prova de entrada."],
            ["   O motor varre os XMLs de entrada buscando o mesmo NCM com retenção de ST."],
            ["4. ALÍQUOTAS (ESCALA): O sistema converte pontuações brasileiras e americanas automaticamente."],
            ["   Exemplo: 18.0, 18,0 e 18 são interpretados como 18.0%."],
            ["5. NCM AUSENTE: Indica que o código NCM do XML não foi localizado na sua planilha GitHub."],
            ["   O sistema aponta em qual aba (ICMS, PIS ou IPI) o cadastro está faltando."],
            ["6. COMPLEMENTO: Valor financeiro estimado do imposto não recolhido ou recolhido a maior."]
        ]
        pd.DataFrame(man_l).to_excel(writer, sheet_name='MANUAL', index=False, header=False)
        writer.sheets['MANUAL'].set_column('A:A', 120)

        def cruzar_aut(df, f):
            if df.empty or not f: return df
            try:
                df_a = pd.read_excel(f); col_c = next((c for c in df_a.columns if 'Chave' in str(c)), None)
                col_s = next((c for c in df_a.columns if 'Status' in str(c) or 'Situação' in str(c)), None)
                if col_c and col_s:
                    df_a[col_c] = df_a[col_c].astype(str).str.strip()
                    m = df_a.set_index(col_c)[col_s].to_dict()
                    df['Situação Nota'] = df['CHAVE_ACESSO'].map(m).fillna('⚠️ Chave Não Localizada')
                return df
            except: return df
        df_sai = cruzar_aut(df_sai, as_f)

        if not df_sai.empty:
            # ICMS AUDIT (MAXIMALISTA)
            df_i = df_sai.copy(); ncm_st = df_ent[(df_ent['CST-ICMS']=="60")]['NCM'].unique().tolist() if not df_ent.empty else []
            def audit_icms(row):
                info = base_icms[base_icms['NCM_KEY'] == row['NCM']]
                st_e = "✅ Entrada com ST Localizada" if row['NCM'] in ncm_st else "❌ Sem Histórico de ST na Entrada"
                sit = row.get('Situação Nota', '⚠️ Arquivo de Autenticidade não processado')
                if row['CST-ICMS'] == "60":
                    diag = "✅ ST Validado na Saída" if row['NCM'] in ncm_st else "❌ Alerta: Saída como CST 60 sem comprovante de ST na entrada"
                    return pd.Series([sit, st_e, diag])
                if info.empty: return pd.Series([sit, st_e, f"❌ NCM {row['NCM']} Ausente na aba ICMS da Base GitHub"])
                aliq_b = info.iloc[0, 2]; alq_b_val = safe_float(aliq_b)
                if pd.isna(aliq_b): return pd.Series([sit, st_e, "❌ Erro: Alíquota não preenchida na Base GitHub para este NCM"])
                diag = "✅ Correto" if abs(row['ALQ-ICMS'] - alq_b_val) < 0.01 else f"❌ Alíquota XML ({row['ALQ-ICMS']}%) diverge da Base ({alq_b_val}%)"
                return pd.Series([sit, st_e, diag])
            df_i[['Situação Nota', 'Check ST Entrada', 'Diagnóstico ICMS']] = df_i.apply(audit_icms, axis=1)
            df_i.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)

            # PIS_COFINS AUDIT
            df_p = df_sai.copy()
            def audit_pc(row):
                info = base_pc[base_pc['NCM_KEY'] == row['NCM']]
                if info.empty: return f"❌ NCM {row['NCM']} Ausente na aba PIS_COFINS da Base"
                cst_b = str(info.iloc[0, 2]).zfill(2)
                return "✅ Correto" if row['CST-PIS'] == cst_b else f"❌ CST XML ({row['CST-PIS']}) diverge da Base ({cst_b})"
            df_p['Diagnóstico PIS/COF'] = df_p.apply(audit_pc, axis=1)
            df_p.to_excel(writer, sheet_name='PIS_COF_AUDIT', index=False)

            # IPI AUDIT
            df_ipi = df_sai.copy()
            def audit_ipi(row):
                info = base_ipi[base_ipi['NCM_KEY'] == row['NCM']]
                if info.empty: return f"❌ NCM {row['NCM']} Ausente na aba IPI da Base"
                alq_b = safe_float(info.iloc[0, 2])
                return "✅ Correto" if abs(row['ALQ-IPI'] - alq_b) < 0.01 else f"❌ Alíquota IPI ({row['ALQ-IPI']}%) diverge da Base ({alq_b}%)"
            df_ipi['Diagnóstico IPI'] = df_ipi.apply(audit_ipi, axis=1)
            df_ipi.to_excel(writer, sheet_name='IPI_AUDIT', index=False)

            # DIFAL AUDIT (TAGS + REGRA)
            df_dif = df_sai.copy()
            def audit_dif(row):
                if row['UF_EMIT'] != row['UF_DEST'] and row['VAL-DIFAL'] == 0:
                    return "❌ Alerta: Operação Interestadual sem destaque de DIFAL"
                return "✅ OK ou Não Aplicável"
            df_dif['Diagnóstico DIFAL'] = df_dif.apply(audit_dif, axis=1)
            df_dif.to_excel(writer, sheet_name='DIFAL_AUDIT', index=False)

        # ABA RESUMO MAXIMALISTA
        df_res = pd.DataFrame(lista_erros) if lista_erros else pd.DataFrame([{"RESULTADO": "Nenhuma inconsistência maximalista encontrada."}])
        df_res.to_excel(writer, sheet_name='RESUMO_ERROS', index=False)

    return output.getvalue()
