import os
import requests
from bs4 import BeautifulSoup
import re
import json
import youtube_dl
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.shortcuts import render
from django.http import HttpResponse
from .forms import YouTubeURLForm
from django.views.decorators.csrf import csrf_exempt
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_youtube_transcript_and_title(video_url):
    try:
        response = requests.get(video_url)
        if response.status_code != 200:
            logger.error(f"Falha ao acessar a página do vídeo. Status code: {response.status_code}")
            return None, None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        title_element = soup.find("meta", property="og:title")
        title = title_element["content"] if title_element else "sem_titulo"

        script = soup.find("script", string=re.compile("ytInitialPlayerResponse"))
        if not script:
            logger.error("Não foi possível encontrar o script de dados iniciais.")
            return None, title

        json_text = re.search(r"ytInitialPlayerResponse\s*=\s*({.*?});", script.string)
        if not json_text:
            logger.error("Não foi possível extrair os dados JSON.")
            return None, title

        data = json.loads(json_text.group(1))
        captions = data.get('captions')
        if not captions:
            logger.error("Nenhuma transcrição disponível para este vídeo.")
            return None, title

        caption_tracks = captions['playerCaptionsTracklistRenderer']['captionTracks']
        transcript_url = caption_tracks[0]['baseUrl']

        transcript_response = requests.get(transcript_url)
        transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')
        transcript_segments = transcript_soup.find_all('text')
        full_transcript = ' '.join([segment.get_text() for segment in transcript_segments])
        
        return full_transcript, title

    except Exception as e:
        logger.error(f"Erro ao extrair a transcrição: {e}")
        return None, None

def get_video_urls_from_channel(channel_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True
    }
    
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(channel_url, download=False)
        if 'entries' in result:
            video_urls = [entry['url'] for entry in result['entries'] if 'url' in entry]
            video_urls = [f"https://www.youtube.com/watch?v={url.split('v=')[-1]}" if "youtube" not in url else url for url in video_urls]
            return video_urls
        else:
            return []

def fetch_and_append_transcript(url):
    transcript, title = get_youtube_transcript_and_title(url)
    if transcript:
        return f"\n\nTítulo do Vídeo: {title}\n\n{transcript}"
    else:
        logger.warning(f"Transcrição não encontrada para o vídeo: {url}")
        return ""

@csrf_exempt
def transcription_view(request):
    if request.method == 'POST':
        channel_url = request.POST.get('video_url')
        if not channel_url:
            return render(request, 'index.html', {'form': YouTubeURLForm(), 'error': 'URL do canal não fornecida.'})

        video_urls = get_video_urls_from_channel(channel_url)
        if not video_urls:
            return render(request, 'index.html', {'form': YouTubeURLForm(), 'error': 'Nenhum vídeo encontrado no canal.'})

        all_transcripts = ""
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(fetch_and_append_transcript, url): url for url in video_urls}
            for future in as_completed(future_to_url):
                all_transcripts += future.result()

        if all_transcripts:
            response = HttpResponse(all_transcripts, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="channel_transcriptions.txt"'
            return response
        else:
            return render(request, 'index.html', {'form': YouTubeURLForm(), 'error': 'Nenhuma transcrição disponível para os vídeos do canal.'})

    else:
        form = YouTubeURLForm()
    
    return render(request, 'index.html', {'form': form})