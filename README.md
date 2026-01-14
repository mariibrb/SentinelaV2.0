🧡 SENTINELA | Auditoria Digital
O Sentinela é uma ferramenta avançada de auditoria fiscal desenvolvida em Python e Streamlit. Ele automatiza o processamento de arquivos XML (NF-e), cruza dados com relatórios gerenciais e gera planilhas detalhadas em Excel com análises de ICMS, IPI, PIS/COFINS e DIFAL.

🚀 Funcionalidades Principais
Extração Inteligente: Leitura recursiva de arquivos XML (mesmo dentro de múltiplos arquivos .zip).

Cruzamento de Dados: Validação automática entre XMLs e relatórios gerenciais/autenticidade.

Módulos Especialistas: Auditorias automáticas baseadas nas regras de cada tributo.

Integração Dinâmica: Mesclagem de planilhas externas (RET MG e PIS/COFINS) via GitHub.

Interface Premium: Design "Ultra Clean" com fundo cinza e cards brancos, focado em produtividade.

📂 Estrutura do Repositório (Organização das Bases)
Para que o sistema localize as regras fiscais e os modelos de cada empresa automaticamente, mantenha exatamente esta estrutura de pastas e nomes no GitHub:

Plaintext


├── Bases_Tributárias/
│   └── 394-Bases_Tributarias.xlsx      # Regras de alíquotas e CST por cliente
├── RET/
│   └── 394-RET_MG.xlsx                # Modelos de Regime Especial (MG)
├── PIS_COFINS/
│   └── 394-PIS_COFINS.xlsx            # Planilhas específicas de PIS/COFINS
├── .streamlit/
│   ├── config.toml                     # Configurações de tema e limite de upload (1GB)
│   ├── secrets.toml                    # Tokens de acesso ao GitHub (Privado)
│   └── Clientes Ativos.xlsx            # Cadastro de CÓD e CNPJ dos clientes
├── sentinela_app.py                    # Interface do Usuário (Streamlit)
└── sentinela_core.py                   # Motor de processamento fiscal


🛠️ Configurações Técnicas Obrigatórias
1. Limite de Upload (Arquivos Grandes)
O arquivo .streamlit/config.toml deve conter as seguintes linhas para evitar erros com arquivos ZIP pesados:

[server]
headless = true
maxUploadSize = 1000


2. Variáveis de Ambiente (Secrets)
No painel do Streamlit Cloud, você deve configurar as Secrets para que o App acesse seu GitHub privado:

GITHUB_TOKEN: Seu Personal Access Token do GitHub.

GITHUB_REPO: Seu repositório no formato usuario/nome-do-repositorio.

⚖️ Fluxo de Operação
Passo 1: Selecione o cliente na lista. O sistema exibirá um aviso verde confirmando se a Base Tributária foi encontrada no GitHub.

Passo 2: Defina o Regime Tributário e habilite os modelos adicionais (RET ou PIS/COFINS) se desejar que o sistema mescle essas planilhas ao relatório final.

Passo 3: Faça o upload dos XMLs (pode ser o ZIP bruto) e dos arquivos Gerenciais/Autenticidade de Entradas e Saídas.

Finalização: Clique em INICIAR AUDITORIA, aguarde o processamento e baixe o relatório consolidado com todas as abas de auditoria.

🧡 Sentinela - Tecnologia a serviço da conformidade fiscal.
