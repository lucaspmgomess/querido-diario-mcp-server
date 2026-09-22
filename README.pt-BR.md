# Querido Diário MCP Server

<!-- mcp-name: io.github.lucaspmgomess/querido-diario-mcp-server -->

[![PyPI](https://img.shields.io/pypi/v/querido-diario-mcp-server.svg)](https://pypi.org/project/querido-diario-mcp-server/)
[![Python](https://img.shields.io/pypi/pyversions/querido-diario-mcp-server.svg)](https://pypi.org/project/querido-diario-mcp-server/)
[![CI](https://github.com/lucaspmgomess/querido-diario-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/lucaspmgomess/querido-diario-mcp-server/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-published-brightgreen)](https://registry.modelcontextprotocol.io/?q=io.github.lucaspmgomess%2Fquerido-diario-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Servidor local-first de [Model Context Protocol](https://modelcontextprotocol.io) que oferece a clientes de IA acesso estruturado e somente leitura a diários oficiais municipais brasileiros indexados pelo [Querido Diário](https://queridodiario.org.br).

**Sem chave de API · Executa localmente · Somente leitura · Sem telemetria · Código aberto**

> 🌎 [English documentation](./README.md)

O pacote está publicado no [PyPI](https://pypi.org/project/querido-diario-mcp-server/) e no [MCP Registry](https://registry.modelcontextprotocol.io/?q=io.github.lucaspmgomess%2Fquerido-diario-mcp-server).

## O que ele faz

O Querido Diário disponibiliza diários oficiais municipais por meio de uma plataforma de dados abertos e uma API pública. Este servidor expõe uma interface MCP pequena e tipada sobre essa API para que um cliente compatível possa:

- localizar municípios brasileiros e seus códigos IBGE;
- pesquisar diários oficiais por texto, município e período;
- receber resultados estruturados que podem ser analisados ou combinados com outras ferramentas.

O servidor roda como subprocesso local via `stdio` e realiza apenas requisições HTTPS de leitura para a API pública do Querido Diário.

## Início rápido

Requer Python 3.12+ e [uv](https://docs.astral.sh/uv/).

Não é necessário clonar o repositório:

```bash
uvx querido-diario-mcp-server
```

O comando inicia o servidor MCP via `stdio`. Ele foi projetado para ser iniciado por um cliente MCP, não para uso interativo no terminal.

## Configuração dos clientes

Todos os clientes utilizam o mesmo comando:

```text
uvx querido-diario-mcp-server
```

### Claude Desktop / Claude Code

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

Use essa configuração no `claude_desktop_config.json` do Claude Desktop ou em um `.mcp.json` do projeto no Claude Code.

### Cursor

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

Adicione ao `.cursor/mcp.json` ou à configuração global de MCP do Cursor.

### Codex CLI

```toml
[mcp_servers.querido-diario]
command = "uvx"
args = ["querido-diario-mcp-server"]
```

Outros clientes MCP que suportem servidores locais via `stdio` podem executar o mesmo comando.

## Ferramentas

O servidor expõe propositalmente uma superfície pequena e somente leitura.

| Ferramenta | Finalidade |
| --- | --- |
| `search_cities` | Busca municípios brasileiros por nome e resolve o código IBGE de 7 dígitos. Aceita filtro opcional por estado. |
| `get_city` | Consulta um município pelo código IBGE exato de 7 dígitos. |
| `search_gazettes` | Pesquisa textual em diários indexados com filtros por município, período, paginação e ordenação. |

A ferramenta `search_gazettes` utiliza a sintaxe simple-query-string suportada pela API upstream, incluindo `+obrigatório`, `-excluído` e `"expressão exata"`.

## Exemplo

O usuário pode perguntar:

```text
Encontre menções à ACME Ltda nos diários oficiais de Porto Alegre
entre janeiro e julho de 2026.
```

O cliente MCP pode executar:

```text
1. search_cities(city_name="Porto Alegre")
   -> territory_id: "4314902"

2. search_gazettes(
       query='"ACME Ltda"',
       territory_ids=["4314902"],
       published_since="2026-01-01",
       published_until="2026-07-31",
   )
```

O resultado volta como saída estruturada para o cliente resumir, filtrar ou combinar com outras ferramentas.

## Arquitetura

```text
Cliente MCP
   |
   | stdio / MCP
   v
server.py
   |
   | argumentos validados
   v
client.py
   |
   | requisições HTTPS tipadas e somente leitura
   v
API pública do Querido Diário
```

A implementação mantém a integração HTTP separada da camada de protocolo:

```text
src/querido_diario_mcp_server/
    __init__.py   versão do pacote e entry point
    config.py     configuração por ambiente
    errors.py     hierarquia de erros da integração
    models.py     modelos Pydantic tipados
    client.py     cliente HTTP assíncrono sem dependência de MCP
    server.py     ciclo de vida, validação e ferramentas MCP
```

Um único `httpx.AsyncClient` é criado no ciclo de vida do servidor e reutilizado nas chamadas. O cliente HTTP pode ser testado independentemente do MCP, enquanto os testes de integração exercitam o servidor MCP real em processo.

## Princípios de projeto

- **Somente leitura por design.** A integração utiliza um conjunto pequeno de endpoints GET.
- **Local-first.** Não há middleware hospedado, backend proprietário ou exigência de conta.
- **Limites tipados.** Respostas da API e saídas MCP utilizam modelos Pydantic explícitos.
- **Superfície pequena.** O servidor expõe apenas operações de descoberta de municípios e pesquisa de diários.
- **Falhas explícitas.** Erros upstream são convertidos em erros MCP curtos em vez de tracebacks ou páginas HTML.
- **Sem busca arbitrária de URLs.** O servidor não pode ser transformado em um mecanismo genérico de HTTP ou SSRF.
- **Sem telemetria.** Nenhum dado de uso é coletado.

## Segurança

O servidor não segue automaticamente URLs de diários retornadas pela API upstream e não aceita URLs arbitrárias fornecidas pelo chamador. Códigos IBGE, datas, paginação e opções de ordenação são validados antes do uso.

Para reporte de vulnerabilidades e escopo suportado, consulte [SECURITY.md](./SECURITY.md).

## Configuração

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `QD_API_BASE_URL` | `https://api.queridodiario.org.br` | URL base da API do Querido Diário. Pode ser alterada para ambientes locais ou de staging. |

No uso normal, nenhuma variável precisa ser configurada.

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

Execute o servidor a partir do checkout:

```bash
uv run querido-diario-mcp-server
```

Inspecione as ferramentas MCP interativamente:

```bash
uv run mcp dev src/querido_diario_mcp_server/server.py:mcp
```

### Estratégia de testes

Os testes unitários simulam a camada HTTP com `httpx.MockTransport`, então a suíte automatizada não depende da API pública.

A cobertura inclui:

- buscas bem-sucedidas de municípios e diários;
- serialização de consultas e múltiplos códigos de território;
- períodos, paginação e ordenação;
- resultados vazios;
- falhas upstream 4xx e 5xx;
- respostas malformadas;
- falhas de conexão e timeout;
- descoberta das ferramentas MCP, schemas e saídas estruturadas;
- erros de validação e de integração na fronteira MCP.

Scripts manuais de smoke test estão disponíveis para validar a API real e o caminho completo MCP até a API:

```bash
uv run python scripts/smoke_test_api.py
uv run python scripts/smoke_test_mcp.py
```

## Status do projeto

O projeto está atualmente em beta. A superfície MCP é propositalmente pequena e as mudanças são mantidas conservadoras.

Estão fora do escopo atual:

- busca arbitrária de URLs;
- download automático de PDFs ou texto integral;
- OCR;
- operações de escrita;
- crawling e jobs em segundo plano;
- sumarização por LLM embutida;
- interface web.

## Relação com o Querido Diário

Este é um projeto comunitário e não oficial.

O [Querido Diário](https://queridodiario.org.br) é mantido pela [Open Knowledge Brasil](https://ok.org.br/) e sua comunidade. Este repositório não é um projeto oficial da organização, não é endossado ou mantido por ela e apenas consome sua API pública.

Repositórios upstream relevantes:

- [okfn-brasil/querido-diario](https://github.com/okfn-brasil/querido-diario)
- [okfn-brasil/querido-diario-api](https://github.com/okfn-brasil/querido-diario-api)
- [okfn-brasil/querido-diario-deployment](https://github.com/okfn-brasil/querido-diario-deployment)

Notas adicionais sobre o histórico dos endpoints estão em [docs/upstream-api-history.md](./docs/upstream-api-history.md).

## Contribuindo

Issues e pull requests são bem-vindos. Consulte [CONTRIBUTING.md](./CONTRIBUTING.md) para o fluxo de desenvolvimento, escopo do projeto e checklist de revisão.

## Licença

[MIT](./LICENSE)
