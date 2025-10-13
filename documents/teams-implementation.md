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

#### 1.3 Enhanced Team Commands
**File**: `cli_unites/commands/team.py`

Replace the basic team command with comprehensive team management:

```bash
# Team CRUD Operations
notes team create "Team Name" [--description "Description"]
notes team list [--mine] [--all]
notes team show <team_id>
notes team update <team_id> --name "New Name" [--description "New Description"]
notes team delete <team_id> [--confirm]

# Team Membership
notes team invite <email> --team <team_id> [--role member|admin]
notes team members <team_id>
notes team leave <team_id> [--confirm]
notes team remove <user_id> --team <team_id> [--confirm]

# Team Context
notes team switch <team_id>
notes team current
notes team recent
```

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

### Phase 2: Enhanced Collaboration Features (Week 3-4)

#### 2.1 Team-based Note Operations
**Files**: `cli_unites/commands/add.py`, `cli_unites/commands/list.py`, `cli_unites/commands/search.py`

Enhance existing commands to work with teams:

```bash
# Add notes to specific teams
notes add "Title" --team <team_id> [--project "Project Name"]

# List team notes
notes list --team <team_id> [--project "Project Name"] [--member <user_id>]

# Search across team content
notes search "query" --team <team_id> [--semantic] [--project "Project Name"]

# Team activity feed
notes activity --team <team_id> [--limit 10] [--member <user_id>]
```

#### 2.2 Project Management Integration
**File**: `cli_unites/commands/project.py` (new)

Add project management commands:

```bash
# Project Management
notes project create "Project Name" --team <team_id> --path "/absolute/path"
notes project list [--team <team_id>]
notes project show <project_id>
notes project update <project_id> --name "New Name" [--path "/new/path"]
notes project delete <project_id> [--confirm]

# Project Context
notes project switch <project_id>
notes project current
```

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

#### 3.3 Team Invitations
**File**: `cli_unites/commands/invite.py` (new)

Add invitation system:

```bash
# Invitation Management
notes invite send <email> --team <team_id> [--role member|admin]
notes invite list [--team <team_id>] [--status pending|accepted|declined]
notes invite accept <invite_id>
notes invite decline <invite_id>
notes invite cancel <invite_id>
```

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

#### 4.3 Team Onboarding Flow
**File**: `cli_unites/core/onboarding.py`

Enhance onboarding to include team setup:

```python
def _setup_team_collaboration(manager: ConfigManager) -> None:
    """Guide user through team setup and collaboration features."""
    
def _invite_team_members(manager: ConfigManager, team_id: str) -> None:
    """Help user invite team members."""
```

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
-- Team invitations
CREATE TABLE team_invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  invited_by UUID REFERENCES users(id) ON DELETE CASCADE,
  role TEXT DEFAULT 'member',
  status TEXT DEFAULT 'pending', -- pending, accepted, declined, cancelled
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

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
1. ✅ Enhanced team commands (create, list, show, switch)
2. ✅ User-team relationship management
3. ✅ Team-based note filtering and operations
4. ✅ Proper authentication integration

### Medium Priority (Should Have)
1. 🔄 Project management integration
2. 🔄 Team activity feeds
3. 🔄 Role-based permissions
4. 🔄 Rich team interfaces

### Low Priority (Nice to Have)
1. 📋 Team invitations system
2. 📋 Real-time collaboration features
3. 📋 Advanced analytics and insights
4. 📋 Team messaging and notifications

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

## Timeline

- **Week 1-2**: Phase 1 - Core Team Management
- **Week 3-4**: Phase 2 - Enhanced Collaboration
- **Week 5-6**: Phase 3 - Advanced Features
- **Week 7-8**: Phase 4 - UI/UX Enhancements
- **Week 9**: Testing, bug fixes, and documentation
- **Week 10**: Production deployment and monitoring

## Conclusion

This implementation plan transforms CLI-Unites from a personal note-taking tool into a comprehensive team collaboration platform while maintaining its simplicity and offline-first approach. The phased approach ensures incremental value delivery while building toward a full-featured team management system.
