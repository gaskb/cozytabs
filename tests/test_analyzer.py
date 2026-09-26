import pytest
from analyzer import GuitarLesson, Chord

def test_guitar_lesson_model():
    lesson = GuitarLesson(
        title="Progressione A - B - C#m - G#m Voicings Aperti",
        tuning="Standard (E A D G B E)",
        capo="Nessuno",
        key="E maggiore",
        progression="Aadd#4 -> B(add11) -> C#m9 -> G#m(b6)",
        chords=[
            Chord(name="Aadd#4", fingering="x 0 x 4 4 0", description="Open ambient voicing"),
            Chord(name="B(add11)", fingering="x 2 x 4 4 0", description="Indice al 2° tasto"),
        ],
        tablature="e|-------0-------|\nB|-----4---4-----|\nG|---4-------4---|\nD|---------------|\nA|-0-------------|\nE|---------------|",
        right_hand_technique="Arpeggio dita con pollice sul basso e anulare/medio su corde acute",
        execution_tips=["Mantieni le dita fisse sui tasti 4 e 4", "Muta la 4 corda con il polpastrello"],
        summary="Sfrutta un pedale melodico sulle corde 1, 2, 3 muovendo solo il basso"
    )

    assert lesson.title != ""
    assert len(lesson.chords) == 2
    assert lesson.chords[0].name == "Aadd#4"
    assert "e|-------0-------|" in lesson.tablature

def test_extract_audio_track_success(monkeypatch, tmp_path):
    from analyzer import extract_audio_track
    import subprocess
    from unittest.mock import MagicMock

    test_video = str(tmp_path / "video.mp4")
    test_audio = str(tmp_path / "audio.mp3")
    with open(test_video, "w") as vf:
        vf.write("dummy video")

    def mock_run(cmd, stdout=None, stderr=None):
        # simula creazione file audio
        with open(test_audio, "w") as af:
            af.write("dummy audio content")
        mock_res = MagicMock()
        mock_res.returncode = 0
        return mock_res

    monkeypatch.setattr(subprocess, "run", mock_run)
    res = extract_audio_track(test_video, test_audio)
    assert res == test_audio

def test_extract_audio_track_failure(monkeypatch, tmp_path):
    from analyzer import extract_audio_track
    import subprocess
    from unittest.mock import MagicMock

    test_video = str(tmp_path / "video.mp4")
    test_audio = str(tmp_path / "audio.mp3")

    def mock_run(cmd, stdout=None, stderr=None):
        mock_res = MagicMock()
        mock_res.returncode = 1
        return mock_res

    monkeypatch.setattr(subprocess, "run", mock_run)
    res = extract_audio_track(test_video, test_audio)
    assert res is None
