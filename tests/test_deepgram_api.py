#!/usr/bin/env python3
"""
Quick script to test Deepgram API key validity.
"""

import requests
import os
from dotenv import load_dotenv

def test_deepgram_api():
    """Test if Deepgram API key is valid."""
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('DEEPGRAM_API_KEY')
    
    if not api_key:
        print("❌ No se encontró DEEPGRAM_API_KEY en .env")
        return False
    
    if api_key == "your_deepgram_api_key_here":
        print("❌ API key tiene valor por defecto, necesitas configurar una real")
        return False
    
    print(f"🔍 Probando API key: {api_key[:8]}...")
    
    # Test API key with projects endpoint
    headers = {'Authorization': f'Token {api_key}'}
    
    try:
        response = requests.get(
            'https://api.deepgram.com/v1/projects', 
            headers=headers,
            timeout=10
        )
        
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            projects = data.get('projects', [])
            print(f"✅ API key VÁLIDA")
            print(f"📊 Proyectos disponibles: {len(projects)}")
            
            if projects:
                project = projects[0]
                print(f"📁 Proyecto principal: {project.get('name', 'Sin nombre')}")
                print(f"🆔 ID: {project.get('project_id', 'N/A')}")
            
            return True
            
        elif response.status_code == 401:
            print("❌ API key INVÁLIDA (401 Unauthorized)")
            print("💡 Verifica tu API key en: https://console.deepgram.com/")
            return False
            
        elif response.status_code == 403:
            print("❌ API key sin permisos (403 Forbidden)")
            return False
            
        else:
            print(f"⚠️  Respuesta inesperada: {response.status_code}")
            print(f"📄 Respuesta: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_deepgram_usage():
    """Test Deepgram usage/billing info."""
    
    load_dotenv()
    api_key = os.getenv('DEEPGRAM_API_KEY')
    
    if not api_key:
        return
    
    headers = {'Authorization': f'Token {api_key}'}
    
    try:
        # Get first project
        projects_response = requests.get(
            'https://api.deepgram.com/v1/projects', 
            headers=headers,
            timeout=10
        )
        
        if projects_response.status_code == 200:
            projects = projects_response.json().get('projects', [])
            if projects:
                project_id = projects[0]['project_id']
                
                # Get usage info
                usage_response = requests.get(
                    f'https://api.deepgram.com/v1/projects/{project_id}/usage',
                    headers=headers,
                    timeout=10
                )
                
                if usage_response.status_code == 200:
                    usage = usage_response.json()
                    print(f"\n💰 Información de uso:")
                    print(f"📊 Requests este mes: {usage.get('requests', 'N/A')}")
                    print(f"⏱️  Horas procesadas: {usage.get('hours', 'N/A')}")
                
    except Exception as e:
        print(f"⚠️  No se pudo obtener info de uso: {e}")

if __name__ == "__main__":
    print("🚀 Probando API key de Deepgram...")
    print("=" * 50)
    
    if test_deepgram_api():
        test_deepgram_usage()
        print("\n🎉 ¡API key funcionando correctamente!")
    else:
        print("\n❌ Necesitas configurar una API key válida")
        print("📝 Pasos:")
        print("1. Ve a https://console.deepgram.com/")
        print("2. Crea una cuenta o inicia sesión")
        print("3. Genera una nueva API key")
        print("4. Actualiza el archivo .env con tu API key")