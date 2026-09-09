# Backlog Oficial de Issues do Projeto

Este arquivo mapeia todas as **Issues** do sistema da agência de tráfego local, prontas para serem cadastradas no GitHub e associadas aos Pull Requests correspondentes.

---

### Issue #1: [FEAT] Portal do Cliente Mobile-First com Magic Link e Aprovação de Criativos
* **Tipo:** Feature
* **Status:** Concluído (Merge Pendente)
* **Descrição:** Donos de negócios locais não utilizam sistemas com login e senha convencionais. Criação de um portal mobile-first acessível por link com token seguro temporário (Magic Link), exibindo apenas as métricas essenciais (Investimento, Leads WhatsApp, CPA) e esteira de aprovação de anúncios estilo cartões interativos ([Aprovar] e [Pedir Ajuste]).
* **PR Vinculado:** `feat/issue-1-portal-cliente` $\rightarrow$ `Closes #1`

---

### Issue #2: [FEAT] Mesa de Tráfego Pipedrive Edition com Drag & Drop Nativo e Gamificação
* **Tipo:** Feature / Usabilidade
* **Status:** Concluído (Merge Pendente)
* **Descrição:** Transformar a visualização operacional da agência no padrão de ergonomia do Pipedrive: permitir arrastar cartões de anúncios entre colunas (Aguardando Cliente, Ajuste Solicitado e Aprovados) com salvamento assíncrono via AJAX sem recarregar a tela, contadores dinâmicos, busca instantânea e pontuação de XP automática.
* **PR Vinculado:** `feat/issue-2-mesa-trafego-pipedrive` $\rightarrow$ `Closes #2`

---

### Issue #3: [ENHANCEMENT] Suporte Nativo a Reprodução de Vídeos do Google Drive
* **Tipo:** Enhancement
* **Status:** Concluído (Merge Pendente)
* **Descrição:** Eliminar custos de armazenamento de mídia pesada no servidor próprio permitindo que a agência cole links de compartilhamento do Google Drive. O sistema deve converter automaticamente URLs para o formato `/preview` e carregar o player embutido sem quebrar a navegação no celular do cliente.
* **PR Vinculado:** `feat/issue-3-google-drive-player` $\rightarrow$ `Closes #3`

---

### Issue #4: [FEAT] Endpoint e Simulador de Webhook do Tintim para Vendas no WhatsApp
* **Tipo:** Feature / Integração
* **Status:** Concluído (Merge Pendente)
* **Descrição:** Criar a rota receptora `/api/webhook/tintim` para receber notificações em tempo real de vendas fechadas no WhatsApp e refletir automaticamente no card "Faturamento Rastreado" do cliente, além de bonificar a equipe com XP.
* **PR Vinculado:** `feat/issue-4-webhook-tintim` $\rightarrow$ `Closes #4`

---

### Issue #5: [ENHANCEMENT] Checklist Operacional do Gestor (SOP Negócios Locais) & Prompts de IA
* **Tipo:** Enhancement / Processos
* **Status:** Concluído (Merge Pendente)
* **Descrição:** Integrar o checklist operacional do documento *The AI Checklist* com rotinas diárias matinais (+20 XP) e semanais de escala (+50 XP), acompanhado de uma gaveta com os 4 prompts de ouro para análise de fadiga e modelagem de criativos.
* **PR Vinculado:** `feat/issue-5-sop-prompts-ia` $\rightarrow$ `Closes #5`

---

### Issue #6: [DEPLOY] Configuração de VPS na Nuvem (Hostinger/Hetzner) com Domínio SSL
* **Tipo:** Deploy / Infraestrutura
* **Status:** Planejado
* **Descrição:** Preparar a esteira de deploy em contêiner ou serviço systemd na VPS (Hostinger KVM / Hetzner) com proxy reverso (Nginx/Traefik) e certificado SSL gratuito (Let's Encrypt) para disponibilizar o sistema em `app.suaagencia.com.br`.
* **PR Vinculado:** `infra/issue-6-deploy-vps-ssl` $\rightarrow$ `Closes #6`
