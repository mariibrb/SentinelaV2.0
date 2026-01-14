# 🧡 SENTINELA | Manual de Operação e Auditoria Digital

O **Sentinela** é uma ferramenta de auditoria fiscal de alta performance desenvolvida em Python. Este manual orienta a configuração do ambiente, a organização das bases no GitHub e a preparação dos dados para garantir que os cruzamentos fiscais sejam 100% precisos.

---

## 🚀 1. O que o Sentinela Auditora?

* **ICMS:** Confronto de alíquotas XML vs. Base Tributária e validação de CST.
* **IPI:** Verificação de enquadramento e cálculo de imposto por NCM.
* **PIS/COFINS:** Análise baseada no Regime Tributário (Real/Presumido) e cruzamento com bases personalizadas.
* **DIFAL:** Cálculo automático do diferencial de alíquotas em operações interestaduais.
* **RET MG:** Integração de modelos de Regime Especial para empresas mineiras.

---

## 📂 2. Estrutura de Pastas e Bases (GitHub)

O sistema busca arquivos dinamicamente no seu repositório privado. Para o funcionamento correto, respeite exatamente esta estrutura:

- **Bases_Tributárias/** -> Arquivo: CÓDIGO-Bases_Tributarias.xlsx (Ex: 394-Bases_Tributarias.xlsx)
- **RET/** -> Arquivo: CÓDIGO-RET_MG.xlsx (Ex: 394-RET_MG.xlsx)
- **PIS_COFINS/** -> Arquivo: CÓDIGO-PIS_COFINS.xlsx (Ex: 394-PIS_COFINS.xlsx)
- **.streamlit/** -> Arquivos: config.toml, secrets.toml e Clientes Ativos.xlsx.

---

## 📥 3. Preparação dos Arquivos para Upload

### 📄 Arquivos XML (Notas Fiscais)
* O sistema aceita arquivos .xml individuais ou pastas compactadas em .zip.
* A leitura é recursiva: o Sentinela vasculha todas as subpastas dentro do ZIP automaticamente.

### 📄 Relatórios Gerenciais (CSV ou Excel)
As colunas devem conter os nomes padrões para cruzamento:
* NUM_NF ou NF (Número da Nota)
* VLR_NF ou VITEM (Valor do Item/Total)
* CFOP e NCM (8 dígitos)
* CST-ICMS ou CST

### 📄 Relatórios de Autenticidade
* Utilizados para validar o status da nota (Autorizada/Cancelada). O sistema lê a chave de acesso e busca o status na 6ª coluna do arquivo.

---

## 🛠️ 4. Configurações Técnicas (Desenvolvedor)

### Limite de Upload (1GB)
O arquivo .streamlit/config.toml DEVE conter estas linhas para permitir arquivos pesados:

[server]
headless = true
maxUploadSize = 1000

### Variáveis de Segurança (Secrets no Streamlit Cloud)
Configure no painel Settings > Secrets:
* GITHUB_TOKEN: Seu Personal Access Token do GitHub.
* GITHUB_REPO: Seu repositório no formato usuario/nome-do-projeto.

---

## ⚖️ 5. Fluxo de Operação Passo a Passo

1. **Seleção do Cliente:** Selecione a empresa. O sistema emitirá um aviso Verde confirmando que as bases foram localizadas no GitHub.
2. **Habilitar Modelos:** Ative os botões (Toggles) de RET MG ou PIS/COFINS apenas se você subiu os arquivos correspondentes para as pastas no GitHub.
3. **Upload de Arquivos:** Insira os XMLs e os relatórios de Entradas e Saídas nos campos indicados.
4. **Execução:** Clique em INICIAR AUDITORIA. O sistema processará os dados e aplicará as fórmulas de auditoria.

---

## 💾 6. Entendendo o Relatório Final (Excel)

* **RESUMO:** Painel geral com as principais divergências encontradas.
* **AUDITORIAS:** Abas coloridas onde cada linha aponta o valor calculado pelo sistema vs. o valor da nota, destacando erros de alíquota ou base de cálculo.
* **MESCLAGEM:** Se habilitado, as abas extras de PIS/COFINS ou RET serão anexadas ao final do arquivo, mantendo toda a formatação original.

---
🧡 Sentinela - Tecnologia a serviço da conformidade fiscal.
