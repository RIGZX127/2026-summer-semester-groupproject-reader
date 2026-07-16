# Mercury

A cross-platform AI-powered RSS reader.


# Project Goal

## Project Vision

Develop a simple, elegant and intelligent RSS reader application.

Mercury aims to help users efficiently collect, read and manage information
through traditional RSS technology combined with AI assistance.


## Core Goal

Build a local-first RSS reader that provides:

- RSS subscription and article reading
- AI-powered content understanding
- Personal knowledge management


# Key Features


## 1. RSS Reading System

The system should support:

- RSS Feed subscription
- OPML parsing
- Automatic article synchronization
- Article list and detail view
- Content cleaning and formatting


## 2. AI Assistant

The system should provide:

- Article summarization
- Article translation
- Support for different LLM providers
- LLM usage statistics


## 3. Knowledge Management

The system should support:

- Article notes
- Article export
- Article tags
- Tag-based article filtering
- AI-assisted tag generation


## 4. Auxiliary Features

The system should provide:

- Multi-language support
- Logging and debugging tools
- User-friendly error handling


# Architecture


## Design Principles

### Modular Architecture

The system should be divided into independent modules:

- RSS Module
- AI Module
- Data Module
- UI Module


Each module should have clear responsibilities
and communicate through well-defined interfaces.


### Local First

The application should:

- Store user data locally
- Require no account registration
- Avoid collecting user information


### AI Provider Independence

The AI system should support any LLM service
with standard API interfaces.


# Tech Stack


## Language

Python


## GUI Framework

PyQt6


Reason:

- Mature desktop application framework
- Cross-platform support
- Suitable for rapid development


## Database

SQLite


Reason:

- Lightweight
- Local storage
- No additional server required


## Main Libraries

RSS:

- feedparser


HTML Processing:

- BeautifulSoup


Markdown:

- markdownify


AI:

- OpenAI-compatible API


# Technical Constraints


## Platform Support

The application should support:

- Windows
- Linux
- macOS


## Privacy

The application should:

- Not require login
- Not actively collect user data


## Maintainability

The project should:

- Keep modules independent
- Avoid unnecessary complexity
- Maintain clear documentation


# Current Status


## Completed

- Requirement analysis
- Initial architecture design
- Technology selection


## Developing

- Basic RSS reading function
- GUI prototype
- Database structure


## Future

- AI functions
- Knowledge management
- Product optimization


# Roadmap


## Phase 1

Build basic RSS reader:

- RSS parsing
- Article display
- Local storage


## Phase 2

Add AI capabilities:

- Summary Agent
- Translation Agent


## Phase 3

Improve knowledge management:

- Notes
- Tags
- Export


## Phase 4

Product optimization:

- UI improvement
- Multi-language support
- Debugging tools
