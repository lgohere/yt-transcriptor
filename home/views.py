import os
import requests
from bs4 import BeautifulSoup
import re
import json
import string
import unicodedata
from django.shortcuts import render
from django.http import HttpResponse
from .forms import YouTubeURLForm
from html import unescape
from django.views.decorators.csrf import csrf_exempt
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_youtube_transcript_and_title(video_url):
    try:
        response = requests.get(video_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extrair o título
        title_element = soup.find("meta", property="og:title")
        title = title_element["content"] if title_element else "sem_titulo"

        # Encontrar o script que contém os dados da transcrição
        script = soup.find("script", string=re.compile("ytInitialPlayerResponse"))
        if not script:
            logger.warning("Não foi possível encontrar o script de dados iniciais.")
            return None, title

        # Extrair e analisar os dados JSON
        json_text = re.search(r"ytInitialPlayerResponse\s*=\s*({.*?});", script.string).group(1)
        data = json.loads(json_text)

        # Extrair a transcrição
        captions = data.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        if not captions:
            logger.warning("Nenhuma transcrição disponível para este vídeo.")
            return None, title

        # Pegar a primeira transcrição disponível (geralmente em inglês)
        transcript_url = captions[0]['baseUrl']
        transcript_response = requests.get(transcript_url)
        transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')

        # Extrair o texto da transcrição
        transcript_segments = transcript_soup.find_all('text')
        full_transcript = ' '.join([unescape(segment.get_text()) for segment in transcript_segments])

        logger.info(f"Transcrição obtida com sucesso para o vídeo: {title}")
        return full_transcript, title

    except Exception as e:
        logger.error(f"Erro ao extrair a transcrição: {e}", exc_info=True)
        return None, None 
    
def sanitize_filename(title):
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    sanitized_title = ''.join(c for c in title if c in valid_chars or unicodedata.category(c) in ['Ll', 'Lu', 'Lm', 'Lo', 'Lt', 'N'])
    sanitized_title = sanitized_title.replace(' ', '_')
    return sanitized_title

@csrf_exempt
def transcription_view(request):
    if request.method == 'POST':
        video_urls = request.POST.getlist('video_url')
        all_transcripts = ""
        valid_urls = []
        transcriptions_obtained = False  # Nova variável para rastrear se alguma transcrição foi obtida
        valid_url_patterns = [
            re.compile(r'^(https?://)?(www\.)?youtube\.com/'),
            re.compile(r'^(https?://)?(www\.)?youtu\.be/'),
            re.compile(r'^(https?://)?youtube\.com/'),
            re.compile(r'^(https?://)?youtu\.be/')
        ]
        
        for video_url in video_urls:
            video_url = video_url.strip()
            if video_url and any(pattern.match(video_url) for pattern in valid_url_patterns):
                valid_urls.append(video_url)
                transcript, title = get_youtube_transcript_and_title(video_url)
                if transcript:
                    all_transcripts += f"\n\n{title}\n\n"
                    all_transcripts += transcript
                    transcriptions_obtained = True 

        if valid_urls and transcriptions_obtained:
            filename = 'Transcriptions.txt'
            response = HttpResponse(all_transcripts, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        else:
            form = YouTubeURLForm()
            error_message = 'Nenhuma transcrição disponível para os vídeos fornecidos.' if valid_urls else 'Nenhuma URL válida encontrada.'
            return render(request, 'index.html', {'form': form, 'error': error_message})

    else:
        form = YouTubeURLForm()
    
    return render(request, 'index.html', {'form': form})
