from django import forms

class YouTubeURLForm(forms.Form):
    video_url = forms.URLField(label='YouTube Video URL', required=True)