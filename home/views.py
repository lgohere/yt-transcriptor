# .TXT

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
from urllib.parse import quote
from django.http import FileResponse
from django.conf import settings
from django.utils.text import slugify

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

                # Extrair a data de envio
        upload_date = None
        date_span = soup.find("span", class_="style-scope yt-formatted-string bold", string=re.compile("Transmitido ao vivo em|Estreou em|Enviado em"))
        if date_span:
            upload_date = date_span.text.strip()
        else:
            # Tentar encontrar a data em um formato alternativo
            script_data = soup.find("script", string=re.compile("dateText"))
            if script_data:
                date_match = re.search(r'"dateText":\s*{\s*"simpleText":\s*"([^"]+)"', script_data.string)
                if date_match:
                    upload_date = date_match.group(1)

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
        
        full_transcript = []
        for segment in transcript_segments:
            timestamp = segment.get('start')
            text = segment.get_text()
            formatted_timestamp = format_timestamp(float(timestamp))
            full_transcript.append(f"{formatted_timestamp} {text}")
        
        full_transcript = '\n'.join(full_transcript)
        
        return full_transcript, title, upload_date

    except Exception as e:
        logger.error(f"Erro ao extrair a transcrição: {e}")
        return None, None, None
    
def format_timestamp(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

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
    transcript, title, upload_date = get_youtube_transcript_and_title(url)
    if transcript:
        return title, transcript, upload_date
    else:
        logger.warning(f"Transcrição não encontrada para o vídeo: {url}")
        return None, None, None

def is_channel_url(url):
    return '/channel/' in url or '/@' in url or '/c/' in url or '/user/' in url

@csrf_exempt
@csrf_exempt
def transcription_view(request):
    if request.method == 'POST':
        urls = request.POST.getlist('video_url')
        if not urls:
            return render(request, 'index.html', {'form': YouTubeURLForm(), 'error': 'Nenhuma URL fornecida.'})

        all_video_urls = []
        for url in urls:
            if is_channel_url(url):
                channel_videos = get_video_urls_from_channel(url)
                all_video_urls.extend(channel_videos)
            else:
                all_video_urls.append(url)

        if not all_video_urls:
            return render(request, 'index.html', {'form': YouTubeURLForm(), 'error': 'Nenhum vídeo encontrado.'})

        transcripts = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(fetch_and_append_transcript, url): url for url in all_video_urls}
            for future in as_completed(future_to_url):
                title, transcript, upload_date = future.result()
                if title and transcript:
                    transcripts.append((title, transcript, upload_date))

        if transcripts:
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_transcripts')
            os.makedirs(temp_dir, exist_ok=True)

            if len(transcripts) == 1:
                # Se houver apenas uma transcrição, use o nome do vídeo
                title, transcript, upload_date = transcripts[0]
                safe_title = slugify(title)
                file_name = f"{safe_title}.txt"
                file_path = os.path.join(temp_dir, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Título do Vídeo: {title}\n")
                    if upload_date:
                        f.write(f"Data de Envio: {upload_date}\n")
                    f.write("\n")
                    f.write(transcript)
            else:
                # Se houver múltiplas transcrições, use 'all_transcriptions.txt'
                file_name = 'all_transcriptions.txt'
                file_path = os.path.join(temp_dir, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    for title, transcript, upload_date in transcripts:
                        f.write(f"Título do Vídeo: {title}\n")
                        if upload_date:
                            f.write(f"Data de Envio: {upload_date}\n")
                        f.write("\n")
                        f.write(transcript)
                        f.write("\n\n" + "="*50 + "\n\n")  # Separador entre transcrições

            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
        else:
            return render(request, 'index.html', {'form': YouTubeURLForm(), 'error': 'Nenhuma transcrição disponível para os vídeos fornecidos.'})

    else:
        form = YouTubeURLForm()
    
    return render(request, 'index.html', {'form': form})

## JSONL


# import os
# import requests
# from bs4 import BeautifulSoup
# import re
# import json
# import youtube_dl
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from django.shortcuts import render
# from django.http import HttpResponse, JsonResponse
# from .forms import YouTubeURLForm
# from django.views.decorators.csrf import csrf_exempt
# import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# def get_youtube_transcript_and_title(video_url):
#     try:
#         response = requests.get(video_url)
#         if response.status_code != 200:
#             logger.error(f"Falha ao acessar a página do vídeo. Status code: {response.status_code}")
#             return None

#         soup = BeautifulSoup(response.content, 'html.parser')
#         title_element = soup.find("meta", property="og:title")
#         title = title_element["content"] if title_element else "sem_titulo"

#         script = soup.find("script", string=re.compile("ytInitialPlayerResponse"))
#         if not script:
#             logger.error("Não foi possível encontrar o script de dados iniciais.")
#             return None

#         json_text = re.search(r"ytInitialPlayerResponse\s*=\s*({.*?});", script.string)
#         if not json_text:
#             logger.error("Não foi possível extrair os dados JSON.")
#             return None

#         data = json.loads(json_text.group(1))
#         captions = data.get('captions')
#         if not captions:
#             logger.error("Nenhuma transcrição disponível para este vídeo.")
#             return None

#         caption_tracks = captions['playerCaptionsTracklistRenderer']['captionTracks']
#         transcript_url = caption_tracks[0]['baseUrl']

#         transcript_response = requests.get(transcript_url)
#         transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')
#         transcript_segments = transcript_soup.find_all('text')
#         full_transcript = ' '.join([segment.get_text() for segment in transcript_segments])
        
#         return {"theme": title, "content": full_transcript}

#     except Exception as e:
#         logger.error(f"Erro ao extrair a transcrição: {e}")
#         return None

# def get_video_urls_from_channel(channel_url):
#     ydl_opts = {
#         'quiet': True,
#         'extract_flat': True,
#         'skip_download': True
#     }
    
#     with youtube_dl.YoutubeDL(ydl_opts) as ydl:
#         result = ydl.extract_info(channel_url, download=False)
#         if 'entries' in result:
#             video_urls = [entry['url'] for entry in result['entries'] if 'url' in entry]
#             video_urls = [f"https://www.youtube.com/watch?v={url.split('v=')[-1]}" if "youtube" not in url else url for url in video_urls]
#             return video_urls
#         else:
#             return []

# def fetch_transcript(url):
#     return get_youtube_transcript_and_title(url)

# def is_channel_url(url):
#     return '/channel/' in url or '/@' in url or '/c/' in url or '/user/' in url

# @csrf_exempt
# def transcription_view(request):
#     if request.method == 'POST':
#         urls = request.POST.getlist('video_url')
#         if not urls:
#             return JsonResponse({'error': 'Nenhuma URL fornecida.'}, status=400)

#         all_video_urls = []
#         for url in urls:
#             if is_channel_url(url):
#                 channel_videos = get_video_urls_from_channel(url)
#                 all_video_urls.extend(channel_videos)
#             else:
#                 all_video_urls.append(url)

#         if not all_video_urls:
#             return JsonResponse({'error': 'Nenhum vídeo encontrado.'}, status=404)

#         dataset = []
#         with ThreadPoolExecutor(max_workers=10) as executor:
#             future_to_url = {executor.submit(fetch_transcript, url): url for url in all_video_urls}
#             for future in as_completed(future_to_url):
#                 result = future.result()
#                 if result:
#                     dataset.append(result)

#         if dataset:
#             response = HttpResponse(content_type='application/json')
#             response['Content-Disposition'] = 'attachment; filename="youtube_transcriptions_dataset.jsonl"'
            
#             for item in dataset:
#                 json.dump(item, response, ensure_ascii=False)
#                 response.write('\n')
            
#             return response
#         else:
#             return JsonResponse({'error': 'Nenhuma transcrição disponível para os vídeos fornecidos.'}, status=404)

#     else:
#         form = YouTubeURLForm()
    
#     return render(request, 'index.html', {'form': form})