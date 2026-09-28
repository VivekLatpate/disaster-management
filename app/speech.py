import assemblyai as aai
from .config import settings

def transcribe_audio(data: bytes) -> str:
    aai.settings.api_key = settings.assemblyai_api_key
    transcript = aai.Transcriber().transcribe(data)
    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(transcript.error or "AssemblyAI transcription failed")
    return (transcript.text or "").strip()
