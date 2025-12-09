-- Life Assistant Database Schema
-- Extends Optimus to support personal life and work management
-- Version: 1.0.0
-- Created: 2024-11-29

-- =====================================================
-- Users Table - Single user for now, multi-user ready
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    preferences JSONB DEFAULT '{}',
    voice_settings JSONB DEFAULT '{"voice_id": "pNInz6obpgDQGcFmaJgB", "transform": true}',
    notification_settings JSONB DEFAULT '{"email": true, "push": false, "quiet_hours": {"start": "22:00", "end": "08:00"}}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create default user (you)
INSERT INTO users (email, name, timezone) 
VALUES ('user@optimus.local', 'Primary User', 'America/Los_Angeles')
ON CONFLICT (email) DO NOTHING;

-- =====================================================
-- Life Contexts - Domains of life to balance
-- =====================================================
CREATE TABLE IF NOT EXISTS life_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(20) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3B82F6',
    icon VARCHAR(50),
    priority INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, code)
);

-- Seed default life contexts
INSERT INTO life_contexts (user_id, name, code, description, color, icon) 
SELECT id, 'Work', 'WORK', 'Professional responsibilities and career', '#3B82F6', '💼'
FROM users WHERE email = 'user@optimus.local';

INSERT INTO life_contexts (user_id, name, code, description, color, icon)
SELECT id, 'Health', 'HEALTH', 'Physical and mental wellbeing', '#10B981', '🏃'
FROM users WHERE email = 'user@optimus.local';

INSERT INTO life_contexts (user_id, name, code, description, color, icon)
SELECT id, 'Social', 'SOCIAL', 'Relationships and social activities', '#F59E0B', '👥'
FROM users WHERE email = 'user@optimus.local';

INSERT INTO life_contexts (user_id, name, code, description, color, icon)
SELECT id, 'Growth', 'GROWTH', 'Learning and personal development', '#8B5CF6', '📚'
FROM users WHERE email = 'user@optimus.local';

INSERT INTO life_contexts (user_id, name, code, description, color, icon)
SELECT id, 'Family', 'FAMILY', 'Family responsibilities and time', '#EF4444', '👨‍👩‍👧‍👦'
FROM users WHERE email = 'user@optimus.local';

-- =====================================================
-- Goals - What the user wants to achieve
-- =====================================================
CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    context_id UUID REFERENCES life_contexts(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) DEFAULT 'ACHIEVEMENT', -- ACHIEVEMENT, HABIT, MILESTONE, PROJECT
    status VARCHAR(50) DEFAULT 'ACTIVE', -- ACTIVE, PAUSED, COMPLETED, ABANDONED
    priority INTEGER DEFAULT 5, -- 1-10
    target_date DATE,
    completed_date DATE,
    progress_percentage INTEGER DEFAULT 0,
    success_metrics JSONB DEFAULT '[]',
    blockers JSONB DEFAULT '[]',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_goals_user_status ON goals(user_id, status);
CREATE INDEX idx_goals_target_date ON goals(target_date);

-- =====================================================
-- Habits - Recurring behaviors to track
-- =====================================================
CREATE TABLE IF NOT EXISTS habits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES goals(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    frequency VARCHAR(50) NOT NULL, -- DAILY, WEEKLY, MONTHLY
    target_count INTEGER DEFAULT 1,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    total_completions INTEGER DEFAULT 0,
    reminder_time TIME,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- Events - Calendar items and scheduled activities
-- =====================================================
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    context_id UUID REFERENCES life_contexts(id) ON DELETE SET NULL,
    external_id VARCHAR(255), -- ID from Google Calendar, Outlook, etc.
    source VARCHAR(50), -- GOOGLE_CALENDAR, OUTLOOK, MANUAL, GENERATED
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    all_day BOOLEAN DEFAULT false,
    recurring_rule TEXT, -- iCal RRULE format
    attendees JSONB DEFAULT '[]',
    reminders JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'CONFIRMED', -- TENTATIVE, CONFIRMED, CANCELLED
    category VARCHAR(50), -- MEETING, FOCUS, PERSONAL, SOCIAL, HEALTH
    energy_level INTEGER, -- 1-5, how much energy this requires
    preparation_time INTEGER, -- minutes needed to prepare
    travel_time INTEGER, -- minutes of travel
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(external_id, source)
);

CREATE INDEX idx_events_user_time ON events(user_id, start_time, end_time);
CREATE INDEX idx_events_source ON events(source, external_id);

-- =====================================================
-- Tasks - Things to do
-- =====================================================
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id UUID REFERENCES goals(id) ON DELETE SET NULL,
    context_id UUID REFERENCES life_contexts(id) ON DELETE SET NULL,
    external_id VARCHAR(255), -- ID from Todoist, Notion, etc.
    source VARCHAR(50), -- TODOIST, NOTION, MANUAL, GENERATED
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    priority INTEGER DEFAULT 5, -- 1-10
    due_date TIMESTAMP WITH TIME ZONE,
    completed_date TIMESTAMP WITH TIME ZONE,
    estimated_minutes INTEGER,
    actual_minutes INTEGER,
    energy_required INTEGER, -- 1-5
    focus_required INTEGER, -- 1-5
    tags TEXT[],
    dependencies UUID[], -- Other task IDs
    recurrence_rule TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);

-- =====================================================
-- Interactions - Communications and messages
-- =====================================================
CREATE TABLE IF NOT EXISTS interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    context_id UUID REFERENCES life_contexts(id) ON DELETE SET NULL,
    external_id VARCHAR(255), -- Email ID, message ID, etc.
    source VARCHAR(50) NOT NULL, -- GMAIL, OUTLOOK, SLACK, WHATSAPP, SMS
    type VARCHAR(50) NOT NULL, -- EMAIL, MESSAGE, CALL, MEETING_NOTES
    direction VARCHAR(10), -- INBOUND, OUTBOUND
    counterpart_name VARCHAR(255),
    counterpart_email VARCHAR(255),
    subject VARCHAR(500),
    preview TEXT,
    content TEXT, -- Encrypted
    sentiment VARCHAR(50), -- POSITIVE, NEUTRAL, NEGATIVE, URGENT
    importance_score INTEGER, -- 1-10
    requires_response BOOLEAN DEFAULT false,
    response_deadline TIMESTAMP WITH TIME ZONE,
    response_drafted BOOLEAN DEFAULT false,
    response_sent BOOLEAN DEFAULT false,
    thread_id VARCHAR(255),
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    interaction_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_interactions_user_time ON interactions(user_id, interaction_time);
CREATE INDEX idx_interactions_response ON interactions(user_id, requires_response, response_sent);

-- =====================================================
-- Suggestions - AI-generated recommendations
-- =====================================================
CREATE TABLE IF NOT EXISTS suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- TASK, EVENT, RESPONSE, DECISION, OPTIMIZATION
    category VARCHAR(50), -- SCHEDULING, PRODUCTIVITY, SOCIAL, HEALTH, FINANCE
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    reasoning TEXT, -- Why this suggestion was made
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    priority INTEGER DEFAULT 5,
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, ACCEPTED, REJECTED, EXPIRED
    suggested_actions JSONB DEFAULT '[]', -- Structured actions to take
    context_data JSONB DEFAULT '{}', -- Related IDs and context
    expires_at TIMESTAMP WITH TIME ZONE,
    presented_at TIMESTAMP WITH TIME ZONE,
    responded_at TIMESTAMP WITH TIME ZONE,
    response VARCHAR(50), -- ACCEPTED, REJECTED, MODIFIED, DEFERRED
    user_feedback TEXT,
    outcome_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_suggestions_user_status ON suggestions(user_id, status);
CREATE INDEX idx_suggestions_expires ON suggestions(expires_at);

-- =====================================================
-- Assistant Interactions - Track all assistant usage
-- =====================================================
CREATE TABLE IF NOT EXISTS assistant_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    query_type VARCHAR(50), -- PLANNING, DRAFTING, DECISION, ANALYSIS, GENERAL
    mode VARCHAR(50), -- AUTO, WORK, LIFE, SOCIAL, GROWTH
    context JSONB DEFAULT '{}',
    agents_used TEXT[],
    tools_used TEXT[],
    response TEXT,
    response_format VARCHAR(50), -- TEXT, STRUCTURED, ACTIONS
    confidence_score DECIMAL(3,2),
    processing_time_ms INTEGER,
    tokens_used INTEGER,
    suggestion_ids UUID[], -- Related suggestions created
    user_rating INTEGER, -- 1-5 stars
    user_feedback TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assistant_interactions_user ON assistant_interactions(user_id, created_at);

-- =====================================================
-- Time Blocks - For time boxing and scheduling
-- =====================================================
CREATE TABLE IF NOT EXISTS time_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    context_id UUID REFERENCES life_contexts(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL, -- FOCUS, BUFFER, BREAK, ROUTINE, FLEXIBLE
    title VARCHAR(255) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_locked BOOLEAN DEFAULT false, -- Can't be moved by optimization
    energy_level INTEGER, -- 1-5, expected energy
    actual_activity TEXT, -- What actually happened
    quality_score INTEGER, -- 1-5, how well it went
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_time_blocks_user_time ON time_blocks(user_id, start_time);

-- =====================================================
-- Metrics - Track patterns and performance
-- =====================================================
CREATE TABLE IF NOT EXISTS life_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    context_id UUID REFERENCES life_contexts(id) ON DELETE SET NULL,
    metric_type VARCHAR(50) NOT NULL, -- PRODUCTIVITY, BALANCE, HEALTH, SOCIAL, MOOD
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL,
    metric_unit VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date, metric_type, metric_name)
);

CREATE INDEX idx_life_metrics_user_date ON life_metrics(user_id, date);

-- =====================================================
-- Relationships - Track important people
-- =====================================================
CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(50), -- FAMILY, FRIEND, COLLEAGUE, MENTOR, CLIENT
    email VARCHAR(255),
    phone VARCHAR(50),
    birthday DATE,
    last_contact DATE,
    contact_frequency_days INTEGER, -- Target days between contacts
    notes TEXT,
    importance INTEGER DEFAULT 5, -- 1-10
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_relationships_user ON relationships(user_id);

-- =====================================================
-- Functions and Triggers
-- =====================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_goals_updated_at BEFORE UPDATE ON goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Views for Common Queries
-- =====================================================

-- Today's agenda view
CREATE OR REPLACE VIEW today_agenda AS
SELECT 
    u.id as user_id,
    'event' as item_type,
    e.id as item_id,
    e.title,
    e.start_time,
    e.end_time,
    lc.name as context,
    lc.color,
    e.location,
    e.energy_level
FROM users u
JOIN events e ON u.id = e.user_id
LEFT JOIN life_contexts lc ON e.context_id = lc.id
WHERE DATE(e.start_time) = CURRENT_DATE
UNION ALL
SELECT 
    u.id as user_id,
    'task' as item_type,
    t.id as item_id,
    t.title,
    t.due_date as start_time,
    t.due_date as end_time,
    lc.name as context,
    lc.color,
    NULL as location,
    t.energy_required as energy_level
FROM users u
JOIN tasks t ON u.id = t.user_id
LEFT JOIN life_contexts lc ON t.context_id = lc.id
WHERE DATE(t.due_date) = CURRENT_DATE AND t.status != 'COMPLETED'
ORDER BY start_time;

-- Active goals summary
CREATE OR REPLACE VIEW active_goals_summary AS
SELECT 
    g.user_id,
    g.id,
    g.title,
    g.type,
    g.progress_percentage,
    g.target_date,
    lc.name as context,
    lc.color,
    COUNT(DISTINCT t.id) as total_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'COMPLETED') as completed_tasks
FROM goals g
LEFT JOIN life_contexts lc ON g.context_id = lc.id
LEFT JOIN tasks t ON g.id = t.goal_id
WHERE g.status = 'ACTIVE'
GROUP BY g.user_id, g.id, g.title, g.type, g.progress_percentage, 
         g.target_date, lc.name, lc.color;

-- =====================================================
-- Initial Data and Permissions
-- =====================================================

-- Grant permissions (uncomment and adjust based on your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO optimus_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO optimus_user;
-- GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO optimus_user;