import os
import logging
from utils.download import download_gcp_folder

# Configurar logging para ver tudo
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_download():
    print("🚀 Iniciando download...")
    
    try:
        temp_path, temp_dir = download_gcp_folder(
            bucket_path='benchmarks-musicai-gt/all-5stems-gtr-separate-channels/Ariana_Grande_-_Greedy_(24_Stems)'
        )
        
        try:
            print(f"✅ Download concluído em: {temp_path}")
            print("\n🎵 Arquivos _mix.wav mantidos:")
            for root, dirs, files in os.walk(temp_path):
                for file in files:
                    if file.endswith('_mix.wav'):
                        print(f"  - {os.path.join(root, file)}")
                    
        finally:
            # Cleanup temporário
            temp_dir.cleanup()
            print("\n🧹 Diretório temporário limpo")
                
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        raise
    finally:
        print("\n🏁 Teste concluído!")

if __name__ == "__main__":
    test_download()