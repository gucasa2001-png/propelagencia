"""
PROPEL CRM — CAMADA INDUSTRIAL DE OBSERVABILIDADE
Integracao de OpenTelemetry (CNCF), Sentry (Error e Performance Tracing)
e suporte unificado a OTLP (Datadog / New Relic).
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("propel_observability")
logging.basicConfig(level=logging.INFO)

# Configuracoes via variaveis de ambiente
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "propel-crm-operacoes")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")


def init_sentry():
    """Inicializa o Sentry para captura de excecoes e performance tracing."""
    if not SENTRY_DSN:
        logger.info("[Sentry] SENTRY_DSN nao configurado. Modo local/mock ativo.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlite import SqliteIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=ENVIRONMENT,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqliteIntegration(),
            ],
            traces_sample_rate=1.0 if ENVIRONMENT == "development" else 0.2,
            profiles_sample_rate=1.0 if ENVIRONMENT == "development" else 0.1,
            send_default_pii=False,
        )
        logger.info(f"[Sentry] Inicializado com sucesso para o ambiente: {ENVIRONMENT}")
        return True
    except ImportError:
        logger.warning("[Sentry] sentry-sdk nao instalado. Execute: pip install sentry-sdk")
        return False
    except Exception as e:
        logger.error(f"[Sentry] Falha ao inicializar: {e}")
        return False


def init_opentelemetry(app=None):
    """
    Inicializa o OpenTelemetry (OTel) para traces distribuidos agnosticos.
    Compativel com Datadog Agent, New Relic OTLP e Jaeger.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({
            "service.name": OTEL_SERVICE_NAME,
            "service.version": "2.0.0",
            "deployment.environment": ENVIRONMENT,
        })

        provider = TracerProvider(resource=resource)

        # Se houver endpoint OTLP configurado (Datadog / New Relic), envia para ele
        if OTEL_EXPORTER_OTLP_ENDPOINT:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                otlp_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info(f"[OpenTelemetry] Exportador OTLP conectado a: {OTEL_EXPORTER_OTLP_ENDPOINT} (Datadog/NewRelic Target)")
            except Exception as otlp_err:
                logger.warning(f"[OpenTelemetry] Falha ao configurar OTLP Exporter: {otlp_err}")
        else:
            logger.info("[OpenTelemetry] TracerProvider ativo com captura local.")

        trace.set_tracer_provider(provider)

        # Instrumenta FastAPI se a aplicacao for passada
        if app:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
                logger.info("[OpenTelemetry] FastAPI instrumentado com sucesso.")
            except ImportError:
                pass

        # Instrumenta SQLite
        try:
            from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
            SQLite3Instrumentor().instrument()
            logger.info("[OpenTelemetry] SQLite3 instrumentado com sucesso.")
        except ImportError:
            pass

        return True
    except ImportError:
        logger.info("[OpenTelemetry] Pacotes OTel opcionais nao instalados. Modo padrao de telemetria ativo.")
        return False
    except Exception as e:
        logger.error(f"[OpenTelemetry] Erro ao inicializar OpenTelemetry: {e}")
        return False


def setup_observability(app=None):
    """Orquestrador principal de observabilidade do sistema Propel CRM."""
    sentry_ok = init_sentry()
    otel_ok = init_opentelemetry(app)
    return {
        "sentry_active": sentry_ok,
        "opentelemetry_active": otel_ok,
        "service_name": OTEL_SERVICE_NAME,
        "environment": ENVIRONMENT
    }
