# INTENT.md -- HarmonyLab

## Primary Intent
A tool for visualizing and memorizing chord progressions so Corey can sense harmonic movement in a song. Not theory reference. Not ear training. The goal is to see where a song moves harmonically, learn the progression from that visualization, and play it from memory.

## Success Is
- Corey can load a song, see its chord progressions and harmonic movement, and use that visualization to memorize the harmony.
- The chord analysis is accurate. When it's wrong, the underlying notes are visible for audit so bugs can be found and fixed.
- Corey can play American standards with right hand on melody plus harmony fill and left hand on bass rhythm. The harmony is learned from seeing the progression in HarmonyLab.
- MuseScore export produces a color-coded score with Roman numerals, key centers, and harmonic markup baked in. The score itself becomes the study tool (HL-015).
- Playback works measure by measure at the tempo of the score.

## Success Is NOT
- A music theory reference tool. Corey understands theory. He can read a score and play it. He needs harmonic movement visualization, not theory lessons.
- Ear training for chord quality recognition. Inexpensive tools already exist for that.
- A formal pedagogical system (Barry Harris, Mark Levine, etc.). Corey plays for fun and personal enjoyment. 18 years of lessons, never formal. Learning from lead sheets, scores, and trying to improvise.
- High-fidelity audio output. Computer playback quality is fine for confirming chord quality. The piano in the studio is for playing.

## Decision Boundaries
- Chord analysis accuracy is the top priority. HL-016 (show underlying notes) and HL-017 (store note timing) exist because the analysis has bugs. These are audit tools for fixing the analysis, not features for users.
- Song CRUD regression (rename/delete broken) must be fixed. Basic functionality before new features.
- MuseScore import (HL-008) matters because MuseScore is the score format Corey uses. MIDI already works.
- MuseScore export with annotations (HL-015) is the "adjacent possible." After analysis, the score becomes the study tool.
- Audio playback: add measure-by-measure playback at score tempo. Already has MIDI output.

## Anti-Goals
- Reinventing notation capabilities. MuseScore handles that. Export to MuseScore, don't rebuild it.
- Building for performing musicians or music students. This serves one jazz piano player.
- Gamification or practice tracking. Playing is the practice.
- Over-investing in audio quality. The two HD touchscreen monitors on the piano are for scores, not for HarmonyLab to compete with professional audio tools.

## This Project Serves Portfolio Intents
- Cognitive vitality: Understanding harmonic movement is an intellectual challenge that directly improves piano playing.
- Personal learning outcomes: Better harmony sense leads to better improvisation leads to more enjoyment at the piano.
- Creative exploration: Experimental. The technology is being figured out. The annotated MuseScore export is a frontier idea nobody else is doing.

## Communication Standards
8th grade reading level. Short sentences. No em dashes. No filler. Direct.

## Historical Context
Corey plays jazz piano with professional equipment in his home studio. Two 43-inch 4K monitors on the desk, two HD touchscreen monitors on the piano for paging through scores while playing. 18 years of weekly lessons. Can play many tunes by ear but wants to improve his sense of harmonic movement. HarmonyLab is experimental. The chord analysis has gotten pretty good in the past couple of weeks, but bugs remain. The jazz teacher has helped validate (and find mistakes in) the analysis.

## The Moment
Corey sits at the piano. An American standard is loaded in HarmonyLab. He can see the chord progression, the key centers, the transitions. He plays the melody with his right hand, fills in harmony, and his left hand handles bass rhythm. The harmony he's playing was learned from seeing the progression in HarmonyLab. That's the moment.
