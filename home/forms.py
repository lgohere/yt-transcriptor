from django import forms

class YouTubeURLForm(forms.Form):
    video_url = forms.CharField(widget=forms.Textarea(attrs={'rows': 10, 'cols': 80}), label='YouTube Video URLs')
