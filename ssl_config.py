import os

# IMPORTANTE: Este arquivo deve ser importado ANTES de qualquer outro
# Configura variáveis de ambiente para SSL

# Desabilita verificação SSL para httpx e requests
os.environ['HTTPX_VERIFY_SSL'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

# Certificado Petrobras (se existir)
cert_path = os.path.join(os.path.dirname(__file__), 'petrobras_root_cadeia.pem')
if os.path.exists(cert_path):
    print(f"✅ Certificado Petrobras encontrado: {cert_path}")
else:
    print("⚠️ Certificado Petrobras não encontrado")

print("🔓 Verificação SSL desabilitada (apenas desenvolvimento)")
