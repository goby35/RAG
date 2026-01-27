# utils/temporal_ranking.py - Temporal-aware Ranking Module
"""
Temporal Ranking Module for Graph-based RAG Application.

Implements Time Decay Function and Combined Scoring for Claims.

Scoring Formula:
    final_score = (semantic_weight * semantic_score) 
                + (confidence_weight * confidence_score)
                + (freshness_weight * freshness_score)

Default Weights:
    - Semantic: 40%
    - Confidence: 40%
    - Freshness: 20%
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
import math
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION
# ============================================================================

# Scoring weights (must sum to 1.0)
SEMANTIC_WEIGHT = 0.40
CONFIDENCE_WEIGHT = 0.40
FRESHNESS_WEIGHT = 0.20

# Time decay parameters
FRESH_PERIOD_DAYS = 180  # 6 months - information stays fresh
HALF_LIFE_DAYS = 365     # 1 year - time for score to halve after fresh period
MIN_FRESHNESS_SCORE = 0.1  # Minimum freshness score (never goes to 0)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _convert_to_datetime(value: Any) -> Optional[datetime]:
    """
    Convert various datetime formats to Python datetime.
    
    Handles:
    - None -> None
    - Python datetime -> datetime
    - Neo4j DateTime -> Python datetime
    - ISO string -> datetime
    """
    if value is None:
        return None
    
    # Already a Python datetime
    if isinstance(value, datetime):
        return value
    
    # Neo4j DateTime (has to_native() method)
    if hasattr(value, 'to_native'):
        return value.to_native()
    
    # String format
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    return None


# ============================================================================
# TIME DECAY FUNCTION
# ============================================================================

def calculate_time_decay(
    verified_at: Optional[datetime],
    expiration_date: Optional[datetime] = None,
    reference_time: Optional[datetime] = None
) -> float:
    """
    Calculate time-based freshness score using logarithmic decay.
    
    Logic:
    - If expired: return MIN_FRESHNESS_SCORE
    - If within FRESH_PERIOD_DAYS (6 months): return 1.0
    - If older: apply logarithmic decay
    
    Args:
        verified_at: When the claim was verified/created
        expiration_date: Optional expiration date
        reference_time: Reference time for calculation (default: now)
        
    Returns:
        float: Freshness score between MIN_FRESHNESS_SCORE and 1.0
    """
    if reference_time is None:
        reference_time = datetime.now()
    
    # Handle None verified_at - use minimum score
    if verified_at is None:
        return MIN_FRESHNESS_SCORE
    
    # Handle datetime objects that might be timezone-aware
    if hasattr(verified_at, 'tzinfo') and verified_at.tzinfo is not None:
        verified_at = verified_at.replace(tzinfo=None)
    
    # Check expiration first
    if expiration_date is not None:
        if hasattr(expiration_date, 'tzinfo') and expiration_date.tzinfo is not None:
            expiration_date = expiration_date.replace(tzinfo=None)
        if reference_time > expiration_date:
            return MIN_FRESHNESS_SCORE
    
    # Calculate age in days
    age_days = (reference_time - verified_at).days
    
    # Fresh period: full score
    if age_days <= FRESH_PERIOD_DAYS:
        return 1.0
    
    # Calculate decay for older information
    # Using logarithmic decay: score = 1 / (1 + log(1 + days_over_fresh / half_life))
    days_over_fresh = age_days - FRESH_PERIOD_DAYS
    decay_factor = 1.0 / (1.0 + math.log1p(days_over_fresh / HALF_LIFE_DAYS))
    
    # Ensure minimum score
    return max(decay_factor, MIN_FRESHNESS_SCORE)


def calculate_freshness_score(
    claim: Dict[str, Any],
    reference_time: Optional[datetime] = None
) -> float:
    """
    Calculate freshness score for a claim.
    
    Uses verified_at if available, otherwise falls back to created_at.
    
    Args:
        claim: Claim dictionary with temporal metadata
        reference_time: Reference time for calculation
        
    Returns:
        float: Freshness score
    """
    # Try verified_at first (more relevant for attested claims)
    verified_at = claim.get('verified_at')
    
    # Fall back to created_at
    if verified_at is None:
        verified_at = claim.get('created_at')
    
    # Convert Neo4j DateTime to Python datetime if needed
    verified_at = _convert_to_datetime(verified_at)
    
    # Get expiration date
    expiration_date = claim.get('expiration_date')
    expiration_date = _convert_to_datetime(expiration_date)
    
    return calculate_time_decay(verified_at, expiration_date, reference_time)


# ============================================================================
# COMBINED SCORING
# ============================================================================

@dataclass
class ScoredClaim:
    """A claim with all its scoring components."""
    claim: Dict[str, Any]
    semantic_score: float = 0.0
    confidence_score: float = 0.0
    freshness_score: float = 0.0
    final_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "scores": {
                "semantic": round(self.semantic_score, 4),
                "confidence": round(self.confidence_score, 4),
                "freshness": round(self.freshness_score, 4),
                "final": round(self.final_score, 4)
            }
        }


def calculate_combined_score(
    semantic_score: float,
    confidence_score: float,
    freshness_score: float,
    semantic_weight: float = SEMANTIC_WEIGHT,
    confidence_weight: float = CONFIDENCE_WEIGHT,
    freshness_weight: float = FRESHNESS_WEIGHT
) -> float:
    """
    Calculate the combined ranking score.
    
    Formula:
        final = (semantic_weight * semantic_score) 
              + (confidence_weight * confidence_score)
              + (freshness_weight * freshness_score)
    
    Args:
        semantic_score: Vector similarity score (0-1)
        confidence_score: Claim confidence score (0-1)
        freshness_score: Time decay score (0-1)
        *_weight: Custom weights (must sum to 1.0)
        
    Returns:
        float: Combined score (0-1)
    """
    # Normalize weights if they don't sum to 1
    total_weight = semantic_weight + confidence_weight + freshness_weight
    if abs(total_weight - 1.0) > 0.001:
        semantic_weight /= total_weight
        confidence_weight /= total_weight
        freshness_weight /= total_weight
    
    return (
        semantic_weight * semantic_score +
        confidence_weight * confidence_score +
        freshness_weight * freshness_score
    )


def rank_claims(
    claims: List[Dict[str, Any]],
    semantic_scores: List[float],
    reference_time: Optional[datetime] = None
) -> List[ScoredClaim]:
    """
    Rank claims using combined scoring.
    
    Args:
        claims: List of claim dictionaries
        semantic_scores: Corresponding semantic similarity scores
        reference_time: Reference time for freshness calculation
        
    Returns:
        List of ScoredClaim objects, sorted by final_score descending
    """
    if len(claims) != len(semantic_scores):
        raise ValueError("claims and semantic_scores must have same length")
    
    scored_claims = []
    
    for claim, sem_score in zip(claims, semantic_scores):
        # Get confidence score from claim
        conf_score = claim.get('confidence_score', 0.3)
        
        # Calculate freshness score
        fresh_score = calculate_freshness_score(claim, reference_time)
        
        # Calculate final score
        final = calculate_combined_score(sem_score, conf_score, fresh_score)
        
        scored_claims.append(ScoredClaim(
            claim=claim,
            semantic_score=sem_score,
            confidence_score=conf_score,
            freshness_score=fresh_score,
            final_score=final
        ))
    
    # Sort by final score (descending)
    scored_claims.sort(key=lambda x: x.final_score, reverse=True)
    
    return scored_claims


def rerank_with_temporal_awareness(
    claims_with_scores: List[tuple],  # [(claim, semantic_score), ...]
    reference_time: Optional[datetime] = None,
    top_k: Optional[int] = None
) -> List[ScoredClaim]:
    """
    Re-rank claims with temporal awareness.
    
    Convenience function that takes claims with their semantic scores
    and returns re-ranked results.
    
    Args:
        claims_with_scores: List of (claim, semantic_score) tuples
        reference_time: Reference time for freshness calculation
        top_k: Optional limit on results
        
    Returns:
        Top-k ScoredClaim objects
    """
    claims = [c for c, _ in claims_with_scores]
    scores = [s for _, s in claims_with_scores]
    
    ranked = rank_claims(claims, scores, reference_time)
    
    if top_k:
        return ranked[:top_k]
    return ranked


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_freshness_label(freshness_score: float) -> str:
    """
    Get human-readable label for freshness score.
    
    Args:
        freshness_score: Freshness score (0-1)
        
    Returns:
        str: Label like "Very Fresh", "Recent", etc.
    """
    if freshness_score >= 0.95:
        return "🟢 Very Fresh"
    elif freshness_score >= 0.8:
        return "🟢 Fresh"
    elif freshness_score >= 0.5:
        return "🟡 Recent"
    elif freshness_score >= 0.3:
        return "🟠 Aging"
    else:
        return "🔴 Stale"


def format_score_breakdown(scored_claim: ScoredClaim) -> str:
    """
    Format score breakdown for display.
    
    Args:
        scored_claim: ScoredClaim object
        
    Returns:
        str: Formatted string
    """
    return (
        f"📊 Score Breakdown:\n"
        f"  • Semantic Relevance: {scored_claim.semantic_score:.1%}\n"
        f"  • Confidence: {scored_claim.confidence_score:.1%}\n"
        f"  • Freshness: {scored_claim.freshness_score:.1%} {get_freshness_label(scored_claim.freshness_score)}\n"
        f"  • Final Score: {scored_claim.final_score:.1%}"
    )


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def batch_calculate_freshness(
    claims: List[Dict[str, Any]],
    reference_time: Optional[datetime] = None
) -> List[float]:
    """
    Calculate freshness scores for multiple claims.
    
    Args:
        claims: List of claim dictionaries
        reference_time: Reference time for calculation
        
    Returns:
        List of freshness scores
    """
    return [calculate_freshness_score(claim, reference_time) for claim in claims]


def filter_expired_claims(
    claims: List[Dict[str, Any]],
    reference_time: Optional[datetime] = None,
    include_expired: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter out expired claims.
    
    Args:
        claims: List of claim dictionaries
        reference_time: Reference time for checking expiration
        include_expired: If True, include expired claims (with flag)
        
    Returns:
        Filtered list of claims
    """
    if reference_time is None:
        reference_time = datetime.now()
    
    result = []
    for claim in claims:
        expiration_date = claim.get('expiration_date')
        
        if expiration_date is None:
            result.append(claim)
            continue
        
        if isinstance(expiration_date, str):
            try:
                expiration_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                result.append(claim)
                continue
        
        if hasattr(expiration_date, 'tzinfo') and expiration_date.tzinfo is not None:
            expiration_date = expiration_date.replace(tzinfo=None)
        
        if reference_time <= expiration_date:
            result.append(claim)
        elif include_expired:
            claim['_expired'] = True
            result.append(claim)
    
    return result
