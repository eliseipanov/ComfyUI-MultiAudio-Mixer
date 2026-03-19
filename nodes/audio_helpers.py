from pydub import AudioSegment

def apply_audio_settings(audio_segment, volume_db, balance, start_sec, stop_sec):
    # 1. Обрізка за Start/Stop (Duration)
    # Pydub працює в мілісекундах
    start_ms = int(start_sec * 1000)
    stop_ms = int(stop_sec * 1000) if stop_sec > 0 else len(audio_segment)
    
    track = audio_segment[start_ms:stop_ms]
    
    # 2. Гучність
    track = track + volume_db
    
    # 3. Баланс (Pan)
    # -1.0 (left) to 1.0 (right)
    track = track.pan(balance)
    
    return track

def mix_to_master(master_track, overlay_track, indent_sec):
    indent_ms = int(indent_sec * 1000)
    # Накладаємо трек на майстер з відступом
    return master_track.overlay(overlay_track, position=indent_ms)