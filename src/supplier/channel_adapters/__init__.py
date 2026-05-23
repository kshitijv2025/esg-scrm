"""
Channel adapters for supplier messaging.

Provides concrete implementations of MessagingGateway for different channels.
"""

from src.supplier.channel_adapters.whatsapp_gateway import WhatsAppGateway

__all__ = ["WhatsAppGateway"]
