import os

from .nodes.multi_audio_mixer import MultipleAudioUpload

NODE_CLASS_MAPPINGS = {
    "MultipleAudioUpload": MultipleAudioUpload
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MultipleAudioUpload": "🔊 Multi-Track Audio Mixer"
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]