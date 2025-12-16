"""
Patch para desabilitar verificação SSL no httpx
Necessário em ambientes corporativos com certificados auto-assinados
"""
import ssl
import httpx

# Salva o método original
_original_init = httpx.Client.__init__

def patched_init(self, *args, **kwargs):
    # Remove verify ou define como False
    kwargs['verify'] = False
    # Chama o construtor original
    _original_init(self, *args, **kwargs)

# Aplica o patch
httpx.Client.__init__ = patched_init
httpx.AsyncClient.__init__ = patched_init

print("🔓 Patch aplicado: verificação SSL desabilitada no httpx")
