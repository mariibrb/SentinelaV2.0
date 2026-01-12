import pandas as pd

def gerar_aba_entradas_ac(writer, ge, regras_tes):
    """
    Processa o Gerencial de Entradas e aplica as regras de estorno da aba TES.
    ge: Arquivo gerencial de entradas enviado pelo usuário.
    regras_tes: DataFrame vindo da aba 'TES' do arquivo RET no GitHub.
    """
    if ge is None:
        return

    # 1. Carregar o Gerencial de Entrada
    try:
        df_ge = pd.read_excel(ge) if ge.name.endswith('.xlsx') else pd.read_csv(ge, sep=None, engine='python')
    except:
        return

    # 2. Padronizar nomes de colunas (Ajuste conforme seu ERP)
    # Vamos focar no ACUMULADOR e nos valores de ICMS
    
    # 3. Cruzamento com as Regras da Aba TES
    # Criamos um dicionário de regras: {Acumulador: Regra}
    mapa_regras = dict(zip(regras_tes['ACUMULADOR'].astype(str), regras_tes['REGRA_ESTORNO']))

    def calcular_estorno(linha):
        acu = str(linha.get('codi_acu', linha.get('ACUMULADOR', ''))).strip()
        regra = mapa_regras.get(acu, 'SEM FORMULA')
        vlr_icms = float(linha.get('valor_icms', linha.get('Vlr ICMS', 0)))

        if regra == 'ESTORNA TUDO':
            return vlr_icms
        return 0

    df_ge['Estorno'] = df_ge.apply(calcular_estorno, axis=1)

    # 4. Salvar na Planilha Final
    df_ge.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)
