# 🧡 SENTINELA | Manual de Operação e Guia de Auditoria

O **Sentinela** é uma ferramenta de auditoria fiscal de alta performance. Este manual orienta a configuração, a preparação dos dados e, principalmente, como agir sobre os diagnósticos gerados pelo sistema.

---

## 🚀 1. O que o Sentinela Auditora?

* **ICMS:** Confronto de alíquotas XML vs. Base Tributária e validação de CST.
* **IPI:** Verificação de enquadramento e cálculo de imposto por NCM.
* **PIS/COFINS:** Análise baseada no Regime Tributário (Real/Presumido) e cruzamento com bases personalizadas.
* **DIFAL:** Cálculo automático do diferencial de alíquotas em operações interestaduais.
* **RET MG:** Integração de modelos de Regime Especial para empresas mineiras.

---

## 📂 2. Estrutura de Pastas e Bases (GitHub)

O sistema busca arquivos dinamicamente no seu repositório. Respeite esta estrutura:

- **Bases_Tributárias/** -> CÓDIGO-Bases_Tributarias.xlsx (Regras de alíquotas e CST)
- **RET/** -> CÓDIGO-RET_MG.xlsx (Modelos de Regime Especial)
- **PIS_COFINS/** -> CÓDIGO-PIS_COFINS.xlsx (Bases personalizadas)
- **.streamlit/** -> config.toml (Upload de 1GB), secrets.toml e Clientes Ativos.xlsx.

---

## 📥 3. Preparação dos Arquivos para Upload

### 📄 XMLs
* O sistema aceita arquivos .xml ou .zip. A leitura é recursiva (lê todas as pastas internas).

### 📄 Relatórios Gerenciais
* As colunas devem conter: `NUM_NF`, `VLR_NF` (ou `VITEM`), `CFOP`, `NCM`, `CST-ICMS`.

### 📄 Relatórios de Autenticidade
* Usados para validar o status da nota. O sistema busca o status na 6ª coluna.

---

## 🛠️ 4. Configurações Técnicas (Servidor)

### Limite de Upload (1GB) e Tema
O arquivo `.streamlit/config.toml` deve conter:
[server]
headless = true
maxUploadSize = 1000

---

## ⚖️ 5. Guia de Diagnóstico: O que fazer em cada situação?

Quando o relatório final apontar divergências, siga estas orientações:

### 🚩 Erro de Alíquota de ICMS (Aba ICMS)
* **Situação:** O valor calculado pelo Sentinela difere do valor destacado na nota.
* **O que fazer:** Verifique se a regra na "Base Tributária" do GitHub está atualizada para aquele NCM/Estado. Se a regra estiver certa, a empresa destacou o imposto errado; se a regra mudou, atualize a planilha no GitHub.

### 🚩 Diferença de Base de Cálculo (Aba IPI/ICMS)
* **Situação:** A base de cálculo da nota está menor que o valor do item.
* **O que fazer:** Avalie se há benefícios fiscais (redução de base) não mapeados. Caso contrário, pode haver uma omissão de base tributável.

### 🚩 CST Incorreto
* **Situação:** O CST informado na nota não condiz com a operação ou com a regra do cliente.
* **O que fazer:** Cruze com o CFOP. Se for uma operação de Substituição Tributária (ST) e o CST for de Tributação Integral, há um erro de parametrização no ERP do cliente.

### 🚩 PIS/COFINS em Desacordo (Aba PIS_COFINS)
* **Situação:** Alíquota calculada diverge do regime (Real 1,65%/7,6% ou Presumido 0,65%/3%).
* **O que fazer:** Verifique se o item é monofásico ou alíquota zero. Se o toggle "Habilitar PIS/COFINS" foi usado, confira se o item está na lista de exceções da sua base personalizada.

### 🚩 Nota "Não Encontrada" ou "Cancelada"
* **Situação:** Status da nota aparece como erro ou divergente do Gerencial.
* **O que fazer:** Verifique o arquivo de Autenticidade. Notas canceladas no SEFAZ mas presentes no Gerencial indicam que o financeiro/fiscal do cliente não processou o cancelamento no sistema interno.

---

## 💾 6. O Relatório Final

* **RESUMO:** Visão executiva das falhas.
* **AUDITORIAS:** Detalhamento linha a linha para correções no ERP.
* **MESCLAGEM:** Abas externas (RET/PC) anexadas ao final para conferência completa.

---
🧡 Sentinela - Tecnologia a serviço da conformidade fiscal.
