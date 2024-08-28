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
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_video_id(url):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

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

def get_transcript_from_api(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        logger.warning(f"Não foi possível obter transcrição via API para {video_id}: {e}")
        return None

def get_transcript_from_html(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        script = soup.find("script", string=re.compile("ytInitialPlayerResponse"))
        if not script:
            return None

        json_text = re.search(r"ytInitialPlayerResponse\s*=\s*({.*?});", script.string).group(1)
        data = json.loads(json_text)

        captions = data.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        if not captions:
            return None

        transcript_url = captions[0]['baseUrl']
        transcript_response = requests.get(transcript_url)
        transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')

        transcript_segments = transcript_soup.find_all('text')
        return ' '.join([segment.get_text() for segment in transcript_segments])
    except Exception as e:
        logger.warning(f"Não foi possível obter transcrição via HTML para {video_id}: {e}")
        return None

def get_youtube_transcript_and_title(video_url):
    logger.info(f"Tentando obter transcrição para: {video_url}")
    video_id = get_video_id(video_url)
    if not video_id:
        logger.error(f"ID do vídeo não encontrado para URL: {video_url}")
        return None, None

    title = get_video_title(video_id)
    
    transcript = get_transcript_from_api(video_id)
    if transcript:
        logger.info(f"Transcrição obtida via API para o vídeo: {title}")
        return transcript, title

    transcript = get_transcript_from_html(video_id)
    if transcript:
        logger.info(f"Transcrição obtida via HTML para o vídeo: {title}")
        return transcript, title

    logger.warning(f"Não foi possível obter transcrição para o vídeo: {title}")
    return None, title

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
                else:
                    all_transcripts.append((title, "Transcrição não disponível para este vídeo."))

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