# 🧡 SENTINELA | Auditoria Digital

O **Sentinela** é uma ferramenta avançada de auditoria fiscal desenvolvida em Python e Streamlit. Ele automatiza o processamento de arquivos XML (NF-e), cruza dados com relatórios gerenciais e gera planilhas detalhadas em Excel com análises de ICMS, IPI, PIS/COFINS e DIFAL.

---

## 🚀 Funcionalidades Principais

* **Extração Inteligente:** Leitura recursiva de arquivos XML (mesmo dentro de arquivos .zip pesados).
* **Cruzamento de Dados:** Validação automática entre XMLs e relatórios gerenciais/autenticidade.
* **Módulos Especialistas:** Auditorias automáticas baseadas nas regras de cada tributo.
* **Integração Dinâmica:** Mesclagem de planilhas externas (RET MG e PIS/COFINS) via GitHub.
* **Interface Premium:** Design "Ultra Clean" com fundo cinza e cards brancos, focado em produtividade.

---

## 📂 Estrutura do Repositório

Para que o sistema localize as regras fiscais e os modelos de cada empresa automaticamente, mantenha exatamente esta estrutura de pastas e nomes no GitHub:

- Bases_Tributárias/ (Arquivo: 394-Bases_Tributarias.xlsx)
- RET/ (Arquivo: 394-RET_MG.xlsx)
- PIS_COFINS/ (Arquivo: 394-PIS_COFINS.xlsx)
- .streamlit/ (Arquivos: config.toml, secrets.toml e Clientes Ativos.xlsx)
- sentinela_app.py
- sentinela_core.py

---

## 🛠️ Configurações Técnicas Obrigatórias

### 1. Limite de Upload (Arquivos Grandes)
O arquivo .streamlit/config.toml deve conter as seguintes linhas para permitir uploads de até 1GB:

[server]
headless = true
maxUploadSize = 1000

### 2. Variáveis de Ambiente (Secrets)
No painel do Streamlit Cloud, configure as Secrets:

- GITHUB_TOKEN: Seu Personal Access Token do GitHub.
- GITHUB_REPO: Seu repositório no formato usuario/nome-do-repositorio.

---

## ⚖️ Fluxo de Operação

1. Passo 1: Selecione o cliente na lista. O sistema exibirá um aviso verde confirmando se a Base Tributária foi encontrada.
2. Passo 2: Defina o Regime Tributário e habilite os modelos adicionais (RET ou PIS/COFINS) via Toggle, se necessário.
3. Passo 3: Faça o upload dos XMLs (ZIP bruto) e dos arquivos Gerenciais de Entradas e Saídas.
4. Finalização: Clique em INICIAR AUDITORIA e baixe o relatório consolidado com todas as abas processadas.

---
🧡 Sentinela - Tecnologia a serviço da conformidade fiscal.
