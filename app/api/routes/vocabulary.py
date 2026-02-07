"""
Vocabulary API Routes

Endpoints for chord symbols and roman numerals vocabulary.
"""
from typing import List
from fastapi import APIRouter, Depends
from app.models import ChordVocabulary, RomanNumeralVocabulary
from app.db.connection import DatabaseConnection, get_db


router = APIRouter(prefix="/api/v1/vocabulary", tags=["vocabulary"])


@router.get("/chord-symbols", response_model=List[ChordVocabulary])
async def get_chord_symbols(db: DatabaseConnection = Depends(get_db)):
    """
    Get all chord symbols for dropdown menus.
    
    Returns standardized chord notation vocabulary.
    """
    query = "SELECT * FROM ChordVocabulary ORDER BY canonical_symbol"
    return db.execute_query(query)


@router.get("/roman-numerals", response_model=List[RomanNumeralVocabulary])
async def get_roman_numerals(db: DatabaseConnection = Depends(get_db)):
    """
    Get all roman numerals for dropdown menus.
    
    Returns standardized roman numeral vocabulary.
    """
    query = "SELECT * FROM RomanNumeralVocabulary ORDER BY canonical_symbol"
    return db.execute_query(query)
