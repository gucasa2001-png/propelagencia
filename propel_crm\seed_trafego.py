"""
Seed de Dados de Demonstração para a Suíte de Tráfego Pago & Portal do Cliente
"""

from database import get_db, init_db
from datetime import datetime

def seed_trafego():
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()

        # Limpa dados antigos da suíte de tráfego para teste limpo
        cursor.execute("DELETE FROM criativos_aprovacao")
        cursor.execute("DELETE FROM metricas_trafego")
        cursor.execute("DELETE FROM atividades_agencia")
        cursor.execute("DELETE FROM clientes_trafego")
        cursor.execute("DELETE FROM gamificacao_equipe")

        # 1. Clientes de Demonstração
        cursor.execute("""
        INSERT INTO clientes_trafego (id, nome_empresa, segmento, responsavel_nome, whatsapp, magic_token, verba_mensal, meta_cpa, status, data_inicio)
        VALUES 
        (1, 'Clínica Dra. Camila — Odontologia & Estética', 'Saúde & Odontologia', 'Dra. Camila Prado', '11987654321', 'odonto-camila', 2500.0, 25.0, 'ativo', '2026-08-01'),
        (2, 'Bella Vista — Pizzaria & Forno a Lenha', 'Gastronomia Local', 'Sr. Rogério', '11976543210', 'bella-vista', 1200.0, 8.0, 'ativo', '2026-08-15')
        """)

        # 2. Métricas Consolidadas (com dados do Tintim e Meta Ads)
        cursor.execute("""
        INSERT INTO metricas_trafego (cliente_id, mes_referencia, investimento_total, conversas_whatsapp, vendas_tintim, faturamento_rastreado, ultima_atualizacao)
        VALUES
        (1, 'Setembro/2026', 1845.50, 74, 16, 32400.00, 'Hoje, às 08:30 (Sincronizado via Tintim & Meta)'),
        (2, 'Setembro/2026', 820.00, 118, 76, 7850.00, 'Hoje, às 08:15 (Sincronizado via Tintim & Meta)')
        """)

        # 3. Criativos para Aprovação
        cursor.execute("""
        INSERT INTO criativos_aprovacao (cliente_id, titulo, midia_url, formato, texto_copy, publico_alvo, status, feedback_cliente, data_envio)
        VALUES
        (1, 'Vídeo 01 — Protocolo de Implante sem Dor', 'https://images.unsplash.com/photo-1629909613654-28e377c37b09?w=800&auto=format&fit=crop', 'video', 
         'Descubra como recuperar o prazer de sorrir e mastigar com o tratamento de implante rápido e humanizado da Dra. Camila Prado.\n\n👉 Toque no botão e fale direto com nossa recepção no WhatsApp para agendar sua avaliação nesta semana!', 
         'Mulheres e Homens 40+ no raio de 7km', 'pendente', '', '08/09/2026 às 16:30'),

        (1, 'Carrossel 02 — Antes e Depois: Lentes de Resina', 'https://images.unsplash.com/photo-1606811841689-23dfddce3e95?w=800&auto=format&fit=crop', 'imagem', 
         'Um sorriso alinhado e natural em apenas duas sessões. Veja a transformação real de quem confiou na Dra. Camila.\n\nRestam apenas 4 horários disponíveis para este mês.', 
         'Público Feminino 25-50 anos - Interesse em Estética', 'pendente', '', '08/09/2026 às 17:15'),

        (1, 'Banner 03 — Clareamento Dental a Laser', 'https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?w=800&auto=format&fit=crop', 'imagem', 
         'Seu sorriso até 4 tons mais branco com a tecnologia de laser frio mais moderna de São Paulo.', 
         'Público Geral 20-45 anos', 'aprovado', 'Adorei a foto! Aprovado para rodar.', '05/09/2026 às 11:00'),

        (2, 'Combo Família 2 Pizzas Grandes + Refri', 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&auto=format&fit=crop', 'imagem', 
         'Quarta e Quinta da Pizza! Peça 2 pizzas tradicionais e ganhe 1 refrigerante 2L com entrega grátis.\n\nPeça direto pelo WhatsApp!', 
         'Raio de 5km da Pizzaria', 'pendente', '', '08/09/2026 às 18:00')
        """)

        # 4. Atividades da Agência (Para gerar certeza no cliente)
        cursor.execute("""
        INSERT INTO atividades_agencia (cliente_id, acao, categoria, data_hora)
        VALUES
        (1, 'Otimização de Lances: Reduzido CPA de Implantes de R$ 32 para R$ 24,90', 'otimizacao', 'Ontem às 18:45'),
        (1, '2 novos criativos em vídeo enviados para aprovação nesta tela', 'criativo', 'Ontem às 17:15'),
        (1, 'Exclusão de bairros fora do raio de entrega/atendimento no Google Ads', 'otimizacao', '06/09/2026 às 14:10'),
        (1, 'Sincronização de 16 conversões confirmadas pelo WhatsApp (Tintim)', 'relatorio', '05/09/2026 às 19:00'),
        (2, 'Aumento de 20% no orçamento para o final de semana', 'campanha', '06/09/2026 às 11:30')
        """)

        # 5. Gamificação da Equipe
        cursor.execute("""
        INSERT INTO gamificacao_equipe (gestor_nome, evento, pontos, categoria, data_hora)
        VALUES
        ('Samuel Tráfego', 'Criativo subido antes do prazo (Dra. Camila)', 50, 'agilidade', '08/09 às 17:20'),
        ('Samuel Tráfego', 'Meta de CPA batida (R$ 24,90 vs meta de R$ 25)', 100, 'performance', '08/09 às 18:50'),
        ('Gabriel Copywriter', 'Texto do anúncio aprovado de primeira', 40, 'qualidade', '05/09 às 11:05'),
        ('Samuel Tráfego', 'Checklist de Onboarding concluído em 24h', 80, 'onboarding', '02/09 às 16:00')
        """)

        conn.commit()
    print("Sucesso! Banco populado com clientes de tráfego, criativos e gamificação.")

if __name__ == "__main__":
    seed_trafego()
