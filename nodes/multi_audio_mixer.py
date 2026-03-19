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
                "track_count": ("INT", {"default": 2, "min": 1, "max": 5, "step": 1}),
            },
            "optional": {}
        }

        for i in range(1, 6):
            # Текстове поле для назви треку (твоя ідея з лейблами)
            inputs["optional"][f"label_{i}"] = ("STRING", {"default": f"Track {i}"})
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
        return float("NaN")

    def comfy_to_pydub(self, waveform, sample_rate):
        try:
            y = waveform.cpu().numpy()
            if len(y.shape) == 3:
                y = y[0]

            if len(y.shape) == 1:
                y = y.reshape(-1, 1)
            else:
                y = y.T

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

            waveform = torch.from_numpy(samples).unsqueeze(0)
            return {"waveform": waveform, "sample_rate": segment.frame_rate}
        except Exception as e:
            logger.error(f"Error in pydub_to_comfy: {e}")
            raise e

    def mix_tracks(self, track_count, **kwargs):
        try:
            processed_tracks = []
            max_length_ms = 0
            target_sample_rate = 44100

            # 1. Збираємо дані про всі підключені треки
            for i in range(1, track_count + 1):
                audio = kwargs.get(f"audio_{i}")
                if audio is None:
                    continue

                track = self.comfy_to_pydub(audio['waveform'], audio['sample_rate'])
                target_sample_rate = audio['sample_rate']

                start_ms = int(kwargs.get(f"start_{i}", 0.0) * 1000)
                stop_ms = int(kwargs.get(f"stop_{i}", 0.0) * 1000)
                indent_ms = int(kwargs.get(f"indent_{i}", 0.0) * 1000)

                if stop_ms > start_ms:
                    track = track[start_ms:stop_ms]
                else:
                    track = track[start_ms:]

                vol = kwargs.get(f"volume_{i}", 0.0)
                bal = kwargs.get(f"balance_{i}", 0.0)
                if vol != 0: track = track.apply_gain(vol)
                if bal != 0: track = track.pan(bal)

                processed_tracks.append((track, indent_ms))
                max_length_ms = max(max_length_ms, indent_ms + len(track))

            if not processed_tracks:
                return ({"waveform": torch.zeros((1, 1, 44100)), "sample_rate": 44100}, 0.0)

            # 2. Створюємо майстер потрібної довжини
            master = AudioSegment.silent(duration=max_length_ms, frame_rate=target_sample_rate)

            # 3. Накладаємо треки
            for track, indent in processed_tracks:
                master = master.overlay(track, position=indent)

            result_audio = self.pydub_to_comfy(master)
            logger.info(f"Mixing completed. Final duration: {len(master)/1000.0}s")

            return (result_audio, float(len(master) / 1000.0))

        except Exception as e:
            logger.error(f"Critical error in mix_tracks: {e}")
            return ({"waveform": torch.zeros((1, 1, 44100)), "sample_rate": 44100}, 0.0)
