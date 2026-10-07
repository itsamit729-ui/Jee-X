import io
import struct
import wave
import pytest
from social import speech_audio
from social.test_narration import wav


def streamed(data, metadata=False):
    result=bytearray(data)
    struct.pack_into('<I',result,4,0xffffffff)
    if metadata:
        result[36:36]=b'JUNK'+struct.pack('<I',3)+b'abc\0'
    pos=result.index(b'data')
    struct.pack_into('<I',result,pos+4,0xffffffff)
    return bytes(result)


@pytest.mark.parametrize('metadata',[False,True])
def test_streaming_size_is_not_duration(metadata):
    source=streamed(wav(2),metadata)
    normalized,metrics=speech_audio.normalize(source)
    assert metrics['streaming_header'] is True
    assert metrics['seconds']==2
    assert normalized==wav(2)
    with wave.open(io.BytesIO(normalized),'rb') as audio:
        assert audio.getnframes()==48000
    assert speech_audio.duration(source)==2


def test_regular_wav_and_trailing_metadata():
    data=bytearray(wav(2)+b'LIST'+struct.pack('<I',4)+b'INFO')
    struct.pack_into('<I',data,4,len(data)-8)
    result,metrics=speech_audio.normalize(data)
    assert result==wav(2) and not metrics['streaming_header']


@pytest.mark.parametrize('bad,code',[
    (b'not a WAV', 'not_pcm_wav'),
    (wav()[:-10], 'riff_size_mismatch'),
    (streamed(wav())[:-1], 'partial_pcm_frame'),
    (wav(21), 'duration_out_of_bounds'),
    (wav(0), 'duration_out_of_bounds'),
    (b'x'*(speech_audio.MAX_BYTES+1), 'audio_too_large'),
])
def test_bad_audio_is_still_rejected(bad,code):
    with pytest.raises(speech_audio.AudioValidationError) as exc:
        speech_audio.normalize(bad)
    assert exc.value.code==code


def test_known_data_truncation_is_not_repaired():
    data=bytearray(wav()[:-10]);struct.pack_into('<I',data,4,len(data)-8)
    with pytest.raises(speech_audio.AudioValidationError,match='truncated_chunk'):
        speech_audio.normalize(data)


def test_complete_odd_length_eight_bit_pcm():
    out=io.BytesIO()
    with wave.open(out,'wb') as audio:
        audio.setparams((1,1,8000,0,'NONE','not compressed'))
        audio.writeframes(b'\x80'*801)
    normalized,metrics=speech_audio.normalize(out.getvalue())
    assert metrics['pcm_bytes']==801
    assert speech_audio.duration(normalized)==801/8000
