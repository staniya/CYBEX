CREATE SCHEMA shinnosuketaniya;
CREATE TABLE shinnosuketaniya.groups (
    id TEXT,
    name TEXT,
    channel_id TEXT,
    access_hash TEXT
);
CREATE TABLE shinnosuketaniya.statistics (
    user_id TEXT,
    group_id TEXT,
    count_text INTEGER,
    count_mention INTEGER,
    count_hashtag INTEGER,
    count_bot_command INTEGER,
    count_url INTEGER,
    count_email INTEGER,
    count_photo INTEGER,
    count_sticker INTEGER,
    count_gif INTEGER,
    count_video INTEGER,
    count_voice INTEGER,
    joindate INTEGER,
    count_document INTEGER
);
CREATE TABLE shinnosuketaniya.users (
    id TEXT,
    first_name TEXT,
    last_name TEXT,
    username TEXT
);
