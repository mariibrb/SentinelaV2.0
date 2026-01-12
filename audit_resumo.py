import pandas as pd

def gerar_aba_resumo(writer):
    # Estrutura do Manual em Blocos para facilitar a leitura
    manual = [
        ["🛡️ MANUAL DE DIAGNÓSTICOS SENTINELA - AUDITORIA FISAL DIGITAL"],
        [""],
        ["📌 1. ENTENDA OS SÍMBOLOS DE STATUS"],
        ["✅ OK: O valor ou código no XML está idêntico ao esperado pela legislação ou Gabarito."],
        ["❌ Erro / Divergente: Foi identificada uma diferença que impacta o cálculo do imposto."],
        ["⚠️ Atenção / Alerta: A situação é legalmente possível (ex: Base Reduzida), mas requer conferência."],
        [""],
        ["📂 2. GUIA DAS ABAS DE AUDITORIA"],
        [""],
        ["📗 [ICMS_AUDIT] - Auditoria de ICMS Próprio e ST"],
        ["   • Analisa a 'Trava de 4%' (Importados) e alíquotas interestaduais."],
        ["   • Cruza o NCM com o Gabarito do Cliente para validar CST e Alíquota."],
        ["   • Coluna 'VALOR_NF_COMPLEMENTAR': Indica o valor exato a ser pago em caso de erro."],
        [""],
        ["📘 [IPI_AUDIT] - Auditoria de IPI"],
        ["   • Confronta a alíquota do XML com a TIPI (Tabela de IPI) por NCM."],
        ["   • Valida se a CST de IPI é compatível com a operação."],
        [""],
        ["📙 [PIS_COFINS_AUDIT] - Contribuições Federais"],
        ["   • Valida o cálculo baseado no Regime selecionado (Lucro Real ou Presumido)."],
        ["   • Identifica se produtos Monofásicos ou Alíquota Zero foram tributados indevidamente."],
        [""],
        ["📕 [DIFAL_AUDIT] - Diferencial de Alíquota (EC 87/15)"],
        ["   • Analisa se a nota deveria ter DIFAL e se o destaque foi esquecido."],
        ["   • Valida as novas alíquotas internas de destino (2025/2026)."],
        [""],
        ["📊 [APURAÇÃO_DIFAL] - Resumo para Pagamento"],
        ["   • Consolida os valores totais de DIFAL e FCP por Estado (UF)."],
        ["   • Utilizado pelo financeiro para conferência de guias GNRE."],
        [""],
        ["🛠️ 3. AÇÕES CORRETIVAS SUGERIDAS"],
        ["• 'Emitir NF Complementar': Quando o imposto destacado é menor que o devido."],
        ["• 'Registrar CC-e': Para erros de CST ou NCM que não alteram valores."],
        ["• 'Avaliar Restituição': Quando houve pagamento maior que o legalmente exigido."],
        [""],
        ["--- Relatório Gerado pelo Motor Sentinela ---"]
    ]

    # Criando o DataFrame sem cabeçalho e sem índice
    df_manual = pd.DataFrame(manual)
    
    # Gravando no Excel
    df_manual.to_excel(writer, sheet_name='RESUMO', index=False, header=False)
    
    # Ajustando a largura da coluna para o texto não ficar cortado
    worksheet = writer.sheets['RESUMO']
    worksheet.set_column(0, 0, 100) # Deixa a coluna A bem larga para o manual
