CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  spreadsheet_id TEXT NOT NULL UNIQUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL,
  group_id INTEGER NOT NULL,
  student_chat_id TEXT NULL,
  father_chat_id TEXT NULL,
  mother_chat_id TEXT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
  UNIQUE(full_name, group_id)
);

CREATE TABLE IF NOT EXISTS subjects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id INTEGER NOT NULL,
  sheet_name TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
  UNIQUE(group_id, sheet_name)
);

CREATE TABLE IF NOT EXISTS grade_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id INTEGER NOT NULL,
  student_full_name TEXT NOT NULL,
  subject TEXT NOT NULL,
  lesson_type TEXT NULL,
  lesson_date TEXT NULL,
  column_letter TEXT NULL,
  row_index INTEGER NULL,
  old_value TEXT NULL,
  new_value TEXT NULL,
  gsheet_edit_timestamp TEXT NULL,
  processed INTEGER NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_grade_events_processed ON grade_events(processed);
CREATE INDEX IF NOT EXISTS idx_students_group_id ON students(group_id);
CREATE INDEX IF NOT EXISTS idx_students_full_name ON students(full_name);
