# Team Management Implementation Plan

## Overview

This document outlines a comprehensive implementation plan for adding full team management capabilities to the CLI-Unites project, leveraging the existing Supabase schema to transform it from a personal note-taking tool into a collaborative team platform.

## Current State Analysis

### Existing Infrastructure
- ✅ **Supabase Schema**: Complete team/user/project structure in database
- ✅ **Authentication**: OAuth flow with GitHub via Supabase Auth
- ✅ **Database Layer**: Basic Supabase client with note operations
- ✅ **Configuration**: Team ID storage in local config
- ✅ **Basic Commands**: `team --set`, `team --recent`, `team` (view current)

### Current Limitations
- ❌ **No Team CRUD**: Can't create, list, or manage teams
- ❌ **No User Management**: No team membership or user relationships
- ❌ **String-based Teams**: Teams are just string IDs, not database entities
- ❌ **No Permissions**: No access control or team-based permissions
- ❌ **Limited Collaboration**: No shared visibility or team features

## Implementation Phases

### Phase 1: Core Team Management (Week 1-2)

#### 1.1 Enhanced Database Layer
**File**: `cli_unites/core/db.py`

Add comprehensive team management methods to the `Database` class:

```python
# Team Management
def create_team(self, name: str, description: str = None) -> str
def get_team(self, team_id: str) -> Optional[Dict[str, Any]]
def list_user_teams(self, user_id: str) -> List[Dict[str, Any]]
def update_team(self, team_id: str, **updates) -> bool
def delete_team(self, team_id: str) -> bool

# User-Team Relationships
def add_user_to_team(self, user_id: str, team_id: str, role: str = "member") -> bool
def remove_user_from_team(self, user_id: str, team_id: str) -> bool
def get_team_members(self, team_id: str) -> List[Dict[str, Any]]
def get_user_teams(self, user_id: str) -> List[Dict[str, Any]]

# Team-based Queries
def list_notes_for_team(self, team_id: str, limit: int = None) -> List[Dict[str, Any]]
def search_team_notes(self, team_id: str, query: str) -> List[Dict[str, Any]]
def get_team_activity(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]
```

#### 1.2 User Management Integration
**File**: `cli_unites/core/auth.py`

Enhance authentication to work with the users table:

```python
def ensure_user_exists(self, user_data: Dict[str, Any]) -> str:
    """Ensure user exists in our users table, create if not."""
    
def get_current_user_id(self) -> Optional[str]:
    """Get current authenticated user ID from Supabase Auth."""
    
def refresh_user_session(self) -> bool:
    """Refresh expired authentication tokens."""
```

#### 1.3 Enhanced Team Commands (Simplified)
**File**: `cli_unites/commands/team.py`

Replace the basic team command with streamlined team management:

```bash
# Team CRUD Operations (using names, UUIDs auto-resolved)
notes team create "Team Name" [--description "Description"]
notes team list [--mine] [--all]
notes team show <team_name_or_id>
notes team update <team_name_or_id> --name "New Name" [--description "New Description"]
notes team delete <team_name_or_id> [--confirm]

# Team Membership (simplified with invite codes)
notes team invite <email> [--role member|admin]  # Invites to current team
notes team members [<team_name_or_id>]
notes team leave [<team_name_or_id>] [--confirm]
notes team remove <user_id> [--confirm]  # Removes from current team

# Team Context (with smart name resolution)
notes team switch <team_name_or_id>
notes team current
notes team recent

# Invitation Management (consolidated under team)
notes team invitations [--team <team_name_or_id>]  # List invitations
notes team join <invite_code>  # Accept invitation (creates team if needed)
```

**Key UX Improvements:**
- **Name-based commands**: Users can use team names instead of UUIDs
- **Current team context**: Commands default to current team when possible
- **Invite codes**: Simple codes instead of complex UUID-based invitations
- **Consolidated commands**: Fewer command groups, more intuitive

#### 1.4 Configuration Updates
**File**: `cli_unites/core/config.py`

Add team-related configuration options:

```python
DEFAULT_CONFIG.update({
    "current_team_id": None,  # UUID of current team
    "team_membership_cache": {},  # Cache user's teams
    "team_permissions": {},  # Cache team permissions
    "last_team_sync": None,  # Timestamp of last team sync
})
```

### Phase 1.5: Email Service Integration with Resend (Week 2.5)

#### 1.5.1 Email Service Configuration
**File**: `cli_unites/core/config.py`

Add Resend email service configuration:

```python
DEFAULT_CONFIG.update({
    # Email service configuration
    "email_service": "resend",  # resend, supabase, sendgrid, aws_ses, postmark
    "resend_api_key": os.getenv("RESEND_API_KEY"),
    "email_from_address": os.getenv("CLI_UNITES_EMAIL_FROM"),
    "email_from_name": "CLI-Unites",
    "email_templates_enabled": True,
    "email_notifications_enabled": True,
    "email_domain": None,  # Custom domain for Resend (optional)
})
```

#### 1.5.2 Simplified Email Service with Invite Codes
**File**: `cli_unites/core/email.py` (new)

Create email service focused on invite codes:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import resend

class EmailService(ABC):
    @abstractmethod
    def send_invitation_email(self, email: str, team_name: str, inviter_name: str, invite_code: str) -> bool:
        pass
    
    @abstractmethod
    def send_welcome_email(self, email: str, team_name: str) -> bool:
        pass

class ResendEmailService(EmailService):
    def __init__(self, api_key: str, from_address: str, from_name: str = "CLI-Unites"):
        self.api_key = api_key
        self.from_address = from_address
        self.from_name = from_name
        resend.api_key = api_key
    
    def send_invitation_email(self, email: str, team_name: str, inviter_name: str, invite_code: str) -> bool:
        """Send team invitation email with simple invite code."""
        try:
            params = {
                "from": f"{self.from_name} <{self.from_address}>",
                "to": [email],
                "subject": f"You've been invited to join {team_name}",
                "html": self._render_invitation_template(team_name, inviter_name, invite_code),
                "text": self._render_invitation_template_text(team_name, inviter_name, invite_code)
            }
            resend.Emails.send(params)
            return True
        except Exception as e:
            print(f"Failed to send invitation email: {e}")
            return False
    
    def send_welcome_email(self, email: str, team_name: str) -> bool:
        """Send welcome email after joining team."""
        try:
            params = {
                "from": f"{self.from_name} <{self.from_address}>",
                "to": [email],
                "subject": f"Welcome to {team_name}!",
                "html": self._render_welcome_template(team_name),
                "text": self._render_welcome_template_text(team_name)
            }
            resend.Emails.send(params)
            return True
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
            return False
    
    def _render_invitation_template(self, team_name: str, inviter_name: str, invite_code: str) -> str:
        """Render HTML invitation email template with invite code."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Team Invitation - CLI-Unites</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>You've been invited to join {team_name}!</h2>
            <p>Hi there,</p>
            <p>{inviter_name} has invited you to join the <strong>"{team_name}"</strong> team on CLI-Unites.</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                <h3>Your Invite Code:</h3>
                <code style="background-color: #e9ecef; padding: 15px; border-radius: 4px; font-size: 24px; font-weight: bold; display: block; margin: 10px 0; letter-spacing: 2px;">
                    {invite_code}
                </code>
                <p>Run this command to join:</p>
                <code style="background-color: #e9ecef; padding: 10px; border-radius: 4px; display: block; margin: 10px 0;">
                    notes team join {invite_code}
                </code>
            </div>
            
            <p><strong>First time using CLI-Unites?</strong></p>
            <ol>
                <li>Install: <code>pip install cli-unites</code></li>
                <li>Join team: <code>notes team join {invite_code}</code></li>
            </ol>
            
            <p style="color: #6c757d; font-size: 14px;">
                This invitation expires in 7 days.
            </p>
            
            <hr style="margin: 30px 0;">
            <p style="color: #6c757d; font-size: 14px;">
                Best regards,<br>
                The CLI-Unites Team
            </p>
        </body>
        </html>
        """
    
    def _render_invitation_template_text(self, team_name: str, inviter_name: str, invite_code: str) -> str:
        """Render plain text invitation email template."""
        return f"""
You've been invited to join {team_name}!

Hi there,

{inviter_name} has invited you to join the "{team_name}" team on CLI-Unites.

Your Invite Code: {invite_code}

To join the team, run:
notes team join {invite_code}

First time using CLI-Unites?
1. Install: pip install cli-unites
2. Join team: notes team join {invite_code}

This invitation expires in 7 days.

Best regards,
The CLI-Unites Team
        """
    
    def _render_welcome_template(self, team_name: str) -> str:
        """Render HTML welcome email template."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to {team_name} - CLI-Unites</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Welcome to {team_name}!</h2>
            <p>Hi there,</p>
            <p>Welcome to the <strong>"{team_name}"</strong> team! You can now:</p>
            
            <ul>
                <li>Add notes: <code>notes add "My Note"</code></li>
                <li>List team notes: <code>notes list</code></li>
                <li>Search notes: <code>notes search "keyword"</code></li>
                <li>See team activity: <code>notes activity</code></li>
            </ul>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Get started:</h3>
                <code style="background-color: #e9ecef; padding: 10px; border-radius: 4px; display: block;">
                    notes help
                </code>
            </div>
            
            <p>Happy collaborating!</p>
            
            <hr style="margin: 30px 0;">
            <p style="color: #6c757d; font-size: 14px;">
                Best regards,<br>
                The CLI-Unites Team
            </p>
        </body>
        </html>
        """
    
    def _render_welcome_template_text(self, team_name: str) -> str:
        """Render plain text welcome email template."""
        return f"""
Welcome to {team_name}!

Hi there,

Welcome to the "{team_name}" team! You can now:

- Add notes: notes add "My Note"
- List team notes: notes list
- Search notes: notes search "keyword"
- See team activity: notes activity

Get started: notes help

Happy collaborating!

Best regards,
The CLI-Unites Team
        """

def get_email_service() -> Optional[EmailService]:
    """Get configured email service instance."""
    from .config import ConfigManager
    config = ConfigManager()
    
    if not config.get("email_notifications_enabled", False):
        return None
    
    service_type = config.get("email_service", "resend")
    
    if service_type == "resend":
        api_key = config.get("resend_api_key")
        from_address = config.get("email_from_address")
        from_name = config.get("email_from_name", "CLI-Unites")
        
        if not api_key or not from_address:
            return None
            
        return ResendEmailService(api_key, from_address, from_name)
    
    return None
```

#### 1.5.3 Email Configuration Commands
**File**: `cli_unites/commands/email.py` (new)

Simple email configuration commands:

```python
from __future__ import annotations

import click
from ..core import console, print_success, print_error, print_warning
from ..core.config import ConfigManager
from ..core.email import get_email_service

@click.group(name="email")
def email_group():
    """Configure email service for team invitations."""
    pass

@email_group.command(name="setup")
@click.option("--api-key", help="Resend API key")
@click.option("--from-address", help="From email address")
@click.option("--from-name", default="CLI-Unites", help="From name")
def setup_email(api_key: str, from_address: str, from_name: str):
    """Configure Resend email service for team invitations."""
    manager = ConfigManager()
    
    if not api_key:
        api_key = click.prompt("Enter your Resend API key", hide_input=True)
    
    if not from_address:
        from_address = click.prompt("Enter your from email address")
    
    # Save configuration
    updates = {
        "email_service": "resend",
        "resend_api_key": api_key,
        "email_from_address": from_address,
        "email_from_name": from_name,
        "email_notifications_enabled": True,
        "email_templates_enabled": True
    }
    
    manager.update(updates)
    print_success("Email service configured! Team invitations will now send emails.")

@email_group.command(name="test")
@click.option("--to", help="Test email address")
def test_email(to: str):
    """Send a test invitation email."""
    email_service = get_email_service()
    
    if not email_service:
        print_error("Email service not configured. Run 'notes email setup' first.")
        return
    
    if not to:
        to = click.prompt("Enter test email address")
    
    success = email_service.send_invitation_email(
        to, 
        "Test Team", 
        "Test User", 
        "TEST123"
    )
    
    if success:
        print_success(f"Test email sent to {to}")
    else:
        print_error("Failed to send test email")

@email_group.command(name="status")
def email_status():
    """Show current email service configuration."""
    manager = ConfigManager()
    
    service_type = manager.get("email_service", "none")
    enabled = manager.get("email_notifications_enabled", False)
    from_address = manager.get("email_from_address")
    
    console.print(f"Email Service: {service_type}")
    console.print(f"Enabled: {'Yes' if enabled else 'No'}")
    console.print(f"From Address: {from_address or 'Not set'}")
    
    if enabled:
        email_service = get_email_service()
        if email_service:
            print_success("Email service is properly configured")
        else:
            print_warning("Email service configuration is incomplete")

@email_group.command(name="disable")
def disable_email():
    """Disable email notifications (invitations will show codes only)."""
    manager = ConfigManager()
    manager.set("email_notifications_enabled", False)
    print_success("Email notifications disabled")

@email_group.command(name="enable")
def enable_email():
    """Enable email notifications."""
    manager = ConfigManager()
    manager.set("email_notifications_enabled", True)
    print_success("Email notifications enabled")
```

#### 1.5.4 Enhanced Team Commands with Email Integration
**File**: `cli_unites/commands/team.py`

Update team commands to integrate with email service:

```python
def send_invitation_with_email(email: str, role: str = "member") -> str:
    """Send team invitation with email notification and invite code."""
    from ..core.email import get_email_service
    from ..core.db import get_connection
    from ..core.config import ConfigManager
    
    manager = ConfigManager()
    current_team_id = manager.get("current_team_id")
    
    if not current_team_id:
        print_error("No team selected. Run 'notes team switch <team>' first.")
        return None
    
    # Generate simple invite code
    import random
    import string
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # Create invitation in database
    with get_connection() as db:
        invitation_id = db.create_team_invitation(email, current_team_id, role, invite_code)
        
        # Get team and inviter details
        team = db.get_team(current_team_id)
        current_user = db.get_current_user()
        
        # Send email notification
        email_service = get_email_service()
        if email_service and team and current_user:
            email_sent = email_service.send_invitation_email(
                email=email,
                team_name=team["name"],
                inviter_name=current_user.get("full_name", current_user.get("email", "Unknown")),
                invite_code=invite_code
            )
            
            if email_sent:
                print_success(f"Invitation sent to {email} via email")
                print_success(f"Invite code: {invite_code}")
            else:
                print_warning(f"Email failed, but invitation created")
                print_success(f"Share this invite code: {invite_code}")
        else:
            print_success(f"Invitation created (no email configured)")
            print_success(f"Share this invite code: {invite_code}")
    
    return invite_code

def accept_invitation_with_welcome(invite_code: str) -> bool:
    """Accept invitation and send welcome email."""
    from ..core.email import get_email_service
    from ..core.db import get_connection
    
    with get_connection() as db:
        # Accept invitation
        success = db.accept_team_invitation(invite_code)
        
        if success:
            # Get team details for welcome email
            team = db.get_team(success["team_id"])
            user_email = success["user_email"]
            
            # Send welcome email
            email_service = get_email_service()
            if email_service and team:
                email_service.send_welcome_email(user_email, team["name"])
            
            print_success(f"Joined team: {team['name'] if team else 'Unknown'}")
            return True
        else:
            print_error("Invalid or expired invite code")
            return False
```

### Phase 2: Enhanced Collaboration Features (Week 3-4)

#### 2.1 Team-based Note Operations (Enhanced)
**Files**: `cli_unites/commands/add.py`, `cli_unites/commands/list.py`, `cli_unites/commands/search.py`

Enhance existing commands to work with teams using smart defaults:

```bash
# Add notes (auto-detects team from current context)
notes add "Title" [--team <team_name_or_id>] [--project "Project Name"]

# List team notes (defaults to current team)
notes list [--team <team_name_or_id>] [--member <user_id>] [--project "Project Name"]

# Search across team content (defaults to current team)
notes search "query" [--team <team_name_or_id>] [--semantic] [--all-teams]

# Team activity feed (defaults to current team)
notes activity [--team <team_name_or_id>] [--limit 10] [--member <user_id>]
```

**Smart Defaults:**
- Commands default to current team when no team specified
- Projects are auto-created from git context when adding notes
- `--all-teams` flag for searching across all teams
- Team names are resolved to UUIDs automatically

#### 2.2 Project Management Integration (Auto-managed)
**File**: `cli_unites/commands/project.py` (new)

Add minimal project management with auto-creation:

```bash
# Project Management (projects auto-created from git context)
notes project list [--team <team_name_or_id>]  # Show all projects
notes project show <project_name_or_path>      # Show specific project
notes project link <project_name> --path "/absolute/path"  # Manually link project

# Project Context (optional - defaults to git context)
notes project switch <project_name_or_path>
notes project current
```

**Auto-Project Creation:**
- Projects are automatically created when adding notes in a git repository
- Project name defaults to repository name
- Path is auto-detected from git root
- Manual project creation only needed for non-git directories

#### 2.3 Team Activity and Analytics
**File**: `cli_unites/commands/analytics.py` (new)

Add team analytics and insights:

```bash
# Team Analytics
notes analytics team <team_id> [--period week|month|year]
notes analytics user <user_id> [--team <team_id>]
notes analytics projects --team <team_id>
notes analytics tags --team <team_id> [--popularity]
```

### Phase 3: Advanced Features (Week 5-6)

#### 3.1 Real-time Collaboration
**File**: `cli_unites/core/realtime.py` (enhance existing)

Extend realtime capabilities for team collaboration:

```python
class TeamRealtimeClient:
    def subscribe_to_team_activity(self, team_id: str, callback: Callable)
    def subscribe_to_team_notes(self, team_id: str, callback: Callable)
    def subscribe_to_project_updates(self, project_id: str, callback: Callable)
    def broadcast_typing_indicator(self, team_id: str, user_id: str)
    def send_team_notification(self, team_id: str, message: str)
```

#### 3.2 Team Permissions and Roles
**File**: `cli_unites/core/permissions.py` (new)

Implement role-based access control:

```python
class TeamPermissions:
    ROLES = {
        "owner": ["read", "write", "admin", "delete"],
        "admin": ["read", "write", "admin"],
        "member": ["read", "write"],
        "viewer": ["read"]
    }
    
    def check_permission(self, user_id: str, team_id: str, action: str) -> bool
    def get_user_role(self, user_id: str, team_id: str) -> str
    def update_user_role(self, user_id: str, team_id: str, role: str) -> bool
```

#### 3.3 Team Invitations (Simplified with Codes)
**File**: `cli_unites/commands/team.py` (integrated)

Enhanced invitation system with simple codes:

```bash
# Invitation Management (consolidated under team commands)
notes team invite <email> [--role member|admin]  # Send invitation with code
notes team invitations [--team <team_name_or_id>]  # List invitations
notes team join <invite_code>  # Accept invitation (one-step process)
notes team leave [<team_name_or_id>] [--confirm]  # Leave team
```

**Simplified Invitation Flow:**
1. **Admin sends**: `notes team invite user@email.com`
   - Generates simple 6-8 character invite code (e.g., `ABC123`)
   - Sends email with code and instructions
   - Shows code in CLI for manual sharing

2. **User accepts**: `notes team join ABC123`
   - Automatically creates user account if needed
   - Joins team and switches to it
   - Sends welcome email

**Benefits:**
- No complex UUIDs to remember
- Single command to accept invitation
- Works offline (manual code sharing)
- Clear success/failure feedback

### Phase 4: UI/UX Enhancements (Week 7-8)

#### 4.1 Rich Team Interfaces
**File**: `cli_unites/core/output.py`

Add team-specific UI components:

```python
def render_team_panel(team: Dict[str, Any]) -> Panel
def render_team_list(teams: List[Dict[str, Any]]) -> Table
def render_team_members(members: List[Dict[str, Any]]) -> Table
def render_team_activity(activities: List[Dict[str, Any]]) -> Table
def render_invitation_panel(invitation: Dict[str, Any]) -> Panel
```

#### 4.2 Interactive Team Selection
**File**: `cli_unites/commands/team.py`

Add interactive team selection:

```python
@click.command(name="team")
@click.option("--interactive", "-i", is_flag=True, help="Interactive team selection")
def team_interactive():
    """Interactive team management interface."""
    # Show rich interface with team selection, member management, etc.
```

#### 4.3 Enhanced Team Onboarding Flow
**File**: `cli_unites/core/onboarding.py`

Comprehensive onboarding with authentication-first approach:

```python
def _guided_team_onboarding(manager: ConfigManager) -> None:
    """Enhanced onboarding flow: Auth → Team → First Note → Collaboration"""
    
    # Step 1: Authentication (required for teams)
    if not _ensure_authenticated():
        return
        
    # Step 2: Team Setup
    team_choice = _prompt_team_setup()
    
    if team_choice == "join":
        _join_existing_team()
    elif team_choice == "create":
        _create_new_team()
    else:
        _skip_team_setup()
    
    # Step 3: First Note (existing)
    note = _capture_first_note(manager, team_id)
    
    # Step 4: Collaboration Features
    _show_collaboration_highlights(manager, team_id, note)

def _ensure_authenticated() -> bool:
    """Ensure user is authenticated before team features."""
    # Check if already authenticated
    # If not, guide through login process
    # Return True if authenticated, False if skipped
    
def _prompt_team_setup() -> str:
    """Ask user about team collaboration preferences."""
    # "Do you want to collaborate with a team?"
    # Options: join existing, create new, skip for now
```

**New Onboarding Flow:**
1. **Authentication First**: User must be logged in for team features
2. **Team Choice**: Join existing team or create new one
3. **Invite Code Flow**: Simple codes for joining teams
4. **First Note**: Capture note in team context
5. **Collaboration Demo**: Show team features and next steps

**Authentication Indicators:**
- Clear messaging about what requires authentication
- Graceful fallback for offline users
- Visual indicators for authenticated vs offline features

## Database Schema Utilization

### Leveraging Existing Tables

1. **`teams`**: Store team information with names and metadata
2. **`users`**: Link to Supabase Auth users with additional profile data
3. **`users_teams`**: Manage team membership with roles and join dates
4. **`projects`**: Organize notes by projects within teams
5. **`paths`**: Provide hierarchical organization within projects
6. **`notes`**: Link notes to users, projects, and teams
7. **`tags`**: Enable cross-team tag sharing and organization
8. **`messages`**: Support team messaging and notifications

### New Tables (if needed)

```sql
-- Team invitations (with simple codes)
CREATE TABLE team_invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  invited_by UUID REFERENCES users(id) ON DELETE CASCADE,
  role TEXT DEFAULT 'member',
  invite_code TEXT UNIQUE NOT NULL, -- Simple 6-8 character code (e.g., ABC123)
  status TEXT DEFAULT 'pending', -- pending, accepted, declined, cancelled
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast invite code lookup
CREATE INDEX ON team_invitations(invite_code);
CREATE INDEX ON team_invitations(email);

-- Team roles and permissions
CREATE TABLE team_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL, -- owner, admin, member, viewer
  granted_by UUID REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(team_id, user_id)
);

-- Team activity log
CREATE TABLE team_activity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  action TEXT NOT NULL, -- note_created, member_joined, project_created, etc.
  target_type TEXT, -- note, user, project, etc.
  target_id UUID,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Implementation Priority

### High Priority (Must Have)
1. ✅ Enhanced team commands (create, list, show, switch) - **Simplified with name resolution**
2. ✅ User-team relationship management - **With invite codes**
3. ✅ Team-based note filtering and operations - **Smart defaults to current team**
4. ✅ Proper authentication integration - **Authentication-first onboarding**
5. ✅ Email service integration with Resend - **Invite code emails**

### Medium Priority (Should Have)
1. 🔄 Project management integration - **Auto-creation from git context**
2. 🔄 Team activity feeds - **With smart team defaults**
3. 🔄 Role-based permissions - **Simplified owner/admin/member/viewer**
4. 🔄 Rich team interfaces - **Interactive team selection**

### Low Priority (Nice to Have)
1. 📋 Advanced analytics and insights - **Team productivity metrics**
2. 📋 Real-time collaboration features - **Live updates and notifications**
3. 📋 Team messaging and notifications - **In-app communication**
4. 📋 Advanced project management - **Manual project linking**

## Testing Strategy

### Unit Tests
- Database operations for team management
- Permission checking logic
- Team-based query filtering
- Authentication and user management

### Integration Tests
- End-to-end team creation and management
- Team membership workflows
- Cross-team data isolation
- Real-time collaboration features

### User Acceptance Tests
- Team onboarding flow
- Collaborative note-taking scenarios
- Permission enforcement
- Multi-user team workflows

## Migration Strategy

### Backward Compatibility
- Existing team_id strings should map to team names
- Graceful migration of existing notes to proper team structure
- Fallback to string-based teams if database is unavailable

### Data Migration
1. Create teams table entries for existing team_id strings
2. Migrate existing notes to link with proper team UUIDs
3. Set up user accounts for existing users
4. Establish team memberships

## Security Considerations

### Row Level Security (RLS)
- Ensure team data isolation
- Prevent cross-team data access
- Secure team membership management
- Protect team invitation system

### Authentication
- JWT token validation for all team operations
- Secure team invitation links
- Role-based access control
- Audit logging for team actions

## Performance Considerations

### Caching Strategy
- Cache team membership information
- Cache team permissions locally
- Implement efficient team-based queries
- Use database indexes for team operations

### Scalability
- Efficient team-based pagination
- Optimized queries for large teams
- Background processing for team analytics
- Real-time updates without performance impact

## Success Metrics

### Functional Metrics
- ✅ Users can create and manage teams
- ✅ Team-based note organization works
- ✅ Multi-user collaboration is functional
- ✅ Permissions are properly enforced

### Performance Metrics
- Team operations complete in <200ms
- Real-time updates have <100ms latency
- Support for teams with 100+ members
- Handle 1000+ notes per team efficiently

### User Experience Metrics
- Intuitive team management interface
- Smooth onboarding for new team members
- Effective collaboration workflows
- Clear permission and role management

## UX Improvements Summary

### Key UX Enhancements Made

#### 1. **Simplified Command Structure**
- **Before**: 40+ commands across multiple namespaces
- **After**: ~20 commands with smart defaults and context awareness
- **Benefit**: Users can learn and remember the core commands more easily

#### 2. **Name-Based Team References**
- **Before**: Users had to remember UUIDs like `550e8400-e29b-41d4-a716-446655440000`
- **After**: Users can use team names like `backend-team` (UUIDs auto-resolved)
- **Benefit**: Intuitive and human-readable team references

#### 3. **Invite Code System**
- **Before**: Complex UUID-based invitation system
- **After**: Simple 6-character codes like `ABC123`
- **Benefit**: Easy to share verbally, type, and remember

#### 4. **Authentication-First Onboarding**
- **Before**: Team features available without authentication
- **After**: Clear authentication flow before team collaboration
- **Benefit**: Users understand what requires login vs works offline

#### 5. **Smart Defaults and Context**
- **Before**: Required explicit team specification for most operations
- **After**: Commands default to current team, auto-detect git context
- **Benefit**: Less typing, more intuitive workflow

#### 6. **Auto-Project Creation**
- **Before**: Manual project creation required
- **After**: Projects auto-created from git repositories
- **Benefit**: Zero-configuration project organization

#### 7. **Progressive Disclosure**
- **Before**: All commands shown at once
- **After**: Contextual help and command grouping
- **Benefit**: Users discover features gradually without overwhelm

### Command Count Reduction

| Phase | Original Commands | Simplified Commands | Reduction |
|-------|------------------|-------------------|-----------|
| **Team Management** | 15 commands | 10 commands | 33% |
| **Invitations** | 5 commands | 2 commands | 60% |
| **Projects** | 8 commands | 4 commands | 50% |
| **Email** | 5 commands | 5 commands | 0% |
| **Analytics** | 4 commands | 4 commands | 0% |
| **Total** | 37 commands | 25 commands | 32% |

### User Flow Improvements

#### **New User Journey**
1. **Install**: `pip install cli-unites`
2. **Onboard**: `notes onboarding` (guides through auth → team → first note)
3. **Authenticate**: GitHub OAuth flow
4. **Team Setup**: Choose to join existing or create new team
5. **First Note**: Add note in team context
6. **Collaborate**: Invite others with simple codes

#### **Team Invitation Flow**
1. **Admin**: `notes team invite user@email.com`
2. **System**: Generates code `ABC123`, sends email
3. **User**: `notes team join ABC123`
4. **System**: Joins team, sends welcome email
5. **User**: Ready to collaborate!

#### **Daily Workflow**
1. **Switch Team**: `notes team switch backend-team` (one time)
2. **Add Notes**: `notes add "Bug fix"` (auto-uses current team)
3. **Search**: `notes search "authentication"` (searches current team)
4. **Activity**: `notes activity` (shows current team activity)

## Timeline

- **Week 1-2**: Phase 1 - Core Team Management (Simplified)
- **Week 2.5**: Phase 1.5 - Email Service Integration with Resend
- **Week 3-4**: Phase 2 - Enhanced Collaboration Features
- **Week 5-6**: Phase 3 - Advanced Features
- **Week 7-8**: Phase 4 - UI/UX Enhancements
- **Week 9**: Testing, bug fixes, and documentation
- **Week 10**: Production deployment and monitoring

## Conclusion

This implementation plan transforms CLI-Unites from a personal note-taking tool into a comprehensive team collaboration platform while **significantly improving the user experience**. The key improvements include:

### **UX Achievements**
- **32% reduction** in total commands (37 → 25)
- **Simple invite codes** instead of complex UUIDs
- **Name-based team references** with automatic UUID resolution
- **Authentication-first onboarding** with clear offline/online boundaries
- **Smart defaults** that reduce typing and cognitive load
- **Auto-project creation** from git context
- **Progressive disclosure** to prevent command overwhelm

### **Maintained Principles**
- **Offline-first approach** preserved throughout
- **Developer-friendly simplicity** enhanced, not compromised
- **Git-like command patterns** for familiarity
- **Rich terminal UI** with clear feedback
- **Backward compatibility** with existing workflows

### **Enhanced Collaboration**
- **One-step invitation acceptance** with `notes team join ABC123`
- **Professional email integration** with Resend
- **Team context awareness** in all commands
- **Real-time collaboration** capabilities
- **Role-based permissions** system

The phased approach ensures incremental value delivery while building toward a full-featured team management system that developers will love to use. The focus on UX improvements ensures that the enhanced functionality doesn't come at the cost of the tool's core simplicity and ease of use.
