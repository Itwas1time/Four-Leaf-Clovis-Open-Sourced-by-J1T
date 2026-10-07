"""
LLM-powered spatial reference extraction from historical text.

Historical documents contain spatial information in forms that defy simple
regex or NER: "three days' march north of the great mound," "at the
confluence of the two rivers where the bluffs rise steeply," "near the
old Shawnee village called Chillicothe." An LLM can parse these varied
expressions into structured data — named places, relative directions,
travel-time distances, and landscape features — that the reference
resolver can then geocode.

The extraction layer is model-agnostic: it defaults to the Anthropic API
(Claude) but abstracts the call so any LLM with a compatible chat/tool-use
interface can be substituted.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from core.schemas import HistoricalReference, TimePeriod

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Extraction result models
# ------------------------------------------------------------------

class SpatialReferenceRaw(BaseModel):
    """
    A single spatial reference as extracted by the LLM, before geocoding.

    This is the bridge between unstructured text and the structured
    HistoricalReference schema. The LLM fills in what it can identify;
    the reference_resolver handles the actual coordinate resolution.
    """

    place_name: str = Field(default="", description="Named place if identified")
    place_type: str = Field(
        default="",
        description="Type: settlement, river, mound, mountain, confluence, etc.",
    )
    relative_anchor: str = Field(
        default="",
        description="Anchor place for relative references ('north of X')",
    )
    relative_direction: str = Field(
        default="",
        description="Cardinal/intercardinal direction from anchor",
    )
    relative_distance_text: str = Field(
        default="",
        description="Raw distance text: 'three days march', '20 miles', etc.",
    )
    feature_description: str = Field(
        default="",
        description="Landscape features: 'confluence of two rivers', 'high bluff'",
    )
    structure_description: str = Field(
        default="",
        description="Built features: 'large mound', 'stone walls', 'earthen enclosure'",
    )
    temporal_context: str = Field(
        default="",
        description="Any time indicators: dates, period names, relative chronology",
    )
    time_period: str = Field(
        default="",
        description="Best-guess archaeological time period",
    )
    extracted_passage: str = Field(
        default="",
        description="The exact text passage this reference was drawn from",
    )
    extraction_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="LLM's self-assessed confidence in this extraction",
    )


class ExtractionResult(BaseModel):
    """Full extraction output for a single text chunk."""

    chunk_id: str = ""
    document_id: str = ""
    references: list[SpatialReferenceRaw] = Field(default_factory=list)
    raw_llm_response: str = Field(default="", description="Raw LLM output for debugging")


# ------------------------------------------------------------------
# LLM provider abstraction
# ------------------------------------------------------------------

class LLMProvider(ABC):
    """
    Abstract base for LLM API providers.

    The spatial extractor needs exactly one capability: send a prompt with
    a tool/function schema and get back structured JSON. Any LLM that
    supports tool-use (Claude, GPT-4, Mistral, local Ollama models) can
    implement this interface.
    """

    @abstractmethod
    def extract_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Send a message with tool definitions and return tool-call results.

        Args:
            system_prompt: System instructions for the LLM.
            user_message: The text chunk to analyze.
            tools: Tool/function definitions in the provider's format.

        Returns:
            List of dicts, each representing one tool call's parsed arguments.
        """
        ...


class AnthropicProvider(LLMProvider):
    """
    Claude API provider using the anthropic library.

    Default provider. Uses Claude's native tool-use to get structured
    spatial reference extractions.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._api_key = api_key

    def _get_client(self) -> Any:
        """Lazy-load the anthropic client."""
        import anthropic

        kwargs: dict[str, Any] = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        return anthropic.Anthropic(**kwargs)

    def extract_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        client = self._get_client()

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=tools,
        )

        results: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "tool_use":
                results.append(block.input)

        return results


# ------------------------------------------------------------------
# Tool definition for the LLM
# ------------------------------------------------------------------

SPATIAL_EXTRACTION_TOOL = {
    "name": "record_spatial_reference",
    "description": (
        "Record a spatial reference found in a historical text passage. "
        "Call this once for each distinct spatial reference identified. "
        "A single passage may contain multiple references."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "place_name": {
                "type": "string",
                "description": "Named place (e.g., 'Cahokia', 'Fort Ancient', 'Chillicothe')",
            },
            "place_type": {
                "type": "string",
                "description": "Category: settlement, river, mound, mountain, confluence, fort, village, cave, spring, trail",
            },
            "relative_anchor": {
                "type": "string",
                "description": "For relative references, the anchor place name",
            },
            "relative_direction": {
                "type": "string",
                "description": "Direction from anchor: N, NE, E, SE, S, SW, W, NW, upstream, downstream",
            },
            "relative_distance_text": {
                "type": "string",
                "description": "Distance as stated: '3 days march', '20 miles', 'half a league'",
            },
            "feature_description": {
                "type": "string",
                "description": "Landscape: 'at the confluence of two rivers', 'on a high bluff overlooking the valley'",
            },
            "structure_description": {
                "type": "string",
                "description": "Built features: 'a large earthen mound', 'stone enclosure walls', 'platform mound with ramp'",
            },
            "temporal_context": {
                "type": "string",
                "description": "Time indicators: '1803', 'before the removal', 'ancient', 'recently abandoned'",
            },
            "time_period": {
                "type": "string",
                "enum": [p.value for p in TimePeriod],
                "description": "Best-guess archaeological time period",
            },
            "extracted_passage": {
                "type": "string",
                "description": "The exact words from the text this reference is based on",
            },
            "extraction_confidence": {
                "type": "number",
                "description": "Confidence 0.0-1.0 that this is a real spatial reference",
            },
        },
        "required": ["extracted_passage", "extraction_confidence"],
    },
}


# ------------------------------------------------------------------
# System prompt
# ------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """\
You are an expert archaeologist and historical geographer analyzing historical \
documents for spatial references. Your task is to identify every mention of a \
physical location, whether named or described indirectly.

Extract ALL of the following reference types:

1. **Named places** — settlements, rivers, mountains, forts, villages, mounds, \
   springs, caves, trails, and any other named geographic feature.

2. **Relative references** — locations described relative to a known place: \
   "three days' march north of...", "20 miles upstream from...", "half a day's \
   ride west of the fort."

3. **Directional/feature references** — locations described by landscape features \
   without a name: "at the confluence of two large rivers", "where the bluffs \
   rise above the floodplain", "on the terrace overlooking the creek."

4. **Temporal context** — any date, era, or relative chronology associated with \
   the place: "in 1803", "before the removal", "ancient earthworks."

5. **Structure references** — built features that indicate human activity: mounds, \
   earthworks, walls, platforms, enclosures, village remains, middens.

For each reference, call the record_spatial_reference tool. A single passage may \
contain multiple distinct references — call the tool once per reference.

Be thorough but precise. Only extract references you can support with specific \
quoted text from the passage. Assign confidence based on how clear and unambiguous \
the reference is.
"""


# ------------------------------------------------------------------
# Main extractor class
# ------------------------------------------------------------------

class SpatialExtractor:
    """
    Extract structured spatial references from text using an LLM.

    Archaeological rationale: Historical texts are the only source for
    sites that have been plowed flat, flooded by reservoirs, or built
    over by modern development. A 19th-century surveyor's note that
    "three large mounds stood on the terrace above the river junction"
    may be the only record that those mounds ever existed.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        """
        Args:
            provider: LLM provider to use. Defaults to AnthropicProvider.
                      Pass any LLMProvider implementation to use a different model.
        """
        self.provider = provider or AnthropicProvider()

    def extract_from_text(
        self,
        text: str,
        *,
        chunk_id: str = "",
        document_id: str = "",
        source_document: str = "",
        author: str = "",
        document_date: str = "",
    ) -> ExtractionResult:
        """
        Extract spatial references from a single text passage.

        Args:
            text: The passage to analyze.
            chunk_id: ID of the source chunk.
            document_id: ID of the source document.
            source_document: Human-readable document title for HistoricalReference.
            author: Document author.
            document_date: Document date.

        Returns:
            ExtractionResult with all identified spatial references.
        """
        if not text.strip():
            return ExtractionResult(chunk_id=chunk_id, document_id=document_id)

        try:
            tool_calls = self.provider.extract_with_tools(
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                user_message=text,
                tools=[SPATIAL_EXTRACTION_TOOL],
            )
        except Exception:
            logger.exception("LLM extraction failed for chunk %s", chunk_id)
            return ExtractionResult(
                chunk_id=chunk_id,
                document_id=document_id,
                raw_llm_response="ERROR: extraction call failed",
            )

        references: list[SpatialReferenceRaw] = []
        for call_args in tool_calls:
            try:
                ref = SpatialReferenceRaw(**call_args)
                references.append(ref)
            except Exception:
                logger.warning("Could not parse tool call args: %s", call_args)

        return ExtractionResult(
            chunk_id=chunk_id,
            document_id=document_id,
            references=references,
            raw_llm_response=json.dumps(tool_calls, default=str),
        )

    def extract_batch(
        self,
        chunks: list[dict[str, Any]],
        *,
        source_document: str = "",
        author: str = "",
        document_date: str = "",
    ) -> list[ExtractionResult]:
        """
        Extract spatial references from multiple text chunks.

        Args:
            chunks: List of dicts with keys 'text', 'chunk_id', 'document_id'.
            source_document: Document title.
            author: Document author.
            document_date: Document date.

        Returns:
            List of ExtractionResult, one per chunk.
        """
        results: list[ExtractionResult] = []
        for chunk in chunks:
            result = self.extract_from_text(
                text=chunk.get("text", ""),
                chunk_id=chunk.get("chunk_id", ""),
                document_id=chunk.get("document_id", ""),
                source_document=source_document,
                author=author,
                document_date=document_date,
            )
            results.append(result)
        return results

    def raw_to_historical_references(
        self,
        extraction: ExtractionResult,
        *,
        source_document: str = "",
        author: str = "",
        document_date: str = "",
    ) -> list[HistoricalReference]:
        """
        Convert raw extraction results to core HistoricalReference objects.

        This is a convenience bridge — coordinates are NOT resolved here.
        The reference_resolver handles geocoding. This method populates
        all the text-derived fields.
        """
        refs: list[HistoricalReference] = []
        for raw in extraction.references:
            # Attempt to map time_period string to enum
            time_period: TimePeriod | None = None
            if raw.time_period:
                try:
                    time_period = TimePeriod(raw.time_period)
                except ValueError:
                    pass

            # Collect described features from structure + feature descriptions
            described_features: list[str] = []
            if raw.structure_description:
                described_features.append(raw.structure_description)
            if raw.feature_description:
                described_features.append(raw.feature_description)
            if raw.place_type:
                described_features.append(raw.place_type)

            ref = HistoricalReference(
                source_document=source_document or extraction.document_id,
                author=author,
                document_date=document_date,
                extracted_text=raw.extracted_passage,
                confidence=raw.extraction_confidence,
                time_period=time_period,
                described_features=described_features,
            )
            refs.append(ref)
        return refs
