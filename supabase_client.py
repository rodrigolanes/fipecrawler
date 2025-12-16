import os
import ssl
import certifi
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Variáveis de configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Cliente Supabase (singleton)
_supabase_client = None

# Usa certificados padrão do sistema
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()


def get_supabase_client() -> Client:
    """
    Retorna uma instância do cliente Supabase.
    Cria a conexão apenas uma vez (singleton pattern).
    
    Returns:
        Client: Cliente Supabase configurado
    """
    global _supabase_client
    
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "Credenciais do Supabase não encontradas. "
                "Verifique se o arquivo .env está configurado corretamente."
            )
        
        # Desabilita verificação SSL (necessário em ambientes corporativos)
        import warnings
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        
        # Desabilita verificação SSL globalmente
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("🔓 Conexão com Supabase (SSL verificação desabilitada)")
    
    return _supabase_client


# Testa a conexão quando o módulo é importado
if __name__ == "__main__":
    try:
        client = get_supabase_client()
        print("✅ Conexão com Supabase estabelecida com sucesso!")
        print(f"📍 URL: {SUPABASE_URL}")
    except Exception as e:
        print(f"❌ Erro ao conectar com Supabase: {e}")
