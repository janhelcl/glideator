"""Tracing and observability configuration for the AutoGen Chat Application.

This module handles OpenTelemetry setup for tracing AutoGen agent interactions,
tool calls, and general application telemetry.
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


def setup_tracing(
    service_name: str = "parra-glideator-chat",
    otlp_endpoint: Optional[str] = None,
    console_output: bool = False,
    disabled: bool = False
) -> bool:
    """Set up OpenTelemetry tracing for the application.
    
    Args:
        service_name: Name to identify this service in traces
        otlp_endpoint: OTLP endpoint URL (e.g., "http://localhost:4317")
        console_output: Whether to also output traces to console
        disabled: Whether to disable tracing entirely
        
    Returns:
        bool: True if tracing was set up successfully, False otherwise
    """
    if disabled:
        logger.info("Tracing is disabled")
        return True
    
    try:
        logger.info(f"Setting up tracing for service: {service_name}")
        
        # Create resource with service identification
        resource = Resource({"service.name": service_name})
        
        # Set up tracer provider
        tracer_provider = TracerProvider(resource=resource)
        
        # Add span processors
        if otlp_endpoint:
            logger.info(f"Setting up OTLP exporter to: {otlp_endpoint}")
            otel_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            span_processor = BatchSpanProcessor(otel_exporter)
            tracer_provider.add_span_processor(span_processor)
        
        if console_output:
            logger.info("Setting up console span exporter")
            console_exporter = ConsoleSpanExporter()
            console_processor = BatchSpanProcessor(console_exporter)
            tracer_provider.add_span_processor(console_processor)
        
        # Set the global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Instrument OpenAI calls
        logger.info("Instrumenting OpenAI calls")
        try:
            OpenAIInstrumentor().instrument()
        except Exception as e:
            # This might fail if already instrumented, which is fine
            logger.debug(f"OpenAI instrumentation note: {e}")
        
        logger.info("Tracing setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to set up tracing: {str(e)}")
        return False


def setup_tracing_from_env() -> bool:
    """Set up tracing based on environment variables.
    
    Environment variables:
        TRACING_ENABLED: Set to "true" to enable tracing (default: false)
        TRACING_OTLP_ENDPOINT: OTLP endpoint URL (default: http://localhost:4317)
        TRACING_CONSOLE_OUTPUT: Set to "true" to output traces to console (default: false)
        TRACING_SERVICE_NAME: Service name for traces (default: parra-glideator-chat)
        
    Returns:
        bool: True if tracing was set up successfully, False otherwise
    """
    # Check if tracing is enabled
    tracing_enabled = os.getenv("TRACING_ENABLED", "false").lower() == "true"
    if not tracing_enabled:
        logger.info("Tracing not enabled (set TRACING_ENABLED=true to enable)")
        return True
    
    # Get configuration from environment
    service_name = os.getenv("TRACING_SERVICE_NAME", "parra-glideator-chat")
    otlp_endpoint = os.getenv("TRACING_OTLP_ENDPOINT", "http://localhost:4317")
    console_output = os.getenv("TRACING_CONSOLE_OUTPUT", "false").lower() == "true"
    
    return setup_tracing(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        console_output=console_output,
        disabled=False
    )


def get_tracer(name: str = "parra-glideator-chat") -> trace.Tracer:
    """Get a tracer instance.
    
    Args:
        name: Name for the tracer
        
    Returns:
        OpenTelemetry tracer instance
    """
    return trace.get_tracer(name)
