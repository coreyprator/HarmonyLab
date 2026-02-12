"""
Pydantic models for Harmony Lab API.

These models match the database schema defined in HarmonyLab-Schema-v1.0.sql
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================
# Song Models
# =============================================

class SongBase(BaseModel):
    """Base model for Song data."""
    title: str = Field(..., max_length=200)
    composer: Optional[str] = Field(None, max_length=200)
    arranger: Optional[str] = Field(None, max_length=200)
    original_key: Optional[str] = Field(None, max_length=10)
    tempo_marking: Optional[str] = Field(None, max_length=50)
    genre: Optional[str] = Field(None, max_length=50)
    time_signature: str = Field(default="4/4", max_length=10)
    year_composed: Optional[int] = None
    notes: Optional[str] = None
    source_file_name: Optional[str] = Field(None, max_length=255)
    source_file_type: Optional[str] = Field(None, max_length=20)


class SongCreate(SongBase):
    """Model for creating a new song."""
    pass


class SongUpdate(BaseModel):
    """Model for updating song data (all fields optional)."""
    title: Optional[str] = Field(None, max_length=200)
    composer: Optional[str] = Field(None, max_length=200)
    arranger: Optional[str] = Field(None, max_length=200)
    original_key: Optional[str] = Field(None, max_length=10)
    tempo_marking: Optional[str] = Field(None, max_length=50)
    genre: Optional[str] = Field(None, max_length=50)
    time_signature: Optional[str] = Field(None, max_length=10)
    year_composed: Optional[int] = None
    notes: Optional[str] = None


class Song(SongBase):
    """Complete song model with database fields."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# =============================================
# Section Models
# =============================================

class SectionBase(BaseModel):
    """Base model for Section data."""
    song_id: int
    name: str = Field(..., max_length=50)
    section_order: int
    repeat_count: int = 1
    notes: Optional[str] = Field(None, max_length=500)


class SectionCreate(SectionBase):
    """Model for creating a new section."""
    pass


class Section(SectionBase):
    """Complete section model with database ID."""
    id: int
    
    class Config:
        from_attributes = True


# =============================================
# Measure Models
# =============================================

class MeasureBase(BaseModel):
    """Base model for Measure data."""
    section_id: int
    measure_number: int


class MeasureCreate(MeasureBase):
    """Model for creating a new measure."""
    pass


class Measure(MeasureBase):
    """Complete measure model with database fields."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# =============================================
# Chord Models
# =============================================

class ChordBase(BaseModel):
    """Base model for Chord data."""
    measure_id: int
    beat_position: Decimal = Decimal("1.0")
    chord_symbol: str = Field(..., max_length=20)
    roman_numeral: Optional[str] = Field(None, max_length=20)
    key_center: Optional[str] = Field(None, max_length=20)
    function_label: Optional[str] = Field(None, max_length=50)
    comments: Optional[str] = Field(None, max_length=500)
    chord_order: int


class ChordCreate(ChordBase):
    """Model for creating a new chord."""
    pass


class Chord(ChordBase):
    """Complete chord model with database ID."""
    id: int
    
    class Config:
        from_attributes = True


# =============================================
# Vocabulary Models
# =============================================

class ChordVocabulary(BaseModel):
    """Chord vocabulary for standardized notation."""
    id: int
    canonical_symbol: str = Field(..., max_length=20)
    display_name: Optional[str] = Field(None, max_length=30)
    chord_type: Optional[str] = Field(None, max_length=30)
    intervals: Optional[str] = Field(None, max_length=50)
    aliases: Optional[str] = Field(None, max_length=200)
    
    class Config:
        from_attributes = True


class RomanNumeralVocabulary(BaseModel):
    """Roman numeral vocabulary for standardized notation."""
    id: int
    canonical_symbol: str = Field(..., max_length=20)
    scale_degree: Optional[int] = None
    quality: Optional[str] = Field(None, max_length=30)
    function_type: Optional[str] = Field(None, max_length=30)
    
    class Config:
        from_attributes = True


# =============================================
# Melody Models
# =============================================

class MelodyNoteBase(BaseModel):
    """Base model for melody notes."""
    song_id: int
    measure_number: Optional[int] = None
    beat_position: Optional[Decimal] = None
    midi_note: Optional[int] = None
    duration: Optional[Decimal] = None
    velocity: Optional[int] = None


class MelodyNote(MelodyNoteBase):
    """Complete melody note model."""
    id: int
    
    class Config:
        from_attributes = True


# =============================================
# Progress Models
# =============================================

class UserSongProgressBase(BaseModel):
    """Base model for user progress."""
    user_id: int
    song_id: int
    last_practiced: Optional[datetime] = None
    times_practiced: int = 0
    accuracy_rate: Optional[Decimal] = None
    mastery_level: int = 0
    notes: Optional[str] = Field(None, max_length=500)


class UserSongProgressCreate(BaseModel):
    """Model for creating/updating progress."""
    user_id: int
    song_id: int


class UserSongProgress(UserSongProgressBase):
    """User progress tracking per song."""
    id: int
    
    class Config:
        from_attributes = True


class ProgressResponse(BaseModel):
    """Response model with song title."""
    song_id: int
    song_title: str
    last_practiced: Optional[datetime]
    times_practiced: int
    accuracy_rate: Optional[float]
    mastery_level: int


# =============================================
# Quiz Models
# =============================================

class QuizQuestion(BaseModel):
    """Single quiz question."""
    measure_number: int
    beat_position: float
    is_blank: bool
    displayed_chord: Optional[str] = None


class QuizGenerate(BaseModel):
    """Request to generate a quiz."""
    song_id: int
    section_id: Optional[int] = None
    blank_percentage: float = 0.3
    num_questions: Optional[int] = None
    

class QuizSubmission(BaseModel):
    """User's quiz answers."""
    attempt_id: int
    answers: List[str]


class QuizResult(BaseModel):
    """Quiz results."""
    attempt_id: int
    total_questions: int
    correct_answers: int
    accuracy: float
    details: List[dict]


class QuizAttemptBase(BaseModel):
    """Base model for quiz attempts."""
    user_id: int
    song_id: int
    quiz_type: Optional[str] = Field(None, max_length=30)
    section_id: Optional[int] = None


class QuizAttempt(QuizAttemptBase):
    """Complete quiz attempt model."""
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_questions: Optional[int] = None
    correct_answers: Optional[int] = None
    details: Optional[str] = None
    
    class Config:
        from_attributes = True


# =============================================
# Composite Models (with relationships)
# =============================================

class ChordWithMeasure(Chord):
    """Chord with measure context."""
    measure_number: int


class MeasureWithChords(Measure):
    """Measure with all its chords."""
    chords: List[Chord] = []


class SectionWithMeasures(Section):
    """Section with all measures and chords."""
    measures: List[MeasureWithChords] = []


class SongDetail(Song):
    """Complete song with all sections, measures, and chords."""
    sections: List[SectionWithMeasures] = []
