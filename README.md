# Reddit Insight

A personal, non-commercial research tool for reading and analyzing 
public Reddit discussions.

## Purpose

This tool fetches public posts and comments from selected subreddits 
via Reddit's official Data API for personal research and analysis.

## Features

- Read-only access to public Reddit posts and comments
- Data stored locally for offline analysis
- Respects Reddit API rate limits
- OAuth2 authentication

## Technical Stack

- **Language**: Python 3.12+
- **Reddit API**: AsyncPRAW (official async Reddit API wrapper)
- **Database**: SQLite (local storage)
- **Backend**: FastAPI

## Usage Scope

- Personal/research use only
- No commercial purpose
- No data redistribution
- No AI/ML model training with Reddit data
- Compliant with Reddit's Data API Terms and Responsible Builder Policy

## API Usage

- Read-only operations (GET requests only)
- Low volume: ~30-50 requests per minute during active collection
- Periodic collection (a few times per week)
- Target: 3-5 specific subreddits

## Status

🚧 In early development
