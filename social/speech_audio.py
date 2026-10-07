"""Bounded PCM WAV validation, including unknown-length streaming headers.

A streaming RIFF/data size of 0xffffffff is a sentinel, not sample duration.
Only that sentinel is repaired; ordinary truncated/misaligned WAVs are rejected.
"""
import io
import struct
import wave

MAX_BYTES = 1024 * 1024
MAX_SECONDS = 20
UNKNOWN = 0xffffffff


class AudioValidationError(ValueError):
    def __init__(self, code, **metrics):
        super().__init__(code)
        self.code = code
        self.metrics = metrics


def decode(data):
    size = len(data)
    if size > MAX_BYTES:
        raise AudioValidationError('audio_too_large', bytes=size)
    if size < 12 or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        raise AudioValidationError('not_pcm_wav', bytes=size)
    riff_size = struct.unpack_from('<I', data, 4)[0]
    if riff_size != UNKNOWN and riff_size + 8 != size:
        raise AudioValidationError('riff_size_mismatch', bytes=size, declared_bytes=riff_size+8)
    fixed = bytearray(data)
    struct.pack_into('<I', fixed, 4, size-8)
    offset = 12
    audio_size = None
    streaming = riff_size == UNKNOWN
    fmt_seen = False
    while offset < size:
        if offset + 8 > size:
            raise AudioValidationError('truncated_chunk_header', bytes=size)
        tag = data[offset:offset+4]
        declared = struct.unpack_from('<I', data, offset+4)[0]
        start = offset+8
        length = declared
        if declared == UNKNOWN:
            if tag != b'data':
                raise AudioValidationError('unknown_non_audio_chunk_size')
            length = size-start  # Unknown-size data must be the final chunk.
            struct.pack_into('<I', fixed, offset+4, length)
            streaming = True
        if start + length > size:
            raise AudioValidationError('truncated_chunk', bytes=size, declared_bytes=length)
        if tag == b'fmt ':
            if fmt_seen or audio_size is not None:
                raise AudioValidationError('invalid_fmt_order')
            fmt_seen = True
        elif tag == b'data':
            if audio_size is not None or not fmt_seen:
                raise AudioValidationError('invalid_data_order')
            audio_size = length
        offset = start+length+(length % 2)
        # For an unknown terminal payload there may be no RIFF padding byte.
        if declared == UNKNOWN:
            offset = size
        elif offset > size:
            if tag == b'data' and start+length == size:
                offset = size  # Python's WAV writer omits a terminal odd-byte pad.
            else:
                raise AudioValidationError('missing_chunk_padding')
    if audio_size is None:
        raise AudioValidationError('missing_audio_chunk')
    try:
        with wave.open(io.BytesIO(fixed), 'rb') as audio:
            channels, width, rate = audio.getnchannels(), audio.getsampwidth(), audio.getframerate()
            if channels not in (1,2) or width not in (1,2,3,4) or not 8000 <= rate <= 96000:
                raise AudioValidationError('unsupported_pcm_format', channels=channels, sample_bytes=width, rate=rate)
            stride = channels*width
            if audio_size % stride:
                raise AudioValidationError('partial_pcm_frame', pcm_bytes=audio_size, frame_bytes=stride)
            # Bound the read by actual response bytes, never by a remote frame count.
            pcm = audio.readframes(audio_size//stride+1)
            if len(pcm) != audio_size:
                raise AudioValidationError('truncated_pcm', pcm_bytes=len(pcm), expected_bytes=audio_size)
    except (wave.Error, EOFError, struct.error) as error:
        raise AudioValidationError('unsupported_or_invalid_wav') from error
    seconds = len(pcm)/(rate*stride)
    metrics = {'bytes':size, 'pcm_bytes':len(pcm), 'rate':rate, 'channels':channels,
               'sample_bytes':width, 'seconds':round(seconds,3), 'streaming_header':streaming}
    if not 0.1 <= seconds <= MAX_SECONDS:
        raise AudioValidationError('duration_out_of_bounds', **metrics)
    return pcm, channels, width, rate, metrics


def normalize(data):
    pcm, channels, width, rate, metrics = decode(data)
    out = io.BytesIO()
    with wave.open(out, 'wb') as audio:
        audio.setparams((channels,width,rate,0,'NONE','not compressed'))
        audio.writeframes(pcm)
    return out.getvalue(), metrics


def duration(data):
    *_, metrics = decode(data)
    return metrics['pcm_bytes']/(metrics['rate']*metrics['channels']*metrics['sample_bytes'])
