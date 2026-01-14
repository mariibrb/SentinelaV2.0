# 🧡 SENTINELA | Auditoria Digital

O **Sentinela** é uma ferramenta avançada de auditoria fiscal desenvolvida em Python e Streamlit. Ele automatiza o processamento de arquivos XML (NF-e), cruza dados com relatórios gerenciais e autenticidade, e gera relatórios detalhados em Excel com análises de ICMS, IPI, PIS/COFINS e DIFAL.



## 🚀 Funcionalidades Principal

* **Extração Inteligente:** Leitura recursiva de arquivos XML (mesmo dentro de múltiplos arquivos .zip).
* **Cruzamento de Dados:** Validação automática entre XMLs de saída e relatórios de auditoria.
* **Módulos Especialistas:** Auditorias automáticas de ICMS, IPI, PIS/COFINS e DIFAL.
* **Mesclagem Dinâmica:** Integração de planilhas externas de impostos (RET MG e PIS/COFINS personalizados) baseada em Flags.
* **Visual Premium:** Interface "Ultra Clean" com design focado na experiência do usuário.

---

## 📂 Estrutura do Repositório

Para que o sistema localize as bases de dados e modelos corretamente, mantenha a seguinte estrutura no GitHub:

```text
├── Bases_Tributárias/
│   └── 394-Bases_Tributarias.xlsx      # Regras fiscais por cliente
├── RET/
│   └── 394-RET_MG.xlsx                # Modelos de Regime Especial (MG)
├── PIS_COFINS/
│   └── 394-PIS_COFINS.xlsx            # Bases personalizadas de PIS/COFINS
├── .streamlit/
│   ├── config.toml                     # Configurações de tema e limite de upload
│   ├── secrets.toml                    # Tokens do GitHub e Credenciais
│   └── Clientes Ativos.xlsx            # Base de dados dos clientes (CÓD/CNPJ)
├── sentinela_app.py                    # Arquivo principal da interface
└── sentinela_core.py                   # Motor de processamento e lógica
