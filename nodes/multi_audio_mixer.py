import torch
import io
import os
import numpy as np
from pydub import AudioSegment

import logging
import folder_paths

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
            inputs["optional"][f"start_{i}"] = ("FLOAT", {"default": 0.0, "min": 0.0, "max": 10000.0, "step": 0.01})
            inputs["optional"][f"stop_{i}"] = ("FLOAT", {"default": 0.0, "min": 0.0, "max": 10000.0, "step": 0.01})
            inputs["optional"][f"indent_{i}"] = ("FLOAT", {"default": 0.0, "min": 0.0, "max": 10000.0, "step": 0.01})
            
        return inputs

    RETURN_TYPES = ("AUDIO", "FLOAT")
    RETURN_NAMES = ("combined_audio", "total_duration")
    FUNCTION = "mix_tracks"
    CATEGORY = "AudioMixer"

    @classmethod
    def IS_CHANGED(s, **kwargs):
        # Змушує ComfyUI ігнорувати кеш і перераховувати звук при кожному запуску
        return float("NaN")

    def comfy_to_pydub(self, waveform, sample_rate):
        try:
            y = waveform.cpu().numpy()
            if len(y.shape) == 3:
                y = y[0] 
            
            # Якщо моно [samples], перетворюємо в [samples, 1]
            if len(y.shape) == 1:
                y = y.reshape(-1, 1)
            else:
                y = y.T # [channels, samples] -> [samples, channels]
            
            # Нормалізація та конвертація в 16-bit PCM
            y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
            return AudioSegment(y.tobytes(), frame_rate=sample_rate, sample_width=2, channels=y.shape[1])
        except Exception as e:
            logger.error(f"Error in comfy_to_pydub: {e}")
            raise e

    def pydub_to_comfy(self, segment):
        try:
            samples = np.array(segment.get_array_of_samples()).astype(np.float32) / 32768.0
            channels = segment.channels
            
            if channels > 1:
                samples = samples.reshape((-1, channels)).T
            else:
                samples = samples.reshape((1, -1))
            
            # ВАЖЛИВО: [1, channels, samples] - формат, який розуміє Save Audio
            waveform = torch.from_numpy(samples).unsqueeze(0)
            return {"waveform": waveform, "sample_rate": segment.frame_rate}
        except Exception as e:
            logger.error(f"Error in pydub_to_comfy: {e}")
            raise e

    def mix_tracks(self, track_count, **kwargs):
        try:
            # Створюємо базу (0.1 сек тиші)
            master = AudioSegment.silent(duration=100, frame_rate=44100)
            max_length_ms = 0

            for i in range(1, track_count + 1):
                audio = kwargs.get(f"audio_{i}")
                if audio is None:
                    continue
                
                try:
                    overlay_track = self.comfy_to_pydub(audio['waveform'], audio['sample_rate'])
                    
                    vol = kwargs.get(f"volume_{i}", 0.0)
                    bal = kwargs.get(f"balance_{i}", 0.0)
                    start_sec = kwargs.get(f"start_{i}", 0.0)
                    stop_sec = kwargs.get(f"stop_{i}", 0.0)
                    indent_sec = kwargs.get(f"indent_{i}", 0.0)

                    # 1. Розумна обрізка (Crop)
                    start_ms = int(start_sec * 1000)
                    if stop_sec > start_sec:
                        stop_ms = int(stop_sec * 1000)
                        overlay_track = overlay_track[start_ms:stop_ms]
                    else:
                        # Якщо stop = 0 або менше start — беремо до кінця
                        overlay_track = overlay_track[start_ms:]

                    # 2. Ефекти
                    if vol != 0:
                        overlay_track = overlay_track.apply_gain(vol)
                    if bal != 0:
                        overlay_track = overlay_track.pan(bal)

                    # 3. Накладання (Overlay)
                    indent_ms = int(indent_sec * 1000)
                    master = master.overlay(overlay_track, position=indent_ms)
                    
                    # Рахуємо тривалість
                    current_end = indent_ms + len(overlay_track)
                    if current_end > max_length_ms:
                        max_length_ms = current_end
                        
                except Exception as track_err:
                    logger.error(f"Error processing track {i}: {track_err}")
                    continue

            # Обрізаємо майстер до фінальної довжини звуку
            master = master[:max_length_ms]
            
            # Конвертуємо в тензор для ComfyUI
            result_audio = self.pydub_to_comfy(master)
            
            logger.info(f"Mixing completed. Final duration: {max_length_ms/1000.0}s")
            return (result_audio, float(max_length_ms / 1000.0))

        except Exception as e:
            logger.error(f"Critical error in mix_tracks: {e}")
            empty_wf = torch.zeros((1, 1, 44100))
            return ({"waveform": empty_wf, "sample_rate": 44100}, 0.0)