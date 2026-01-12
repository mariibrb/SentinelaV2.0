import pandas as pd
import os

def processar_icms(df, writer, cod_cliente):
    """
    Realiza a auditoria de ICMS baseada na Base Tributária do cliente.
    Analisa: Alíquota por UF, Trava de 4% para importados e CST.
    """
    df_i = df.copy()

    # 1. TENTA CARREGAR A BASE TRIBUTÁRIA DO CLIENTE
    # O arquivo deve estar na pasta 'bases' com o nome exato do código do cliente
    caminho_base = f"bases/base_tributaria_{cod_cliente}.xlsx"
    
    base_gabarito = pd.DataFrame()
    if os.path.exists(caminho_base):
        try:
            base_gabarito = pd.read_excel(caminho_base)
            # Garante que NCM seja string e tenha 8 dígitos
            base_gabarito['NCM'] = base_gabarito['NCM'].astype(str).str.strip().str.zfill(8)
        except:
            pass

    # 2. DICIONÁRIO DE ALÍQUOTAS INTERESTADUAIS (Regra Geral)
    # Sul/Sudeste para Norte/Nordeste/ES = 7% | O resto = 12%
    ALQ_INTER = {
        'SUL_SUDESTE': ['SP', 'RJ', 'MG', 'PR', 'RS', 'SC'],
        'NORTE_NORDESTE': ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'RN', 'RO', 'RR', 'SE', 'TO']
    }

    def audit_linha(r):
        uf_origem = str(r.get('UF_EMIT', ''))
        uf_destino = str(r.get('UF_DEST', ''))
        ncm = str(r.get('NCM', '')).zfill(8)
        origem_prod = str(r.get('ORIGEM', '0'))
        alq_xml = r.get('ALQ-ICMS', 0.0)
        
        # --- DEFINIÇÃO DA ALÍQUOTA ESPERADA ---
        alq_esperada = 18.0 # Default interno
        
        # Regra 1: Trava de 4% (Produtos Importados ou com conteúdo de importação > 40%)
        if origem_prod in ['1', '2', '3', '8']:
            if uf_origem != uf_destino: # Apenas em operações interestaduais
                alq_esperada = 4.0
        
        # Regra 2: Alíquota Interestadual (7% ou 12%) se não for 4%
        elif uf_origem != uf_destino:
            if uf_origem in ALQ_INTER['SUL_SUDESTE'] and uf_destino in ALQ_INTER['NORTE_NORDESTE']:
                alq_esperada = 7.0
            else:
                alq_esperada = 12.0
                
        # Regra 3: Consulta a Base Tributária (Gabarito por NCM)
        # Se o NCM existir no arquivo excel do cliente, ele manda na regra
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            filtro = base_gabarito[base_gabarito['NCM'] == ncm]
            # Se houver alíquota específica para a UF de destino no gabarito
            if 'ALQ_INTER' in filtro.columns:
                alq_esperada = safe_float(filtro['ALQ_INTER'].values[0])

        # --- DIAGNÓSTICO FINAL ---
        if abs(alq_xml - alq_esperada) < 0.01:
            diag = "✅ OK"
        elif alq_xml > alq_esperada:
            diag = "⚠️ Alíquota Maior que o Esperado"
        else:
            diag = "❌ Alíquota Menor que o Esperado"

        return pd.Series([diag, alq_esperada])

    # Aplicando a auditoria
    df_i[['Diagnóstico ICMS', 'Alq. Esperada']] = df_i.apply(audit_linha, axis=1)

    # Organizando as colunas para o Excel (Tags originais + Auditoria)
    cols_finais = [c for c in df_i.columns if c not in ['Diagnóstico ICMS', 'Alq. Esperada', 'Situação Nota']]
    cols_finais += ['Situação Nota', 'Alq. Esperada', 'Diagnóstico ICMS']

    df_i[cols_finais].to_excel(writer, sheet_name='ICMS_AUDIT', index=False)

def safe_float(v):
    try: return float(v)
    except: return 0.0
