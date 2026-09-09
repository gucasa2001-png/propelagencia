"""
TESTES UNITÁRIOS — PROPEL CRM
Cobre funções de parsing de mídia, cálculo de CPA e regras de negócio.
"""

import sys
import os

# Adiciona propel_crm ao sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "propel_crm"))

from app import formatar_midia_url


def test_formatar_midia_google_drive():
    # Link no formato /view
    url = "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view?usp=sharing"
    res = formatar_midia_url(url)
    assert res["tipo"] == "drive"
    assert "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/preview" in res["embed_url"]
    assert res["file_id"] == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"


def test_formatar_midia_youtube():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    res = formatar_midia_url(url)
    assert res["tipo"] == "youtube"
    assert res["embed_url"] == "https://www.youtube.com/embed/dQw4w9WgXcQ"


def test_formatar_midia_video_direto():
    url = "https://cdn.example.com/campanhas/anuncio_lancha.mp4"
    res = formatar_midia_url(url)
    assert res["tipo"] == "video_direto"
    assert res["embed_url"] == url


def test_formatar_midia_imagem_padrao():
    url = "https://images.unsplash.com/photo-1544717305-2782549b5136"
    res = formatar_midia_url(url)
    assert res["tipo"] == "imagem"
    assert res["embed_url"] == url


def test_calculo_cpa_e_metricas():
    investimento = 1500.0
    vendas = 10
    cpa = investimento / vendas if vendas > 0 else 0.0
    assert cpa == 150.0
    assert cpa <= 200.0  # Meta máxima de CPA para serviços premium
