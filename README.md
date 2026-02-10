# WriteWinged API

A collaborative writing platform backend

## What is WriteWinged?

WriteWinged reimagines creative writing as a dynamic, version-controlled experience. Similar to how development teams build software together, WriteWinged empowers writers to build stories collaboratively—with full version history, collaborative suggestions, and transparent ownership across contributions.
Whether you're a solo author tracking your creative iterations or a community building worlds together, WriteWinged provides the infrastructure for stories to grow, adapt, and improve through meaningful collaboration

## Core Concepts

- **Documents** are owned by a single author
- **Versions** represent authoritative snapshots of content
- **Contributors** may suggest changes but cannot directly mutate content
- **Proposals** act like pull requests — suggested changes awaiting review
- **Publishing** is an explicit intent, not a side effect
- **Merging** is a controlled operation with strict invariants

## Features

### Implemented

#### Authentication & Users

- Email/password registration
- Google OAuth login
- JWT-based authentication
- User profile management

#### Documents

- Create, read, update, delete (soft deletion)
- Ownership enforcement
- Visibility controls (public/private)
- Lifecycle states:
  - Active
  - Locked (readable, no writes)
  - Archived (immutable, unreadable)
- Mutability guards enforced at the service layer

#### Version Control

- Version creation with transactional locking
- Single draft invariant per document
- Publish / unpublish flows
- Strong consistency using row-level locks
- Illegal state prevention via service-level invariants

#### Collaboration

- Contributor invitations and revocation
- Owner-only management
- Immutable contribution history (no soft deletes)
- Archived documents preserve contributor history
- Contributors cannot directly create or publish versions

#### Proposals (Pull Request Model)

- Contributors submit proposals instead of editing directly
- Owners review, accept, or reject proposals
- Accepted proposals can be merged into new versions
- Merge operation is atomic and auditable
- Proposal lifecycle enforced via explicit states

## Current Status

**Yet to deploy**

**In Active Development**

This project is part of my journey learning backend development with FastAPI. It reflects a deep exploration of backend architecture, domain modeling, and professional engineering practices using FastAPI and SQLAlchemy.
