import re
from collections import Counter
from functools import lru_cache
from typing import Literal

from fastapi import HTTPException
from pydantic import Field
from app.validation import InputModel
from app.stories.metadata import LANGUAGE_NAMES

ConcreteLanguage = Literal["en", "id", "ja", "ko", "zh-CN", "fr", "de", "es"]
DETECTOR_VERSION = "langdetect-1.0.9-seed0-c2-v1"
SUPPORTED = set(LANGUAGE_NAMES) - {"und"}


class LanguageOptions(InputModel):
    output_language: ConcreteLanguage | None = None
    response_language: ConcreteLanguage | None = None
    conversation_preference: ConcreteLanguage | None = None


class DetectionRequest(InputModel):
    text: str = Field(max_length=40000)


@lru_cache(maxsize=1)
def detector():
    from langdetect.detector_factory import DetectorFactory, PROFILES_DIRECTORY
    factory = DetectorFactory()
    factory.seed = 0
    factory.load_profile(PROFILES_DIRECTORY)
    return factory


def _score(text):
    instance = detector().create()
    instance.append(text)
    from langdetect.lang_detect_exception import LangDetectException
    try:
        scores = instance.get_probabilities()
    except LangDetectException:
        return "und", 0.0, 0.0
    if not scores:
        return "und", 0.0, 0.0
    code = scores[0].lang
    return ("zh-CN" if code == "zh-cn" else code), scores[0].prob, scores[0].prob - (scores[1].prob if len(scores) > 1 else 0)


def detect(text: str, *, strip_quotes=True):
    text = text.strip()[:40000]
    clean = re.sub(r'```[\s\S]*?```|"[^"\n]*"|“[^”]*”|«[^»]*»', ' ', text) if strip_quotes else text
    letters = sum(character.isalpha() for character in clean)
    result = dict(language="und", status="uncertain", confidence=0.0, detector=DETECTOR_VERSION, review_required=True)
    if not text:
        return {**result, "status": "empty"}
    # A statistical guess on a name or tiny instruction is not an approved language.
    if letters < 20:
        return {**result, "status": "short"}
    code, confidence, margin = _score(clean)
    result["confidence"] = round(confidence, 4)
    if code in {"en", "id", "fr", "de", "es"} and len(re.findall(r"\w+", clean)) < 6:
        return {**result, "status":"short"}
    if code not in SUPPORTED:
        return {**result, "status": "unsupported"} if confidence>=0.65 and margin>=0.15 else result
    if confidence < 0.65 or margin < 0.15:
        return result
    weights = Counter()
    for part in re.split(r'[.!?。！？\n]+', clean):
        size = sum(character.isalpha() for character in part)
        if size < 20:
            continue
        language, score, distance = _score(part)
        if score >= 0.65 and distance >= 0.15:
            weights[language] += size
    if len(weights) > 1 and max(weights.values()) / sum(weights.values()) < 0.75:
        return {**result, "status": "mixed"}
    return {**result, "language": code, "status": "detected", "review_required": False}


def production_language(saved, override=None):
    language = override or (saved if saved in SUPPORTED else "en")
    return dict(language=language, source="operation_override" if override else "saved_story" if saved in SUPPORTED else "fallback",
                fallback=not override and saved not in SUPPORTED)


def conversation_language(message, override=None, preference=None, saved=None):
    detection = detect(message or "")
    language = override or (detection["language"] if not detection["review_required"] else None) or preference or (saved if saved in SUPPORTED else "en")
    source = "operation_override" if override else "message" if not detection["review_required"] else "confirmed_preference" if preference else "fallback"
    return dict(language=language, source=source, fallback=source == "fallback", detection=detection)


def validate_output(text, language):
    """Reject a confident mismatch; short/name/quoted output remains explicitly unverified."""
    detection = detect(text, strip_quotes=False)
    if detection["status"] == "unsupported" or (not detection["review_required"] and detection["language"] != language):
        raise HTTPException(502, "Generated output did not match the requested language. No content was saved. Please retry or revise the request.")
    return "verified" if not detection["review_required"] else "unverified_short_or_ambiguous"


def creation_language(premise, language, mode):
    detection = detect(premise or "") if mode == "automatic" else None
    if mode == "automatic" and (detection["review_required"] or language != detection["language"]):
        raise HTTPException(422, "Story language needs confirmation. Detect the current premise again or choose a supported language explicitly.")
    if mode == "explicit" and language not in SUPPORTED:
        raise HTTPException(422, "Choose a supported Story language.")
    from app.db.types import utc_now
    return dict(source="automatic_creation" if mode == "automatic" else "explicit_creation" if language in SUPPORTED else "legacy_unspecified",
                language=language, detection=detection, changed_at=utc_now().isoformat())


RECEIPTS = {
    "en": "The generated Scene is saved for review. Your Story language and Canon are unchanged.",
    "id": "Adegan hasil penulisan tersimpan untuk ditinjau. Bahasa Cerita dan Kanon tetap sama.",
    "ja": "生成されたシーンを確認用に保存しました。物語の言語と設定は変更されていません。",
    "ko": "생성된 장면을 검토할 수 있도록 저장했습니다. 이야기 언어와 설정은 변경되지 않았습니다.",
    "zh-CN": "生成的场景已保存以供审阅。故事语言和设定保持不变。",
    "fr": "La scène générée est enregistrée pour révision. La langue du récit et le canon restent inchangés.",
    "de": "Die erzeugte Szene ist zur Prüfung gespeichert. Die Sprache der Geschichte und der Kanon bleiben unverändert.",
    "es": "La escena generada está guardada para revisión. El idioma de la historia y el canon no han cambiado.",
}

PENDING_RECEIPTS = {
    "en":"This request needs review. No Scene was saved.", "id":"Permintaan ini perlu ditinjau. Belum ada Adegan yang disimpan.",
    "ja":"このリクエストは確認が必要です。シーンは保存されていません。", "ko":"이 요청은 검토가 필요합니다. 저장된 장면이 없습니다.",
    "zh-CN":"此请求需要审阅。尚未保存场景。", "fr":"Cette demande nécessite une révision. Aucune scène n’a été enregistrée.",
    "de":"Diese Anfrage muss geprüft werden. Es wurde keine Szene gespeichert.", "es":"Esta solicitud requiere revisión. No se ha guardado ninguna escena.",
}
