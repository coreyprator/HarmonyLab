# Changelog

All notable changes to this methodology are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.5.0] - 2024-12-27

### Added
- **Meta-project structure**: Organized methodology into dedicated repository
- **Pre-Kickoff Checklist**: Standalone document for questions before kickoff
- **Sprint Checklists**: Separate checklists for Sprint 1 and Sprint 2
- **Deployment Checklist**: GCP verification steps
- **Document Templates**: TEST_PLAN, UI_DESIGN, USER_GUIDE templates
- **ArtForge Example**: Real-world kickoff document for reference

### Changed
- **Repository structure**: From single document to organized folder structure
- **Lessons learned**: Moved to dedicated LESSONS_LEARNED.md with detailed context

---

## [3.4.0] - 2024-12-27

### Added
- **Help Content Strategy** (Section 0.12): External link approach vs embedded docs
- **Definition of Done** (Section 0.16): Explicit completion criteria for both sprints

### Changed
- **Testing Philosophy**: Added distinction between happy path errors and system errors

---

## [3.3.0] - 2024-12-27

### Added
- **Testing Philosophy** (Section 0.11): Guidelines for what to test and error messages
- **Required Documentation** (Section 0.10): TEST_PLAN.md, UI_DESIGN.md, USER_GUIDE.md
- **Document Templates** (Sections 0.13-0.15): Starter templates for required docs

### Changed
- **Responsibility Matrix**: Added TEST_PLAN.md, UI_DESIGN.md, USER_GUIDE.md to Claude deliverables

---

## [3.2.0] - 2024-12-27

### Added
- **Sprint Planning Requirements** (Section 0.9): Two-sprint model defined
  - Sprint 1: Infrastructure & API
  - Sprint 2: Testing, UI/UX, Documentation

### Changed
- **Responsibility Matrix**: Clarified that VS Code AI implements tests in Sprint 2

---

## [3.1.0] - 2024-12-27

### Added
- **GitHub & Deployment Workflow** (Section 0.7): Git init, push, Cloud Run URL retrieval
- **Responsibility Matrix** (Section 0.8): Explicit task assignments

### Fixed
- **LL-007**: Git initialization now in VS Code AI responsibilities
- **LL-001**: Database user creation now in VS Code AI responsibilities

---

## [3.0.0] - 2024-12-27

### Added
- **Development & Testing Environment** (Section 0.5): NO LOCALHOST rule
- **Kickoff Document Variables** (Section 0.6): Standardized placeholders

### Changed
- **Major restructure**: Moved from implicit assumptions to explicit documentation
- **Workflow**: Established cloud-first development pattern

### Fixed
- **LL-006**: Added "No localhost servers" section

---

## [2.0.0] - 2024-12-27

### Added
- **Authentication Flow** (Section 0.3): Exact command order to avoid password prompts
- **SQL Execution Environment** (Section 0.4): Tool selection for GO statements
- **GCP Project Guidance** (Section 0.2): When to use shared vs dedicated projects

### Fixed
- **LL-002**: Authentication order documented
- **LL-003**: Project verification added
- **LL-005**: SQL tool selection documented

---

## [1.0.0] - 2024-12-27

### Added
- **Pre-Kickoff Questions** (Section 0.1): Questions Claude asks before generating kickoff
- **Initial Lessons Learned Log**: First entries from ArtForge development

### Notes
- First formal version of the methodology
- Based on accumulated experience from ArtForge, HarmonyLab planning, Etymython, Super-Flashcards

---

## Version Numbering

- **Major** (X.0.0): Significant restructuring or new phases
- **Minor** (0.X.0): New sections or features added
- **Patch** (0.0.X): Clarifications, typo fixes, minor updates

## Contributing

When adding changes:
1. Add entry under `[Unreleased]` section
2. When releasing, move to versioned section with date
3. Reference Lessons Learned entries (LL-XXX) where applicable
