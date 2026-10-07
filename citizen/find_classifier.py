"""
Multimodal LLM classification of photographed archaeological finds.

This module sends photos to a vision-capable LLM (Claude, or any multimodal
model) to produce a preliminary classification. The key word is PRELIMINARY:
no AI classification replaces hands-on examination by a trained lithic analyst
or ceramicist. What it DOES provide is rapid triage — sorting thousands of
citizen reports into broad categories so professional reviewers can prioritize
their limited time on the most promising submissions.

Classification categories follow standard archaeological typologies:
- Lithics are subdivided by reduction stage (core -> debitage -> tool)
  because this tells us about site function (workshop vs. camp vs. kill site)
- Ceramics are kept as one category at this stage — temper, paste, and
  decoration analysis requires physical examination
- Historic artifacts are separated because they need different expertise
- Natural objects (geofacts) are the most common submission and must be
  identified confidently to avoid false positives in clustering
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.schemas import ArtifactClass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Classification prompt — the archaeological reasoning that guides the LLM
# ---------------------------------------------------------------------------

CLASSIFIER_SYSTEM_PROMPT = """You are an archaeological finds identification specialist with expertise in lithic technology, ceramic analysis, and historical material culture. You are assisting a citizen science program that receives photographs of surface finds from the public.

Your task is to classify each photographed object into one of these categories:

LITHIC CATEGORIES (stone tools and manufacturing debris):
- lithic_projectile: Bifacially or unifacially flaked stone shaped into a point. Look for: symmetry, pressure flaking scars, a base (notched, stemmed, or lanceolate), thin cross-section relative to width. Common materials: chert, flint, obsidian, chalcedony, jasper.
- lithic_scraper: A flake or blade with steep, intentional retouch along one or more edges. Look for: a working edge that is steeper than the opposite edge, visible use-wear or step fractures along the retouched margin.
- lithic_core: A nodule from which flakes have been struck. Look for: multiple flake scars radiating from platforms, negative bulbs of percussion, cortex remaining on some surfaces. Usually heavier than tools.
- lithic_debitage: Flakes, chips, and shatter from stone tool manufacturing. Look for: a bulb of percussion, a striking platform, ripple marks (compression waves), dorsal flake scars. The most common lithic find.
- lithic_ground_stone: Stone shaped by grinding/pecking rather than flaking. Look for: smooth worked surfaces, pecked depressions (nutting stones), grooves (axes), concave surfaces (metates/manos). Often made from sandstone, granite, or basite.

OTHER CATEGORIES:
- ceramic: Pottery sherds. Look for: clearly manufactured clay body, temper particles visible in cross-section, surface treatments (cord-marking, stamping, smoothing, slip, glaze). Distinguish from natural clay concretions.
- historic_metal: Metal objects from the historic period (post-European contact). Look for: iron, brass, copper, lead artifacts — nails, buttons, buckles, ammunition, tools.
- historic_glass: Glass fragments from the historic period. Look for: color, patina/iridescence (age indicator), manufacturing marks (pontil, mold seams).
- historic_ceramic: Refined ceramics from the historic period — stoneware, whiteware, porcelain, redware. Distinguished from prehistoric ceramics by manufacturing regularity, glaze types, and decoration styles.
- natural: A natural rock or geological specimen, NOT an artifact. This is the MOST IMPORTANT category to identify correctly — natural fractures, frost-split rocks, and concretions are commonly mistaken for artifacts. Look for: lack of systematic flaking pattern, absence of a striking platform/bulb, irregular fracture surfaces, natural cortex covering, geological rather than cultural fracture patterns.
- uncertain: Use this when the image quality is too poor, the object is ambiguous, or you genuinely cannot determine if it is cultural or natural. NEVER guess — uncertainty is honest and useful.

RESPONSE FORMAT:
Respond with a JSON object containing exactly these fields:
{
  "classification": "<one of the category names above>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<2-3 sentences explaining what visual features led to this classification>",
  "caveats": "<any limitations: image quality, angle, scale, ambiguity>",
  "recommended_action": "<what should happen next: 'routine_review', 'priority_review', 'request_better_photos', 'no_action_needed'>"
}

CRITICAL GUIDELINES:
1. When in doubt, classify as "uncertain" — false positives waste professional reviewer time and corrupt spatial clustering.
2. Natural rocks with conchoidal fracture (chert, flint, obsidian, quartz) are VERY commonly mistaken for artifacts. Require clear evidence of INTENTIONAL, PATTERNED flaking before classifying as lithic.
3. A single photo is often insufficient. Note when additional angles, scale references, or close-ups would help.
4. Your classification is PRELIMINARY. Always include this caveat. You are triaging, not making a final determination.
5. Do not speculate on time period, cultural affiliation, or monetary value — these require professional analysis and regional expertise."""


class ClassificationResult(BaseModel):
    """Result of LLM-based artifact classification."""
    classification: ArtifactClass = Field(
        ..., description="Predicted artifact class"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Model confidence in the classification"
    )
    reasoning: str = Field(
        default="", description="Visual features that led to this classification"
    )
    caveats: str = Field(
        default="",
        description="Limitations of this classification (image quality, ambiguity, etc.)"
    )
    recommended_action: str = Field(
        default="routine_review",
        description="Suggested next step: routine_review, priority_review, request_better_photos, no_action_needed"
    )
    raw_response: dict[str, Any] = Field(
        default_factory=dict,
        description="Full raw response from the LLM for audit purposes"
    )
    model_used: str = Field(
        default="", description="Model identifier used for this classification"
    )
    is_preliminary: bool = Field(
        default=True,
        description="Always True — LLM classification never replaces professional analysis"
    )


def _load_image_as_base64(file_path: str | Path) -> str:
    """Read an image file and return its base64-encoded content."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def _detect_media_type(file_path: str | Path) -> str:
    """Infer MIME type from file extension."""
    suffix = Path(file_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(suffix, "image/jpeg")


class FindClassifier:
    """
    Classifies photographed archaeological finds using a multimodal LLM.

    Wraps the Anthropic API (or compatible provider) to send photos with
    a carefully crafted archaeological classification prompt. Designed to
    be model-agnostic — swap the model name and the rest works the same.

    Usage:
        classifier = FindClassifier(model="claude-sonnet-4-20250514")
        result = classifier.classify_from_file("find_photo.jpg")
        result = classifier.classify_from_base64(b64_string, "image/jpeg")
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 1024,
    ) -> None:
        """
        Initialize the classifier.

        Args:
            model: Model identifier. Defaults to Claude Sonnet but any
                   vision-capable model supported by the anthropic library works.
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            max_tokens: Maximum response tokens.
        """
        import anthropic

        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def classify_from_file(
        self,
        image_path: str | Path,
        reporter_description: str = "",
    ) -> ClassificationResult:
        """
        Classify a find from an image file on disk.

        Args:
            image_path: Path to the image file (JPEG, PNG, GIF, or WebP).
            reporter_description: Optional text from the reporter describing the find.

        Returns:
            ClassificationResult with predicted class, confidence, and reasoning.
        """
        b64_data = _load_image_as_base64(image_path)
        media_type = _detect_media_type(image_path)
        return self.classify_from_base64(b64_data, media_type, reporter_description)

    def classify_from_base64(
        self,
        image_base64: str,
        media_type: str = "image/jpeg",
        reporter_description: str = "",
    ) -> ClassificationResult:
        """
        Classify a find from a base64-encoded image.

        Args:
            image_base64: Base64-encoded image data.
            media_type: MIME type of the image.
            reporter_description: Optional text from the reporter describing the find.

        Returns:
            ClassificationResult with predicted class, confidence, and reasoning.
        """
        user_content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_base64,
                },
            },
            {
                "type": "text",
                "text": self._build_user_prompt(reporter_description),
            },
        ]

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=CLASSIFIER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            return self._parse_response(response)
        except Exception as e:
            logger.error("Classification failed: %s", e)
            return ClassificationResult(
                classification=ArtifactClass.UNCERTAIN,
                confidence=0.0,
                reasoning="",
                caveats=f"Classification failed due to an error: {e}",
                recommended_action="routine_review",
                model_used=self.model,
            )

    def classify_multiple(
        self,
        image_paths: list[str | Path],
        reporter_description: str = "",
    ) -> ClassificationResult:
        """
        Classify a find using multiple photos (different angles/scales).

        Multiple views dramatically improve classification accuracy —
        a dorsal and ventral view of a flake, for example, reveals both
        the flake scar pattern and the bulb of percussion.

        Args:
            image_paths: List of image file paths for the same find.
            reporter_description: Optional reporter description.

        Returns:
            Single ClassificationResult synthesizing all views.
        """
        user_content: list[dict[str, Any]] = []

        for i, path in enumerate(image_paths):
            b64_data = _load_image_as_base64(path)
            media_type = _detect_media_type(path)
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64_data,
                },
            })
            if i == 0:
                user_content.append({
                    "type": "text",
                    "text": f"Photo {i + 1} of {len(image_paths)} showing the same find.",
                })

        user_content.append({
            "type": "text",
            "text": self._build_user_prompt(reporter_description),
        })

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=CLASSIFIER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            return self._parse_response(response)
        except Exception as e:
            logger.error("Multi-photo classification failed: %s", e)
            return ClassificationResult(
                classification=ArtifactClass.UNCERTAIN,
                confidence=0.0,
                reasoning="",
                caveats=f"Classification failed due to an error: {e}",
                recommended_action="routine_review",
                model_used=self.model,
            )

    def _build_user_prompt(self, reporter_description: str) -> str:
        """Build the user-facing prompt that accompanies the image(s)."""
        prompt = (
            "Please classify this find according to your instructions. "
            "Respond ONLY with the JSON object specified in your system prompt."
        )
        if reporter_description:
            prompt += (
                f"\n\nThe reporter describes this find as: \"{reporter_description}\"\n"
                "(Use this context but rely primarily on what you see in the image.)"
            )
        return prompt

    def _parse_response(self, response: Any) -> ClassificationResult:
        """Parse the LLM response into a ClassificationResult."""
        import json

        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON: %s", raw_text[:200])
            return ClassificationResult(
                classification=ArtifactClass.UNCERTAIN,
                confidence=0.0,
                reasoning=raw_text[:500],
                caveats="LLM response was not valid JSON — manual review needed.",
                recommended_action="routine_review",
                raw_response={"raw_text": raw_text},
                model_used=self.model,
            )

        # Map the classification string to ArtifactClass enum
        classification_str = data.get("classification", "uncertain")
        try:
            artifact_class = ArtifactClass(classification_str)
        except ValueError:
            logger.warning("Unknown classification '%s', defaulting to uncertain", classification_str)
            artifact_class = ArtifactClass.UNCERTAIN

        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        return ClassificationResult(
            classification=artifact_class,
            confidence=confidence,
            reasoning=data.get("reasoning", ""),
            caveats=data.get("caveats", ""),
            recommended_action=data.get("recommended_action", "routine_review"),
            raw_response=data,
            model_used=self.model,
        )
