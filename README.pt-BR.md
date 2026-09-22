# Querido Diário MCP Server

<!-- mcp-name: io.github.lucaspmgomess/querido-diario-mcp-server -->

**Consulte diários oficiais municipais brasileiros diretamente pelo Claude, Cursor, Codex e outros clientes compatíveis com MCP.**

[![PyPI](https://img.shields.io/pypi/v/querido-diario-mcp-server.svg)](https://pypi.org/project/querido-diario-mcp-server/)
[![Python](https://img.shields.io/pypi/pyversions/querido-diario-mcp-server.svg)](https://pypi.org/project/querido-diario-mcp-server/)
[![CI](https://github.com/lucaspmgomess/querido-diario-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/lucaspmgomess/querido-diario-mcp-server/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-published-brightgreen)](https://registry.modelcontextprotocol.io/?q=io.github.lucaspmgomess%2Fquerido-diario-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**Sem chave de API · Executa localmente · Somente leitura · Sem telemetria · Código aberto**

> 🌎 **English version:** [README.md](./README.md)

O **Querido Diário MCP Server** conecta agentes de IA à API pública do [Querido Diário](https://queridodiario.org.br), permitindo consultar diários oficiais municipais brasileiros por meio de ferramentas estruturadas do Model Context Protocol (MCP).

> **Exemplo de uso:**  
> "Encontre todas as menções a inteligência artificial nos diários oficiais de Porto Alegre em 2026."

O agente pode identificar o município correto, resolver seu código IBGE, consultar o índice de diários oficiais e devolver resultados estruturados sem que o usuário precise conhecer a API.

---

## Por que este projeto existe?

O [Querido Diário](https://queridodiario.org.br), mantido pela [Open Knowledge Brasil](https://ok.org.br/), torna diários oficiais municipais brasileiros pesquisáveis por meio de uma plataforma de dados abertos e de uma API pública.

Este projeto adiciona uma **interface nativa de MCP** sobre essa API, permitindo que clientes e agentes de IA utilizem os dados diretamente como ferramentas.

Sem o MCP, um fluxo típico exigiria:

1. descobrir o município correto;
2. obter o código IBGE correspondente;
3. conhecer a API do Querido Diário;
4. montar os parâmetros de busca;
5. interpretar manualmente a resposta.

Com este servidor, um agente compatível com MCP pode executar esse fluxo de forma estruturada.

O servidor roda localmente como um subprocesso e realiza apenas requisições HTTPS de leitura para a API pública do Querido Diário.

---

## O que dá para fazer?

### Licitações, compras públicas e contratos

Pesquise empresas, processos licitatórios, contratos, termos de contratação e referências a compras governamentais.

> "Encontre menções à ACME Ltda nos diários oficiais de Porto Alegre entre janeiro e julho de 2026."

### Pessoas e organizações

Acompanhe menções a pessoas, empresas, associações, órgãos públicos e outras organizações.

> "Pesquise João da Silva nos diários oficiais de Torres, RS."

### Leis, decretos e atos administrativos

Pesquise legislação municipal, decretos, nomeações, exonerações, atos administrativos e mudanças regulatórias.

> "Encontre publicações relacionadas à regulamentação de inteligência artificial."

### Jornalismo de dados e pesquisa cívica

Use o Querido Diário como fonte estruturada em fluxos de pesquisa assistidos por IA.

> "Busque contratos públicos relacionados a reconhecimento facial nos diários oficiais de Porto Alegre."

### Agentes e automações

Combine a busca em diários oficiais com outros servidores MCP para criar fluxos maiores de investigação, classificação, acompanhamento e análise de informações públicas.

---

## Início rápido

Requisitos:

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/), que fornece o comando `uvx`

Não é necessário clonar o repositório.

```bash
uvx querido-diario-mcp-server
```

Esse comando inicia o servidor MCP via `stdio`.

O servidor não possui interface interativa no terminal por design: ele foi feito para ser iniciado por um cliente MCP.

---

## Conectando ao seu cliente de IA

Todos os clientes abaixo usam o mesmo comando:

```bash
uvx querido-diario-mcp-server
```

### Claude Desktop / Claude Code

Adicione ao `claude_desktop_config.json` no Claude Desktop ou ao `.mcp.json` do projeto no Claude Code:

```json
{
  "mcpServers": {
    "querido-diario": {
      "command": "uvx",
      "args": ["querido-diario-mcp-server"]
    }
  }
}
```

### Cursor

Adicione ao `.cursor/mcp.json` do projeto ou às configurações globais de MCP do Cursor:

```json
{
  "mcpServers": {
    "querido-diario": {
      "command": "uvx",
      "args": ["querido-diario-mcp-server"]
    }
  }
}
```

### Codex CLI

Adicione ao arquivo `~/.codex/config.toml`:

```toml
[mcp_servers.querido-diario]
command = "uvx"
args = ["querido-diario-mcp-server"]
```

### Outros clientes MCP

Qualquer cliente compatível com servidores MCP locais via `stdio` pode utilizar:

- comando: `uvx`
- argumento: `querido-diario-mcp-server`

Consulte a documentação do seu cliente para o formato exato da configuração.

---

## Ferramentas disponíveis

O servidor expõe propositalmente uma superfície pequena e somente leitura.

| Ferramenta | Finalidade |
|---|---|
| `search_cities` | Busca municípios brasileiros por nome parcial e resolve o código IBGE de 7 dígitos. Permite filtro opcional por estado. |
| `get_city` | Consulta os detalhes de um município usando seu código IBGE exato de 7 dígitos. |
| `search_gazettes` | Realiza busca textual em diários oficiais indexados, com filtros por município, período, paginação e ordenação. |

### Sintaxe de busca

A ferramenta `search_gazettes` utiliza a sintaxe **simple query string** do OpenSearch usada pela API do Querido Diário.

Exemplos:

| Consulta | Significado |
|---|---|
| `inteligência artificial` | Encontra qualquer um dos termos |
| `+inteligência +artificial` | Exige os dois termos |
| `-cancelado` | Exclui um termo |
| `"João da Silva"` | Busca uma expressão exata |

---

## Exemplo completo

O usuário pergunta:

```text
Encontre menções à ACME Ltda nos diários oficiais de Porto Alegre
entre janeiro e julho de 2026.
```

O cliente MCP pode executar:

```text
1. search_cities(city_name="Porto Alegre")
   → territory_id: "4314902"

2. search_gazettes(
       query='"ACME Ltda"',
       territory_ids=["4314902"],
       published_since="2026-01-01",
       published_until="2026-07-31",
   )
```

O agente recebe os resultados de forma estruturada e pode então resumir, comparar, classificar ou combinar essas informações com outras ferramentas.

Outros exemplos de prompts:

```text
Qual é o registro do município de Torres, RS, no Querido Diário?
```

```text
Pesquise referências a compras públicas de inteligência artificial
nos diários oficiais de Porto Alegre.
```

```text
Encontre publicações mencionando uma determinada empresa durante 2025.
```

```text
Consulte o município correspondente ao código IBGE 3550308.
```

---

## Demonstração

Ainda não há um vídeo, GIF ou captura de tela desta seção — de propósito, para não sugerir um comportamento que não foi validado de fato. Assim que houver uma demonstração real do servidor rodando dentro do Claude ou do Cursor, ela será adicionada aqui.

---

## Como funciona

```text
Cliente de IA
   │
   │ MCP / stdio
   ▼
querido-diario-mcp-server
   │
   │ requisições HTTPS tipadas
   ▼
API pública do Querido Diário
```

Estrutura do projeto:

```text
src/querido_diario_mcp_server/
    __init__.py   # versão do pacote + ponto de entrada
    config.py     # configuração por variáveis de ambiente
    errors.py     # hierarquia de erros da integração
    models.py     # modelos Pydantic tipados
    client.py     # cliente HTTP assíncrono da API
    server.py     # camada MCP e definição das ferramentas
```

A implementação separa propositalmente a integração HTTP da camada MCP:

- `client.py` não depende do MCP;
- `server.py` concentra validação, ferramentas e comportamento de protocolo;
- um único `httpx.AsyncClient` é criado no ciclo de vida do servidor e reutilizado;
- erros da API são convertidos em mensagens MCP curtas e compreensíveis para o agente.

---

## Local-first e somente leitura

O projeto foi desenhado para ser conservador em relação ao que um agente pode fazer.

- Executa somente requisições `GET`.
- Não possui operações de escrita.
- Não exige conta.
- Não exige chave de API.
- Não coleta telemetria.
- Não utiliza backend proprietário.
- Não utiliza proxy hospedado.
- O agente não pode fornecer uma URL arbitrária para o servidor buscar.
- URLs de diários retornadas pela API não são abertas automaticamente.
- Código IBGE, datas, paginação e ordenação são validados.
- Respostas de erro HTML da API não são repassadas integralmente ao agente.

Isso reduz a superfície de risco e evita transformar o servidor MCP em um mecanismo genérico de requisições externas ou SSRF.

### Fora de escopo nesta fase

A versão atual não implementa:

- busca arbitrária de URLs;
- download automático de PDF ou texto integral;
- OCR;
- operações de escrita;
- banco de dados local;
- crawling;
- jobs em segundo plano;
- sumarização por LLM embutida;
- interface web.

O objetivo é manter uma camada MCP pequena, previsível e segura sobre a API pública existente.

---

## Configuração

| Variável | Padrão | Finalidade |
|---|---|---|
| `QD_API_BASE_URL` | `https://api.queridodiario.org.br` | URL base da API do Querido Diário. Pode ser sobrescrita para ambientes locais ou de staging. |

Para uso normal, nenhuma configuração adicional é necessária.

---

## Instalação e distribuição

O pacote está publicado em:

- [PyPI](https://pypi.org/project/querido-diario-mcp-server/)
- [MCP Registry](https://registry.modelcontextprotocol.io/?q=io.github.lucaspmgomess%2Fquerido-diario-mcp-server)

Nome no PyPI:

```text
querido-diario-mcp-server
```

Nome no MCP Registry:

```text
io.github.lucaspmgomess/querido-diario-mcp-server
```

---

## Desenvolvimento

Clone o repositório apenas se quiser contribuir ou trabalhar na implementação:

```bash
git clone https://github.com/lucaspmgomess/querido-diario-mcp-server.git
cd querido-diario-mcp-server
uv sync
```

Execute os mesmos checks usados pelo CI:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest --cov
```

Para executar o servidor a partir do checkout local:

```bash
uv run querido-diario-mcp-server
```

Para inspecionar as ferramentas MCP interativamente:

```bash
uv run mcp dev src/querido_diario_mcp_server/server.py:mcp
```

---

## Estratégia de testes

### Testes do cliente HTTP

O `client.py` é testado com `httpx.MockTransport`, portanto a suíte automatizada não depende de internet nem de uma instância ativa do Querido Diário.

A cobertura inclui:

- requisições bem-sucedidas;
- busca de municípios;
- serialização de parâmetros;
- múltiplos `territory_ids`;
- períodos;
- paginação;
- ordenação;
- resultados vazios;
- erros 400/404/422;
- erros 5xx;
- respostas malformadas;
- timeouts;
- falhas de conexão.

### Testes de integração MCP

Os testes de integração executam o servidor MCP real por meio do cliente in-process do SDK.

Eles verificam:

- descoberta das ferramentas;
- schemas de entrada;
- saída estruturada e tipada;
- falhas de validação;
- falhas da integração upstream;
- conversão de erros em mensagens MCP limpas, sem traceback Python bruto.

### Smoke tests manuais

Há dois scripts de verificação manual contra produção:

```bash
uv run python scripts/smoke_test_api.py
uv run python scripts/smoke_test_mcp.py
```

Eles podem ser usados para validar a API real e o caminho completo MCP → cliente HTTP → API.

---

## Relação com o Querido Diário

Este é um **projeto comunitário e não oficial**.

O [Querido Diário](https://queridodiario.org.br) é mantido pela [Open Knowledge Brasil](https://ok.org.br/) e sua comunidade.

Este repositório:

- não é um projeto oficial da Open Knowledge Brasil, salvo eventual adoção expressa pela organização;
- não é afiliado, endossado ou mantido pela Open Knowledge Brasil;
- não copia nem distribui a implementação do Querido Diário;
- apenas consulta a API pública do projeto.

Repositórios upstream relevantes:

- [okfn-brasil/querido-diario](https://github.com/okfn-brasil/querido-diario) — coleta/scrapers
- [okfn-brasil/querido-diario-api](https://github.com/okfn-brasil/querido-diario-api) — API pública
- [okfn-brasil/querido-diario-deployment](https://github.com/okfn-brasil/querido-diario-deployment) — configuração de deployment

A API de produção utilizada por padrão é:

```text
https://api.queridodiario.org.br
```

Notas adicionais sobre o histórico dos endpoints estão em:

[`docs/upstream-api-history.md`](./docs/upstream-api-history.md)

---

## Por que código aberto?

Existem integrações hospedadas que expõem dados do Querido Diário para clientes MCP.

Este projeto segue uma abordagem diferente:

- a implementação do servidor é pública;
- o servidor roda na máquina do próprio usuário;
- não há middleware hospedado;
- não há conta;
- não há chave de API;
- não há telemetria;
- a API pública do Querido Diário é acessada diretamente.

Assim, todo o caminho entre o agente e a fonte de dados pode ser inspecionado.

---

## Feedback e uso real

Se você utilizar este projeto em pesquisa, civic tech, jornalismo de dados, análise de compras públicas ou em algum fluxo com agentes de IA, seu feedback é especialmente útil.

Exemplos de feedback que ajudam:

- uma busca difícil de expressar;
- um caso de município que não funcionou como esperado;
- dificuldade de configuração em algum cliente MCP;
- um filtro que faria diferença no uso real;
- comportamento inesperado da API upstream;
- um exemplo de como você está utilizando o servidor.

Abra uma [issue](https://github.com/lucaspmgomess/querido-diario-mcp-server/issues) descrevendo o caso de uso ou problema encontrado.

O objetivo é evoluir o projeto com base em uso real, mantendo o servidor pequeno, seguro e somente leitura.

---

## Contribuindo

Issues e pull requests são bem-vindos.

Antes de abrir uma PR, execute:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest --cov
```

Mantenha novas ferramentas e comportamentos alinhados ao objetivo do projeto: oferecer a agentes compatíveis com MCP acesso seguro e estruturado à API pública do Querido Diário.

---

## Licença

[MIT](./LICENSE)
