import torch
import numpy as np
from pydub import AudioSegment
import io
import logging

# Налаштування логування для консолі ComfyUI
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultiAudioMixer")

class MultipleAudioUpload:
    @classmethod
    def INPUT_TYPES(s):
        inputs = {
            "required": {
                "track_count": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
            },
            "optional": {}
        }
        
        for i in range(1, 11):
            inputs["optional"][f"audio_{i}"] = ("AUDIO",)
            inputs["optional"][f"volume_{i}"] = ("FLOAT", {"default": 0.0, "min": -60.0, "max": 20.0, "step": 0.1})
            inputs["optional"][f"balance_{i}"] = ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01})
            inputs["optional"][f"start_{i}"] = ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.01})
            inputs["optional"][f"stop_{i}"] = ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.01})
            inputs["optional"][f"indent_{i}"] = ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.01})
            
        return inputs

    RETURN_TYPES = ("AUDIO", "FLOAT")
    RETURN_NAMES = ("combined_audio", "total_duration")
    FUNCTION = "mix_tracks"
    CATEGORY = "AudioMixer"

    def comfy_to_pydub(self, waveform, sample_rate):
        try:
            y = waveform.cpu().numpy()
            if len(y.shape) == 3:
                y = y[0] 
            
            y = y.T # Transpose to [samples, channels]
            y = (y * 32767).astype(np.int16)
            return AudioSegment(y.tobytes(), frame_rate=sample_rate, sample_width=2, channels=y.shape[1])
        except Exception as e:
            logger.error(f"Error converting Comfy audio to Pydub: {e}")
            raise e

    def pydub_to_comfy(self, segment):
        try:
            samples = np.array(segment.get_array_of_samples()).astype(np.float32) / 32768.0
            if segment.channels > 1:
                samples = samples.reshape((-1, segment.channels)).T
            
            waveform = torch.from_numpy(samples).unsqueeze(0)
            return {"waveform": waveform, "sample_rate": segment.frame_rate}
        except Exception as e:
            logger.error(f"Error converting Pydub back to Comfy: {e}")
            raise e

    def mix_tracks(self, track_count, **kwargs):
        try:
            # Створюємо базову тишу (100мс), 44.1kHz стерео за замовчуванням
            master = AudioSegment.silent(duration=100, frame_rate=44100)
            max_length_ms = 0

            for i in range(1, track_count + 1):
                audio = kwargs.get(f"audio_{i}")
                if audio is None:
                    continue
                
                logger.info(f"Processing track {i}...")
                
                try:
                    waveform = audio['waveform']
                    sample_rate = audio['sample_rate']
                    
                    overlay_track = self.comfy_to_pydub(waveform, sample_rate)

                    vol = kwargs.get(f"volume_{i}", 0.0)
                    bal = kwargs.get(f"balance_{i}", 0.0)
                    start = kwargs.get(f"start_{i}", 0.0)
                    stop = kwargs.get(f"stop_{i}", 0.0)
                    indent = kwargs.get(f"indent_{i}", 0.0)

                    # Crop
                    if stop > start and stop > 0:
                        overlay_track = overlay_track[int(start*1000):int(stop*1000)]
                    elif start > 0:
                        overlay_track = overlay_track[int(start*1000):]

                    # Gain & Pan
                    overlay_track = overlay_track.apply_gain(vol).pan(bal)

                    # Overlay
                    indent_ms = int(indent * 1000)
                    master = master.overlay(overlay_track, position=indent_ms)
                    
                    current_end = indent_ms + len(overlay_track)
                    if current_end > max_length_ms:
                        max_length_ms = current_end
                        
                except Exception as track_err:
                    logger.error(f"Failed to process track {i}: {track_err}")
                    continue # Пропускаємо битий трек, але йдемо далі

            # Фінальна перевірка тривалості
            if max_length_ms == 0:
                logger.warning("No audio tracks were processed. Returning silence.")
                max_length_ms = 1000 

            master = master[:max_length_ms]
            result_audio = self.pydub_to_comfy(master)
            
            logger.info(f"Mixing finished. Total duration: {max_length_ms/1000.0}s")
            return (result_audio, float(max_length_ms / 1000.0))

        except Exception as e:
            logger.error(f"Critical error in mix_tracks: {e}")
            # Повертаємо порожній тензор, щоб не "впав" весь ComfyUI
            empty_waveform = torch.zeros((1, 1, 44100))
            return ({"waveform": empty_waveform, "sample_rate": 44100}, 1.0)
