import os
import requests
from bs4 import BeautifulSoup
import re
from django.shortcuts import render
from django.http import HttpResponse
from .forms import YouTubeURLForm
from django.views.decorators.csrf import csrf_exempt
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable
from django.utils.text import slugify

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_video_id(url):
    # Extrair o ID do vídeo da URL
    video_id = None
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break
    return video_id

def get_video_title(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('meta', property='og:title')['content']
        return title
    except Exception as e:
        logger.error(f"Erro ao obter o título do vídeo: {e}")
        return "Título não disponível"

def get_youtube_transcript_and_title(video_url):
    logger.info(f"Tentando obter transcrição para: {video_url}")
    video_id = get_video_id(video_url)
    if not video_id:
        logger.error(f"ID do vídeo não encontrado para URL: {video_url}")
        return None, None

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = ' '.join([entry['text'] for entry in transcript])
        title = get_video_title(video_id)
        logger.info(f"Transcrição obtida com sucesso para o vídeo: {title}")
        return full_transcript, title
    except TranscriptsDisabled:
        logger.warning(f"Transcrições desativadas para o vídeo: {video_id}")
    except NoTranscriptAvailable:
        logger.warning(f"Nenhuma transcrição disponível para o vídeo: {video_id}")
    except Exception as e:
        logger.error(f"Erro ao extrair a transcrição: {e}", exc_info=True)
    
    return None, None

@csrf_exempt
def transcription_view(request):
    if request.method == 'POST':
        video_urls = request.POST.getlist('video_url')
        all_transcripts = []
        transcriptions_obtained = False

        for video_url in video_urls:
            video_url = video_url.strip()
            if video_url:
                transcript, title = get_youtube_transcript_and_title(video_url)
                if transcript:
                    all_transcripts.append((title, transcript))
                    transcriptions_obtained = True

        if transcriptions_obtained:
            if len(all_transcripts) == 1:
                title, transcript = all_transcripts[0]
                filename = f"{slugify(title)}.txt"
                content = f"{title}\n\n{transcript}"
            else:
                filename = 'Multiple_Transcriptions.txt'
                content = "\n\n".join([f"{title}\n\n{transcript}" for title, transcript in all_transcripts])

            response = HttpResponse(content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            form = YouTubeURLForm()
            error_message = 'Nenhuma transcrição disponível para os vídeos fornecidos.'
            return render(request, 'index.html', {'form': form, 'error': error_message})

    else:
        form = YouTubeURLForm()

    return render(request, 'index.html', {'form': form})

def test_view(request):
    return HttpResponse("Test view working")