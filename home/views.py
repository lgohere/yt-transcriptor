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
from requests.exceptions import RequestException

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

def get_video_info(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = "Título não disponível"
        title_meta = soup.find('meta', property='og:title')
        if title_meta and 'content' in title_meta.attrs:
            title = title_meta['content']
        
        script = soup.find("script", string=re.compile("ytInitialPlayerResponse"))
        if script:
            json_text = re.search(r"ytInitialPlayerResponse\s*=\s*({.*?});", script.string)
            if json_text:
                data = json.loads(json_text.group(1))
                if 'videoDetails' in data and 'title' in data['videoDetails']:
                    title = data['videoDetails']['title']
        
        return title, soup
    except RequestException as e:
        logger.error(f"Erro ao obter informações do vídeo: {e}")
        return "Título não disponível", None
    except Exception as e:
        logger.error(f"Erro inesperado ao obter informações do vídeo: {e}")
        return "Título não disponível", None

def get_transcript_from_api(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        logger.warning(f"Não foi possível obter transcrição via API para {video_id}: {e}")
        return None

def get_transcript_from_html(soup):
    if not soup:
        return None
    try:
        script = soup.find("script", string=re.compile("ytInitialPlayerResponse"))
        if not script:
            return None

        json_text = re.search(r"ytInitialPlayerResponse\s*=\s*({.*?});", script.string)
        if not json_text:
            return None

        data = json.loads(json_text.group(1))
        captions = data.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        if not captions:
            return None

        transcript_url = captions[0]['baseUrl']
        transcript_response = requests.get(transcript_url)
        transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')

        transcript_segments = transcript_soup.find_all('text')
        return ' '.join([segment.get_text() for segment in transcript_segments])
    except Exception as e:
        logger.warning(f"Não foi possível obter transcrição via HTML: {e}")
        return None

def get_youtube_transcript_and_title(video_url):
    logger.info(f"Tentando obter transcrição para: {video_url}")
    video_id = get_video_id(video_url)
    if not video_id:
        logger.error(f"ID do vídeo não encontrado para URL: {video_url}")
        return None, "URL inválida"

    title, soup = get_video_info(video_id)
    
    transcript = get_transcript_from_api(video_id)
    if transcript:
        logger.info(f"Transcrição obtida via API para o vídeo: {title}")
        return transcript, title

    transcript = get_transcript_from_html(soup)
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

        if all_transcripts:
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