# Aplicativo LinkedIn AutoPost (Kivy)

Este projeto é uma conversão do script Python `LinkedinTelegramPostScheduleModelsV20.py` para um aplicativo Android utilizando o framework Kivy. O objetivo foi adaptar as funcionalidades de automação de postagens no LinkedIn e Telegram (foco no LinkedIn para o app) para uma interface gráfica móvel.

## Estrutura do Projeto

O projeto está organizado da seguinte forma dentro do diretório `linkedin_autopost_app`:

-   `main.py`: Ponto de entrada principal do aplicativo Kivy. Gerencia as telas, a configuração do aplicativo e a inicialização do backend.
-   `backend_logic.py`: Contém toda a lógica de negócios refatorada do script original. Isso inclui:
    -   Gerenciamento de tokens e autenticação com a API do LinkedIn.
    -   Busca e processamento de artigos de feeds RSS (incluindo tradução de títulos).
    -   Geração de resumos de artigos utilizando a API do Azure OpenAI (e outros modelos configurados).
    -   Análise de sentimento de texto utilizando a API de Análise de Texto dos Serviços Cognitivos do Azure.
    -   Postagem de conteúdo no LinkedIn.
    -   Agendamento de postagens (com persistência básica).
    -   Funções de utilidade (limpeza de HTML, manipulação de datas, etc.).
-   `app_gui.kv`: Arquivo de linguagem Kivy que define a estrutura e o layout da interface gráfica do usuário, incluindo todas as telas e widgets.
-   `README.md`: Este arquivo.

Arquivos adicionais na entrega (fora da pasta `linkedin_autopost_app`):
-   `LinkedinTelegramPostScheduleModelsV20.py`: O script Python original que serviu de base para este aplicativo.
-   `todo.md`: Documento que acompanhou o desenvolvimento incremental, listando tarefas e o progresso.

## Configuração e Execução

### Dependências

Para executar este aplicativo, você precisará de:

-   Python 3.7+
-   Kivy 2.0.0+ (`pip install kivy`)
-   Bibliotecas Python listadas no script `backend_logic.py` (e no original). As principais são:
    -   `requests` e `aiohttp` (para chamadas HTTP)
    -   `feedparser` (para feeds RSS)
    -   `googletrans_new` (ou similar, para tradução)
    -   `azure-ai-textanalytics` (para análise de sentimento)
    -   `azure-ai-generative` ou `openai` (para os resumos com Azure OpenAI)
    -   `apscheduler` (para agendamento)
    -   `beautifulsoup4` (para limpeza de HTML)

    É recomendável criar um ambiente virtual e instalar as dependências nele.
    ```bash
    python -m venv kivy_env
    source kivy_env/bin/activate # ou kivy_env\Scripts\activate no Windows
    pip install kivy requests aiohttp feedparser googletrans_new azure-ai-textanalytics azure-ai-generative apscheduler beautifulsoup4
    ```

### Configuração de Credenciais

O aplicativo utiliza um arquivo de configuração (`linkedinautopost.ini` na pasta de dados do usuário do Kivy) para armazenar as chaves de API. Ao executar o aplicativo pela primeira vez, você pode ir para a tela "Configurações" e inserir:

-   **Azure Token:** Seu token de acesso para os serviços Azure OpenAI (usado para geração de resumos).
-   **Azure Text Analytics Endpoint e Key:** (Se for usar) Endpoint e chave para o Azure Text Analytics. (Nota: a UI de configurações pode precisar ser expandida para incluir estes campos explicitamente se não estiverem já lá; `main.py` foi atualizado para carregar `azure_text_analytics_endpoint` e `azure_text_analytics_key` da configuração Kivy).
-   **LinkedIn Client ID e Client Secret:** As credenciais da sua aplicação LinkedIn Developer.
-   **LinkedIn Refresh Token:** Essencial para o aplicativo obter e renovar Access Tokens automaticamente.

### Execução

Após instalar as dependências e configurar as credenciais (pela interface do app na primeira execução), você pode rodar o aplicativo a partir do diretório `linkedin_autopost_app`:

```bash
python main.py
```

## Funcionalidades Implementadas (Incluindo Atualizações Recentes)

-   **Interface Gráfica Multi-tela:** Navegação entre tela principal, configurações, seleção de feeds, lista de artigos, detalhes do artigo e **gerenciamento de agendamentos**.
-   **Configuração de API:** Tela para inserir e salvar credenciais de API.
-   **Seleção de Feeds RSS:** Carrega e exibe feeds RSS configurados.
-   **Listagem e Detalhamento de Artigos:** Busca artigos, exibe lista e detalhes.
-   **Geração de Resumos com IA:** Permite solicitar a geração de um resumo otimizado.
-   **Edição de Resumos Gerados (NOVO):** Na tela de detalhes do artigo, o resumo gerado pela IA agora aparece em um campo de texto editável, permitindo modificações antes da postagem.
-   **Postagem no LinkedIn:** Permite postar o resumo (original ou editado) no LinkedIn.
-   **Tela de Gerenciamento de Agendamentos (NOVO):**
    -   Visualização de posts agendados.
    -   Criação de novos agendamentos via pop-up (título, conteúdo, URL, data/hora).
    -   Cancelamento de agendamentos existentes.
-   **Análise de Sentimento (Backend):** Integração com Azure Text Analytics.
-   **Abertura de Links:** Links de artigos podem ser abertos no navegador.

## Considerações e Próximos Passos

Este aplicativo é um protótipo funcional e pode ser expandido com:

-   **Edição de Agendamentos Existentes:** Permitir modificar data/hora ou conteúdo de um post já agendado.
-   **Armazenamento Seguro de Credenciais Avançado:** Para um APK de produção, integrar com Android Keystore.
-   **Empacotamento para Android (Buildozer):** Utilizar o Buildozer para compilar o projeto Kivy em um arquivo APK. Isso requer a configuração de um arquivo `buildozer.spec`.
-   **Melhorias na Interface do Usuário:** Refinamentos visuais, feedback mais detalhado.

Este README fornece uma visão geral do projeto no seu estado atual. Para compilar para Android, será necessário instalar o Buildozer e suas dependências, e configurar o arquivo `buildozer.spec` corretamente.

