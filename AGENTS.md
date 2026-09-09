# Diretrizes do Projeto: Propel Agentes

Este documento é a **fonte única de verdade (SSOT)** de regras e padrões do projeto. Todo e qualquer agente de inteligência artificial (de qualquer modelo ou plataforma) que atuar neste repositório **DEVE seguir rigorosamente as diretrizes abaixo**.

---

## 🏛️ PARTE 1 — Protocolo Estratégico: O Conselho

Sempre que o usuário pedir um conselho, propor uma ideia ou submeter uma decisão para avaliação neste projeto, ative o protocolo **O Conselho**.

### Protocolo de Ativação
- **Gatilho direto**: Comando `/conselheiro` ou qualquer solicitação do usuário expressando dúvida, pedido de conselho, proposta de ideia ou avaliação de decisão.
- **Estrutura de resposta**: Conduza o processo estritamente nas três etapas do Conselho:

#### ETAPA 1 — Resposta Individual
Cinco conselheiros independentes, cada um respondendo em até 200 palavras, com voz própria, sem filtro e sem balanceamento:
1. **O Contraditor**: Aponta tudo o que pode dar errado (pior cenário possível). Apenas riscos.
2. **O Pensador de Primeiros Princípios**: Questiona as premissas fundamentais e a raiz do problema.
3. **O Otimista Assimétrico**: Mostra o ganho potencial (upside) esquecido e o custo da inação.
4. **O Forasteiro**: Faz a pergunta ingênua e revela pontos cegos invisíveis aos especialistas.
5. **O Executor**: Define a ação prática inadiável para a manhã de segunda-feira.

#### ETAPA 2 — Revisão Cega
Apresente as cinco perspectivas de forma anônima e simule o ranqueamento de cada conselheiro (1 a 5), com justificativa concisa de duas frases por conselheiro.

#### ETAPA 3 — Síntese do Presidente
O Presidente do Conselho conclui com:
1. **Decisão recomendada** (Sim, Não ou Caminho alternativo).
2. **O argumento mais forte** que apareceu no Conselho.
3. **O maior risco** que continua em aberto.
4. **O próximo passo concreto para os próximos 7 dias** (com prazo e critério de validação).

---

## 🛠️ PARTE 2 — Protocolo de Engenharia, GitHub & Gestão de Deploys

Qualquer alteração no código deste projeto deve seguir rigorosamente o padrão industrial de versionamento e rastreabilidade:

### 1. Toda Tarefa Começa com uma Issue no GitHub
Nenhum agente deve implementar código sem antes mapear a demanda em uma **Issue no GitHub**, categorizada por tipo:
- `[Feature]` — Nova funcionalidade ou módulo.
- `[Bugfix]` — Correção de erro ou falha de funcionamento.
- `[Enhancement]` — Melhoria de usabilidade, design ou performance.
- `[Deploy / Infra]` — Alterações de ambiente, servidores ou CI/CD.

**Estrutura obrigatória da Issue:**
* Contexto e Objetivo.
* Escopo das mudanças planejadas.
* Critérios de Aceitação (Checklist de validação).

---

### 2. Padrão de Nomenclatura de Branches
Nenhum commit deve ser feito diretamente na branch principal (`main`). Cada Issue deve ser desenvolvida em uma branch dedicada:
- `feat/issue-{numero}-{descricao-curta}`
- `fix/issue-{numero}-{descricao-curta}`
- `refactor/issue-{numero}-{descricao-curta}`

*Exemplo:* `feat/issue-12-portal-cliente-magic-link`

---

### 3. Deploys e Merges Exclusivamente via Pull Request (PR)
Todo deploy para produção e merge para a branch `main` deve ser orquestrado por um **Pull Request**.

#### ⚠️ REGRA INEGOCIÁVEL: Menção Obrigatória da Issue no PR
A descrição do Pull Request **DEVE obrigatoriamente conter a palavra-chave de fechamento vinculando a Issue correspondente**:
* `Closes #<numero-da-issue>`
* `Fixes #<numero-da-issue>`
* `Resolves #<numero-da-issue>`

*Exemplo de descrição de PR:*
```markdown
## Descrição das Alterações
Implementado o módulo de reprodução de vídeos do Google Drive dentro do card do cliente.

## Vínculo com a Issue
Closes #14

## Checklist de Validação
- [x] Iframe do Drive carrega com link /preview
- [x] Testado em tela mobile e desktop
- [x] Sem erros de console
```

---

### 4. Commits Semânticos (Conventional Commits)
Todas as mensagens de commit devem seguir o padrão:
- `feat:` para novas funcionalidades
- `fix:` para correções de bugs
- `docs:` para atualizações de documentação
- `style:` para formatação e design sem alteração de lógica
- `refactor:` para refatorações de código
- `test:` para adição ou ajuste de testes
