import pandas as pd
import streamlit as st
import requests
import io

def carregar_regras_ret(cod_cliente):
    """Busca o arquivo COD-RET_MG.xlsx no GitHub na pasta Bases_Tributárias"""
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    url = f"https://raw.githubusercontent.com/{repo}/main/Bases_Tributárias/{cod_cliente}-RET_MG.xlsx"
    headers = {"Authorization": f"token {token}"}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return pd.read_excel(io.BytesIO(res.content), sheet_name=None)
        return None
    except:
        return None

def gerar_aba_entradas_ac(writer, ge, regras_tes):
    """
    Processa o Gerencial de Entradas, agrupa por AC e aplica as regras de estorno.
    Mantém o layout de colunas C até K somadas.
    """
    if ge is None or regras_tes is None:
        return

    # 1. Carregar o Gerencial de Entrada (suporta Excel ou CSV)
    try:
        if isinstance(ge, pd.DataFrame):
            df_ge = ge.copy()
        else:
            df_ge = pd.read_excel(ge) if ge.name.endswith('.xlsx') else pd.read_csv(ge, sep=None, engine='python')
    except:
        return

    # 2. Mapeamento das regras de estorno (do arquivo RET no GitHub)
    mapa_regras = dict(zip(regras_tes['ACUMULADOR'].astype(str).str.strip(), regras_tes['REGRA_ESTORNO']))

    # 3. AGRUPAMENTO (A "Tabela Dinâmica" solicitada)
    # Somamos os valores das colunas numéricas (C a J do seu modelo)
    # Utilizamos os nomes técnicos comuns do gerencial de entradas
    resumo = df_ge.groupby(['codi_acu', 'nome_acu']).agg({
        'vlr_cont': 'sum',    # Coluna C
        'base_icms': 'sum',   # Coluna D
        'vlr_icms': 'sum',    # Coluna E
        'vlr_ipi': 'sum',     # Coluna H
        'bc_st': 'sum',       # Coluna I
        'vlr_st': 'sum'       # Coluna J
    }).reset_index()

    # 4. Ajuste de Layout e Nomes de Coluna para o seu padrão
    resumo.columns = ['Código', 'Descrição', 'Vlr Contábil', 'Base ICMS', 'Vlr ICMS', 'Vlr IPI', 'BC ICMS ST', 'Vlr ICMS ST']
    
    # Inserindo colunas vazias para manter as letras F e G na ordem correta
    resumo.insert(5, 'Isentas ICMS', 0)
    resumo.insert(6, 'Outras ICMS', 0)

    # 5. Cálculo da Coluna K (Estorno) e L (Observação detalhada)
    def aplicar_regra(linha):
        ac_str = str(linha['Código']).strip()
        regra = mapa_regras.get(ac_str, 'NÃO MAPEADO')
        vlr_icms_puro = linha['Vlr ICMS']
        
        if regra == 'ESTORNA TUDO':
            estorno = vlr_icms_puro
            obs = f"Cálculo: 100% do ICMS estornado. Valor extraído do AC {ac_str} via regra '{regra}' (GitHub)."
        elif regra == 'SEM FORMULA':
            estorno = 0
            obs = f"Acumulador {ac_str} identificado, mas configurado como 'SEM FORMULA' no GitHub."
        else:
            estorno = 0
            obs = f"Aviso: Acumulador {ac_str} não encontrado na planilha de regras {st.session_state.get('cod_cliente')}-RET_MG.xlsx."
            
        return pd.Series([estorno, obs])

    # Criamos as colunas de resultado final
    resumo[['Estorno', 'Observação']] = resumo.apply(aplicar_regra, axis=1)
    
    # Colunas finais de Check e Estorno de Devolução (M e N)
    resumo['Check'] = ""
    resumo['ESTORNO DEV'] = 0

    # 6. Salvar na Planilha Final
    resumo.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    """
    Função principal que o Core chama para orquestrar as abas de Minas.
    """
    regras = carregar_regras_ret(cod_cliente)
    
    if regras:
        # 1. Cria a aba Espelho do Mapa (Auditabilidade)
        if 'Mapa RET' in regras:
            regras['Mapa RET'].to_excel(writer, sheet_name='MAPA_RET', index=False)
        
        # 2. Cria a aba Entradas AC (Compilado Dinâmico)
        if 'TES' in regras and ge is not None:
            # Pega o primeiro gerencial de entrada
            arquivo_ge = ge[0] if isinstance(ge, list) else ge
            gerar_aba_entradas_ac(writer, arquivo_ge, regras['TES'])
            
        st.success(f"🔺 Processamento RET finalizado para {cod_cliente}.")
    else:
        st.error(f"❌ Arquivo {cod_cliente}-RET_MG.xlsx não localizado na pasta 'Bases_Tributárias' do GitHub.")
