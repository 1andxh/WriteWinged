# WriteWinged API

A collaborative writing platform backend

## What is WriteWinged?

WriteWinged reimagines creative writing as a dynamic, version-controlled experience. Similar to how development teams build software together, WriteWinged empowers writers to build stories collaboratively—with full version history, collaborative suggestions, and transparent ownership across contributions.
Whether you're a solo author tracking your creative iterations or a community building worlds together, WriteWinged provides the infrastructure for stories to grow, adapt, and improve through meaningful collaboration

## Features

### ✅ Implemented

- **User Authentication**

  - Register with email/password
  - Login with Google OAuth
  - JWT-based sessions

- **User Profiles**

  - Profile information (name, bio, avatar)
  - Support for OAuth avatars and custom uploads

- **Documents**

  - CRUD operations for stories and articles
  - Public and private visibility controls
  - State management for lifecycle control (Active, Locked, Archived)
  - Soft deletion using timestamps to prevent accidental data loss
  - Advanced search with title-based filtering
  - Pagination logic (limit and offset) for optimized list retrieval
  - Mutability guards to prevent edits on archived or locked content

### In progress

- **Collaboration**

  - Invite other writers to collaborate
  - Different permission levels (owner, editor, contributor, reader)
  - Suggestion system (like pull requests)

- **Version Control**

  - Save versions of your work
  - View document history
  - Compare changes between versions
  - Rollback to previous versions

- **Discovery**
  - Browse public documents
  - Follow favorite writers
  - Search for stories

## Current Status

**In Active Development**

This project is part of my journey learning backend development with FastAPI. Currently implementing core authentication and will be adding collaborative writing features next.
