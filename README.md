# NOVA-AI

### Seu assistente de inteligência artificial para Windows

A **NOVA-AI** é um assistente de inteligência artificial desenvolvido para Windows, com o objetivo de unir conversas com IA e automação de tarefas no computador.

O projeto combina modelos de inteligência artificial locais e serviços em nuvem, oferecendo uma interface desktop para interagir com a IA e solicitar operações no sistema.

A proposta é permitir que o usuário utilize linguagem natural para fazer perguntas, gerenciar arquivos, pesquisar aplicativos e executar diferentes tarefas com autorização.

---

## Índice

- [Sobre o projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Tecnologias utilizadas](#tecnologias-utilizadas)
- [Requisitos](#requisitos)
- [Instalação para usuários](#instalação-para-usuários)
- [Instalação para desenvolvedores](#instalação-para-desenvolvedores)
- [Configuração da inteligência artificial](#configuração-da-inteligência-artificial)
- [Como utilizar](#como-utilizar)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Armazenamento de dados](#armazenamento-de-dados)
- [Segurança e privacidade](#segurança-e-privacidade)
- [Solução de problemas](#solução-de-problemas)
- [Contribuições](#contribuições)
- [Licença](#licença)

---

## Sobre o projeto

A NOVA-AI foi desenvolvida como um projeto integrador na área de Tecnologia da Informação e Desenvolvimento de Sistemas.

Diferentemente de um chatbot convencional, o projeto busca permitir que a inteligência artificial interaja com ferramentas do próprio computador.

O aplicativo possui uma arquitetura dividida em duas partes:

- **Frontend:** responsável pela interface e interação com o usuário.
- **Backend:** responsável pelo processamento das solicitações, comunicação com os modelos de IA e execução das ferramentas.

O objetivo é desenvolver um assistente que possa auxiliar em atividades cotidianas, técnicas e de produtividade.

## Funcionalidades

Entre os recursos implementados ou em desenvolvimento estão:

### Inteligência artificial

- Integração com Google Gemini.
- Integração com Ollama para execução de modelos locais.
- Comunicação com modelos de inteligência artificial por meio de uma interface de chat.
- Histórico de conversas armazenado localmente.
- Possibilidade de trabalhar com diferentes provedores de IA.

### Gerenciamento de arquivos

A NOVA-AI possui ferramentas para operações como:

- Criar arquivos e pastas.
- Ler arquivos.
- Editar arquivos.
- Renomear arquivos.
- Mover arquivos.
- Organizar arquivos.
- Baixar arquivos.
- Excluir arquivos.

As operações dependem das permissões disponíveis e das confirmações solicitadas pelo aplicativo.

### Gerenciamento de aplicativos

A integração com o Windows Package Manager (WinGet) permite trabalhar com operações como:

- Pesquisar aplicativos disponíveis.
- Consultar informações dos pacotes.
- Verificar aplicativos instalados.
- Solicitar a instalação de aplicativos.

A disponibilidade depende do WinGet, da conexão com a internet e das permissões do Windows.

### Ambiente de trabalho

O projeto também possui uma área de trabalho utilizada pelo backend para armazenar e organizar arquivos relacionados às operações do assistente.

**Observação:** a disponibilidade de cada recurso pode variar conforme a versão instalada.

---

## Tecnologias utilizadas

### Backend

| Tecnologia | Utilização |
|---|---|
| Python | Linguagem principal |
| FastAPI | API local |
| Uvicorn | Servidor da aplicação |
| PyWebView | Interface desktop |
| SQLite | Banco de dados local |
| Requests | Comunicação HTTP |
| Pydantic | Validação de dados |
| Python-dotenv | Configurações de ambiente |
| PSUtil | Informações e gerenciamento de processos |
| Send2Trash | Operações de exclusão |

### Frontend

| Tecnologia | Utilização |
|---|---|
| React | Interface |
| TypeScript | Desenvolvimento tipado |
| Vite | Build e desenvolvimento |
| Tailwind CSS | Estilização |
| Lucide React | Ícones |
| React Markdown | Exibição de conteúdo Markdown |

### Inteligência artificial

- Google Gemini API.
- Ollama.
- Modelos locais compatíveis com Ollama.

---

## Requisitos

### Para utilizar a versão compilada

- Windows 10 ou Windows 11 de 64 bits.
- Memória RAM suficiente para o modelo de IA escolhido.
- Conexão com a internet para utilizar serviços em nuvem e baixar aplicativos.
- Chave de API do Gemini, caso queira utilizar esse provedor.
- Ollama instalado e configurado para utilizar modelos locais, quando necessário.

A execução local de modelos depende também do hardware disponível, especialmente da memória RAM e da memória de vídeo.

### Para executar o código-fonte

- Windows 10 ou Windows 11.
- Python.
- Node.js e npm.
- Git.
- Ollama, caso queira utilizar modelos locais.

Versões utilizadas durante o desenvolvimento incluem Python 3.15 e Node.js 24. A compatibilidade de outras versões deve ser verificada conforme as dependências do projeto.

---

## Instalação para usuários

Quando uma versão compilada estiver publicada na seção **Releases** deste repositório, o usuário poderá baixar o instalador disponibilizado.

1. Acesse a página de Releases do projeto.
2. Baixe a versão mais recente do instalador.
3. Execute o instalador.
4. Siga as instruções apresentadas.
5. Abra a NOVA-AI após a instalação.
6. Configure o provedor de inteligência artificial desejado.

Não baixe executáveis de fontes desconhecidas.

---

## Instalação para desenvolvedores

### 1. Clonar o repositório

Abra o PowerShell:

```powershell
git clone URL_DO_REPOSITORIO
```

Entre na pasta:

```powershell
cd NOVA-AI
```

### 2. Criar o ambiente virtual Python

```powershell
python -m venv .venv
```

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar as dependências Python

```powershell
pip install -r requirements.txt
```

### 4. Instalar as dependências do frontend

Entre na pasta:

```powershell
cd frontend
```

Instale as dependências:

```powershell
npm install
```

Depois volte para a raiz:

```powershell
cd ..
```

### 5. Configurar as variáveis de ambiente

Crie uma cópia do arquivo de exemplo:

```powershell
Copy-Item backend\.env.example backend\.env
```

Edite o arquivo `backend/.env` e informe suas configurações.

### 6. Executar a aplicação

Na raiz do projeto, com o ambiente virtual ativado:

```powershell
python -m backend.desktop
```

O backend será iniciado pelo aplicativo desktop.

---

## Configuração da inteligência artificial

A NOVA-AI utiliza dois provedores principais.

### Google Gemini

O Gemini permite utilizar modelos de inteligência artificial hospedados na nuvem.

Para utilizar:

1. Acesse o Google AI Studio.
2. Gere uma chave de API.
3. Abra o arquivo `backend/.env`.
4. Configure sua chave.

Exemplo:

```env
GEMINI_API_KEY=SUA_CHAVE_AQUI
GEMINI_MODEL=gemini-3.5-flash-lite
```

Site oficial:

https://aistudio.google.com/

Cada usuário deve utilizar sua própria chave de API e respeitar os limites e condições do serviço do Google.

**Nunca publique sua chave de API no GitHub.**

### Ollama

O Ollama permite executar modelos de inteligência artificial localmente.

Site oficial:

https://ollama.com/

Após instalar o Ollama, abra o terminal e baixe um modelo compatível:

```powershell
ollama pull qwen2.5:3b
```

Exemplo de configuração:

```env
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

Para verificar os modelos disponíveis:

```powershell
ollama list
```

Para verificar se o servidor está respondendo:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

**Importante:** a execução de modelos locais depende do hardware, dos drivers e da compatibilidade entre o Ollama e a GPU.

---

## Como utilizar

Depois de iniciar a NOVA-AI:

1. Abra o aplicativo.
2. Selecione ou configure o provedor de IA disponível.
3. Inicie uma conversa.
4. Escreva sua solicitação em linguagem natural.
5. Quando uma operação exigir autorização, revise a ação antes de confirmar.

### Exemplos de solicitações

**Conversação:**

```text
Explique a diferença entre memória RAM e armazenamento SSD.
```

**Gerenciamento de arquivos:**

```text
Crie uma pasta chamada Projetos na minha área de trabalho.
```

**Organização:**

```text
Organize os arquivos da minha pasta Downloads por categoria.
```

**Pesquisa de aplicativos:**

```text
Pesquise aplicativos de edição de código que posso instalar pelo WinGet.
```

**Informações técnicas:**

```text
Verifique informações sobre o meu computador.
```

Os exemplos demonstram o tipo de solicitação pretendido. A execução depende das ferramentas disponíveis, das permissões e da versão do aplicativo.

---

## Estrutura do projeto

```text
NOVA-AI/
│
├── backend/
│   ├── desktop.py
│   ├── main.py
│   ├── tools.py
│   ├── permissions.py
│   ├── .env.example
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── instalador/
│   ├── identidade/
│   ├── NOVA-AI.iss
│   └── ...
│
├── docs/
│
├── .gitignore
├── NOVA-AI.spec
├── requirements.txt
├── INICIAR_NOVA_AI.bat
├── README.md
├── corrigir_nova.py
└── update_nova.py
```

### Principais arquivos

| Arquivo | Responsabilidade |
|---|---|
| `backend/desktop.py` | Inicialização da aplicação desktop |
| `backend/main.py` | API, comunicação com IA e rotas |
| `backend/tools.py` | Ferramentas e operações |
| `backend/permissions.py` | Permissões e validações |
| `frontend/src/` | Interface do aplicativo |
| `requirements.txt` | Dependências Python |
| `frontend/package.json` | Dependências e scripts frontend |
| `NOVA-AI.spec` | Configuração do PyInstaller |
| `instalador/NOVA-AI.iss` | Configuração do instalador Inno Setup |

---

## Armazenamento de dados

A NOVA-AI utiliza SQLite para armazenar informações localmente.

O banco de dados e a área de trabalho da aplicação são configurados para utilizar a pasta de dados do usuário no Windows.

O caminho utilizado pelo backend é:

```text
%LOCALAPPDATA%\NOVA-AI
```

Essa pasta pode conter:

- Banco de dados.
- Histórico de conversas.
- Arquivos da área de trabalho.
- Outros dados utilizados pela aplicação.

Antes de reinstalar ou remover o aplicativo, recomenda-se fazer uma cópia de segurança dos dados importantes.

---

## Segurança e privacidade

A segurança é um aspecto importante da NOVA-AI, principalmente porque o projeto permite operações no computador.

Recomendações:

- Revise as operações antes de autorizá-las.
- Não permita operações que você não compreenda.
- Não compartilhe chaves de API.
- Não publique arquivos `.env`.
- Não envie senhas, tokens ou informações pessoais ao repositório.
- Mantenha backups dos arquivos importantes.
- Utilize modelos e serviços de IA de fontes confiáveis.

### Dados e serviços externos

Quando o Gemini é utilizado, as solicitações são enviadas ao serviço do Google conforme as condições da API.

Quando um modelo local do Ollama é utilizado, o processamento do modelo ocorre no próprio computador, embora recursos que dependam de internet possam realizar comunicações externas.

O comportamento exato depende do provedor e das ferramentas utilizadas.

---

## Solução de problemas

### A NOVA-AI informa que nenhuma IA está disponível

Verifique:

- Se o Ollama está instalado.
- Se o servidor do Ollama está em execução.
- Se existe um modelo instalado.
- Se o nome do modelo está configurado corretamente.
- Se a chave do Gemini foi configurada corretamente.

Comando para listar modelos:

```powershell
ollama list
```

### Erro ao executar o modelo pela GPU

Verifique:

- Driver da GPU.
- Compatibilidade do driver com o mecanismo de execução.
- Memória disponível.
- Compatibilidade do modelo e do Ollama.

Também é possível investigar a execução do modelo sem aceleração pela GPU, quando essa opção estiver disponível na configuração utilizada.

### Erro de chave do Gemini

Confira:

- Se a chave foi informada corretamente.
- Se o arquivo `.env` está no local esperado.
- Se a chave possui acesso ao modelo configurado.
- Se a API está habilitada e dentro dos limites de utilização.

### Erro ao executar o frontend

Dentro da pasta `frontend`, execute:

```powershell
npm install
npm run build
```

### Erro de dependências Python

Com o ambiente virtual ativado:

```powershell
pip install -r requirements.txt
```

---

## Desenvolvimento e testes

Para verificar a sintaxe dos módulos Python:

```powershell
python -m compileall backend
```

Para verificar o frontend:

```powershell
cd frontend
npm run lint
npm run build
```

Esses comandos verificam aspectos técnicos da aplicação, mas não substituem os testes funcionais.

O projeto continua sujeito a melhorias e testes em diferentes computadores e configurações de hardware.

---

## Contribuições

Contribuições são bem-vindas.

Se você deseja colaborar:

1. Faça um fork do repositório.
2. Crie uma branch para sua alteração.
3. Implemente a melhoria.
4. Teste as alterações.
5. Envie um Pull Request explicando o que foi modificado.

Sugestões, correções e relatos de problemas também são úteis para a evolução do projeto.

Ao contribuir, evite enviar:

- Chaves de API.
- Senhas.
- Arquivos pessoais.
- Bancos de dados reais.
- Executáveis desnecessários.
- Modelos de IA pesados.

---

## Licença

A licença do projeto deverá ser definida pelo responsável pelo repositório.

Até que um arquivo de licença seja adicionado, não presuma que o código pode ser redistribuído ou utilizado livremente.

---

## Sobre

**NOVA-AI — Inteligência artificial integrada ao computador.**

Projeto desenvolvido na área de Tecnologia da Informação e Desenvolvimento de Sistemas, com foco em inteligência artificial, automação e produtividade no Windows.